import os
from fastapi import BackgroundTasks, FastAPI
import logging
from app.agent import EmailPayload, process_email
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI()

ALLOWED_INBOUND_EMAILS = os.getenv("ALLOWED_INBOUND_EMAILS").split(",")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/api/v1/webhook/email")
async def email_webhook(
    email: EmailPayload,
    background_tasks: BackgroundTasks,
):
    # todo - validate webhook signature

    if email.from_address not in ALLOWED_INBOUND_EMAILS:
        logger.warning(f"Email not allowed: {email.from_address}, allowed: {ALLOWED_INBOUND_EMAILS}")
        return {"message": "Email not allowed"}

    logger.info(f"Received email: {email}")
    background_tasks.add_task(process_email, email)
    return {"message": "Email received"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
