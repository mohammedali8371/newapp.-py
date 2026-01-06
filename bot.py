import os, random, requests
import telebot
from telebot.types import ReplyKeyboardMarkup
from config import BOT_TOKEN, OWNER_ID, CHANNEL_USERNAME, API_KEYS, DOWNLOAD_DIR, USERS_FILE, DECORATIONS

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ======== أدوات المستخدم ========
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

def random_decor(text):
    return "".join(random.choice(DECORATIONS) + c for c in text)

def get_available_api():
    return random.choice(API_KEYS)

# ======== قائمة الأزرار ========
def menu(is_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📥 تحميل", "🖌 تعديل صورة")
    kb.row("📢 القناة", "👤 المطور")
    kb.row("▶️ start")
    if is_admin:
        kb.row("👥 الأعضاء")
    return kb

# ======== /start ========
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    save_user(uid)

    if not check_sub(uid):
        bot.send_message(msg.chat.id,
            f"🚫 اشترك بالقناة أولاً\n\n📢 {CHANNEL_USERNAME}\n👤 المطور: {BOT_NAME}",
            reply_markup=menu(uid == OWNER_ID))
        return

    bot.send_message(msg.chat.id,
        f"👋 أهلاً بك في البوت\n\n📥 أرسل أي رابط للتحميل أو اضغط تعديل صورة\n📢 القناة: {CHANNEL_USERNAME}\n👤 المطور: {BOT_NAME}",
        reply_markup=menu(uid == OWNER_ID))

# ======== الرسائل النصية ========
@bot.message_handler(content_types=["text"])
def text_handler(msg):
    uid = msg.from_user.id
    save_user(uid)

    if not check_sub(uid):
        bot.send_message(msg.chat.id,
            f"🚫 اشترك بالقناة أولاً\n📢 {CHANNEL_USERNAME}")
        return

    if msg.text in ["▶️ start", "/start"]:
        start(msg)

    elif msg.text == "📢 القناة":
        bot.send_message(msg.chat.id, f"📢 القناة الرسمية:\n{CHANNEL_USERNAME}")

    elif msg.text == "👤 المطور":
        bot.send_message(msg.chat.id, f"👤 حساب المطور:\n{BOT_NAME}")

    elif msg.text == "📥 تحميل":
        bot.send_message(msg.chat.id, "📎 أرسل رابط الفيديو أو الصوت الآن")

    elif msg.text == "🖌 تعديل صورة":
        bot.send_message(msg.chat.id, "📎 أرسل الصورة الآن")

    elif msg.text == "👥 الأعضاء" and uid == OWNER_ID:
        with open(USERS_FILE) as f:
            users = f.read().splitlines()
        text = "\n".join(users) if users else "لا يوجد أعضاء"
        bot.send_message(msg.chat.id, f"👥 الأعضاء:\n{text}")

    elif msg.text.startswith("http"):
        download(msg)

# ======== تحميل الفيديوهات ========
import yt_dlp
def download(msg):
    wait = bot.send_message(msg.chat.id, "⚡ جاري التحميل...")

    opts = {"format":"best","outtmpl":f"{DOWNLOAD_DIR}/%(title)s.%(ext)s","quiet":True,"noplaylist":True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(msg.text, download=True)
            path = ydl.prepare_filename(info)

        bot.send_document(msg.chat.id, open(path,"rb"), caption=f"✅ تم التحميل\n📢 {CHANNEL_USERNAME}\n👤 {BOT_NAME}")
        os.remove(path)
        bot.delete_message(msg.chat.id, wait.message_id)
    except:
        bot.edit_message_text("❌ فشل التحميل", msg.chat.id, wait.message_id)

# ======== تعديل الصور ========
def edit_image(image_path):
    api_key = get_available_api()
    url = "https://api-inference.huggingface.co/models/your-model"
    headers = {"Authorization": f"Bearer {api_key}"}
    with open(image_path, "rb") as f:
        data = f.read()
    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            out_path = image_path.replace(".", "_edited.")
            with open(out_path, "wb") as out:
                out.write(response.content)
            return out_path
        elif "quota" in response.text.lower():
            return edit_image(image_path)
        else:
            return None
    except:
        return None

@bot.message_handler(content_types=["photo"])
def handle_photo(msg):
    file_info = bot.get_file(msg.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    path = f"{DOWNLOAD_DIR}/{msg.from_user.id}_photo.jpg"
    with open(path, "wb") as f:
        f.write(downloaded_file)

    edited = edit_image(path)
    if edited:
        bot.send_photo(msg.chat.id, open(edited, "rb"), caption="✅ تم تعديل الصورة")
    else:
        bot.send_message(msg.chat.id, "❌ فشل تعديل الصورة، حاول لاحقًا")

# ======== تشغيل البوت ========
bot.infinity_polling(skip_pending=True)
