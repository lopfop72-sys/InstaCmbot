import os
import random
import string
import threading
import time

from flask import Flask
import instaloader

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# =========================================================
# إعدادات أساسية
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")


# =========================================================
# Flask - حتى يبقى Render يعتبر الخدمة تعمل
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "InstaCmbot is running"


def run_web():
    port = int(os.getenv("PORT", "10000"))
    app.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False
    )


# =========================================================
# Instagram
# =========================================================

loader = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
)


# =========================================================
# حالة الفحص
# =========================================================

scanning_users = set()


# =========================================================
# توليد أسماء Instagram
# =========================================================

def generate_username(length=4):
    """
    إنشاء اسم عشوائي من أحرف وأرقام وunderscore.
    مثال:
    a7x_
    m9q2
    z4_k
    """

    characters = string.ascii_lowercase + string.digits + "_"

    return "".join(
        random.choice(characters)
        for _ in range(length)
    )


# =========================================================
# فحص اسم مستخدم واحد
# =========================================================

def check_username(username):
    """
    يرجع:
    True  = الاسم غير موجود ويمكن أن يكون متاحًا
    False = الحساب موجود
    None  = حدث خطأ/تقييد ولا يمكن التأكد
    """

    try:
        instaloader.Profile.from_username(
            loader.context,
            username
        )

        # الحساب موجود
        return False

    except instaloader.exceptions.ProfileNotExistsException:
        # Instagram لم يجد الحساب
        return True

    except Exception as error:
        # لا نعتبر أي خطأ "متاح"
        print(f"Instagram error for @{username}: {error}")
        return None


# =========================================================
# فحص تلقائي
# =========================================================

def scan_usernames(chat_id, bot, stop_event, length=4, target=5):
    """
    يفحص أسماء تلقائيًا حتى يجد العدد المطلوب.
    """

    found = 0
    checked = 0

    while not stop_event.is_set() and found < target:

        username = generate_username(length)

        checked += 1

        result = check_username(username)

        if result is True:

            found += 1

            message = (
                "✅ اسم قد يكون متاحًا\n\n"
                f"👤 @{username}\n\n"
                f"https://www.instagram.com/{username}/\n\n"
                f"🔎 تم فحص: {checked}\n"
                f"🎯 المتاح: {found}/{target}"
            )

            try:
                bot.send_message(
                    chat_id=chat_id,
                    text=message
                )
            except Exception as error:
                print("Telegram send error:", error)

        elif result is None:

            # توقف بسيط عند حدوث خطأ حتى لا نزيد الضغط
            time.sleep(5)

        else:
            # الحساب موجود
            pass

        # تأخير بين الطلبات
        time.sleep(2)

    try:
        if stop_event.is_set():
            bot.send_message(
                chat_id=chat_id,
                text=(
                    "🛑 تم إيقاف الفحص.\n\n"
                    f"🔎 تم فحص: {checked}\n"
                    f"✅ تم العثور على: {found}"
                )
            )

        else:
            bot.send_message(
                chat_id=chat_id,
                text=(
                    "🏁 انتهى الفحص.\n\n"
                    f"🔎 تم فحص: {checked}\n"
                    f"✅ تم العثور على: {found}"
                )
            )

    except Exception as error:
        print("Telegram final message error:", error)

    scanning_users.discard(chat_id)


# =========================================================
# /start
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "🔎 فحص أسماء 4 خانات",
                callback_data="scan_4"
            )
        ],
        [
            InlineKeyboardButton(
                "🔎 فحص أسماء 5 خانات",
                callback_data="scan_5"
            )
        ],
        [
            InlineKeyboardButton(
                "🛑 إيقاف الفحص",
                callback_data="stop"
            )
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 أهلاً بك في InstaCmbot\n\n"
        "🤖 البوت يولّد أسماء Instagram تلقائيًا "
        "ويفحصها بحثًا عن أسماء غير موجودة.\n\n"
        "اختر نوع الفحص:",
        reply_markup=reply_markup
    )


# =========================================================
# /scan
# =========================================================

async def scan_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat_id = update.effective_chat.id

    if chat_id in scanning_users:
        await update.message.reply_text(
            "⚠️ يوجد فحص يعمل حاليًا.\n"
            "استخدم /stop لإيقافه."
        )
        return

    scanning_users.add(chat_id)

    stop_event = threading.Event()

    context.application.bot_data[
        f"stop_{chat_id}"
    ] = stop_event

    await update.message.reply_text(
        "🚀 بدأ الفحص التلقائي...\n\n"
        "سيقوم البوت بتوليد أسماء وفحصها تلقائيًا.\n"
        "لن تحتاج إلى إرسال أسماء بنفسك."
    )

    thread = threading.Thread(
        target=scan_usernames,
        args=(
            chat_id,
            context.bot,
            stop_event,
        ),
        kwargs={
            "length": 4,
            "target": 5,
        },
        daemon=True
    )

    thread.start()


# =========================================================
# /stop
# =========================================================

async def stop_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat_id = update.effective_chat.id

    stop_event = context.application.bot_data.get(
        f"stop_{chat_id}"
    )

    if stop_event:
        stop_event.set()

        await update.message.reply_text(
            "🛑 طلب إيقاف الفحص تم استلامه."
        )

    else:
        await update.message.reply_text(
            "ℹ️ لا يوجد فحص يعمل حاليًا."
        )


# =========================================================
# الأزرار
# =========================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    chat_id = query.message.chat_id

    # -----------------------------------------------------
    # إيقاف
    # -----------------------------------------------------

    if query.data == "stop":

        stop_event = context.application.bot_data.get(
            f"stop_{chat_id}"
        )

        if stop_event:
            stop_event.set()

            await query.message.reply_text(
                "🛑 جارٍ إيقاف الفحص..."
            )
        else:
            await query.message.reply_text(
                "ℹ️ لا يوجد فحص يعمل حاليًا."
            )

        return

    # -----------------------------------------------------
    # منع تشغيل أكثر من فحص
    # -----------------------------------------------------

    if chat_id in scanning_users:

        await query.message.reply_text(
            "⚠️ يوجد فحص يعمل بالفعل.\n"
            "انتظر حتى ينتهي أو اضغط إيقاف."
        )

        return

    # -----------------------------------------------------
    # تحديد طول الاسم
    # -----------------------------------------------------

    if query.data == "scan_4":
        length = 4
    elif query.data == "scan_5":
        length = 5
    else:
        return

    scanning_users.add(chat_id)

    stop_event = threading.Event()

    context.application.bot_data[
        f"stop_{chat_id}"
    ] = stop_event

    await query.message.reply_text(
        f"🚀 بدأ فحص أسماء بطول {length} خانات.\n\n"
        "🤖 البوت يولّد الأسماء ويفحصها تلقائيًا.\n"
        "⏳ قد يستغرق العثور على أسماء وقتًا بسبب "
        "حدود Instagram."
    )

    thread = threading.Thread(
        target=scan_usernames,
        args=(
            chat_id,
            context.bot,
            stop_event,
        ),
        kwargs={
            "length": length,
            "target": 5,
        },
        daemon=True
    )

    thread.start()


# =========================================================
# Main
# =========================================================

def main():

    # تشغيل Flask في الخلفية
    web_thread = threading.Thread(
        target=run_web,
        daemon=True
    )

    web_thread.start()

    print("Web server started")

    # إنشاء Telegram application
    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # الأوامر
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("scan", scan_command)
    )

    application.add_handler(
        CommandHandler("stop", stop_command)
    )

    # الأزرار
    application.add_handler(
        CallbackQueryHandler(button_handler)
    )

    print("Telegram bot is starting...")

    # تشغيل البوت
    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# تشغيل البرنامج
# =========================================================

if __name__ == "__main__":
    main()
