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

# User State for Report (Inline Flow)
user_state = defaultdict(dict)   # {user_id: {"step": "chatid", "data": {...}} }

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
    return "✅ Anti-Scam Bot is Running Smoothly!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ========================= MAIN MENU (Inline) =========================
def send_main_menu(chat_id, user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🚨 স্ক্যামার রিপোর্ট করুন", callback_data="start_report"),
        types.InlineKeyboardButton("❓ হেল্প", callback_data="help_cmd"),
        types.InlineKeyboardButton("👤 আমার স্ট্যাটাস", callback_data="my_status")
    )
    if is_bot_admin(user_id):
        markup.add(types.InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel"))

    bot.send_message(
        chat_id,
        "👋 স্বাগতম! প্রফেশনাল এন্টি-স্ক্যাম বট\n\n"
        "স্ক্যামার দেখলে প্রমাণসহ রিপোর্ট করুন।\n"
        "গ্রুপে স্ক্যামার অটো ব্যান হবে।\n\n"
        "Developer: @jhgmaing + @bot_developer_io",
        reply_markup=markup
    )

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in db['users']:
        db['users'].append(user_id)
        save_db(db)

    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url="https://t.me/earning_channel24"))
        markup.add(types.InlineKeyboardButton("✅ জয়েন চেক", callback_data="check_join"))
        bot.send_message(message.chat.id, "❌ চ্যানেলে জয়েন করুন প্রথমে।", reply_markup=markup)
        return

    send_main_menu(message.chat.id, user_id)

# ========================= CALLBACK HANDLER (সব Inline) =========================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data

    if data == "check_join":
        if is_joined(user_id):
            bot.answer_callback_query(call.id, "✅ জয়েন সফল!", show_alert=True)
            send_main_menu(call.message.chat.id, user_id)
        else:
            bot.answer_callback_query(call.id, "❌ এখনো জয়েন করেননি", show_alert=True)

    elif data == "start_report":
        if not is_joined(user_id):
            bot.answer_callback_query(call.id, "চ্যানেলে জয়েন করুন!", show_alert=True)
            return
        user_state[user_id] = {"step": "chatid", "data": {}}
        bot.send_message(call.message.chat.id, "🔹 **Step 1:** স্ক্যামারের Chat ID অথবা @username দিন:")
        bot.answer_callback_query(call.id)

    elif data == "help_cmd":
        help_text = "📖 **হেল্প**\n\n• Report Scammer বাটন চাপুন\n• প্রমাণ ছবি দিন\n• গ্রুপে স্ক্যামার অটো ব্যান\n• /unban গ্রুপ অ্যাডমিনরা ব্যবহার করতে পারবেন"
        bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')

    elif data == "my_status":
        total = len(db['scammers'])
        bot.answer_callback_query(call.id, f"📊 মোট স্ক্যামার: {total}\nআপনার ID: {user_id}", show_alert=True)

    elif data == "admin_panel":
        if not is_bot_admin(user_id):
            bot.answer_callback_query(call.id, "❌ অ্যাক্সেস নেই!", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📋 সব স্ক্যামার দেখুন", callback_data="list_scammers"))
        markup.add(types.InlineKeyboardButton("🚫 স্ক্যামার রিমুভ", callback_data="remove_scammer_btn"))
        markup.add(types.InlineKeyboardButton("👑 নতুন Bot Admin যোগ", callback_data="add_bot_admin_btn"))
        markup.add(types.InlineKeyboardButton("🔙 মেনু", callback_data="back_menu"))
        bot.edit_message_text("🛠 **Admin Control Panel**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "list_scammers":
        if not is_bot_admin(user_id): return
        if not db['scammers']:
            bot.answer_callback_query(call.id, "কোনো স্ক্যামার নেই")
            return
        text = "📋 **সব স্ক্যামার**\n\n"
        for s in db['scammers']:
            text += f"🆔 `{s['user_id']}` | বিকাশ: {s.get('bikash','নেই')}\n"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')

    elif data == "remove_scammer_btn":
        if not is_bot_admin(user_id): return
        bot.send_message(call.message.chat.id, "🚫 রিমুভ করতে Chat ID দিন:")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_remove_scammer)

    elif data == "add_bot_admin_btn":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "শুধু মালিক!", show_alert=True)
            return
        bot.send_message(call.message.chat.id, "👑 নতুন Bot Admin এর Chat ID দিন:")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_add_bot_admin)

    elif data == "back_menu":
        send_main_menu(call.message.chat.id, user_id)

    # Report Approval
    elif data.startswith("approve_") or data.startswith("reject_"):
        if not is_bot_admin(user_id):
            bot.answer_callback_query(call.id, "❌ অ্যাডমিন নন!", show_alert=True)
            return
        action = data.split("_")[0]
        if action == "reject":
            bot.edit_message_caption("❌ রিপোর্ট রিজেক্ট হয়েছে।", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_caption("✅ এপ্রুভ হয়েছে। এখন সঠিক Chat ID দিন:", call.message.chat.id, call.message.message_id)
            bot.register_next_step_handler_by_chat_id(call.message.chat.id, lambda m: save_approved(m, call.message.caption))

# Report Step Handler (Inline Flow)
@bot.message_handler(func=lambda m: True)
def handle_text_input(message):
    user_id = message.from_user.id
    if user_id not in user_state:
        return

    state = user_state[user_id]
    step = state["step"]

    if step == "chatid":
        state["data"]["scammer_id"] = message.text.strip()
        state["step"] = "bikash"
        bot.reply_to(message, "🔹 **Step 2:** বিকাশ নাম্বার দিন (না থাকলে `skip` লিখুন)")

    elif step == "bikash":
        bikash = None if message.text.strip().lower() == "skip" else message.text.strip()
        state["data"]["bikash"] = bikash
        state["step"] = "details"
        bot.reply_to(message, "🔹 **Step 3:** বিস্তারিত কারণ লিখুন")

    elif step == "details":
        state["data"]["details"] = message.text.strip()
        state["step"] = "photo"
        bot.reply_to(message, "🔹 **Step 4:** প্রমাণের ছবি পাঠান (Screenshot)")

    elif step == "photo":
        if not message.photo:
            bot.reply_to(message, "❌ ছবি দিন!")
            return
        file_id = message.photo[-1].file_id
        data = state["data"]

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Approve", callback_data="approve_report"),
            types.InlineKeyboardButton("❌ Reject", callback_data="reject_report")
        )

        caption = f"🆕 নতুন রিপোর্ট\nরিপোর্টার: {user_id}\nস্ক্যামার: {data.get('scammer_id')}\nবিকাশ: {data.get('bikash','নেই')}\nকারণ: {data.get('details')}"

        bot.send_photo(OWNER_ID, file_id, caption=caption, reply_markup=markup)
        bot.send_message(message.chat.id, "✅ রিপোর্ট পাঠানো হয়েছে। অ্যাডমিন চেক করবে।")
        del user_state[user_id]

# Save Approved Scammer
def save_approved(message, original_caption):
    if not is_bot_admin(message.from_user.id):
        return
    try:
        scammer_id = int(message.text.strip())
        bikash = None
        if "বিকাশ:" in original_caption:
            for line in original_caption.split("\n"):
                if "বিকাশ:" in line:
                    bikash = line.split(":", 1)[1].strip()
        add_scammer(scammer_id, None, bikash, original_caption, message.from_user.id)
        bot.reply_to(message, f"✅ স্ক্যামার {scammer_id} সেভ হয়েছে। সব গ্রুপে অটো ব্যান হবে।")
    except:
        bot.reply_to(message, "❌ ভুল Chat ID! আবার চেষ্টা করুন।")

# ========================= GROUP FEATURES =========================
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
                f"ইউজার: {username}\n"
                f"Chat ID: `{member.id}`\n"
                f"লিঙ্ক: tg://user?id={member.id}"
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

# Broadcast & Addadmin (আগের মতো)
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if not is_bot_admin(message.from_user.id): return
    text = message.text.replace('/broadcast', '').strip()
    if not text: 
        bot.reply_to(message, "মেসেজ লিখুন!")
        return
    count = 0
    for uid in db['users']:
        try:
            bot.send_message(uid, f"📣 **Broadcast**\n\n{text}")
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
        bot.reply_to(message, "ভুল ID!")

def process_add_bot_admin(message):
    if message.from_user.id != OWNER_ID: return
    try:
        nid = int(message.text.strip())
        if nid not in db['admins']:
            db['admins'].append(nid)
            save_db(db)
            bot.reply_to(message, f"✅ {nid} Bot Admin হয়েছে।")
    except:
        bot.reply_to(message, "ভুল ID!")

# ========================= RUN =========================
if __name__ == "__main__":
    print("🚀 Anti-Scam Bot Started - Full Inline Mode")
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling(none_stop=True)
