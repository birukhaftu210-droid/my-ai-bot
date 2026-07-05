import os
import threading
from flask import Flask, request
import telebot
from google import genai

app = Flask(__name__)

# Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

# Telegram Bot
bot = telebot.TeleBot(BOT_TOKEN)

# Gemini AI
ai_client = genai.Client(api_key=GEMINI_API_KEY)


def process_ai_reply(message_text, chat_id, reply_to_id):
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=message_text,
        )

        bot.send_message(
            chat_id,
            response.text,
            reply_to_message_id=reply_to_id
        )

    except Exception as e:
        print("AI Error:", e)
        try:
            bot.send_message(
                chat_id,
                "❌ ይቅርታ፣ አሁን ምላሽ መስጠት አልቻልኩም።"
            )
        except:
            pass


@app.route("/")
def home():
    return "Bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":

        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)

        if update.message and update.message.text:

            threading.Thread(
                target=process_ai_reply,
                args=(
                    update.message.text,
                    update.message.chat.id,
                    update.message.message_id
                ),
            ).start()

        return "ok", 200

    return "forbidden", 403


if __name__ == "__main__":

    if RENDER_URL:
        try:
            bot.remove_webhook()

            bot.set_webhook(
                url=f"{RENDER_URL}/webhook"
            )

            print("✅ Webhook Set Successfully")

        except Exception as e:
            print("Webhook Error:", e)

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
