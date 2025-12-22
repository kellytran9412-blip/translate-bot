import os
from flask import Flask, request, abort
from google import genai
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 1. CẤU HÌNH BIẾN MÔI TRƯỜNG
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

# 2. KHỞI TẠO CLIENT GEMINI (SDK MỚI)
client = genai.Client(api_key=GEMINI_KEY)

# 3. CẤU HÌNH LINE
line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

@app.route("/", methods=['GET'])
def index():
    return "Bot is running!"

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
        # Gọi Gemini dịch thuật
        response = client.models.generate_content(
           model="models/gemini-1.5-flash",
            contents=f"Dịch tiếng Trung Phồn thể sang tiếng Việt và ngược lại, trả về kết quả trực tiếp: {user_text}"
        )
        
        translated_text = response.text.strip()
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=translated_text)
        )
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"❌ Lỗi: {str(e)}")
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

