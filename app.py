import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

app = Flask(__name__)

# 1. Cấu hình thông số từ Environment Variables
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 2. Cấu hình Gemini - Dùng thư viện ổn định
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Khởi tạo model theo cách truyền thống để tránh lỗi 404 v1beta
model = genai.GenerativeModel('gemini-1.5-flash')

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
    
    # Prompt dịch thuật song ngữ
    prompt = (
        f"Dịch văn bản sau: Nếu là tiếng Việt thì dịch sang tiếng Trung Phồn thể (Taiwan). "
        f"Nếu là tiếng Trung thì dịch sang tiếng Việt. "
        f"Chỉ trả về bản dịch, không giải thích: {user_text}"
    )

    try:
        # Thực hiện gọi AI
        response = model.generate_content(prompt)
        
        if response.text:
            reply_text = response.text.strip()
        else:
            reply_text = "AI không phản hồi nội dung. Hãy thử lại."
            
    except Exception as e:
        error_msg = str(e)
        print(f"Lỗi thực tế tại Log: {error_msg}")
        
        if "404" in error_msg:
            reply_text = "Lỗi kết nối API (404). Đang chờ hệ thống cập nhật lại phiên bản."
        elif "429" in error_msg:
            reply_text = "Hạn mức miễn phí đã hết, vui lòng đợi 1 phút."
        else:
            reply_text = "Hệ thống bận, vui lòng thử lại sau."

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)