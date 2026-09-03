import os
import asyncio
import threading

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

# =========================
# الإعدادات
# =========================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")

# =========================
# Flask
# =========================

app = Flask(__name__)


@app.route("/")
def home():
    return "InstaCmbot is running ✅"


@app.route("/health")
def health():
    return "OK"


def run_web():
    port = int(os.environ.get("PORT", 10000))
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
    compress_json=False,
)


def get_instagram_info(username):
    username = username.strip().lstrip("@")

    try:
        profile = instaloader.Profile.from_username(
            loader.context,
            username
        )

        return (
            "📊 معلومات الحساب\n\n"
            f"👤 Username: @{profile.username}\n"
            f"📝 الاسم: {profile.full_name or 'غير متوفر'}\n"
            f"👥 المتابعون: {profile.followers}\n"
            f"➡️ يتابع: {profile.followees}\n"
            f"📸 المنشورات: {profile.mediacount}\n"
            f"🔒 خاص: {'نعم' if profile.is_private else 'لا'}\n"
            f"✓ موثق: {'نعم' if profile.is_verified else 'لا'}\n\n"
            f"🔗 https://www.instagram.com/{profile.username}/"
        )

    except Exception as e:
        print("Instagram error:", e)

        return (
            "❌ لم أستطع الوصول إلى هذا الحساب.\n\n"
            "تأكد من أن اسم المستخدم صحيح، "
            "وقد يكون Instagram قد منع الطلب مؤقتًا."
        )


# =========================
# Telegram
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك!\n\n"
        "أرسل لي اسم مستخدم Instagram، مثال:\n"
        "@instagram\n\n"
        "وسأحاول إظهار المعلومات العامة المتاحة عنه."
    )


async def handle_username(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    username = update.message.text.strip()

    if username.startswith("http"):
        username = username.rstrip("/").split("/")[-1]

    username = username.lstrip("@")

    if not username:
        await update.message.reply_text(
            "❌ أرسل اسم المستخدم."
        )
        return

    await update.message.reply_text(
        "🔎 جاري البحث..."
    )

    loop = asyncio.get_running_loop()

    result = await loop.run_in_executor(
        None,
        get_instagram_info,
        username
    )

    await update.message.reply_text(result)


# =========================
# تشغيل البوت
# =========================

async def main():
    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_username
        )
    )

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    print("Telegram bot is running ✅")

    # إبقاء البرنامج يعمل
    await asyncio.Event().wait()


if __name__ == "__main__":

    # Flask في Thread منفصل
    web_thread = threading.Thread(
        target=run_web,
        daemon=True
   
