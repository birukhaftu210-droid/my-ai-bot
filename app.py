import os
import threading
import time
from collections import defaultdict
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").lstrip("@")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
client = genai.Client(api_key=GEMINI_API_KEY)

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

def is_user_member(chat_id, user_id):
    if not CHANNEL_USERNAME:
        return True
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Membership check error: {e}")
        return False

# ============ የተስተካከሉት ቁልፎች እዚህ ናቸው ============
def force_join_keyboard():
    if not CHANNEL_USERNAME:
        return InlineKeyboardMarkup()
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_join = InlineKeyboardButton("📢 ቻናሉን ይቀላቀሉ", url=f"https://t.me/{CHANNEL_USERNAME}")
    btn_check = InlineKeyboardButton("✅ ተቀላቀልኩ (አረጋግጥ)", callback_data="check_join")
    keyboard.add(btn_join, btn_check)
    return keyboard

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_help = InlineKeyboardButton("🆘 እርዳታ", callback_data="help")
    btn_about = InlineKeyboardButton("ℹ️ ስለ ቦት", callback_data="about")
    keyboard.add(btn_help, btn_about)
    if CHANNEL_USERNAME:
        btn_channel = InlineKeyboardButton("📢 ቻናላችን", url=f"https://t.me/{CHANNEL_USERNAME}")
        keyboard.add(btn_channel)
    return keyboard
# ==================================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if is_user_member(chat_id, user_id):
        welcome_text = (
            f"👋 እንኳን ደህና መጣህ/ሽ {message.from_user.first_name}!\n\n"
            "እኔ <b>XP AI</b> ነኝ። ማንኛውንም ጥያቄ በነጻ ልትጠይቀኝ ትችላለህ/ሽ።\n"
            "ልክ ማንኛውንም ነገር ወደኔ ላክኝ፣ በጥበብ እመልስልሃለሁ።"
        )
        bot.send_message(chat_id, welcome_text, reply_markup=main_menu_keyboard())
    else:
        force_text = (
            f"⛔ ይቅርታ {message.from_user.first_name}!\n\n"
            "ይህን ቦት ለመጠቀም በመጀመሪያ የኛን የቴሌግራም ቻናል መቀላቀል አለብህ/ሽ።"
        )
        bot.send_message(chat_id, force_text, reply_markup=force_join_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    message_id = call.message.message_id

    if call.data == "check_join":
        if is_user_member(chat_id, user_id):
            bot.edit_message_text("✅ እንኳን ደህና መጣህ! ቻናሉን ተቀላቅለሃል/ሽ።", chat_id=chat_id, message_id=message_id)
            bot.send_message(chat_id, "👇 አሁን ጥያቄህን ልትጠይቅ ትችላለህ።", reply_markup=main_menu_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ ገና አልተቀላቀልክም!", show_alert=True)
    elif call.data == "help":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "🆘 ማንኛውንም ጥያቄ በቀላሉ ላክልኝ።")
    elif call.data == "about":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "ℹ️ <b>XP AI</b> በGoogle Gemini የተጎላበተ ነው።")

def ask_ai(chat_id, text, reply_id):
    try:
        if CHANNEL_USERNAME and not is_user_member(chat_id, chat_id):
            bot.send_message(chat_id, "⛔ በመጀመሪያ ቻናሉን ተቀላቀል!", reply_to_message_id=reply_id)
            return

        history[chat_id].append(f"User: {text}")
        conversation = SYSTEM_PROMPT + "\n\n"
        for msg in history[chat_id][-10:]:
            conversation += msg + "\n"

        safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
        ]

        max_retries = 3
        answer = None
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=conversation,
                    config=types.GenerateContentConfig(safety_settings=safety_settings, temperature=0.7)
                )
                answer = response.text
                break
            except Exception as api_error:
                if "429" in str(api_error) and attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                else:
                    raise api_error

        if not answer:
            raise Exception("No response")

        history[chat_id].append(f"Assistant: {answer}")
        bot.send_message(chat_id, answer, reply_to_message_id=reply_id, reply_markup=main_menu_keyboard())

    except Exception as e:
        error_text = str(e)
        print(f"ERROR: {error_text}")
        msg = f"❌ ስህተት፦ {error_text[:100]}"
        bot.send_message(chat_id, msg, reply_to_message_id=reply_id)

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        if update.message and update.message.text:
            threading.Thread(target=ask_ai, args=(update.message.chat.id, update.message.text, update.message.message_id), daemon=True).start()
        return "OK", 200
    return "Forbidden", 403

@app.route("/set_webhook")
def set_webhook():
    if not RENDER_URL:
        return "RENDER_EXTERNAL_URL not found"
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/webhook")
        return "Webhook Set Successfully"
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
