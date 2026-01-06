import os, random, re
import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from config import *
import yt_dlp
import requests

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ===== حفظ الأعضاء =====
def save_user(uid):
    uid = str(uid)
    if not os.path.exists(USERS_FILE):
        open(USERS_FILE, "w").close()
    with open(USERS_FILE, "r+") as f:
        users = f.read().splitlines()
        if uid not in users:
            f.write(uid + "\n")

def check_sub(uid):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ===== زخرفة النصوص =====
def decorate(text, style):
    return "".join(random.choice(DECORATIONS_SETS[style]) + c for c in text)

# ===== قائمة المستخدم =====
def main_menu(is_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📥 تحميل")
    kb.row("🎨 زخرفة", "🏠 القائمة الرئيسية")
    kb.row("💬 AI", "📢 القناة")
    kb.row("👤 المطور")
    if is_admin:
        kb.row("👥 الأعضاء")
    return kb

def decoration_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    for key in DECORATIONS_SETS.keys():
        kb.add(InlineKeyboardButton(text=key, callback_data=f"decor_{key}"))
    kb.add(InlineKeyboardButton(text="🏠 العودة للقائمة الرئيسية", callback_data="main_menu"))
    return kb

# ===== /start =====
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    save_user(uid)

    if not check_sub(uid):
        bot.send_message(msg.chat.id,
            f"🚫 اشترك بالقناة أولاً\n📢 {CHANNEL_USERNAME}\n👤 المطور: {BOT_NAME}",
            reply_markup=main_menu(uid==OWNER_ID))
        return

    bot.send_message(msg.chat.id,
        f"👋 أهلاً بك في البوت\n📥 أرسل رابط الفيديو للتحميل\n📢 القناة: {CHANNEL_USERNAME}\n👤 المطور: {BOT_NAME}",
        reply_markup=main_menu(uid==OWNER_ID))

# ===== التعامل مع الرسائل =====
@bot.message_handler(content_types=["text"])
def text_handler(msg):
    uid = msg.from_user.id
    save_user(uid)

    if not check_sub(uid):
        bot.send_message(msg.chat.id,
            f"🚫 اشترك بالقناة أولاً\n📢 {CHANNEL_USERNAME}")
        return

    text = msg.text.strip()

    if text == "📥 تحميل":
        bot.send_message(msg.chat.id, "📎 أرسل رابط الفيديو الآن")
    elif text == "🎨 زخرفة":
        bot.send_message(msg.chat.id, "اختر نوع الزخرفة:", reply_markup=decoration_menu())
    elif text == "🏠 القائمة الرئيسية":
        bot.send_message(msg.chat.id, "🏠 القائمة الرئيسية:", reply_markup=main_menu(uid==OWNER_ID))
    elif text == "📢 القناة":
        bot.send_message(msg.chat.id, f"📢 القناة الرسمية:\n{CHANNEL_USERNAME}")
    elif text == "👤 المطور":
        bot.send_message(msg.chat.id, f"👤 حساب المطور:\n{BOT_NAME}")
    elif text == "👥 الأعضاء" and uid == OWNER_ID:
        with open(USERS_FILE) as f:
            users = f.read().splitlines()
        bot.send_message(msg.chat.id, "👥 الأعضاء:\n" + ("\n".join(users) if users else "لا يوجد أعضاء"))
    elif text == "💬 AI":
        bot.send_message(msg.chat.id, "💬 أرسل أي رسالة لتجربة AI الذكي!")
    elif re.match(r'^https?://', text):
        download(msg)
    else:
        if uid == OWNER_ID:
            bot.send_message(msg.chat.id, f"📬 رسالة غير مصنفة:\n{text}")

# ===== أزرار الزخارف =====
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    uid = call.from_user.id
    if call.data.startswith("decor_"):
        style = call.data.split("_")[1]
        bot.send_message(call.message.chat.id,
            f"✍️ أرسل النص للزخرفة ({style}):")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, lambda msg: send_decorated(msg, style))
    elif call.data == "main_menu":
        bot.edit_message_text("🏠 العودة للقائمة الرئيسية", call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "🏠 القائمة الرئيسية:", reply_markup=main_menu(uid==OWNER_ID))

def send_decorated(msg, style):
    decorated = decorate(msg.text, style)
    bot.send_message(msg.chat.id, f"🎨 النتيجة:\n{decorated}", reply_markup=decoration_menu())

# ===== تحميل الفيديو =====
def download(msg):
    wait = bot.send_message(msg.chat.id, "⚡ جاري التحميل...")
    url = msg.text.strip()

    opts = {
        "format":"best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "merge_output_format": "mp4"
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)

        bot.send_document(msg.chat.id, open(path, "rb"),
                          caption=f"✅ تم التحميل\n📢 {CHANNEL_USERNAME}\n👤 {BOT_NAME}")
        os.remove(path)
        bot.delete_message(msg.chat.id, wait.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ فشل التحميل\n{str(e)}", msg.chat.id, wait.message_id)

# ===== AI بسيط =====
@bot.message_handler(func=lambda m: True)
def ai_handler(msg):
    if msg.text and msg.text != "":
        try:
            resp = requests.post(
                "https://api-inference.huggingface.co/models/gpt2",
                headers={"Authorization": f"Bearer {AI_API_KEY}"},
                json={"inputs": msg.text}
            ).json()
            if isinstance(resp, list):
                text = resp[0]["generated_text"]
                bot.send_message(msg.chat.id, f"🤖 AI:\n{text}")
        except:
            bot.send_message(msg.chat.id, "❌ فشل الرد الذكي، حاول لاحقاً.")

# ===== تشغيل البوت =====
bot.infinity_polling(skip_pending=True)
