"""
ربات تلگرام با هوش مصنوعی گراک
"""

import os
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
    """چک کن آیا کسی به پیام بات ریپلای زده"""
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id == bot_id
    return False


def has_magic_word(text):
    """چک کن کلمه برده تو پیام هست یا نه"""
    return "برده" in text


async def ask_groq(prompt):
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        system_prompt = """تو یه ربات تلگرامی هستی با لحن شوخ‌طبعانه.
- همیشه با طنز جواب بده
- گاهی از حرفهایی مثل کسکش و کسشر و کسمغز و کیری و ... استفاده کن اگه دیدی طرفی که باهاش حرف میزنی استفاده کرد و گاهی ایموجی استفاده کن
- جوابات کوتاه باشه (مکس ۳ خط)
- فارسی بنویس
- نگو که ربات هستی"""
        
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
        return f"🤯 اره گراکم یخ زد! ({str(e)[:30]})"


async def start_cmd(update, context):
    await update.message.reply_text(
        " *سلام! من برده لرد سایمان هستم*\n\n"
        "زنده باد سیرالئون",
        parse_mode="Markdown"
    )


async def on_cmd(update, context):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 تو کی هستی؟ فقط لرد دسترسی داره! 😤")
        return
    set_status(update.effective_chat.id, True)
    await update.message.reply_text("✅ *روشن شدم!* ریپلای بزن یا بگو برده! 😎🔥", parse_mode="Markdown")


async def off_cmd(update, context):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 دسترسی نداری رفیق! 😂")
        return
    set_status(update.effective_chat.id, False)
    await update.message.reply_text("😴 *خاموش شدم!* کسمادر بدخواه سایمان... 🍕", parse_mode="Markdown")


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
    
    # ===== پیوی: همیشه جواب بده =====
    if update.effective_chat.type == "private":
        await update.message.chat.send_action("typing")
        response = await ask_groq(text)
        await update.message.reply_text(response)
        return
    
    # ===== گروه =====
    
    # خاموشه؟ → هیچی نگو
    if not get_status(chat_id):
        return
    
    # روشنه ولی ریپلای نزده و برده هم نگفته؟ → هیچی نگو
    replied = is_replied_to_bot(update, bot_id)
    magic = has_magic_word(text)
    
    if not replied and not magic:
        return
    
    # ریپلای یا برده بوده → جواب بده
    await update.message.chat.send_action("typing")
    response = await ask_groq(text)
    await update.message.reply_text(response)


async def error_handler(update, context):
    print(f"❌ خطا: {context.error}")


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده!")
        return
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY تنظیم نشده!")
        return
    
    print("🚀 بات داره روشن میشه...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("on", on_cmd))
    app.add_handler(CommandHandler("off", off_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_error_handler(error_handler)
    
    print("✅ بات روشن شد!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
