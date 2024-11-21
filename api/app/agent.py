import os

from crewai import Agent, Crew, Task
import asyncio
import logging
from crewai_tools import tool, BaseTool
from humanlayer import ContactChannel, EmailContactChannel, HumanLayer, FunctionCallSpec
from pydantic import BaseModel
from typing import Optional, List, Any

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
#
#
# async def async_process_email(email: EmailPayload):
#     return await run_async(process_email, email)
#



from stripe_agent_toolkit.crewai.toolkit import StripeAgentToolkit
from crewai import Agent, Task, Crew


def make_stripe_tools_safer(hl: HumanLayer):
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
                "invoinces": {
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
    for tool in scary_tools.get_tools():

        class SafeTool(BaseTool):
            def __init__(self, t):
                super().__init__(
                    name=t.name,
                    description=t.description,
                    args_schema=t.args_schema,
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
                    return tool.stripe_api.run(tool.method, *args, **kwargs)
                else:
                    raise Exception(f"User denied tool with feedback:{result.as_completed().comment}")

        safe_tools += [SafeTool(tool)]

    return safe_tools + readonly_tools

async def process_email(email: EmailPayload):

    hl = HumanLayer(
        contact_channel=ContactChannel(
            email=EmailContactChannel(
                address=email.from_address,
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
        verbose=True,
    )

    task = Task(
        name="Process Email",
        description=f"""
        {f"The previous thread is: {[x.model_dump_json() for x in email.previous_thread]}" if email.previous_thread else ""}
        
        
        Handle this email: 

        From: {email.from_address}
        To: {email.to_address}
        Subject: {email.subject}
        
        
        {email.body}
        

        """,
        agent=email_processor,
        tools=[
            tool(hl.human_as_tool()),
            *make_stripe_tools_safer(hl)
        ],
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
