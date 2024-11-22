import os

import asyncio
import logging
from crewai import Agent, Task, Crew
from crewai_tools import tool, BaseTool
from humanlayer import ContactChannel, EmailContactChannel, HumanLayer, FunctionCallSpec
from pydantic import BaseModel
from typing import Optional, List, Any

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


#
#
async def run_async(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn, *args)



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

        # TODO - humanlayer needs a more native crew integration
        class SafeTool(BaseTool):
            tool: Any
            def __init__(self, t):
                super().__init__(
                    name=t.name,
                    description=t.description,
                    args_schema=t.args_schema,
                    tool=t,
                )

            def _run(
                self,
                *args: Any,
                **kwargs: Any,
            ) -> Any:
                result = hl.fetch_approval(
                    FunctionCallSpec(
                        fn=self.name,
                        kwargs=kwargs,
                    )
                )
                if result.as_completed().approved is True:
                    try:
                        return self.tool.stripe_api.run(self.tool.method, *args, **kwargs)
                    except Exception as e:
                        return f"Error calling tool: {str(e)}"
                else:
                    return f"User denied tool with feedback:{result.as_completed().comment}"

        safe_tools += [SafeTool(stripe_tool)]

    return safe_tools + readonly_tools


async def process_email(email: EmailPayload):
    hl = HumanLayer(
        contact_channel=ContactChannel(
            email=EmailContactChannel(
                address=email.from_address,
                context_about_user="the user who made the request",
                experimental_in_reply_to_message_id=email.message_id,
                experimental_references_message_id=email.message_id,
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
    return await run_async(hl.human_as_tool(), f"Task completed: {ret}")

