import os
import json
import logging
import time
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from dotenv import load_dotenv

load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
APP_LEVEL_TOKEN = os.getenv("APP_LEVEL_TOKEN")

if not SLACK_BOT_TOKEN or not APP_LEVEL_TOKEN:
    logging.error("環境変数 SLACK_BOT_TOKEN または APP_LEVEL_TOKEN が設定されていません。")
    exit(1)

client = WebClient(token=SLACK_BOT_TOKEN)
socket_client = SocketModeClient(app_token=APP_LEVEL_TOKEN, web_client=client)

CONFIG_FILE = "daily_post.json"
TEMP_FILE = "daily_post_temp.json"


def save_json(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"{file_path} の保存に失敗しました: {e}")


def load_json(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"{file_path} の読み込みに失敗しました: {e}")
        return None


def clear_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logging.error(f"{file_path} の削除に失敗しました: {e}")


def get_channel_id(channel_name):
    """チャンネル名 #general などからチャンネルIDを取得する"""
    if not channel_name.startswith("#"):
        logging.warning("チャンネル名は # で始めてください。")
        return None
    try:
        # Slack APIのconversations_listはページングあり、簡易版
        response = client.conversations_list(types="public_channel,private_channel", limit=1000)
        if not response["ok"]:
            logging.error(f"conversations_list APIエラー: {response['error']}")
            return None
        channels = response["channels"]
        for ch in channels:
            if ch["name"] == channel_name[1:]:
                return ch["id"]
        logging.warning(f"チャンネル名 {channel_name} が見つかりません。")
        return None
    except Exception as e:
        logging.error(f"チャンネルID取得時に例外発生: {e}")
        return None


def post_message(channel_id, text):
    try:
        res = client.chat_postMessage(channel=channel_id, text=text)
        if not res["ok"]:
            logging.error(f"メッセージ送信失敗: {res['error']}")
    except Exception as e:
        logging.error(f"メッセージ送信時に例外発生: {e}")


def handle_command(text, channel):
    text = text.strip()
    try:
        if text.startswith("!毎日投稿停止"):
            clear_file(CONFIG_FILE)
            clear_file(TEMP_FILE)
            post_message(channel, "✅ 毎日投稿を停止しました。")

        elif text.startswith("!毎日投稿設定"):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                post_message(channel, "❌ 使用方法: `!毎日投稿設定 HH:MM #channel`")
                return
            time_str, channel_name = parts[1], parts[2].strip()
            channel_id = get_channel_id(channel_name)
            if not channel_id:
                post_message(channel, f"❌ チャンネル `{channel_name}` が見つかりません。")
                return
            save_json(TEMP_FILE, {"time": time_str, "channel_id": channel_id, "channel_name": channel_name})
            post_message(channel, "✅ 投稿時間とチャンネルを設定しました。\n続けて `!毎日投稿内容 メッセージ内容` を送信してください。")

        elif text.startswith("!毎日投稿内容"):
            temp = load_json(TEMP_FILE)
            if not temp:
                post_message(channel, "⚠️ 先に `!毎日投稿設定` を使用してください。")
                return
            message = text[len("!毎日投稿内容 "):].strip()
            if not message:
                post_message(channel, "❌ 投稿内容が空です。")
                return
            config = {
                "time": temp["time"],
                "channel_id": temp["channel_id"],
                "channel_name": temp.get("channel_name", ""),
                "message": message
            }
            save_json(CONFIG_FILE, config)
            clear_file(TEMP_FILE)
            post_message(
                channel,
                f"✅ 毎日 `{config['time']}` に `{config['channel_name']}` へ以下の内容を投稿します。\n---\n{message}"
            )
    except Exception as e:
        logging.error(f"コマンド処理中に例外発生: {e}")


@socket_client.socket_mode_request_listeners.append
def handle_events(payload: SocketModeRequest):
    logging.debug(f"イベント受信: type={payload.type}")
    try:
        if payload.type == "events_api":
            event = payload.payload.get("event", {})
            if event.get("type") == "message" and "bot_id" not in event:
                handle_command(event.get("text", ""), event.get("channel"))
            socket_client.send_socket_mode_response(SocketModeResponse(envelope_id=payload.envelope_id))
    except Exception as e:
        logging.error(f"イベント処理中に例外発生: {e}")


def main_loop():
    logging.info("Bot 起動中...")
    socket_client.connect()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Bot 終了中...")
        socket_client.disconnect()


if __name__ == "__main__":
    main_loop()


