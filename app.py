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
    return "Bot Dịch Thuật Việt - Trung đang chạy!", 200

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
    
    # SYSTEM PROMPT CỰC MẠNH: Buộc phải dịch qua lại
    system_instruction = (
        "Bạn là máy thông dịch song ngữ Trung Phồn thể (Taiwan) và Việt Nam. "
        "Nhiệm vụ của bạn là luôn luôn cung cấp bản dịch cho cả hai ngôn ngữ bất kể đầu vào là gì:\n"
        "- Nếu người dùng nhập tiếng Việt (có dấu hoặc không dấu): Hãy dịch sang Trung Phồn thể.\n"
        "- Nếu người dùng nhập tiếng Trung: Hãy dịch sang tiếng Việt chuẩn.\n"
        "Định dạng trả về duy nhất:\n"
        "🇹🇼 CH: [Bản dịch Trung Phồn thể]\n"
        "🇻🇳 VN: [Bản dịch tiếng Việt chuẩn có dấu]\n"
        "Lưu ý: Không lặp lại văn bản của người dùng nếu không cần thiết, chỉ trả về bản dịch chính xác."
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1, # Giữ độ chính xác tuyệt đối
        )
        reply_text = chat_completion.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Lỗi Groq: {e}")
        reply_text = "Hệ thống đang bận, bạn vui lòng thử lại nhé!"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)