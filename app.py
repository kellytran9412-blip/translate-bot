import os
import logging
from flask import Flask, request, abort
from google import genai
from google.genai import types
from google.genai.errors import APIError
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. CẤU HÌNH BIẾN MÔI TRƯỜNG
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

# Mặc định dùng gemini-2.5-flash cho tốc độ phản hồi nhanh
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

if not all([GEMINI_KEY, LINE_TOKEN, LINE_SECRET]):
    raise RuntimeError(
        "Thiếu GEMINI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN "
        "hoặc LINE_CHANNEL_SECRET"
    )

# 2. KHỞI TẠO GOOGLE GENAI CLIENT
client = genai.Client(api_key=GEMINI_KEY)

# 3. KHỞI TẠO LINE BOT
line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# 4. PROMPT DỊCH THUẬT (SYSTEM INSTRUCTION)
TRANSLATION_INSTRUCTION = """
Bạn là chuyên gia dịch thuật tiếng Việt và tiếng Trung Phồn thể (Đài Loan).

QUY TẮC:
1. Nếu văn bản là tiếng Việt:
   Dịch sang tiếng Trung Phồn thể (繁體中文).
2. Nếu văn bản là tiếng Trung:
   Dịch sang tiếng Việt.
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

# 5. LINE WEBHOOK
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    if not signature:
        abort(400)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature")
        abort(400)

    return "OK", 200

# 6. XỬ LÝ TIN NHẮN
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip()

    if not user_text:
        return

    try:
        # Gọi Gemini API với system_instruction và giới hạn token
        response = client.models.generate_content(
            model=MODEL,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=TRANSLATION_INSTRUCTION,
                max_output_tokens=3000,
                temperature=0.2  # Giảm nhiệt độ để bản dịch chính xác, sát nghĩa
            )
        )

        translated_text = (response.text or "").strip()

        if not translated_text:
            translated_text = "❌ Không nhận được bản dịch."

        # Giới hạn ký tự tin nhắn của LINE
        if len(translated_text) > 5000:
            translated_text = translated_text[:4990] + "\n..."

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=translated_text)
        )

    except APIError as e:
        logger.exception("Gemini API error")
        error_msg = str(e)

        if "404" in error_msg or "not found" in error_msg.lower():
            msg = (
                "❌ Không tìm thấy model Gemini.\n"
                "Hãy kiểm tra biến GEMINI_MODEL."
            )
        elif "429" in error_msg or "quota" in error_msg.lower():
            msg = (
                "❌ API đang bị giới hạn hoặc hết quota.\n"
                "Vui lòng kiểm tra tài khoản Google AI Studio."
            )
        elif "400" in error_msg and "key" in error_msg.lower():
            msg = "❌ GEMINI_API_KEY không hợp lệ."
        else:
            msg = "❌ Dịch thuật thất bại. Vui lòng thử lại."

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=msg)
        )

    except Exception:
        logger.exception("Unexpected error")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="❌ Hệ thống xảy ra lỗi. Vui lòng thử lại."
            )
        )

# 7. CHẠY SERVER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
