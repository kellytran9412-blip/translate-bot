import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from groq import Groq

app = Flask(__name__)

# 1. Cấu hình thông số từ Render Environment Variables
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# Cấu hình Groq
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

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
        # 2. Gọi Groq AI để dịch thuật
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Bạn là chuyên gia dịch thuật. Nếu thấy tiếng Việt, hãy dịch sang Trung Phồn thể (Taiwan). Nếu thấy tiếng Trung, hãy dịch sang tiếng Việt. Chỉ trả về bản dịch, không giải thích."
                },
                {
                    "role": "user",
                    "content": user_text,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2, # Độ chính xác cao
        )
        
        reply_text = chat_completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"Lỗi Groq: {e}")
        reply_text = "Hệ thống dịch thuật đang bận, vui lòng thử lại sau."

    # 3. Gửi tin nhắn trả lời
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)