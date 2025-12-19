import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai

app = Flask(__name__)

# Cấu hình biến môi trường trên Render
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

# Khởi tạo Client theo chuẩn mới
client = genai.Client(api_key=GEMINI_API_KEY)
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

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
    
    # Thiết lập chỉ dẫn hệ thống (System Instruction)
    instruction = "Bạn là chuyên gia dịch thuật Đài Loan. Dịch Việt sang Trung Phồn thể và ngược lại. Chỉ trả về bản dịch."
    
    try:
        # Gọi model Gemini 3 Pro Preview
        response = client.models.generate_content(
            model="gemini-2.0-flash", # Gợi ý: Nếu 3-pro-preview lỗi 404, dùng 2.0-flash đang rất ổn định
            contents=user_text,
            config={
                "system_instruction": instruction,
                "temperature": 0.3 # Thấp để dịch thuật chính xác hơn
            }
        )
        
        reply_text = response.text.strip()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        
    except Exception as e:
        print(f"Error: {e}")
        # Phản hồi lỗi thân thiện
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="Hệ thống đang bận, vui lòng thử lại sau!")
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)