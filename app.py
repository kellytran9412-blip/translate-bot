import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from groq import Groq

app = Flask(__name__)

# --- CẤU HÌNH ---
# Hãy đảm bảo bạn đã nhập GROQ_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET trên Render
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# --- ĐƯỜNG DẪN GIỮ 24/7 ---
@app.route("/", methods=['GET'])
def index():
    return "Bot is running 24/7", 200

@app.route("/health", methods=['GET'])
def health_check():
    return "OK", 200

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
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
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Bạn là chuyên gia dịch thuật. Dịch sang tiếng Trung Phồn thể (Taiwan) nếu thấy tiếng Việt, và ngược lại. Chỉ trả về bản dịch."
                },
                {"role": "user", "content": user_text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        reply_text = chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Lỗi: {e}")
        reply_text = "Hệ thống đang bận, vui lòng thử lại sau."

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)