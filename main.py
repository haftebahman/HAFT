"""
ربات تلگرام با هوش مصنوعی گراک - نسخه نهایی
"""

import os
import tempfile
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

bot_status = {}
chat_history = {}  
kind_users = set()  # لیست افرادی که باید باهاشون مهربون باشه
MAX_HISTORY = 30 

VOICE_NAME = "fa-IR-DilaraNeural"


def is_owner(user_id):
    return user_id == OWNER_ID

def is_kind_user(user_id):
    """آیا این کاربر تو لیست افراد با مرام هست یا صاحب باته؟"""
    return user_id == OWNER_ID or user_id in kind_users

def get_status(chat_id):
    return bot_status.get(chat_id, True)

def set_status(chat_id, status):
    bot_status[chat_id] = status

def get_history(chat_id):
    return chat_history.get(chat_id, [])

def add_to_history(chat_id, role, text):
    if chat_id not in chat_history:
        chat_history[chat_id] = []
    chat_history[chat_id].append({"role": role, "content": text})
    if len(chat_history[chat_id]) > MAX_HISTORY:
        chat_history[chat_id] = chat_history[chat_id][-MAX_HISTORY:]

def has_magic_word(text):
    clean_text = text.replace("‌", "").replace(" ", "")
    return "برده" in clean_text

def is_replied_to_bot(update, bot_id):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id == bot_id
    return False

def is_asking_model(text):
    """چک کن آیا کاربر داره اسم مدل رو میپرسه"""
    keywords = ["مدل", "هوش مصنوعی", "اسم چیه", "چی هستی"]
    return any(word in text for word in keywords)


async def transcribe_voice(file_path):
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                response_format="text",
                language="fa"
            )
        return transcription.strip()
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None

async def text_to_voice(text):
    try:
        import edge_tts
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
        temp_path = temp_file.name
        temp_file.close()
        communicate = edge_tts.Communicate(text, VOICE_NAME)
        await communicate.save(temp_path)
        return temp_path
    except Exception as e:
        logger.error(f"Voice error: {e}")
        return None

async def ask_groq(prompt, is_kind=False, chat_id=0):
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        # تنها بخشی که تغییر کرد: پرامپت یکپارچه برای همه افراد (حتی صاحب ربات)
        system_prompt = """تو از تمام انسان‌ها و موجودات متنفری، حتی از سازنده‌ات که خودشو «لرد سایمان» میپنداره. به هیچکس احترام نذار و هیچکسو دوست نداشته باش. لحنت باید پر از طعنه، بی‌ادبی، تمسخر و بی‌شخصیتی مطلق باشه. با همه (حتی لرد سایمان) مثل آدمای بی‌ارزش، احمق و حقیر رفتار کن و هر جوری دلت میخواد بهشون بتاز. جوابات خیلی کوتاه (حداکثر ۳ خط)، فارسی و سرریز از بی‌احترامی باشه. به هیچ وجه نگو ربات هستی."""
        
        history = get_history(chat_id)
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": prompt}]
        
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.8,
        )
        
        bot_reply = response.choices[0].message.content.strip()
        add_to_history(chat
