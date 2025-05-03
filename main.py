from fastapi import FastAPI, Query
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

@app.get("/slack/today_summary")
def fetch_today_messages(channel_id: str):
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    oldest = today_start.timestamp()
    latest = (today_start + timedelta(days=1)).timestamp()

    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
    }
    params = {
        "channel": channel_id,
        "oldest": oldest,
        "latest": latest,
        "limit": 1000
    }

    response = requests.get("https://slack.com/api/conversations.history", headers=headers, params=params)
    data = response.json()

    if not data.get("ok"):
        return {"error": data.get("error", "Failed to fetch messages.")}

    messages = data.get("messages", [])
    result = [{"user": m.get("user", ""), "text": m.get("text", ""), "ts": m.get("ts", "")} for m in messages]
    return {"count": len(result), "messages": result}