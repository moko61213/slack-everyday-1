import os
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

response = client.auth_test()
if response["ok"]:
    print("Botは正しくインストールされています。")
    print("チーム名:", response["team"])
    print("ユーザー名:", response["user"])
else:
    print("Botの認証に失敗しました。")