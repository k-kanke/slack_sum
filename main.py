from fastapi import FastAPI, Request
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# エンドポイント作成
@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.json()

    # Slackの初回URL検証
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}

    # イベント処理
    event = body.get("event", {})
    if event.get("type") == "app_mention":
        text = event.get("text", "")
        channel = event.get("channel")
        user = event.get("user")

        # 本日のメッセージ取得 → Difyで要約 → Slackに返信
        slack_token = os.environ["SLACK_BOT_TOKEN"]
        channel_id = channel
        dify_key = os.environ["DIFY_API_KEY"]
        dify_app_id = os.environ["DIFY_APP_ID"]

        messages = get_today_messages(slack_token, channel_id)
        summary = summarize_with_dify(dify_key, dify_app_id, messages, user)
        post_to_slack(slack_token, channel_id, f"<@{user}> さん、要約はこちら👇\n\n{summary}")

    return {"ok": True}

# 本番では使用しないが、デバッグ用に残す
@app.get("/slack/summary")
def generate_summary():
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    channel_id = os.environ["SLACK_CHANNEL_ID"]
    dify_key = os.environ["DIFY_API_KEY"]
    dify_app_id = os.environ["DIFY_APP_ID"]

    messages = get_today_messages(slack_token, channel_id)
    summary = summarize_with_dify(dify_key, dify_app_id, messages)
    post_to_slack(slack_token, channel_id, summary)

    return {"message": "要約完了", "summary": summary}


# Slack投稿取得
def get_today_messages(slack_token, channel_id):
    import requests, datetime, time

    headers = {"Authorization": f"Bearer {slack_token}"}
    today = datetime.datetime.now()
    start_of_day = datetime.datetime(today.year, today.month, today.day)
    start_ts = time.mktime(start_of_day.timetuple())

    res = requests.get("https://slack.com/api/conversations.history", params={
        "channel": channel_id,
        "oldest": start_ts,
        "limit": 1000
    }, headers=headers)

    messages = res.json().get("messages", [])
    texts = [msg["text"] for msg in messages if "subtype" not in msg]
    return "\n".join(reversed(texts))


# Dify要約
def summarize_with_dify(dify_api_key, app_id, text, user):
    import requests, json

    headers = {
        "Authorization": f"Bearer {dify_api_key}",
        "Content-Type": "application/json"
    }

    res = requests.post(
        f"https://api.dify.ai/v1/chat-messages",
        headers=headers,
        json={
            "inputs": {},
            "query": text,
            "response_mode": "blocking",
            "conversation_id": None,
            "app_id": app_id,
            "user": user
        }
    )

    try:
        return res.json()["answer"]
    except Exception as e:
        print("Dify Error: ", res.text)
        return f"要約失敗: {res.text}"

# Slackに送信
def post_to_slack(slack_token, channel_id, summary_text):
    import requests
    headers = {"Authorization": f"Bearer {slack_token}"}
    res = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json={
        "channel": channel_id,
        "text": f"📌 *本日の要約*\n{summary_text}"
    })
    return res.json()
