import os
import json
from slack_sdk import WebClient

# GitHub Actions上では環境変数のみを使い、.envは読み込まない
if os.getenv("GITHUB_ACTIONS") != "true":
    from dotenv import load_dotenv
    load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
if not SLACK_BOT_TOKEN:
    print("Error: SLACK_BOT_TOKENが設定されていません。")
    exit(1)

client = WebClient(token=SLACK_BOT_TOKEN)
CONFIG_FILE = "daily_post.json"

def post_daily_message():
    if not os.path.exists(CONFIG_FILE):
        print("投稿設定がありません。")
        return
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    channel = config.get("channel")
    message = config.get("message")
    if not channel or not message:
        print("チャンネルまたはメッセージが設定されていません。")
        return
    response = client.chat_postMessage(channel=channel, text=message)
    if response["ok"]:
        print(f"メッセージを投稿しました: {channel}")
    else:
        print(f"投稿に失敗しました: {response['error']}")

if __name__ == "__main__":
    post_daily_message()
