import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from groq import Groq

app = Flask(__name__)

# --- CẤU HÌNH ---
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

@app.route("/", methods=['GET'])
def index():
    return "Bot Dịch Thuật Đối Ứng đang hoạt động!", 200

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
    
    # SYSTEM PROMPT: Logic lọc bỏ ngôn ngữ đầu vào
    system_instruction = (
        "Bạn là máy thông dịch thông minh TIẾNG VIỆT - TRUNG PHỒN THỂ ĐÀI LOAN . "
        "Nhiệm vụ của bạn là dịch văn bản người dùng cung cấp sang ngôn ngữ CÒN LẠI. "
        "QUY TẮC BẮT BUỘC:\n"
        "1. Nếu người dùng nhập tiếng Trung phồn thể đài loan: Hiện dòng VN:.\n"
        "2. Nếu người dùng nhập tiếng Việt: Hiện dòng CH:.\n"
        "Luôn tự sửa lỗi chính tả và thêm dấu cho tiếng Việt trước khi dịch nếu có."
        "CHỈ CẦN DỊCH KHÔNG CẦN GIẢI THÍCH THÊM"
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
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