import os
import logging
from flask import Flask, request, abort

# Google GenAI SDK
from google import genai
from google.genai import types
from google.genai.errors import APIError

# LINE Bot SDK v3
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

# 1. CẤU HÌNH BIẾN MÔI TRƯỜNG
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

if not all([GEMINI_KEY, LINE_TOKEN, LINE_SECRET]):
    raise RuntimeError(
        "Thiếu GEMINI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN hoặc LINE_CHANNEL_SECRET"
    )

# 2. KHỞI TẠO CLIENTS
# api_version='v1beta' để hỗ trợ system_instruction mà không bị lỗi 400
gemini_client = genai.Client(
    api_key=GEMINI_KEY,
    http_options={"api_version": "v1beta"}
)

line_configuration = Configuration(access_token=LINE_TOKEN)
line_handler = WebhookHandler(LINE_SECRET)

# 3. PROMPT DỊCH THUẬT (SYSTEM INSTRUCTION)
TRANSLATION_INSTRUCTION = """
Bạn là chuyên gia dịch thuật tiếng Việt và tiếng Trung Phồn thể (Đài Loan).

QUY TẮC:
1. Nếu văn bản là tiếng Việt: Dịch sang tiếng Trung Phồn thể (繁體中文).
2. Nếu văn bản là tiếng Trung: Dịch sang tiếng Việt.
3. Sử dụng từ ngữ tự nhiên, phổ biến tại Đài Loan.
4. Dịch chính xác thuật ngữ công ty, nhà máy, nhân sự, lao động và hành chính.
5. Giữ nguyên tên riêng, mã số, ngày tháng, số tiền và định dạng xuống dòng khi phù hợp.
6. Không tự ý thêm hoặc bỏ nội dung.
7. Chỉ trả về bản dịch.
8. Không giải thích, không thêm tiêu đề.
"""

@app.route("/", methods=["GET"])
def index():
    return f"LINE Translation Bot ({MODEL}) is running!"

# 4. LINE WEBHOOK ROUTE
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

    with ApiClient(line_configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        try:
            response = gemini_client.models.generate_content(
                model=MODEL,
                contents=user_text,
                config=types.GenerateContentConfig(
                    system_instruction=TRANSLATION_INSTRUCTION,
                    max_output_tokens=3000,
                    temperature=0.2
                )
            )

            translated_text = (response.text or "").strip()
            if not translated_text:
                translated_text = "❌ Không nhận được bản dịch."

            # Giới hạn 5000 ký tự của LINE
            if len(translated_text) > 5000:
                translated_text = translated_text[:4990] + "\n..."

            reply_msg = translated_text

        except APIError as e:
            logger.exception("Gemini API error")
            err_str = str(e).lower()
            if "404" in err_str or "not found" in err_str:
                reply_msg = "❌ Không tìm thấy model Gemini. Vui lòng kiểm tra lại tên model."
            elif "429" in err_str or "quota" in err_str:
                reply_msg = "❌ API đang quá tải hoặc hết hạn mức sử dụng (Quota)."
            elif "400" in err_str and "key" in err_str:
                reply_msg = "❌ GEMINI_API_KEY không hợp lệ."
            else:
                reply_msg = "❌ Lỗi dịch thuật từ AI. Vui lòng thử lại sau."

        except Exception:
            logger.exception("Unexpected error")
            reply_msg = "❌ Hệ thống xảy ra lỗi. Vui lòng thử lại sau."

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_msg)]
            )
        )

# 6. KHỞI CHẠY SERVER CỤC BỘ
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
