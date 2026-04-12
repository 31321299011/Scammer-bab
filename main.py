import telebot
from telebot import types
import json
import os
import threading
import time
from flask import Flask
from collections import defaultdict

# ========================= CONFIG =========================
API_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770
CHANNEL_USERNAME = "@earning_channel24"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# ========================= DATABASE =========================
DB_FILE = 'database.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "scammers": [],
        "admins": [OWNER_ID],
        "users": []
    }

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# User Report State
user_state = defaultdict(dict)

# ========================= HELPERS =========================
def is_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def is_bot_admin(user_id):
    return user_id in db['admins'] or user_id == OWNER_ID

def is_group_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def is_scammer(user_id, bikash=None):
    for s in db['scammers']:
        if str(s.get('user_id')) == str(user_id) or (bikash and s.get('bikash') == bikash):
            return True
    return False

def add_scammer(user_id, username=None, bikash=None, proof_details="", added_by=OWNER_ID):
    new_scam = {
        "user_id": int(user_id),
        "username": username,
        "bikash": bikash,
        "proof_details": proof_details,
        "added_by": added_by,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    db['scammers'].append(new_scam)
    save_db(db)

# ========================= FLASK =========================
@app.route('/')
def index():
    return "✅ Premium Anti-Scam Bot Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ========================= BOX BUTTON MENU (Private Chat) =========================
def send_main_menu(chat_id, user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚨 স্ক্যামার রিপোর্ট করুন")
    markup.add("❓ হেল্প", "👤 আমার স্ট্যাটাস")
    if is_bot_admin(user_id):
        markup.add("🛠 Admin Panel")
    
    text = (
        "👋 স্বাগতম! প্রিমিয়াম এন্টি-স্ক্যাম বট\n\n"
        "নিচের বাটন থেকে যা চান তা চাপুন।\n\n"
        "Developer: @jhgmaing + @bot_developer_io"
    )
    bot.send_message(chat_id, text, reply_markup=markup)

# ========================= START =========================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in db['users']:
        db['users'].append(user_id)
        save_db(db)

    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url="https://t.me/earning_channel24"))
        markup.add(types.InlineKeyboardButton("✅ জয়েন চেক করুন", callback_data="check_join"))
        bot.send_message(
            message.chat.id,
            "❌ আপনি চ্যানেলে জয়েন করেননি।\nপ্রথমে জয়েন করে **জয়েন চেক করুন** বাটন চাপুন।",
            reply_markup=markup
        )
        return

    send_main_menu(message.chat.id, user_id)

# ========================= TEXT HANDLER (Box Button) =========================
@bot.message_handler(func=lambda m: True)
def handle_buttons(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if not is_joined(user_id):
        bot.reply_to(message, "❌ প্রথমে চ্যানেলে জয়েন করুন!")
        return

    if text == "🚨 স্ক্যামার রিপোর্ট করুন":
        if not is_joined(user_id):
            bot.reply_to(message, "❌ চ্যানেলে জয়েন করুন!")
            return
        user_state[user_id] = {"step": "chatid", "data": {}}
        bot.reply_to(message, "🔹 **Step 1:** স্ক্যামারের Chat ID অথবা @username দিন:")

    elif text == "❓ হেল্প":
        help_text = (
            "📖 **হেল্প**\n\n"
            "• স্ক্যামার রিপোর্ট করুন বাটন চাপুন\n"
            "• ৪টা স্টেপে তথ্য দিন\n"
            "• গ্রুপে স্ক্যামার অটো ব্যান হয়\n"
            "• গ্রুপ অ্যাডমিন /unban <id> করতে পারবেন"
        )
        bot.reply_to(message, help_text)

    elif text == "👤 আমার স্ট্যাটাস":
        total = len(db['scammers'])
        bot.reply_to(message, f"📊 মোট স্ক্যামার: {total}\n🆔 আপনার আইডি: {user_id}")

    elif text == "🛠 Admin Panel" and is_bot_admin(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add("📋 সব স্ক্যামার দেখুন")
        markup.add("🚫 স্ক্যামার রিমুভ")
        markup.add("👑 নতুন Bot Admin যোগ")
        markup.add("🔙 মেনুতে ফিরুন")
        bot.send_message(message.chat.id, "🛠 Admin Control Panel", reply_markup=markup)

    elif text == "📋 সব স্ক্যামার দেখুন" and is_bot_admin(user_id):
        if not db['scammers']:
            bot.reply_to(message, "কোনো স্ক্যামার নেই।")
            return
        txt = "📋 **সব স্ক্যামার**\n\n"
        for s in db['scammers']:
            txt += f"🆔 `{s['user_id']}` | বিকাশ: {s.get('bikash', 'নেই')}\n"
        bot.reply_to(message, txt, parse_mode='Markdown')

    elif text == "🚫 স্ক্যামার রিমুভ" and is_bot_admin(user_id):
        bot.reply_to(message, "🚫 রিমুভ করতে Chat ID দিন:")
        bot.register_next_step_handler(message, process_remove_scammer)

    elif text == "👑 নতুন Bot Admin যোগ" and user_id == OWNER_ID:
        bot.reply_to(message, "👑 নতুন Bot Admin এর Chat ID দিন:")
        bot.register_next_step_handler(message, process_add_bot_admin)

    elif text == "🔙 মেনুতে ফিরুন":
        send_main_menu(message.chat.id, user_id)

    # Report Steps
    elif user_id in user_state:
        state = user_state[user_id]
        step = state["step"]

        if step == "chatid":
            state["data"]["scammer_id"] = text
            state["step"] = "bikash"
            bot.reply_to(message, "🔹 **Step 2:** বিকাশ নাম্বার দিন (না থাকলে `skip` লিখুন)")

        elif step == "bikash":
            bikash = None if text.lower() == "skip" else text
            state["data"]["bikash"] = bikash
            state["step"] = "details"
            bot.reply_to(message, "🔹 **Step 3:** বিস্তারিত কারণ লিখুন")

        elif step == "details":
            state["data"]["details"] = text
            state["step"] = "photo"
            bot.reply_to(message, "🔹 **Step 4:** প্রমাণের ছবি (Screenshot) পাঠান")

        elif step == "photo":
            if not message.photo:
                bot.reply_to(message, "❌ ছবি পাঠান!")
                return
            file_id = message.photo[-1].file_id
            data = state["data"]

            # Admin-এর জন্য Inline Approve/Reject
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ Approve", callback_data="approve_report"),
                types.InlineKeyboardButton("❌ Reject", callback_data="reject_report")
            )

            caption = f"🆕 নতুন রিপোর্ট\nরিপোর্টার: {user_id}\nস্ক্যামার: {data.get('scammer_id')}\nবিকাশ: {data.get('bikash','নেই')}\nকারণ: {data.get('details')}"

            bot.send_photo(OWNER_ID, file_id, caption=caption, reply_markup=markup)
            bot.reply_to(message, "✅ রিপোর্ট অ্যাডমিনদের কাছে পাঠানো হয়েছে।")
            del user_state[user_id]

# ========================= APPROVE / REJECT (Inline) =========================
@bot.callback_query_handler(func=lambda call: call.data in ["approve_report", "reject_report"])
def handle_approval(call):
    bot.answer_callback_query(call.id)
    if not is_bot_admin(call.from_user.id):
        bot.send_message(call.message.chat.id, "❌ আপনি অ্যাডমিন নন!")
        return

    if call.data == "reject_report":
        bot.edit_message_caption("❌ রিপোর্ট রিজেক্ট করা হয়েছে।", call.message.chat.id, call.message.message_id)
        return

    bot.edit_message_caption("✅ এপ্রুভ হয়েছে। এখন সঠিক Chat ID দিন:", call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, save_approved_scammer)

def save_approved_scammer(message):
    if not is_bot_admin(message.from_user.id):
        return
    try:
        scammer_id = int(message.text.strip())
        add_scammer(scammer_id, None, None, "Approved by Admin", message.from_user.id)
        bot.reply_to(message, f"✅ স্ক্যামার `{scammer_id}` সেভ হয়েছে।")
    except:
        bot.reply_to(message, "❌ ভুল Chat ID!")

# ========================= GROUP FEATURES (Inline) =========================
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    for member in message.new_chat_members:
        if member.is_bot or not is_scammer(member.id):
            continue
        try:
            bot.ban_chat_member(message.chat.id, member.id)
            username = f"@{member.username}" if member.username else "No username"
            bot.send_message(
                message.chat.id,
                f"🚫 **সালা আইছিল টাকা মারতে! ভরে দিছি 🔥**\n\n"
                f"ইউজার: {username}\nChat ID: `{member.id}`\nলিঙ্ক: tg://user?id={member.id}"
            )
        except:
            pass

@bot.message_handler(func=lambda m: True)
def handle_group_messages(message):
    if message.chat.type not in ['group', 'supergroup']:
        return

    text = (message.text or "").lower()
    keywords = ['scam', 'scammer', 'টাকা মারছে', 'টাকা মারে', 'প্রতারক', 'ঠকাইছে']

    if any(k in text for k in keywords):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚨 Report Scammer", callback_data="start_report"))
        bot.reply_to(message, "⚠️ স্ক্যাম সংক্রান্ত কথা চলছে। প্রমাণ থাকলে রিপোর্ট করুন।", reply_markup=markup)

    if f"@{bot.get_me().username}" in (message.text or ""):
        bot.reply_to(message, "✅ আমি এন্টি-স্ক্যাম বট। Report Scammer বাটন ব্যবহার করুন।")

# ========================= UNBAN =========================
@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "শুধু গ্রুপে চলবে।")
        return
    try:
        target = int(message.text.split()[1])
    except:
        bot.reply_to(message, "ব্যবহার: /unban <user_id>")
        return

    if is_group_admin(message.chat.id, message.from_user.id) or is_bot_admin(message.from_user.id):
        try:
            bot.unban_chat_member(message.chat.id, target, only_if_banned=True)
            db['scammers'] = [s for s in db['scammers'] if s['user_id'] != target]
            save_db(db)
            bot.reply_to(message, f"✅ {target} আনব্যান + ডাটাবেস থেকে রিমুভ হয়েছে।")
        except:
            bot.reply_to(message, "❌ সমস্যা হয়েছে।")
    else:
        bot.reply_to(message, "❌ গ্রুপ অ্যাডমিন বা Bot Admin হতে হবে।")

# Broadcast & Addadmin
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if not is_bot_admin(message.from_user.id): return
    txt = message.text.replace('/broadcast', '').strip()
    if not txt:
        bot.reply_to(message, "মেসেজ লিখুন!")
        return
    count = 0
    for uid in db['users']:
        try:
            bot.send_message(uid, f"📣 **Broadcast**\n\n{txt}")
            count += 1
        except:
            pass
    bot.reply_to(message, f"✅ {count} জনকে পাঠানো হয়েছে।")

@bot.message_handler(commands=['addadmin'])
def add_admin_cmd(message):
    if message.from_user.id != OWNER_ID: return
    try:
        new_id = int(message.text.split()[1])
        if new_id not in db['admins']:
            db['admins'].append(new_id)
            save_db(db)
            bot.reply_to(message, f"✅ {new_id} Bot Admin হয়েছে।")
    except:
        bot.reply_to(message, "ব্যবহার: /addadmin <chat_id>")

def process_remove_scammer(message):
    if not is_bot_admin(message.from_user.id): return
    try:
        sid = int(message.text.strip())
        db['scammers'] = [s for s in db['scammers'] if s['user_id'] != sid]
        save_db(db)
        bot.reply_to(message, f"✅ {sid} রিমুভ হয়েছে।")
    except:
        bot.reply_to(message, "❌ ভুল ID!")

def process_add_bot_admin(message):
    if message.from_user.id != OWNER_ID: return
    try:
        nid = int(message.text.strip())
        if nid not in db['admins']:
            db['admins'].append(nid)
            save_db(db)
            bot.reply_to(message, f"✅ {nid} Bot Admin হয়েছে।")
    except:
        bot.reply_to(message, "❌ ভুল ID!")

# ========================= RUN =========================
if __name__ == "__main__":
    print("🚀 Premium Anti-Scam Bot Started - Box Button in Private + Inline in Group")
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling(none_stop=True)
