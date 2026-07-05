import os
import threading
import time
from collections import defaultdict
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types  # ይህ ለሴፍቲ ሴቲንግስ አስፈላጊ ነው

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").lstrip("@")  # ምሳሌ: "my_ai_channel"

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

# ======================= አዲስ ባህሪያት =======================

# 1. ተጠቃሚው ቻናሉን መቀላቀሉን የሚፈትሽ ተግባር
def is_user_member(chat_id, user_id):
    if not CHANNEL_USERNAME:
        return True  # CHANNEL_USERNAME ካልተዘጋጀ ማረጋገጫውን ይዝለሉት
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Membership check error: {e}")
        return False

# 2. ቻናል ለመቀላቀል የሚሆን ቁልፍ (Force Join Keyboard)
def force_join_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_join = InlineKeyboardButton(
        text="📢 ቻናሉን ይቀላቀሉ", 
        url=f"https://t.me/{XPWORK1}"
    )
    btn_check = InlineKeyboardButton(
        text="✅ ተቀላቀልኩ (አረጋግጥ)", 
        callback_data="check_join"
    )
    keyboard.add(btn_join, btn_check)
    return keyboard

# 3. ዋና ሜኑ ቁልፎች (ከተቀላቀለ በኋላ)
def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_help = InlineKeyboardButton("🆘 እርዳታ", callback_data="help")
    btn_about = InlineKeyboardButton("ℹ️ ስለ ቦት", callback_data="about")
    btn_channel = InlineKeyboardButton("📢 ቻናላችን", url=f"https://t.me/{CHANNEL_USERNAME}" if CHANNEL_USERNAME else "#")
    keyboard.add(btn_help, btn_about, btn_channel)
    return keyboard

# 4. የ /start ትዕዛዝ አያያዥ
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if is_user_member(chat_id, user_id):
        welcome_text = (
            f"👋 እንኳን ደህና መጣህ/ሽ {message.from_user.first_name}!\n\n"
            "እኔ <b>XP AI</b> ነኝ። ማንኛውንም ጥያቄ በነጻ ልትጠይቀኝ ትችላለህ/ሽ።\n"
            "ልክ ማንኛውንም ነገር ወደኔ ላክኝ፣ በጥበብ እመልስልሃለሁ።\n\n"
            "💡 ምን መጠየቅ ትፈልጋለህ/ሽ?"
        )
        bot.send_message(chat_id, welcome_text, reply_markup=main_menu_keyboard())
    else:
        force_text = (
            f"⛔ ይቅርታ {message.from_user.first_name}!\n\n"
            "ይህን ቦት ለመጠቀም በመጀመሪያ የኛን የቴሌግራም ቻናል መቀላቀል አለብህ/ሽ።\n\n"
            "ከታች ያለውን ቁልፍ ተጫንና ተቀላቀል፣ ከዚያ <b>✅ ተቀላቀልኩ</b> የሚለውን ተጫን።"
        )
        bot.send_message(chat_id, force_text, reply_markup=force_join_keyboard())

# 5. የ "check_join" እና ሌሎች ቁልፎች ምላሽ (Callback)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    message_id = call.message.message_id

    if call.data == "check_join":
        if is_user_member(chat_id, user_id):
            bot.edit_message_text(
                "✅ እንኳን ደህና መጣህ! ቻናሉን በተሳካ ሁኔታ ተቀላቅለሃል/ሽ። አሁን ጥያቄህን ትጠይቅ ይችላል።",
                chat_id=chat_id,
                message_id=message_id
            )
            bot.send_message(
                chat_id,
                "👇 ከታች ካሉት ቁልፎች መምረጥ ትችላለህ፣ ወይም በቀጥታ ማንኛውንም ጥያቄ ልትጠይቀኝ ትችላለህ።",
                reply_markup=main_menu_keyboard()
            )
        else:
            bot.answer_callback_query(
                call.id,
                "❌ ገና ቻናሉን አልተቀላቀልክም! እባክህ መጀመሪያ ቻናሉን ተቀላቀል።",
                show_alert=True
            )

    elif call.data == "help":
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            "🆘 <b>እንዴት መጠቀም እችላለሁ?</b>\n\n"
            "1. ማንኛውንም ጥያቄ በቀላሉ ወደኔ ላክ።\n"
            "2. ኮድ፣ ሒሳብ፣ ትርጉም፣ ምክር እና ሌሎችን መጠየቅ ትችላለህ።\n"
            "3. መልሱን በተቻለ መጠን በዝርዝር እሰጣለሁ።"
        )

    elif call.data == "about":
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            "ℹ️ <b>ስለ ቦቱ</b>\n\n"
            "ስም: <b>XP AI</b>\n"
            "አቅም: በ Google Gemini 2.5 Flash የተጎላበተ\n"
            "ቋንቋ: ሁሉንም ቋንቋዎች ይደግፋል (በተለይ አማርኛ)\n"
        )

# ======================= ዋናው AI አያያዥ (የተሻሻለ) =======================

def ask_ai(chat_id, text, reply_id):
    try:
        # ቁልፍ ማረጋገጫ: ተጠቃሚው ቻናሉን ካልተቀላቀለ ምላሽ አንሰጥም
        if CHANNEL_USERNAME and not is_user_member(chat_id, chat_id):
            bot.send_message(
                chat_id,
                "⛔ ይቅርታ! ቦቱን ለመጠቀም በመጀመሪያ ቻናላችንን መቀላቀል አለብህ/ሽ። /start ብለህ ተመልሰህ ሞክር።",
                reply_to_message_id=reply_id
            )
            return

        # የውይይት ታሪክ ማስቀመጥ
        history[chat_id].append(f"User: {text}")

        conversation = SYSTEM_PROMPT + "\n\n"
        for msg in history[chat_id][-10:]:
            conversation += msg + "\n"

        # --- የደህንነት ቅንጅቶች (Safety Settings) ---
        safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
        ]

        # --- ጥያቄውን ላክ (Retry ያለው) ---
        max_retries = 3
        answer = None
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=conversation,
                    config=types.GenerateContentConfig(
                        safety_settings=safety_settings,
                        temperature=0.7,
                    )
                )
                answer = response.text
                break  # ስራ ከሰራ ከሉፕ ውጣ
            except Exception as api_error:
                error_msg = str(api_error)
                # የጊዜ ገደብ (Rate Limit) ከሆነ ጥቂት ቆይተን እንደገና ሞክር
                if "429" in error_msg or "Resource exhausted" in error_msg:
                    if attempt < max_retries - 1:
                        time.sleep(3)  # 3 ሰከንድ ቆይ
                        continue
                else:
                    # ሌላ ስህተት ከሆነ እንደዚያው አቋርጥ
                    raise api_error

        if answer is None:
            raise Exception("No response from AI after retries")

        history[chat_id].append(f"Assistant: {answer}")

        # መልሱ ከ4000 በላይ ከሆነ ክፍልፍለን እንላካለን
        if len(answer) > 4000:
            for x in range(0, len(answer), 4000):
                bot.send_message(chat_id, answer[x:x+4000], reply_to_message_id=reply_id)
        else:
            bot.send_message(
                chat_id,
                answer,
                reply_to_message_id=reply_id,
                reply_markup=main_menu_keyboard()
            )

    except Exception as e:
        error_text = str(e)
        print(f"ERROR for {chat_id}: {error_text}")  # Render Log ላይ ያሳያል
        
        # ለተጠቃሚው ግልጽ የሆነ መልእክት ላክ
        if "API_KEY" in error_text or "invalid" in error_text.lower():
            msg = "⚠️ የ Google API Key ስህተት ነው! እባክህ አስተካክለህ እንደገና ሞክር።"
        elif "429" in error_text or "quota" in error_text.lower():
            msg = "⏳ በአሁኑ ሰዓት ብዙ ጥያቄዎች መጥተዋል። እባክህ ከ2-3 ደቂቃ ቆይተህ ሞክር።"
        elif "safety" in error_text.lower() or "blocked" in error_text.lower():
            msg = "🚫 ይህ ጥያቄ በደህንነት ህጎች ተረጋግጧል። እባክህ በሌላ መንገድ ጠይቅ።"
        else:
            msg = f"❌ የ AI ስህተት ተከስቷል!\nእባክህ ቆየት ብለህ ሞክር።\n\n(ለገንቢው: {error_text[:150]})"
        
        bot.send_message(chat_id, msg, reply_to_message_id=reply_id)

# ======================= Webhook & Flask =======================

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
        bot.set_webhook(url=f"{RENDER_URL}/webhook")
        return "Webhook Set Successfully"
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000))
    )
