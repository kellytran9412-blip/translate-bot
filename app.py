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

# 2. KHỞI TẠO CLIENT (Sử dụng SDK mới nhất)
client = genai.Client(api_key=GEMINI_KEY, http_options={'api_version': 'v1'})

line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

@app.route("/", methods=['GET'])
def index():
    return "Bot Gemini 2.5 Flash is running!"

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
        # Prompt dịch thuật song ngữ tự động
        instruction = (
            "Bạn là chuyên gia dịch thuật Việt - Trung (Phồn thể). "
            "Nếu là tiếng Trung Phồn thể, hãy dịch sang tiếng Việt. "
            "Nếu là tiếng Việt, hãy dịch sang tiếng Trung Phồn thể. "
            "Chỉ trả về bản dịch, không thêm bất kỳ lời giải thích nào."
        )

        # GỌI ĐÍCH DANH MODEL 2.5 FLASH
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=f"{instruction}\n\nVăn bản: {user_text}"
        )
        
        translated_text = response.text.strip()
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=translated_text)
        )

    except Exception as e:
        error_msg = str(e)
        print(f"Lỗi: {error_msg}")
        
        # Nếu model 2.5 chưa khả dụng, Bot sẽ báo danh sách model bạn ĐANG CÓ
        if "404" in error_msg:
            try:
                available = [m.name.replace("models/", "") for m in client.models.list()]
                msg = f"❌ Phiên bản 2.5 Flash chưa khả dụng với Key này.\n\n✅ Version bạn nên dùng là:\n" + "\n".join(available[:5])
            except:
                msg = "❌ Lỗi 404: Không tìm thấy model. Vui lòng kiểm tra lại API Key."
        else:
            msg = f"❌ Lỗi: {error_msg}"
            
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
