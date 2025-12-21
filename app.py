import os
import sys
from flask import Flask, request, abort

# Thư viện Gemini
import google.generativeai as genai

# Thư viện LINE SDK
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 1. CẤU HÌNH BIẾN MÔI TRƯỜNG ---
# Các giá trị này sẽ được cài đặt trên Dashboard của Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

# Kiểm tra nếu thiếu cấu hình
if not all([GEMINI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET]):
    print("Lỗi: Thiếu cấu hình biến môi trường (Environment Variables).")
    sys.exit(1)

# --- 2. THIẾT LẬP GEMINI ---
genai.configure(api_key=GEMINI_API_KEY)

# Cấu hình "não bộ" cho Bot dịch thuật
generation_config = {
    "temperature": 0.3, # Thấp để dịch chính xác, ít sáng tạo linh tinh
    "top_p": 1,
    "max_output_tokens": 2048,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="Bạn là một bot dịch thuật chuyên nghiệp. Nhiệm vụ của bạn là dịch từ Tiếng Trung Phồn Thể (Traditional Chinese) sang Tiếng Việt. Yêu cầu: Dịch tự nhiên, đúng ngữ cảnh đời sống, không dùng từ hán việt khó hiểu. CHỈ TRẢ VỀ BẢN DỊCH, không kèm giải thích."
)

# --- 3. THIẾT LẬP LINE SDK ---
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Tuyến đường (Route) để nhận tín hiệu từ LINE Webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Lỗi: Chữ ký không hợp lệ. Kiểm tra Channel Secret.")
        abort(400)
    return 'OK'

# --- 4. LOGIC XỬ LÝ TIN NHẮN ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # Lấy tin nhắn người dùng gửi đến
    user_input = event.message.text
    
    try:
        # Gửi đến Gemini để dịch
        # Thêm tiền tố nhắc nhở nhỏ để đảm bảo model tập trung dịch
        prompt = f"Dịch văn bản sau sang tiếng Việt: {user_input}"
        response = model.generate_content(prompt)
        
        translated_text = response.text.strip()
        
        # Phản hồi kết quả dịch lại cho người dùng
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=translated_text)
        )
        
    except Exception as e:
        print(f"Lỗi hệ thống: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="❌ Bot đang bận hoặc có lỗi xảy ra. Vui lòng thử lại sau.")
        )

if __name__ == "__main__":
    # Chạy trên máy local (Port 8000)
    # Khi lên Render, Render sẽ tự quản lý port thông qua Gunicorn
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))