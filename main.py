from fastapi import FastAPI
import requests
import os
from dotenv import load_dotenv

load_dotenv()


SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Slack Summary API is running"}

@app.get("/post_message")
def post_message():
    message = {
        "channel": SLACK_CHANNEL_ID,
        "text": "✅ Slackからのテストメッセージ（FastAPIより送信）"
    }
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://slack.com/api/chat.postMessage", json=message, headers=headers)
    result = response.json()
    return result
