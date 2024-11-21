from fastapi import BackgroundTasks, FastAPI
import logging
from app.agent import EmailPayload, process_email
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/api/v1/webhook/email")
async def email_webhook(
    email: EmailPayload,
    background_tasks: BackgroundTasks,
):
    logger.info(f"Received email: {email}")
    background_tasks.add_task(process_email, email)
    return {"message": "Email received"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)