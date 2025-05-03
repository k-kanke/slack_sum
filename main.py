from fastapi import FastAPI
from typing import Optional
from datetime import datetime

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Slack Summary API is running"}

@app.get("/slack/today_summary")
def fetch_summary(channel_id: Optional[str] = None):
    #仮
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "channel_id": channel_id,
        "date": today,
        "summary": "This is a placeholder summary for testing."
    }
