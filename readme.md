Mailchain
===========


Mailchain is a language model agent that performs various tasks over email, including interacting with Stripe and Coinbase APIs.

Overview
---------

I am super interested in "alternative interfaces" for language models, like slack, email, and SMS,
and wanted to explore what would be a good UX for an an agent that operates over email. 

If you've followed me for a while, you know I'm also very bullish on incorporating
human review into AI Agents so they can be given bigger better tasks.

Since there are some very cool new SDKs just launched from [stripe](https://docs.stripe.com/agents) and [coinbase](https://github.com/coinbase/coinbase-sdk-ai-agent-sample),
I thought it would be super cool to see how we could use these to build an agent that interacts with these APIs. over email.

At the end of the day, we're completing a core loop:

- craft a task in natural language, e.g. "invoice joe for $100" or  "buy $1000 of BTC" 
- send that task to an "agent inbox" via email
- an agent prepares a tool call, then emails the requester for approval 
- the user responds to the email in natural language, either approving or giving feedback
- upon approval the task is completed

If there are any ambiguities or questions, I wanted the agent to be able to ask follow up questions via email.

Stack
----

- Python FastAPI
- Agent SDKs from Stripe and Coinbase
- CrewAI agent for processing
- HumanLayer for agent->human communication over email

Architecture
----

A more detailed architecture diagram:

![Architecture Diagram](./docs/images/architecture.png)


And an example of a conversation flow:

![Conversation Flow](./docs/images/workflow.png)

