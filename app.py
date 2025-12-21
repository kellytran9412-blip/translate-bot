import os
from flask import Flask, request, abort, send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai  # Thư viện chuẩn
from docx import Document

app = Flask(__name__)

# Cấu hình
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# Cấu hình Gemini TRIỆT ĐỂ
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Giải quyết 404 bằng cách gọi trực tiếp tên model chuẩn của Google
model = genai.GenerativeModel(model_name='gemini-1.5-flash')

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
    prompt = f"Dịch văn bản sau sang tiếng Trung Phồn thể nếu là tiếng Việt, và ngược lại. Chỉ trả về bản dịch: {user_text}"

    try:
        # Gọi Gemini
        response = model.generate_content(prompt)
        translated_text = response.text.strip()
        
        # Phản hồi tin nhắn văn bản
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated_text))
        
    except Exception as e:
        print(f"Lỗi thực thi: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Hệ thống bận, hãy thử lại sau."))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)