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
kind_users = set()  
MAX_HISTORY = 30 

VOICE_NAME = "fa-IR-DilaraNeural"


def is_owner(user_id):
    return user_id == OWNER_ID

def is_kind_user(user_id):
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
        add_to_history(chat_id, "user", prompt)
        add_to_history(chat_id, "assistant", bot_reply)
        
        return bot_reply
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return f"🤯 اره گراکم یخ زد! ({str(e)[:50]})"


async def send_text_only(update, response, owner_msg, chat_id):
    sent_msg = await update.message.reply_text(response)
    if update.effective_chat.type == "private" and not owner_msg:
        try: await sent_msg.forward(chat_id=OWNER_ID)
        except: pass

async def send_voice_only(update, response, owner_msg, chat_id):
    sent_msg = None
    voice_path = await text_to_voice(response)
    
    if voice_path:
        try:
            with open(voice_path, 'rb') as vf:
                sent_msg = await update.message.reply_voice(vf)
        except: pass
        finally:
            if os.path.exists(voice_path): os.remove(voice_path)
            
    if not sent_msg:
        sent_msg = await update.message.reply_text(response)
        
    if update.effective_chat.type == "private" and not owner_msg:
        try: await sent_msg.forward(chat_id=OWNER_ID)
        except: pass


async def start_cmd(update, context):
    await update.message.reply_text(" *سلام! من برده لرد سایمان هستم*\n\nLONG LIVE THE LORD", parse_mode="Markdown")

async def on_cmd(update, context):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 تو کی هستی؟ فقط لرد سایمان دسترسی داره! 😤")
        return
    set_status(update.effective_chat.id, True)
    await update.message.reply_text("✅ *روشن شدم!* 😎🔥", parse_mode="Markdown")

async def off_cmd(update, context):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 دسترسی نداری کسخل! ")
        return
    set_status(update.effective_chat.id, False)
    await update.message.reply_text("😴 *خاموش شدم!*... ", parse_mode="Markdown")

async def status_cmd(update, context):
    active = get_status(update.effective_chat.id)
    emoji = "🟢" if active else "🔴"
    text = "روشن" if active else "خاموش"
    await update.message.reply_text(f"{emoji} وضعیت: *{text}*", parse_mode="Markdown")

async def addfriend_cmd(update, context):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 فقط لرد سایمان میتونه آدم با مرام تعریف کنه!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ آیدی عددی رو بفرست!\nمثال:\n`/addfriend 123456789`", parse_mode="Markdown")
        return
        
    try:
        uid = int(context.args[0])
        kind_users.add(uid)
        await update.message.reply_text(f"✅ کاربر `{uid}` به لیست آدمای با مرام اضافه شد! از الان باهاش مهربونم 👌", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ آیدی باید فقط عدد باشه!")


async def handle_msg(update, context):
    chat_id = update.effective_chat.id
    bot_id = context.bot.id
    user_id = update.effective_user.id
    
    text = update.message.text or ""
    if not text.strip() or text.startswith("/"):
        return
    
    owner_msg = is_owner(user_id)
    is_kind = is_kind_user(user_id)
    
    if is_asking_model(text):
        await update.message.reply_text("من از HAFTAI استفاده میکنم 🧠")
        return
    
    wants_voice = "ویس" in text
    
    if update.effective_chat.type == "private":
        await update.message.chat.send_action("typing")
        if not owner_msg:
            try: await update.message.forward(chat_id=OWNER_ID)
            except: pass
            
        response = await ask_groq(text, is_kind, chat_id)
        
        if wants_voice:
            await send_voice_only(update, response, owner_msg, chat_id)
        else:
            await send_text_only(update, response, owner_msg, chat_id)
        return
    
    if not get_status(chat_id): return
    
    replied = is_replied_to_bot(update, bot_id)
    magic = has_magic_word(text)
    if not replied and not magic: return
    
    await update.message.chat.send_action("typing")
    response = await ask_groq(text, is_kind, chat_id)
    
    if wants_voice:
        await send_voice_only(update, response, owner_msg, chat_id)
    else:
        await send_text_only(update, response, owner_msg, chat_id)


async def handle_voice(update, context):
    chat_id = update.effective_chat.id
    bot_id = context.bot.id
    user_id = update.effective_user.id
    owner_msg = is_owner(user_id)
    is_kind = is_kind_user(user_id)

    await update.message.chat.send_action("typing")
    
    voice = update.message.voice
    if not voice: return
        
    try:
        voice_file = await context.bot.get_file(voice.file_id)
        temp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
        temp_in_path = temp_in.name
        temp_in.close()
        await voice_file.download_to_drive(temp_in_path)
    except Exception as e:
        logger.error(f"Download voice error: {e}")
        await update.message.reply_text("❌ خطا در دانلود ویس")
        return

    user_text = await transcribe_voice(temp_in_path)
    
    if os.path.exists(temp_in_path):
        os.remove(temp_in_path)

    if not user_text:
        await update.message.reply_text("🤔 ویس رو متوجه نشدم یا خالی بود!")
        return

    if is_asking_model(user_text):
        await update.message.reply_text("من از HAFTAI استفاده میکنم 🧠")
        return

    wants_voice = "ویس" in user_text

    if update.effective_chat.type == "private":
        if not owner_msg:
            try: await update.message.forward(chat_id=OWNER_ID)
            except: pass
        response = await ask_groq(user_text, is_kind, chat_id)
        
        if wants_voice:
            await send_voice_only(update, response, owner_msg, chat_id)
        else:
            await send_text_only(update, response, owner_msg, chat_id)
        return

    if not get_status(chat_id): return
    
    replied = is_replied_to_bot(update, bot_id)
    magic = has_magic_word(user_text)
    if not replied and not magic: return
    
    response = await ask_groq(user_text, is_kind, chat_id)
    
    if wants_voice:
        await send_voice_only(update, response, owner_msg, chat_id)
    else:
        await send_text_only(update, response, owner_msg, chat_id)


async def error_handler(update, context):
    logger.error(f"Error: {context.error}")


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN تنظیم نشده!")
        return
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY تنظیم نشده!")
        return
    
    logger.info("🚀 بات داره روشن میشه...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("on", on_cmd))
    app.add_handler(CommandHandler("off", off_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("addfriend", addfriend_cmd))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    app.add_error_handler(error_handler)
    
    logger.info("✅ بات روشن شد!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
