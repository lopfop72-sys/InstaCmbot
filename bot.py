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
# TOKEN
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")


# =========================================================
# WEB SERVER
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
# INSTAGRAM
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
# SCAN STATE
# =========================================================

active_scans = {}
used_names = set()

lock = threading.Lock()


# =========================================================
# GENERATE USERNAME
# =========================================================

def generate_username(length):

    characters = (
        string.ascii_lowercase
        + string.digits
        + "_"
    )

    while True:

        username = "".join(
            random.choice(characters)
            for _ in range(length)
        )

        if username not in used_names:

            used_names.add(username)

            return username


# =========================================================
# CHECK USERNAME
# =========================================================

def check_username(username):

    try:

        instaloader.Profile.from_username(
            loader.context,
            username
        )

        # الحساب موجود
        return "taken"

    except instaloader.exceptions.ProfileNotExistsException:

        # Instagram يقول إن الحساب غير موجود
        return "possibly_available"

    except Exception as error:

        error_text = str(error)

        print(
            f"Instagram error for @{username}: "
            f"{error_text}"
        )

        if (
            "429" in error_text
            or "Too Many Requests" in error_text
            or "rate" in error_text.lower()
        ):
            return "rate_limited"

        return "error"


# =========================================================
# SCAN
# =========================================================

def scan_worker(
    chat_id,
    bot,
    stop_event,
    length,
    target
):

    found = 0
    checked = 0

    print(
        f"Starting scan for chat {chat_id}, "
        f"length={length}"
    )

    while (
        not stop_event.is_set()
        and found < target
    ):

        username = generate_username(length)

        print(
            f"Checking @{username}"
        )

        result = check_username(username)

        checked += 1

        # -------------------------------------------------
        # POSSIBLY AVAILABLE
        # -------------------------------------------------

        if result == "possibly_available":

            found += 1

            text = (
                "🟢 اسم غير موجود حاليًا\n\n"
                f"👤 @{username}\n\n"
                f"https://www.instagram.com/"
                f"{username}/\n\n"
                f"🔎 الفحوصات: {checked}\n"
                f"✅ النتائج: {found}/{target}\n\n"
                "⚠️ يجب التأكد من توفر الاسم "
                "مباشرة داخل Instagram."
            )

            try:

                bot.send_message(
                    chat_id=chat_id,
                    text=text
                )

            except Exception as error:

                print(
                    "Telegram error:",
                    error
                )

        # -------------------------------------------------
        # RATE LIMIT
        # -------------------------------------------------

        elif result == "rate_limited":

            try:

                bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "🛑 Instagram قام بتقييد "
                        "طلبات الفحص مؤقتًا.\n\n"
                        f"🔎 تم فحص: {checked}\n"
                        f"✅ النتائج: {found}\n\n"
                        "لن أواصل إرسال الطلبات حتى "
                        "لا يزداد التقييد."
                    )
                )

            except Exception as error:

                print(
                    "Telegram error:",
                    error
                )

            break

        # -------------------------------------------------
        # OTHER ERROR
        # -------------------------------------------------

        elif result == "error":

            print(
                f"Could not verify @{username}"
            )

        # -------------------------------------------------
        # DELAY
        # -------------------------------------------------

        # انتظار طويل نسبيًا لتقليل احتمال التقييد
        wait_time = random.randint(20, 40)

        print(
            f"Waiting {wait_time} seconds..."
        )

        for _ in range(wait_time):

            if stop_event.is_set():
                break

            time.sleep(1)

    # =====================================================
    # FINISH
    # =====================================================

    if stop_event.is_set():

        message = (
            "🛑 تم إيقاف الفحص.\n\n"
            f"🔎 تم فحص: {checked}\n"
            f"🟢 النتائج: {found}"
        )

    elif found >= target:

        message = (
            "🏁 انتهى الفحص.\n\n"
            f"🔎 تم فحص: {checked}\n"
            f"🟢 النتائج: {found}/{target}"
        )

    else:

        message = (
            "⏸️ توقف الفحص بسبب تقييد Instagram.\n\n"
            f"🔎 تم فحص: {checked}\n"
            f"🟢 النتائج: {found}"
        )

    try:

        bot.send_message(
            chat_id=chat_id,
            text=message
        )

    except Exception as error:

        print(
            "Final Telegram error:",
            error
        )

    with lock:

        active_scans.pop(
            chat_id,
            None
        )

    print(
        f"Scan finished for chat {chat_id}"
    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    keyboard = [

        [
            InlineKeyboardButton(
                "🔎 أسماء 4 خانات",
                callback_data="scan_4"
            )
        ],

        [
            InlineKeyboardButton(
                "🔎 أسماء 5 خانات",
                callback_data="scan_5"
            )
        ],

        [
            InlineKeyboardButton(
                "🛑 إيقاف",
                callback_data="stop"
            )
        ],

    ]

    await update.message.reply_text(

        "👋 أهلاً بك في InstaCmbot\n\n"

        "🤖 البوت يولّد أسماء Instagram "
        "تلقائيًا ويفحصها.\n\n"

        "اختر نوع الأسماء:",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# START SCAN
# =========================================================

async def start_scan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    length
):

    chat_id = update.effective_chat.id

    with lock:

        if chat_id in active_scans:

            await update.effective_message.reply_text(
                "⚠️ يوجد فحص يعمل بالفعل."
            )

            return

        stop_event = threading.Event()

        active_scans[chat_id] = stop_event

    await update.effective_message.reply_text(

        f"🚀 بدأ فحص أسماء بطول {length} خانات.\n\n"

        "🤖 سأولد الأسماء تلقائيًا.\n"

        "⏳ سأضع فواصل زمنية بين الطلبات "
        "لتقليل احتمال تقييد Instagram.\n\n"

        "📩 عندما تظهر نتيجة سأرسلها لك تلقائيًا."
    )

    thread = threading.Thread(

        target=scan_worker,

        args=(

            chat_id,
            context.bot,
            stop_event,
            length,
            5

        ),

        daemon=True
    )

    thread.start()


# =========================================================
# BUTTONS
# =========================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    chat_id = query.message.chat_id

    # -----------------------------------------------------
    # STOP
    # -----------------------------------------------------

    if query.data == "stop":

        with lock:

            stop_event = active_scans.get(
                chat_id
            )

        if stop_event:

            stop_event.set()

            await query.message.reply_text(
                "🛑 تم إرسال أمر الإيقاف."
            )

        else:

            await query.message.reply_text(
                "ℹ️ لا يوجد فحص يعمل الآن."
            )

        return

    # -----------------------------------------------------
    # SCAN
    # -----------------------------------------------------

    if query.data == "scan_4":

        await start_scan(
            update,
            context,
            4
        )

    elif query.data == "scan_5":

        await start_scan(
            update,
            context,
            5
        )


# =========================================================
# COMMANDS
# =========================================================

async def scan_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await start_scan(
        update,
        context,
        5
    )


async def stop_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat_id = update.effective_chat.id

    with lock:

        stop_event = active_scans.get(
            chat_id
        )

    if stop_event:

        stop_event.set()

        await update.message.reply_text(
            "🛑 جارٍ إيقاف الفحص..."
        )

    else:

        await update.message.reply_text(
            "ℹ️ لا يوجد فحص يعمل الآن."
        )


# =========================================================
# MAIN
# =========================================================

def main():

    # Flask
    web_thread = threading.Thread(
        target=run_web,
        daemon=True
    )

    web_thread.start()

    print(
        "Web server started"
    )

    # Telegram
    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "scan",
            scan_command
        )
    )

    application.add_handler(
        CommandHandler(
            "stop",
            stop_command
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    print(
        "Telegram bot is starting..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
