import os
import sys
from flask import Flask, request, abort

# Import Gemini
import google.generativeai as genai
from google.generativeai.types import RequestOptions

# Import LINE SDK
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 1. LẤY BIẾN MÔI TRƯỜNG ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

# Kiểm tra cấu hình
if not all([GEMINI_KEY, LINE_TOKEN, LINE_SECRET]):
    print("THIẾU BIẾN MÔI TRƯỜNG! Hãy kiểm tra lại Dashboard Render.")
    sys.exit(1)

# --- 2. CẤU HÌNH GEMINI ---
genai.configure(api_key=GEMINI_KEY)

# Sử dụng tên model ổn định nhất
# Nếu vẫn báo 404, bạn có thể thử đổi thành "gemini-1.5-pro"
MODEL_NAME = "gemini-1.5-flash"

model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction="Bạn là một chuyên gia dịch thuật. Hãy dịch văn bản từ tiếng Trung Phồn thể sang tiếng Việt và ngược lại. Trả về kết quả dịch trực tiếp, văn phong tự nhiên, không kèm theo giải thích."
)

# --- 3. CẤU HÌNH LINE ---
line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

@app.route("/", methods=['GET'])
def index():
    return "Bot dịch thuật đang hoạt động!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    try:
        # Sử dụng API v1 thay vì v1beta để tránh lỗi 404 models
        response = model.generate_content(
            f"Dịch văn bản sau sang tiếng Việt: {user_text}",
            request_options=RequestOptions(api_version='v1')
        )
        
        translated_text = response.text.strip()
        
        # Phản hồi lại LINE
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=translated_text)
        )
        
    except Exception as e:
        print(f"LỖI GEMINI: {str(e)}")
        # Nếu lỗi 404 vẫn tiếp diễn, in ra danh sách model khả dụng trong log
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="❌ Có lỗi xảy ra khi gọi AI. Vui lòng kiểm tra lại cấu hình model.")
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)