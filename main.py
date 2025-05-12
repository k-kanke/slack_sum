from fastapi import FastAPI, Request, Header
import os, hmac, hashlib, asyncio
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# 処理済みイベントID記録用セット
PROCESSED_EVENTS = set()

# エンドポイント作成
@app.post("/slack/events")
async def slack_events(
    request: Request, 
    x_slack_signature: str = Header(...), 
    x_slack_request_timestamp: str = Header(...),
    x_slack_retry_num: str = Header(None)
):
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")

    # Slack署名検証
    slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
    basestring = f"v0:{x_slack_request_timestamp}:{body_str}"
    my_signature = "v0=" + hmac.new(slack_signing_secret.encode(), basestring.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(my_signature, x_slack_signature):
        return {"error": "invalid signature"}
    
    # リトライチェック
    if x_slack_retry_num is not None:
        return {"status": "ok (retry ignored)"}
    
    # JSONとして解析
    payload = await request.json()

    # Slackの初回URL検証
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
    
    # 重複イベントチェック
    event_id = payload.get("event_id")
    if event_id in PROCESSED_EVENTS:
        return {"status": "ok (already processed)"}
    PROCESSED_EVENTS.add(event_id)

    # メンションイベント検知時の非同期処理
    if payload.get("event", {}).get("type") == "app_mention":
        asyncio.create_task(mention_event(payload))

    return {"status": "ok"}

# 非同期で実行する処理本体
async def mention_event(payload):
    user = payload["event"].get("user")
    channel = payload["event"].get("channel")

    # メッセージ取得・要約・投稿
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    dify_key = os.environ["DIFY_API_KEY"]
    dify_app_id = os.environ["DIFY_APP_ID"]

    text = get_today_messages(slack_token, channel)
    summary = summarize_with_dify(dify_key, dify_app_id, text, user)
    post_to_slack(slack_token, channel, f"<@{user}> 要約です！\n{summary}")

    return {"status": "ok"}

# 後で消去（デバッグ用）
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

# 要約をSlackに送信
def post_to_slack(slack_token, channel_id, summary_text):
    import requests
    headers = {"Authorization": f"Bearer {slack_token}"}
    res = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json={
        "channel": channel_id,
        "text": f"📌 *本日の要約*\n{summary_text}"
    })
    return res.json()
