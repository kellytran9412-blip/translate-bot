
import os
import logging
from flask import Flask, request, abort
from openai import OpenAI, OpenAIError
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. CẤU HÌNH BIẾN MÔI TRƯỜNG
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

MODEL = os.environ.get("OPENAI_MODEL", "gpt-6-luna")

if not all([OPENAI_KEY, LINE_TOKEN, LINE_SECRET]):
    raise RuntimeError(
        "Thiếu OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN "
        "hoặc LINE_CHANNEL_SECRET"
    )

# 2. KHỞI TẠO OPENAI
client = OpenAI(
    api_key=OPENAI_KEY,
    timeout=30.0,
    max_retries=1
)

# 3. KHỞI TẠO LINE BOT
line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# 4. PROMPT DỊCH THUẬT
TRANSLATION_INSTRUCTION = """
Bạn là chuyên gia dịch thuật tiếng Việt và
tiếng Trung Phồn thể (Đài Loan).

QUY TẮC:
1. Nếu văn bản là tiếng Việt:
   Dịch sang tiếng Trung Phồn thể (繁體中文).
2. Nếu văn bản là tiếng Trung:
   Dịch sang tiếng Việt.
3. Sử dụng từ ngữ tự nhiên, phổ biến tại Đài Loan.
4. Dịch chính xác thuật ngữ công ty, nhà máy,
   nhân sự, lao động và hành chính.
5. Giữ nguyên tên riêng, mã số, ngày tháng,
   số tiền và định dạng xuống dòng khi phù hợp.
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
        response = client.responses.create(
            model=MODEL,
            instructions=TRANSLATION_INSTRUCTION,
            input=user_text,
            max_output_tokens=3000,
            store=False
        )

        translated_text = (response.output_text or "").strip()

        if not translated_text:
            translated_text = "❌ Không nhận được bản dịch."

        # LINE giới hạn độ dài tin nhắn văn bản.
        if len(translated_text) > 5000:
            translated_text = (
                translated_text[:4990] + "\n..."
            )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=translated_text)
        )

    except OpenAIError as e:
        logger.exception("OpenAI API error")

        error_msg = str(e)

        if "model_not_found" in error_msg or "404" in error_msg:
            msg = (
                "❌ Không tìm thấy model OpenAI.\n"
                "Hãy kiểm tra OPENAI_MODEL và quyền truy cập API."
            )
        elif "429" in error_msg:
            msg = (
                "❌ API đang bị giới hạn hoặc hết hạn mức.\n"
                "Vui lòng kiểm tra tài khoản OpenAI."
            )
        elif "401" in error_msg:
            msg = "❌ OpenAI API Key không hợp lệ."
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
