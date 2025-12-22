import os
from flask import Flask, request, abort
from google import genai
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 1. CẤU HÌNH
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

# Khởi tạo Client với API v1
client = genai.Client(api_key=GEMINI_KEY, http_options={'api_version': 'v1'})

line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

@app.route("/", methods=['GET'])
def index():
    return "Bot Debug Model đang chạy!"

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
        # Thử gọi model mặc định
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Dịch sang tiếng Việt: {user_text}"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response.text))

    except Exception as e:
        error_msg = str(e)
        print(f"Lỗi: {error_msg}")

        # NẾU LỖI 404, QUÉT DANH SÁCH MODEL KHẢ DỤNG
        if "404" in error_msg or "not found" in error_msg.lower():
            try:
                available_models = []
                # Lấy danh sách các model mà API Key này được phép dùng
                for m in client.models.list():
                    # Chỉ lấy tên ngắn gọn (ví dụ: gemini-1.5-flash)
                    name = m.name.replace("models/", "")
                    available_models.append(name)
                
                debug_info = "❌ Lỗi 404: Model không khớp.\n\n"
                debug_info += "✅ Các version bạn CÓ THỂ dùng là:\n"
                debug_info += "\n".join(available_models[:10]) # Lấy 10 cái đầu tiên
                debug_info += "\n\nHãy copy 1 tên ở trên và sửa vào dòng 'model=' trong app.py"
                
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=debug_info))
            except Exception as list_error:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ Không thể lấy danh sách model: {str(list_error)}"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ Lỗi hệ thống: {error_msg}"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

