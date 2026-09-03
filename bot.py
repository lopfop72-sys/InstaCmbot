import telebot
import requests

# استبدل هذا التوكن بالتوكن الخاص بـ بوتك من BotFather
BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
bot = telebot.TeleBot(BOT_TOKEN)

# دالة لفحص ما إذا كان اسم المستخدم متاحاً
def check_instagram_username(username):
    url = f"https://instagram.com{username}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        # إذا كانت استجابة الصفحة 404، فهذا يعني غالباً أن الحساب غير موجود (متاح)
        if response.status_code == 404:
            return "متاح (أو محظور/مخفي)"
        elif response.status_code == 200:
            return "غير متاح (مأخوذ)"
        else:
            return "غير معروف (قد تواجه قيوداً من إنستغرام)"
    except requests.exceptions.RequestException:
        return "خطأ في الاتصال بالخادم"

# استقبال أمر البدء
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! أرسل لي اسم المستخدم (Username) الذي تريد فحص توفره على إنستغرام.")

# استقبال اسم المستخدم وفحصه
@bot.message_handler(func=lambda message: True)
def handle_username(message):
    username = message.text.strip()
    
    # التحقق من أن المدخل عبارة عن كلمة واحدة تشبه اسم المستخدم
    if " " in username or len(username) > 30:
        bot.reply_to(message, "الرجاء إرسال اسم مستخدم صحيح وبدون مسافات.")
        return

    bot.reply_to(message, f"جاري فحص: {username}...")
    result = check_instagram_username(username)
    
    bot.reply_to(message, f"حالة اسم المستخدم @{username}:\n{result}")

# تشغيل البوت بشكل مستمر
bot.infinity_polling()
