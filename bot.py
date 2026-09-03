import os
import time
import random
import string
import threading
import telebot
import requests

# 1. قراءة التوكن والمعلومات الأساسية من Render
BOT_TOKEN = os.environ.get('BOT_TOKEN')
# ضع معرف حسابك على تليجرام هنا لتلقي الإشعارات تلقائياً (يمكنك الحصول عليه من بوت @userinfobot)
# أو سيقوم البوت بإرسال المتاحات لك بمجرد تفعيل أمر /start
YOUR_CHAT_ID = os.environ.get('YOUR_CHAT_ID') 

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise ValueError("خطأ: لم يتم العثور على BOT_TOKEN بشكل صحيح في إعدادات Render.")

bot = telebot.TeleBot(BOT_TOKEN)
is_scanning = False  # متغير للتحكم في تشغيل وإيقاف الفحص التلقائي

# 2. دالة لتوليد اسم مستخدم عشوائي
def generate_random_username(length=5):
    # توليد اسم يتكون من أحرف صغيرة وأرقام ونقاط (صيغة إنستغرام المقبولة)
    characters = string.ascii_lowercase + string.digits + "._"
    # يفضل تبسيط التوليد لتجنب الرموز المتتالية غير المقبولة
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

# 3. دالة فحص توفر الاسم على إنستغرام
def check_instagram_username(username):
    url = f"https://instagram.com{username}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        # إرسال طلب خفيف (Head Request) لتوفير البيانات وسرعة الفحص
        response = requests.head(url, headers=headers, timeout=5)
        if response.status_code == 404:
            return True  # الحساب متاح أو غير موجود
        return False
    except requests.exceptions.RequestException:
        return None

# 4. دالة الفحص المستمر (تشغيل في الخلفية)
def auto_scanner(chat_id):
    global is_scanning
    bot.send_message(chat_id, "🚀 بدأت عملية التوليد والفحص التلقائي لأسماء المستخدمين المتاحة...")
    
    while is_scanning:
        # توليد اسم عشوائي بطول 5 أحرف (يمكنك تعديل الطول هنا)
        target_username = generate_random_username(length=5)
        
        status = check_instagram_username(target_username)
        
        if status is True:
            # إذا وجد اسماً متاحاً، يرسله إليك فوراً
            msg = f"🎉 اسم مستخدم متاح مقترح:\n\n🔗 @{target_username}\n\nسارع بفحصه أو تسجيله!"
            bot.send_message(chat_id, msg)
        
        # ⚠️ تأخير زمني أساسي بمقدار ثانيتين لتجنب حظر الـ IP السريع من إنستغرام
        time.sleep(2)

# 5. معالجات أوامر البوت على تليجرام
@bot.message_handler(commands=['start'])
def start_scan(message):
    global is_scanning
    if not is_scanning:
        is_scanning = True
        # تشغيل الفحص في مسار منفصل (Thread) لضمان عدم تعليق البوت
        threading.Thread(target=auto_scanner, args=(message.chat.id,)).start()
    else:
        bot.reply_to(message, "🔄 الفحص التلقائي يعمل بالفعل في الخلفية!")

@bot.message_handler(commands=['stop'])
def stop_scan(message):
    global is_scanning
    if is_scanning:
        is_scanning = False
        bot.reply_to(message, "🛑 تم إيقاف عملية الفحص التلقائي.")
    else:
        bot.reply_to(message, "الفحص متوقف حالياً.")

# 6. تشغيل البوت
if __name__ == '__main__':
    print("البوت جاهز للاستخدام...")
    bot.infinity_polling()
