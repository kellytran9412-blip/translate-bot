import os
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# Cấu hình API
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

# Thiết lập Model tối ưu cho tiếng Trung Đài Loan
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=(
        "You are a professional translator between Vietnamese and Traditional Chinese (Taiwan). "
        "If the input is Vietnamese, translate it to Traditional Chinese as used in Taiwan. "
        "If the input is Chinese, translate it to Vietnamese. "
        "Maintain a natural, polite tone. Only provide the translation text without explanations."
    )
)

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
    try:
        # Sử dụng stream=False để nhận phản hồi nhanh gọn cho chat
        response = model.generate_content(user_text)
        
        if response and response.text:
            reply_text = response.text.strip()
        else:
            reply_text = "抱歉，無法處理此內容。/ Xin lỗi, không thể xử lý nội dung này."

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as e:
        print(f"Error: {e}")
        # Không báo lỗi AI bận nữa mà báo thử lại
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="系統繁忙，請稍後再試。/ Hệ thống bận, vui lòng thử lại sau.")
        )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))