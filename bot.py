import os
import json
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
APP_LEVEL_TOKEN = os.getenv("APP_LEVEL_TOKEN")

client = WebClient(token=SLACK_BOT_TOKEN)
socket_client = SocketModeClient(app_token=APP_LEVEL_TOKEN, web_client=client)

CONFIG_FILE = "daily_post.json"
TEMP_FILE = "daily_post_temp.json"

def save_temp(data):
    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_temp():
    if not os.path.exists(TEMP_FILE):
        return None
    with open(TEMP_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def clear_temp():
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clear_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)

def handle_command(text, channel):
    if text.startswith("!毎日投稿停止"):
        clear_config()
        clear_temp()
        client.chat_postMessage(channel=channel, text="✅ 毎日投稿を停止しました。")
    
    elif text.startswith("!毎日投稿設定"):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            client.chat_postMessage(channel=channel, text="❌ 使用方法: `!毎日投稿設定 HH:MM #channel`")
            return
        time_str, channel_name = parts[1], parts[2]
        save_temp({"time": time_str, "channel": channel_name})
        client.chat_postMessage(channel=channel, text="✅ 投稿時間とチャンネルを設定しました。\n続けて `!毎日投稿内容 メッセージ内容` を送信してください。")
    
    elif text.startswith("!毎日投稿内容"):
        temp = load_temp()
        if not temp:
            client.chat_postMessage(channel=channel, text="⚠️ 先に `!毎日投稿設定` を使用してください。")
            return
        message = text[len("!毎日投稿内容 "):].strip()
        if not message:
            client.chat_postMessage(channel=channel, text="❌ 投稿内容が空です。")
            return
        config = {
            "time": temp["time"],
            "channel": temp["channel"],
            "message": message
        }
        save_config(config)
        clear_temp()
        client.chat_postMessage(
            channel=channel,
            text=f"✅ 毎日 `{config['time']}` に `{config['channel']}` へ以下の内容を投稿します。\n---\n{message}"
        )

@socket_client.socket_mode_request_listeners.append
def handle_events(payload: SocketModeRequest):
    print("イベント受信:", payload.type, payload.payload)
    if payload.type == "events_api":
        event = payload.payload.get("event", {})
        if event.get("type") == "message" and "bot_id" not in event:
            handle_command(event.get("text", ""), event.get("channel"))
        socket_client.send_socket_mode_response(SocketModeResponse(envelope_id=payload.envelope_id))

if __name__ == "__main__":
    socket_client.connect()
    print("Bot 起動中...")
    import time
    while True:
        time.sleep(1)

