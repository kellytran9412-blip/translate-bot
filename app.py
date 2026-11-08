import os
import logging
from flask import Flask, request, abort

from google import genai
from google.genai import types
from google.genai.errors import APIError

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Tái sử dụng client để giữ connection pool (Keep-Alive)
gemini_client = genai.Client(
    api_key=GEMINI_KEY,
    http_options={"api_version": "v1beta"}
)

line_configuration = Configuration(access_token=LINE_TOKEN)
line_api_client = ApiClient(line_configuration)
line_bot_api = MessagingApi(line_api_client)
line_handler = WebhookHandler(LINE_SECRET)

TRANSLATION_INSTRUCTION = """Chuyên gia dịch thuật song ngữ Việt - Trung Phồn thể (Đài Loan):
- Việt -> Trung Phồn thể (Đài Loan).
- Trung -> Việt.
- Dịch chuẩn ngữ cảnh công ty, xưởng sản xuất, nhân sự.
- Giữ nguyên tên riêng, số, mã, ngày tháng.
- Chỉ trả lời duy nhất bản dịch, không thêm chú thích."""

# Cấu hình tối ưu tốc độ
GEN_CONFIG = types.GenerateContentConfig(
    system_instruction=TRANSLATION_INSTRUCTION,
    max_output_tokens=1500,
    temperature=0.1,
    thinking_config=types.ThinkingConfig(thinking_budget=0)  # Tắt suy nghĩ ngầm
)

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    if not signature:
        abort(400)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK", 200

@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text.strip()
    if not user_text:
        return

    try:
        response = gemini_client.models.generate_content(
            model=MODEL,
            contents=user_text,
            config=GEN_CONFIG
        )

        translated_text = (response.text or "").strip()
        if not translated_text:
            return

        if len(translated_text) > 5000:
            translated_text = translated_text[:4990] + "\n..."

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=translated_text)]
            )
        )

    except (APIError, Exception):
        logger.exception("Error processing translation")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
