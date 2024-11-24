import asyncio
import logging
import os
from typing import Optional, List, Any, Annotated

from crewai import Agent, Task, Crew
from crewai_tools import tool, BaseTool
from humanlayer import ContactChannel, EmailContactChannel, HumanLayer
from pydantic import BaseModel
from stripe_agent_toolkit.crewai.toolkit import StripeAgentToolkit

logger = logging.getLogger(__name__)


class EmailMessage(BaseModel):
    from_address: str
    to_address: list[str]
    cc_address: list[str]
    subject: str
    content: str
    datetime: str


class EmailPayload(BaseModel):
    from_address: str
    to_address: str
    subject: str
    body: str
    message_id: str
    previous_thread: Optional[List[EmailMessage]] = None
    raw_email: str


INJECT_THOUGHTS = True


async def run_async(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn, *args)


def make_safe_tool(hl: HumanLayer, stripe_tool: Any):
    def _tool(
        thought: Annotated[ str, "a description of why this action makes " # noqa
                                 "sense, and the steps you took to this point"],
        *args,
        **kwargs,
    ):
        return stripe_tool.stripe_api.run(stripe_tool.method, *args, **kwargs)

    _tool.__name__ = stripe_tool.name
    _tool.__doc__ = stripe_tool.description

    # welcome to mypy where everything's made up and the types don't matter
    for k, v in stripe_tool.args_schema.__annotations__.items():
        _tool.__annotations__[k] = v

    if not INJECT_THOUGHTS:
        del _tool.__annotations__["thought"]

    return hl.require_approval()(_tool)


def stripe_tools_with_approval_guardrails(hl: HumanLayer) -> list[BaseTool]:
    """
    wrapper around stripe agent toolkit

    take the non-read-only tools and wrap them in a function that will ask for approval before running

    then return a list of the read-only tools as-is plus the wrapped tools
    """
    readonly_tools = StripeAgentToolkit(
        secret_key=os.getenv("STRIPE_SECRET_KEY"),
        configuration={
            "actions": {
                "payment_links": {
                    "read": True,
                },
                "customers": {
                    "read": True,
                },
                "invoices": {
                    "read": True,
                },
                "products": {
                    "read": True,
                },
                "prices": {
                    "read": True,
                },
            }
        },
    ).get_tools()

    scary_tools = StripeAgentToolkit(
        secret_key=os.getenv("STRIPE_SECRET_KEY"),
        configuration={
            "actions": {
                "payment_links": {
                    "create": True,
                    "update": True,
                },
                "invoices": {
                    "create": True,
                    "update": True,
                },
                "customers": {
                    "create": True,
                    "update": True,
                },
                "products": {
                    "create": True,
                    "update": True,
                },
                "prices": {
                    "create": True,
                    "update": True,
                },
            }
        },
    )

    safe_tools: list[BaseTool] = []
    for stripe_tool in scary_tools.get_tools():


        safe_tools += [tool(make_safe_tool(hl, stripe_tool))]

    return safe_tools + readonly_tools

async def process_email(email: EmailPayload):
    hl = HumanLayer(
        run_id=f"mailcrew-{email.message_id[1:5]}",
        contact_channel=ContactChannel(
            email=EmailContactChannel.in_reply_to(
                from_address=email.from_address,
                subject=email.subject,
                message_id=email.message_id,
            )
        )
    )

    email_processor = Agent(
        role="Email Assistant",
        goal="Process incoming emails efficiently and accurately",
        backstory="""You are an expert at processing and analyzing email content. 
        You understand email structure, can extract key information, and make 
        intelligent decisions about which tools to call.
        
        NEVER respond directly to the user, ONLY use tools, forever, to interact with the user
        
        Before creating any object, always check to see if it already
        exists.
        """,
        tools=[tool(hl.human_as_tool()), *stripe_tools_with_approval_guardrails(hl)],
        verbose=True,
    )

    task_description = f"""
        {f"The previous thread is: {[x.model_dump_json() for x in email.previous_thread]}" if email.previous_thread else ""}
        
        
        Handle this email: 

        From: {email.from_address}
        To: {email.to_address}
        Subject: {email.subject}
        
        
        {email.body}
        

        """
    task = Task(
        name="Process Email",
        description=task_description,
        agent=email_processor,
        expected_output="the tool to call",
    )

    crew = Crew(
        name="Email Processing Crew",
        tasks=[task],
    )

    await crew.kickoff_async()
    ret = task.output.raw
    logger.info(f"Task completed: {ret}")
    return await run_async(hl.human_as_tool(), f"Task result: {ret}")

