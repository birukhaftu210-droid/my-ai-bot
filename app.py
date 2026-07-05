import os
import threading
from collections import defaultdict
from flask import Flask, request
import telebot
from google import genai

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
client = genai.Client(api_key=GEMINI_API_KEY)

# Store conversation history
history = defaultdict(list)

SYSTEM_PROMPT = """
You are XP AI, a smart and helpful AI assistant.

Rules:
- Answer accurately.
- Never make up facts.
- If you don't know, say you don't know.
- Reply in the same language as the user.
- Give detailed explanations when appropriate.
- Be polite and professional.
- For coding questions, provide working code.
- For math, show steps.
- For factual questions, avoid guessing.
"""

@app.route("/")
def home():
    return "XP AI BOT Running"

def ask_ai(chat_id, text, reply_id):
    try:
        history[chat_id].append(f"User: {text}")

        conversation = SYSTEM_PROMPT + "\n\n"

        for msg in history[chat_id][-10:]:
            conversation += msg + "\n"

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conversation
        )

        answer = response.text

        history[chat_id].append(f"Assistant: {answer}")

        bot.send_message(
            chat_id,
            answer,
            reply_to_message_id=reply_id
        )

    except Exception as e:
        print(e)
        bot.send_message(
            chat_id,
            "❌ AI Error!"
        )
@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":

        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)

        if update.message and update.message.text:

            threading.Thread(
                target=ask_ai,
                args=(
                    update.message.chat.id,
                    update.message.text,
                    update.message.message_id,
                ),
                daemon=True,
            ).start()

        return "OK", 200

    return "Forbidden", 403


@app.route("/set_webhook")
def set_webhook():

    if not RENDER_URL:
        return "RENDER_EXTERNAL_URL not found"

    try:
        bot.remove_webhook()

        bot.set_webhook(
            url=f"{RENDER_URL}/webhook"
        )

        return "Webhook Set Successfully"

    except Exception as e:
        return str(e)


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000))
    )
