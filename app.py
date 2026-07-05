import os
import threading
from flask import Flask, request
import telebot
from google import genai

app = Flask(__name__)

# ቁልፎችን ከ Render Environment Variables ላይ ያነባል
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

def process_ai_reply(message_text, chat_id, reply_to_id):
    try:
        # ለ AIው ጥያቄውን መላክ (በጣም ፈጣኑን ሞዴል ይጠቀማል)
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message_text,
        )
        # የ AIውን መልስ ለተጠቃሚው መመለስ
        bot.send_message(chat_id, response.text, reply_to_message_id=reply_to_id)
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(chat_id, "ይቅርታ፣ ምላሽ ለመስጠት አልቻልኩም።")

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        
        if update.message and update.message.text:
            # Render ለቴሌግራም ወዲያውኑ OK እንዲመልስ ስራውን በሌላ መስመር (Thread) ማስኬድ
            threading.Thread(
                target=process_ai_reply, 
                args=(update.message.text, update.message.chat.id, update.message.message_id)
            ).start()
            
        return 'ok', 200
    else:
        return 'forbidden', 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
