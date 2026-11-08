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

# 1. BIẾN MÔI TRƯỜNG
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

# Cập nhật model theo khuyến nghị mới nhất từ thông báo API
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

if not all([GEMINI_KEY, LINE_TOKEN, LINE_SECRET]):
    raise RuntimeError("Thiếu GEMINI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN hoặc LINE_CHANNEL_SECRET")

# 2. KHỞI TẠO CLIENT VÀ HANDLER
gemini_client = genai.Client(
    api_key=GEMINI_KEY,
    http_options={"api_version": "v1beta"}
)

line_configuration = Configuration(access_token=LINE_TOKEN)
line_api_client = ApiClient(line_configuration)
line_bot_api = MessagingApi(line_api_client)
line_handler = WebhookHandler(LINE_SECRET)

# 3. PROMPT HỆ THỐNG
TRANSLATION_INSTRUCTION = """Chuyên gia dịch thuật song ngữ Việt - Trung Phồn thể (Đài Loan):
- Việt -> Trung Phồn thể (Đài Loan).
- Trung -> Việt.
- Dịch chuẩn ngữ cảnh công ty, xưởng sản xuất, nhân sự.
- Giữ nguyên tên riêng, số, mã, ngày tháng.
- Chỉ trả lời duy nhất bản dịch, không thêm chú thích."""

@app.route("/", methods=["GET"])
def index():
    return f"LINE Translation Bot ({MODEL}) is running!", 200

# 4. WEBHOOK ROUTE
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    if not signature:
        abort(400)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature")
        abort(400)

    return "OK", 200

# 5. XỬ LÝ TIN NHẮN
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text.strip()
    if not user_text:
        return

    # Danh sách model thử nghiệm
    candidate_models = [MODEL, "gemini-3.8-flash", "gemini-2.5-flash"]
    # Loại bỏ trùng lặp giữ nguyên thứ tự
    models_to_try = list(dict.fromkeys(candidate_models))

    translated_text = ""

    for model_name in models_to_try:
        try:
            config_params = {
                "system_instruction": TRANSLATION_INSTRUCTION,
                "max_output_tokens": 1500,
                "temperature": 0.1,
            }
            # Tắt thinking budget nếu có để tối ưu tốc độ
            if any(ver in model_name for ver in ["2.5", "3."]):
                config_params["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=user_text,
                config=types.GenerateContentConfig(**config_params)
            )

            translated_text = (response.text or "").strip()
            if translated_text:
                break

        except APIError as e:
            err_str = str(e)
            if "429" in err_str or "404" in err_str:
                logger.warning(f"Model {model_name} gặp sự cố (429/404), thử model tiếp theo...")
                continue
            logger.exception(f"Lỗi API ở model {model_name}")
            break
        except Exception:
            logger.exception("Lỗi không xác định")
            break

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

# 6. KHỞI CHẠY SERVER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
