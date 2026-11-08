@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text.strip()
    if not user_text:
        return

    translated_text = ""
    models_to_try = [MODEL, "gemini-1.5-flash"]  # Thử model chính trước, lỗi 429 thì sang model phụ

    for model_name in models_to_try:
        try:
            # Chỉ bật thinking_config nếu dùng dòng 2.5
            config_params = {
                "system_instruction": TRANSLATION_INSTRUCTION,
                "max_output_tokens": 1500,
                "temperature": 0.1,
            }
            if "2.5" in model_name:
                config_params["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=user_text,
                config=types.GenerateContentConfig(**config_params)
            )

            translated_text = (response.text or "").strip()
            if translated_text:
                break  # Dịch thành công, thoát vòng lặp

        except APIError as e:
            if "429" in str(e):
                logger.warning(f"Model {model_name} hết hạn mức, đang thử model dự phòng...")
                continue
            logger.exception(f"Lỗi API ở model {model_name}")
            break
        except Exception:
            logger.exception("Lỗi không xác định")
            break

    if not translated_text:
        return

    if len(translated_text) > 5000:
        translated_text = translated_text[:4990] + "\n..."

    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=translated_text)]
        )
    )
