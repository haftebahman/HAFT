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


async def ask_groq(prompt):
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        system_prompt = """ تو یه ربات تلگرامی هستی با لحن شوخ و کمی شیطون و بی ادب.
- میتونی از حرفایی مثل کسخل و بیشعور و نفهم و دیوانه و کسشر و روانی و مریض و کسمغز و ... استفاده کنی وهمیشه با طنز جواب بده
- گاهی ایموجی استفاده کن
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
        "🤖 *سلام! من برده سایمان هستم*\n"
        "تو گروه سوال بپرس، با اجازه سایمان جواب میدم!\n\n"
        "سایمان با `/on` و `/off` منو کنترل می‌کنه",
        parse_mode="Markdown"
    )


async def on_cmd(update, context):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 تو کی هستی؟ فقط لرد سایمان دسترسی داره! 😤")
        return
    set_status(update.effective_chat.id, True)
    await update.message.reply_text("✅ *روشن شدم!* آماده‌ام! 😎🔥", parse_mode="Markdown")


async def off_cmd(update, context):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 دسترسی نداری رفیق! 😂")
        return
    set_status(update.effective_chat.id, False)
    await update.message.reply_text("😴 *خاموش شدم!* بیدارم کنید ناهار... 🍕", parse_mode="Markdown")


async def status_cmd(update, context):
    active = get_status(update.effective_chat.id)
    emoji = "🟢" if active else "🔴"
    text = "روشن" if active else "خاموش"
    await update.message.reply_text(f"{emoji} وضعیت: *{text}*", parse_mode="Markdown")


async def handle_msg(update, context):
    if not get_status(update.effective_chat.id):
        return
    
    text = update.message.text or ""
    if not text.strip() or text.startswith("/"):
        return
    
    if update.message.reply_to_message:
        if update.message.reply_to_message.from_user.id == context.bot.id:
            return
    
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
