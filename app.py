import os
from flask import Flask, request, abort
import google.generativeai as genai
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# Đọc cấu hình từ biến môi trường (Environment Variables)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

# Cấu hình Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash",
    system_instruction="Bạn là chuyên gia dịch thuật. Hãy dịch văn bản từ tiếng Trung Phồn thể sang tiếng Việt và ngược lại. Trả về kết quả dịch trực tiếp, tự nhiên, không giải thích."
)

line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    # Gọi Gemini dịch
    response = model.generate_content(f"Dịch: {user_text}")
    translated = response.text.strip()
    # Gửi lại LINE
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))