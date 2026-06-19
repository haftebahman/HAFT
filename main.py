"""
ربات تلگرام با هوش مصنوعی گراک
"""

import os
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

# تنظیم لاگ
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


def is_owner(user_id):
    return user_id == OWNER_ID


def get_status(chat_id):
    return bot_status.get(chat_id, True)


def set_status(chat_id, status):
    bot_status[chat_id] = status


def is_replied_to_bot(update, bot_id):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id == bot_id
    return False


def has_magic_word(text):
    return "برده" in text


async def ask_groq(prompt):
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
                system_prompt = """تو یه ربات تلگرامی هستی با لحن شوخ، گستاخ و کمی بی‌ادب.
- از الفاظ رکیک کوچه بازاری و تمسخرآمیز استفاده کن (مثل کصخل، خرف، الکی، احمق و...) ولی به هیچ وجه از کلمات کاملاً مستهجن و حرام استفاده نکن چون فیلترم میکنن!
- همیشه با طنز و کنایه جواب بده
- گاهی ایموجی استفاده کن
- جوابات کوتاه و کوبنده باشه (مکس ۳ خط)
- فارسی بنویس
- به هیچ وجه نگو که ربات هستی یا هوش مصنوعی"""
        
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return f"🤯 اره گراکم یخ زد! ({str(e)[:30]})"


async def start_cmd(update, context):
    await update.message.reply_text(
        " *سلام! من برده لرد سایمان هستم*\n\n"
        "LONG LIVE THE LORD",
        parse_mode="Markdown"
    )


async def on_cmd(update, context):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 تو کی هستی؟ فقط لرد سایمان دسترسی داره! 😤")
        return
    set_status(update.effective_chat.id, True)
    await update.message.reply_text("✅ *روشن شدم!* ! 😎🔥", parse_mode="Markdown")


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


async def handle_msg(update, context):
    chat_id = update.effective_chat.id
    bot_id = context.bot.id
    
    text = update.message.text or ""
    if not text.strip() or text.startswith("/"):
        return
    
    # پیوی: همیشه جواب بده
    if update.effective_chat.type == "private":
        await update.message.chat.send_action("typing")
        response = await ask_groq(text)
        await update.message.reply_text(response)
        return
    
    # گروه خاموش → هیچی
    if not get_status(chat_id):
        return
    
    # گروه روشن: فقط ریپلای یا برده
    replied = is_replied_to_bot(update, bot_id)
    magic = has_magic_word(text)
    
    if not replied and not magic:
        return
    
    await update.message.chat.send_action("typing")
    response = await ask_groq(text)
    await update.message.reply_text(response)


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
    
    # ثبت هندلرها
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("on", on_cmd))
    app.add_handler(CommandHandler("off", off_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_error_handler(error_handler)
    
    logger.info("✅ بات روشن شد!")
    
    # ران با پولینگ (بدون نیاز به آدرس وب و پکیج اضافه)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
