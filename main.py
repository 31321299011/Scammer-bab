import telebot
from telebot import types
import json
import os
import threading
import time
from flask import Flask
from collections import defaultdict

# ========================= CONFIGURATION =========================
API_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770
CHANNEL_USERNAME = "@earning_channel24"
BOT_USERNAME = "@jhgmaing"

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
        "groups": [],        
        "users": []          
    }

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# Temporary storage for report steps (আলাদা আলাদা তথ্য নেওয়ার জন্য)
temp_reports = defaultdict(dict)

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
    for scam in db['scammers']:
        if str(scam.get('user_id')) == str(user_id):
            return True
        if bikash and scam.get('bikash') == bikash:
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
    return new_scam

# ========================= FLASK =========================
@app.route('/')
def index():
    return "✅ Anti-Scam Bot is Running Smoothly on Render!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ========================= START & MENU =========================
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
        bot.send_message(message.chat.id, "❌ আপনি আমাদের চ্যানেলে জয়েন করেননি।\nপ্রথমে জয়েন করে আবার চেষ্টা করুন।", reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🚨 স্ক্যামার রিপোর্ট করুন", callback_data="report_scam"),
        types.InlineKeyboardButton("❓ হেল্প", callback_data="help_cmd"),
        types.InlineKeyboardButton("👤 আমার স্ট্যাটাস", callback_data="my_status")
    )
    
    # শুধু bot admin এর জন্য Admin Panel বাটন (group admin পাবে না)
    if is_bot_admin(user_id):
        markup.add(types.InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel"))

    bot.send_message(
        message.chat.id,
        "👋 স্বাগতম! আমি প্রফেশনাল এন্টি-স্ক্যাম বট।\n\n"
        "• স্ক্যামার দেখলে প্রমাণসহ রিপোর্ট করুন\n"
        "• গ্রুপে স্ক্যামার অটো ব্যান হবে\n"
        "• বিকাশ নাম্বার মিললে অটো ব্যান\n\n"
        "Developer: @jhgmaing + @bot_developer_io",
        reply_markup=markup
    )

# ========================= ADMIN PANEL (শুধু bot admin এর জন্য) =========================
@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel(call):
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📋 সব স্ক্যামার দেখুন", callback_data="list_all_scammers"))
    markup.add(types.InlineKeyboardButton("🚫 স্ক্যামার আনব্যান করুন", callback_data="unban_scammer_btn"))
    markup.add(types.InlineKeyboardButton("👑 নতুন Bot Admin যোগ করুন", callback_data="add_bot_admin_btn"))
    markup.add(types.InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data="back_to_menu"))

    bot.edit_message_text("🛠 **Admin Control Panel**\n\nনিচের বাটন থেকে যা চান তা করুন:", 
                          call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "list_all_scammers")
def list_all_scammers(call):
    if not is_bot_admin(call.from_user.id):
        return
    if not db['scammers']:
        bot.answer_callback_query(call.id, "কোনো স্ক্যামার নেই!", show_alert=True)
        return
    text = "📋 **সব স্ক্যামার লিস্ট**\n\n"
    for s in db['scammers']:
        text += f"🆔 ID: `{s['user_id']}`\n"
        if s.get('username'): text += f"👤 Username: @{s['username']}\n"
        if s.get('bikash'): text += f"💰 বিকাশ: {s['bikash']}\n"
        text += f"📅 {s['timestamp']}\n\n"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "unban_scammer_btn")
def unban_scammer_btn(call):
    if not is_bot_admin(call.from_user.id):
        return
    bot.send_message(call.message.chat.id, "🚫 আনব্যান করতে স্ক্যামারের Chat ID দিন:")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_global_unban)

def process_global_unban(message):
    if not is_bot_admin(message.from_user.id):
        return
    try:
        target = int(message.text.strip())
        db['scammers'] = [s for s in db['scammers'] if s['user_id'] != target]
        save_db(db)
        bot.reply_to(message, f"✅ {target} কে গ্লোবাল ডাটাবেস থেকে রিমুভ করা হয়েছে।")
    except:
        bot.reply_to(message, "❌ ভুল ID! আবার চেষ্টা করুন।")

@bot.callback_query_handler(func=lambda call: call.data == "add_bot_admin_btn")
def add_bot_admin_btn(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "শুধু মালিক পারবেন!", show_alert=True)
        return
    bot.send_message(call.message.chat.id, "👑 নতুন Bot Admin এর Chat ID দিন:")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_add_bot_admin)

def process_add_bot_admin(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        new_id = int(message.text.strip())
        if new_id not in db['admins']:
            db['admins'].append(new_id)
            save_db(db)
            bot.reply_to(message, f"✅ {new_id} কে Bot Admin করা হয়েছে।")
    except:
        bot.reply_to(message, "❌ ভুল ID!")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    start(call.message)

# ========================= REPORT SYSTEM (আলাদা আলাদা স্টেপ) =========================
@bot.callback_query_handler(func=lambda call: call.data == "report_scam")
def report_scam_start(call):
    if not is_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "চ্যানেলে জয়েন করুন!", show_alert=True)
        return
    temp_reports[call.from_user.id] = {}
    bot.send_message(call.message.chat.id, "🔍 **Step 1:** স্ক্যামারের Chat ID অথবা @username দিন")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, report_step_1)

def report_step_1(message):
    uid = message.from_user.id
    temp_reports[uid]['scammer_input'] = message.text.strip()
    bot.send_message(message.chat.id, "🔍 **Step 2:** বিকাশ নাম্বার দিন (না থাকলে /skip লিখুন)")
    bot.register_next_step_handler_by_chat_id(message.chat.id, report_step_2)

def report_step_2(message):
    uid = message.from_user.id
    if message.text.strip() != "/skip":
        temp_reports[uid]['bikash'] = message.text.strip()
    bot.send_message(message.chat.id, "🔍 **Step 3:** বিস্তারিত কারণ লিখুন")
    bot.register_next_step_handler_by_chat_id(message.chat.id, report_step_3)

def report_step_3(message):
    uid = message.from_user.id
    temp_reports[uid]['details'] = message.text.strip()
    bot.send_message(message.chat.id, "🔍 **Step 4:** প্রমাণের ছবি (Screenshot) পাঠান")
    bot.register_next_step_handler_by_chat_id(message.chat.id, report_step_4)

def report_step_4(message):
    uid = message.from_user.id
    if not message.photo:
        bot.reply_to(message, "❌ ছবি দিতে হবে! আবার রিপোর্ট করুন।")
        del temp_reports[uid]
        return

    file_id = message.photo[-1].file_id
    data = temp_reports[uid]

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}")
    )

    caption = (f"🆕 **নতুন রিপোর্ট**\n"
               f"রিপোর্টার: {uid}\n"
               f"স্ক্যামার: {data.get('scammer_input')}\n"
               f"বিকাশ: {data.get('bikash', 'নেই')}\n"
               f"কারণ: {data.get('details')}")

    bot.send_photo(OWNER_ID, file_id, caption=caption, reply_markup=markup)
    bot.send_message(message.chat.id, "✅ রিপোর্ট অ্যাডমিনদের কাছে পাঠানো হয়েছে।")
    del temp_reports[uid]

# Approve / Reject (শুধু bot admin)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def handle_approval(call):
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!", show_alert=True)
        return

    action, reporter = call.data.split('_')
    if action == "reject":
        bot.edit_message_caption("❌ রিপোর্ট রিজেক্ট হয়েছে।", call.message.chat.id, call.message.message_id)
        return

    # Approve
    bot.edit_message_caption("✅ এপ্রুভ হয়েছে। এখন স্ক্যামারের সঠিক Chat ID দিন:", 
                             call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, lambda m: save_approved_scammer(m, call.message.caption))

def save_approved_scammer(message, original_caption):
    if not is_bot_admin(message.from_user.id):
        return
    try:
        scammer_id = int(message.text.strip())
        # Extract bikash & details from caption (আলাদা আলাদা খুঁজে সেভ)
        bikash = None
        details = original_caption
        if "বিকাশ:" in original_caption:
            bikash_line = [line for line in original_caption.split('\n') if "বিকাশ:" in line]
            if bikash_line:
                bikash = bikash_line[0].split(":", 1)[1].strip()

        add_scammer(scammer_id, None, bikash, details, message.from_user.id)
        bot.reply_to(message, f"✅ স্ক্যামার {scammer_id} ডাটাবেসে সেভ হয়েছে। সব গ্রুপে অটো ব্যান হবে।")
    except:
        bot.reply_to(message, "❌ ভুল Chat ID! আবার চেষ্টা করুন।")

# ========================= GROUP FEATURES =========================
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        if is_scammer(member.id):
            try:
                bot.ban_chat_member(message.chat.id, member.id)
                username = f"@{member.username}" if member.username else "No username"
                bot.send_message(
                    message.chat.id,
                    f"🚫 **সালা আইছিল টাকা মারতে! ভরে দিছি 🔥**\n\n"
                    f"**ইউজার:** {username}\n"
                    f"**Chat ID:** `{member.id}`\n"
                    f"**লিঙ্ক:** tg://user?id={member.id}"
                )
            except:
                pass

@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    if message.chat.type not in ['group', 'supergroup']:
        return

    text = (message.text or "").lower()
    scam_keywords = ['scam', 'scammer', 'টাকা মারছে', 'টাকা মারে', 'টাকা মেরে', 'প্রতারক', 'ঠকাইছে', 'scm', 'বিকাশ মেরে']
    if any(kw in text for kw in scam_keywords):
        bot.reply_to(message, "⚠️ স্ক্যাম সংক্রান্ত কথা চলছে। প্রমাণ থাকলে বটের ইনবক্সে Report করুন।")

    bot_mention = f"@{bot.get_me().username}"
    if bot_mention in (message.text or ""):
        bot.reply_to(message, "✅ আমি এন্টি-স্ক্যাম বট। স্ক্যামার দেখলে প্রমাণসহ রিপোর্ট করুন।")

# ========================= UNBAN (Group Admin + Bot Admin) =========================
@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "শুধু গ্রুপে এই কমান্ড চলবে।")
        return

    try:
        target = int(message.text.split()[1])
    except:
        bot.reply_to(message, "ব্যবহার: /unban <user_id>")
        return

    # Group Admin হলে গ্রুপে unban + database থেকে auto remove
    if is_group_admin(message.chat.id, message.from_user.id) or is_bot_admin(message.from_user.id):
        try:
            bot.unban_chat_member(message.chat.id, target, only_if_banned=True)
            # Database থেকে auto remove
            db['scammers'] = [s for s in db['scammers'] if s['user_id'] != target]
            save_db(db)
            bot.reply_to(message, f"✅ {target} কে গ্রুপ থেকে আনব্যান + ডাটাবেস থেকে রিমুভ করা হয়েছে।")
        except Exception as e:
            bot.reply_to(message, f"❌ কিছু সমস্যা হয়েছে: {e}")
    else:
        bot.reply_to(message, "❌ শুধু গ্রুপ অ্যাডমিন বা Bot Admin এই কমান্ড ব্যবহার করতে পারবেন।")

# ========================= OTHER COMMANDS (আগের মতোই রাখা হয়েছে) =========================
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if not is_bot_admin(message.from_user.id): return
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.reply_to(message, "মেসেজ লিখুন!")
        return
    count = 0
    for uid in db['users'][:]:
        try:
            bot.send_message(uid, f"📣 **ব্রডকাস্ট**\n\n{text}")
            count += 1
            time.sleep(0.05)
        except:
            pass
    bot.reply_to(message, f"✅ {count} জনের কাছে ব্রডকাস্ট পাঠানো হয়েছে।")

@bot.message_handler(commands=['addadmin'])
def add_admin_cmd(message):
    if message.from_user.id != OWNER_ID: return
    try:
        new_id = int(message.text.split()[1])
        if new_id not in db['admins']:
            db['admins'].append(new_id)
            save_db(db)
            bot.reply_to(message, f"✅ {new_id} কে Bot Admin করা হয়েছে।")
    except:
        bot.reply_to(message, "ব্যবহার: /addadmin <chat_id>")

# ========================= RUN =========================
if __name__ == "__main__":
    print("🚀 Anti-Scam Bot Starting... (Updated Professional Version)")
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling(none_stop=True)
