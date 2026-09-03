import os
import threading
import asyncio

from flask import Flask
import instaloader

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")


# =========================
# Flask
# =========================

app = Flask(__name__)


@app.route("/")
def home():
    return "InstaCmbot is running"


def run_web():
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)


# =========================
# Instagram
# =========================

loader = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
)


def instagram_info(username):
    username = username.strip().lstrip("@")

    try:
        profile = instaloader.Profile.from_username(
            loader.context,
            username
        )

        return (
            "📊 معلومات الحساب\n\n"
            f"👤 المستخدم: @{profile.username}\n"
            f"📝 الاسم: {profile.full_name or 'غير متوفر'}\n"
            f"👥 المتابعون: {profile.followers}\n"
            f"➡️ يتابع: {profile.followees}\n"
            f"📸 المنشورات: {profile.mediacount}\n"
            f"🔒 خاص: {'نعم' if profile.is_private else 'لا'}\n"
            f"✓ موثق: {'نعم' if profile.is_verified else 'لا'}\n\n"
            f"https://www.instagram.com/{profile.username}/"
        )

    except Exception as error:
        print("Instagram error:", error)

        return (
            "❌ تعذر الوصول إلى الحساب.\n"
            "تأكد من اسم المستخدم وحاول مرة أخرى."
        )


# =========================
# Telegram
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك!\n\n"
        "أرسل اسم مستخدم Instagram، مثل:\n"
        "@instagram"
    )


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    username = update.message.text.strip()

    if username.startswith("https://www.instagram.com/"):
        username = username.rstrip("/").split("/")[-1]

    username = username.lstrip("@")

    if not username:
        await update.message.reply_text("❌ أرسل اسم المستخدم.")
        return

    await update.message.reply_text("🔎 جاري البحث...")

    loop = asyncio.get_running_loop()

    result = await loop.run_in_executor(
        None,
        instagram_info,
        username
    )

    await update.message.reply_text(result)


async def run_bot():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    print("Telegram bot is running")

    await asyncio.Event().wait()


# =========================
# Main
# =========================

if __name__ == "__main__":
    web_thread = threading.Thread(
        target=run_web,
        daemon=True
    )

    web_thread.start()

    asyncio.run(run_bot())
