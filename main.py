import telebot
from telebot import types
import json
import os
import threading
import time
from flask import Flask
from pymongo import MongoClient
from bson.objectid import ObjectId
import re

# -------------------- CONFIGURATION --------------------
API_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770
CHANNEL_USERNAME = "@earning_channel24"
BOT_USERNAME = "@jhgmaing"
CHANNEL_URL = f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"

MONGO_URI = os.environ.get('MONGO_URI', '')  # Render এ Environment Variable দিতে হবে

bot = telebot.TeleBot(API_TOKEN, parse_mode='HTML')
app = Flask(__name__)

# -------------------- DATABASE (MongoDB) --------------------
if MONGO_URI:
    client = MongoClient(MONGO_URI)
    db_mongo = client['antiscam_bot']
    scammers_col = db_mongo['scammers']
    admins_col = db_mongo['admins']
    groups_col = db_mongo['groups']
    users_col = db_mongo['users']
    pending_col = db_mongo['pending_reports']
    print("✅ MongoDB connected")
else:
    print("⚠️ MONGO_URI not set, using local JSON (not recommended for production)")
    # Fallback to local JSON (for testing only)
    DB_FILE = 'database.json'
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        return {"scammers": [], "admins": [OWNER_ID], "groups": [], "users": [], "pending_reports": {}}
    def save_db(data):
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    db = load_db()
    # We'll wrap MongoDB operations with fallback functions (not shown here for brevity; we'll use MongoDB exclusively in this code)

# We'll use MongoDB exclusively if URI is provided, else exit (since Render needs persistence)
if not MONGO_URI:
    raise Exception("MONGO_URI environment variable is required for Render deployment!")

# -------------------- HELPER FUNCTIONS (MongoDB) --------------------
def is_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def is_bot_admin(user_id):
    admin = admins_col.find_one({"user_id": user_id})
    return admin is not None or user_id == OWNER_ID

def is_group_admin(chat_id, user_id):
    try:
        admins = bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False

def extract_id_from_text(text):
    text = text.strip()
    if text.isdigit():
        return text, None
    if text.startswith('@'):
        try:
            chat = bot.get_chat(text)
            return str(chat.id), text
        except:
            return None, text
    return None, None

def main_menu_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚫 Report Scammer", "❓ Help")
    markup.add("📊 My Status")
    if is_bot_admin(user_id):
        markup.add("⚙️ Admin Panel")
    return markup

# -------------------- FLASK --------------------
@app.route('/')
def index():
    return "Anti-Scam Bot Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# -------------------- BOT: START --------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    # Add user if not exists
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id, "joined": time.time()})

    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔄 Check Join", callback_data="check_join"))
        bot.send_message(message.chat.id,
            f"❌ প্রথমে আমাদের চ্যানেলে জয়েন করুন: {CHANNEL_USERNAME}",
            reply_markup=markup)
        return

    bot.send_message(
        message.chat.id,
        "👋 স্বাগতম! আমি প্রফেশনাল এন্টি-স্ক্যাম বট।\nনিচের বাটন ব্যবহার করুন।\n\n<i>Developed by @jhgmaing & @bot_developer_io</i>",
        reply_markup=main_menu_keyboard(user_id)
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    bot.answer_callback_query(call.id)
    if is_joined(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            "✅ জয়েন সম্পন্ন! এখন বট ব্যবহার করুন।",
            reply_markup=main_menu_keyboard(call.from_user.id)
        )
    else:
        bot.answer_callback_query(call.id, "এখনও জয়েন করেননি!", show_alert=True)

# -------------------- PRIVATE CHAT HANDLER --------------------
report_temp = {}  # temporary storage for multi-step report

@bot.message_handler(func=lambda m: m.chat.type == 'private', content_types=['text', 'photo'])
def private_message_handler(message):
    user_id = message.from_user.id
    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔄 Check Join", callback_data="check_join"))
        bot.reply_to(message, f"❌ চ্যানেল জয়েন আবশ্যক: {CHANNEL_USERNAME}", reply_markup=markup)
        return

    # Check report step in temp (we use a collection for steps? we'll keep in memory)
    step = db_temp_steps.get(user_id)  # We'll use a global dict for steps
    if step:
        if step == 'awaiting_scammer_id' and message.content_type == 'text':
            receive_scammer_id(message)
            return
        elif step == 'awaiting_bikash' and message.content_type == 'text':
            receive_bikash(message)
            return
        elif step == 'awaiting_evidence':
            if message.content_type == 'photo':
                receive_evidence(message)
            elif message.content_type == 'text' and message.text.strip().lower() == 'done':
                finalize_report(message)
            else:
                bot.reply_to(message, "ছবি পাঠান অথবা শেষ হলে 'done' লিখুন।")
            return

    if message.content_type == 'text':
        text = message.text.strip()
        if text == "🚫 Report Scammer":
            start_report_step1(message)
        elif text == "❓ Help":
            show_help(message)
        elif text == "📊 My Status":
            show_status(message)
        elif text == "⚙️ Admin Panel" and is_bot_admin(user_id):
            show_admin_panel(message)
        elif text == "/broadcast" and is_bot_admin(user_id):
            msg = bot.reply_to(message, "ব্রডকাস্ট মেসেজ লিখুন:")
            bot.register_next_step_handler(msg, process_broadcast)
        else:
            bot.reply_to(message, "দয়া করে নিচের বাটন ব্যবহার করুন।", reply_markup=main_menu_keyboard(user_id))
    else:
        bot.reply_to(message, "দয়া করে আগে Report Scammer বাটনে ক্লিক করুন।")

# Global dict for report steps (since we can't store in DB for temporary flow easily)
db_temp_steps = {}

def start_report_step1(message):
    user_id = message.from_user.id
    db_temp_steps[user_id] = 'awaiting_scammer_id'
    report_temp.pop(user_id, None)
    bot.reply_to(message,
        "🔍 <b>স্ক্যামারের Chat ID অথবা @username লিখুন:</b>\n(না জানা থাকলে <code>skip</code> লিখুন)",
        parse_mode='HTML',
        reply_markup=types.ReplyKeyboardRemove()
    )

def receive_scammer_id(message):
    user_id = message.from_user.id
    text = message.text.strip()
    if text.lower() == 'skip':
        scammer_id = None
        username = None
    else:
        sid, uname = extract_id_from_text(text)
        scammer_id = sid
        username = uname

    report_temp[user_id] = {
        'scammer_id': scammer_id,
        'username': username,
        'photos': []
    }
    db_temp_steps[user_id] = 'awaiting_bikash'
    bot.reply_to(message,
        "💰 <b>বিকাশ নাম্বার (যদি থাকে):</b>\n(না থাকলে <code>skip</code>)",
        parse_mode='HTML'
    )

def receive_bikash(message):
    user_id = message.from_user.id
    bikash = message.text.strip()
    if bikash.lower() == 'skip':
        bikash = None

    report_temp[user_id]['bikash'] = bikash
    db_temp_steps[user_id] = 'awaiting_evidence'
    bot.reply_to(message,
        "🖼 <b>এখন প্রমাণ হিসেবে এক বা একাধিক ছবি পাঠান।</b>\nসব ছবি পাঠানো শেষ হলে <code>done</code> লিখুন।",
        parse_mode='HTML'
    )

def receive_evidence(message):
    user_id = message.from_user.id
    if not message.photo:
        bot.reply_to(message, "ছবি পাঠান অথবা 'done' লিখুন।")
        return
    file_id = message.photo[-1].file_id
    report_temp[user_id]['photos'].append(file_id)
    bot.reply_to(message, f"✅ ছবি গৃহীত হয়েছে ({len(report_temp[user_id]['photos'])} টি)। আরও পাঠাতে পারেন বা 'done' লিখুন।")

def finalize_report(message):
    user_id = message.from_user.id
    data = report_temp.pop(user_id, {})
    if not data.get('photos'):
        bot.reply_to(message, "❌ অন্তত একটি ছবি দিতে হবে। আবার চেষ্টা করুন।")
        db_temp_steps.pop(user_id, None)
        bot.send_message(user_id, "আপনি আবার রিপোর্ট শুরু করতে 'Report Scammer' বাটনে ক্লিক করুন।", reply_markup=main_menu_keyboard(user_id))
        return

    report_doc = {
        'reporter': user_id,
        'scammer_id': data.get('scammer_id'),
        'username': data.get('username'),
        'bikash': data.get('bikash'),
        'caption': f"প্রমাণ ছবি সংখ্যা: {len(data['photos'])}",
        'evidence_files': data['photos'],
        'timestamp': time.time(),
        'status': 'pending'
    }
    result = pending_col.insert_one(report_doc)
    report_id = str(result.inserted_id)
    db_temp_steps.pop(user_id, None)

    # Notify admins
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{report_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{report_id}")
    )
    admin_text = (
        f"🔔 <b>নতুন রিপোর্ট</b>\n"
        f"👤 রিপোর্টার: <code>{user_id}</code>\n"
        f"🆔 স্ক্যামার আইডি: {report_doc['scammer_id'] or 'N/A'}\n"
        f"📛 ইউজারনেম: {report_doc['username'] or 'N/A'}\n"
        f"💳 বিকাশ: {report_doc['bikash'] or 'N/A'}\n"
        f"🖼 ছবি: {len(data['photos'])} টি"
    )
    admins = list(admins_col.find())
    for admin in admins:
        try:
            if len(data['photos']) == 1:
                bot.send_photo(admin['user_id'], data['photos'][0], caption=admin_text, reply_markup=admin_markup)
            else:
                bot.send_photo(admin['user_id'], data['photos'][0], caption=admin_text, reply_markup=admin_markup)
                media_group = [types.InputMediaPhoto(media=pid) for pid in data['photos'][1:]]
                if media_group:
                    bot.send_media_group(admin['user_id'], media_group)
        except Exception as e:
            bot.send_message(admin['user_id'], admin_text + "\n(ছবি পাঠাতে সমস্যা)", reply_markup=admin_markup)

    bot.reply_to(message,
        "✅ রিপোর্ট জমা হয়েছে। এডমিন যাচাই করবেন।",
        reply_markup=main_menu_keyboard(user_id)
    )

# -------------------- HELP & STATUS --------------------
def show_help(message):
    help_text = (
        "📖 <b>হেল্প</b>\n\n"
        "• Report Scammer: স্ক্যামারের তথ্য ও প্রমাণ জমা দিন।\n"
        "• এডমিন অনুমোদন সাপেক্ষে স্ক্যামার ডাটাবেসে যুক্ত হবে।\n"
        "• ডাটাবেসে থাকা স্ক্যামার যেকোনো গ্রুপে জয়েন করলে অটো-ব্যান হবে।\n"
        "• গ্রুপ এডমিন /unban কমান্ড দিয়ে ভুল ব্যান তুলতে পারবেন।\n"
        "• গ্রুপে বট অ্যাড করলে /scan দিয়ে স্ক্যান করা যায়।"
    )
    bot.reply_to(message, help_text, reply_markup=main_menu_keyboard(message.from_user.id))

def show_status(message):
    user_id = message.from_user.id
    total_reports = pending_col.count_documents({"reporter": user_id})
    is_scammer = scammers_col.find_one({"id": str(user_id)}) is not None
    status = (
        f"👤 <b>আপনার স্ট্যাটাস</b>\n"
        f"├ ইউজার আইডি: <code>{user_id}</code>\n"
        f"├ জমাকৃত রিপোর্ট: {total_reports}\n"
        f"└ স্ক্যামার তালিকায়: {'হ্যাঁ' if is_scammer else 'না'}"
    )
    bot.reply_to(message, status, reply_markup=main_menu_keyboard(user_id))

# -------------------- ADMIN PANEL --------------------
def show_admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 স্ক্যামার লিস্ট", callback_data="list_scammers"),
        types.InlineKeyboardButton("❌ রিমুভ স্ক্যামার", callback_data="remove_scammer_prompt")
    )
    markup.add(
        types.InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="broadcast_prompt"),
        types.InlineKeyboardButton("➕ অ্যাড এডমিন", callback_data="add_admin_prompt")
    )
    bot.reply_to(message, "⚙️ <b>অ্যাডমিন প্যানেল</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["list_scammers", "remove_scammer_prompt", "broadcast_prompt", "add_admin_prompt"])
def admin_inline_handler(call):
    bot.answer_callback_query(call.id)
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "আপনি অনুমোদিত নন!", show_alert=True)
        return

    if call.data == "list_scammers":
        scammers = list(scammers_col.find().limit(30))
        if not scammers:
            text = "কোনো স্ক্যামার নেই।"
        else:
            text = "<b>স্ক্যামার লিস্ট:</b>\n"
            for s in scammers:
                text += f"• <code>{s['id']}</code> {s.get('username','')} - {s.get('bikash','')}\n"
        bot.send_message(call.message.chat.id, text)

    elif call.data == "remove_scammer_prompt":
        msg = bot.send_message(call.message.chat.id, "যে স্ক্যামারের ID রিমুভ করতে চান তা লিখুন:")
        bot.register_next_step_handler(msg, process_remove_scammer)

    elif call.data == "broadcast_prompt":
        msg = bot.send_message(call.message.chat.id, "ব্রডকাস্ট মেসেজ লিখুন:")
        bot.register_next_step_handler(msg, process_broadcast)

    elif call.data == "add_admin_prompt":
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "শুধু মেইন ওনার পারেন!", show_alert=True)
            return
        msg = bot.send_message(call.message.chat.id, "নতুন এডমিনের Chat ID লিখুন:")
        bot.register_next_step_handler(msg, process_add_admin)

def process_remove_scammer(message):
    if not is_bot_admin(message.from_user.id): return
    sid = message.text.strip()
    result = scammers_col.delete_one({"id": sid})
    if result.deleted_count > 0:
        bot.reply_to(message, "✅ সরানো হয়েছে")
    else:
        bot.reply_to(message, "❌ পাওয়া যায়নি")

def process_broadcast(message):
    if not is_bot_admin(message.from_user.id): return
    text = message.text
    count_users = 0
    count_groups = 0
    for user in users_col.find():
        try:
            bot.send_message(user['user_id'], f"📢 ব্রডকাস্ট\n\n{text}")
            count_users += 1
        except: pass
    for group in groups_col.find():
        try:
            bot.send_message(group['chat_id'], f"📢 ব্রডকাস্ট\n\n{text}")
            count_groups += 1
        except: pass
    total_scammers = scammers_col.count_documents({})
    total_users = users_col.count_documents({})
    total_groups = groups_col.count_documents({})
    bot.reply_to(message,
        f"✅ ব্রডকাস্ট সম্পন্ন!\n\n"
        f"👥 মোট ইউজার: {total_users}\n"
        f"💬 মোট গ্রুপ: {total_groups}\n"
        f"📨 পৌঁছেছে ইউজার: {count_users}\n"
        f"📢 পৌঁছেছে গ্রুপ: {count_groups}\n"
        f"🚫 মোট স্ক্যামার: {total_scammers}"
    )

def process_add_admin(message):
    if message.from_user.id != OWNER_ID: return
    try:
        new_id = int(message.text.strip())
        if not admins_col.find_one({"user_id": new_id}):
            admins_col.insert_one({"user_id": new_id})
            bot.reply_to(message, f"✅ {new_id} এডমিন হয়েছে।")
        else:
            bot.reply_to(message, "ইতিমধ্যে এডমিন!")
    except:
        bot.reply_to(message, "ভুল ফরম্যাট!")

# -------------------- APPROVAL --------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def handle_approval(call):
    bot.answer_callback_query(call.id)
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "আপনি অনুমোদিত নন!", show_alert=True)
        return

    action, report_id = call.data.split('_', 1)
    try:
        report = pending_col.find_one({"_id": ObjectId(report_id)})
    except:
        bot.edit_message_caption("রিপোর্ট আর নেই।", call.message.chat.id, call.message.message_id)
        return

    if action == "rej":
        bot.edit_message_caption(call.message.caption + "\n\n❌ রিজেক্ট করা হয়েছে",
                                 call.message.chat.id, call.message.message_id)
        try:
            bot.send_message(report['reporter'], "❌ আপনার রিপোর্ট গৃহীত হয়নি।")
        except: pass
        pending_col.delete_one({"_id": ObjectId(report_id)})
        return

    # Approve
    if not report.get('scammer_id'):
        msg = bot.send_message(call.message.chat.id, f"রিপোর্ট #{report_id}\nস্ক্যামারের Chat ID লিখুন:")
        bot.register_next_step_handler(msg, lambda m: manual_id_then_save(m, report_id, call.message))
        return

    save_scammer_from_report(report, call.message, call.from_user.id)
    pending_col.delete_one({"_id": ObjectId(report_id)})

def manual_id_then_save(message, report_id, original_msg):
    if not is_bot_admin(message.from_user.id): return
    sid, uname = extract_id_from_text(message.text.strip())
    if not sid:
        bot.reply_to(message, "❌ বৈধ ID নয়!")
        return
    try:
        report = pending_col.find_one({"_id": ObjectId(report_id)})
    except:
        bot.reply_to(message, "রিপোর্ট মেয়াদোত্তীর্ণ")
        return
    report['scammer_id'] = sid
    report['username'] = uname or report.get('username')
    save_scammer_from_report(report, original_msg, message.from_user.id)
    pending_col.delete_one({"_id": ObjectId(report_id)})

def ban_scammer_in_all_groups(scammer_id):
    for group in groups_col.find():
        try:
            bot.ban_chat_member(group['chat_id'], scammer_id)
            try:
                bot.send_message(group['chat_id'], f"🚫 স্ক্যামার <code>{scammer_id}</code> কে গ্লোবাল ডাটাবেস থেকে ব্যান করা হয়েছে।")
            except: pass
        except Exception as e:
            print(f"Ban error: {e}")

def save_scammer_from_report(report, message_or_call, admin_id):
    if not scammers_col.find_one({"id": report['scammer_id']}):
        scammers_col.insert_one({
            "id": report['scammer_id'],
            "username": report.get('username'),
            "bikash": report.get('bikash'),
            "details": f"প্রমাণ ছবি: {len(report.get('evidence_files', []))} টি",
            "added_by": admin_id,
            "timestamp": time.time()
        })
        threading.Thread(target=ban_scammer_in_all_groups, args=(report['scammer_id'],)).start()
    try:
        bot.send_message(report['reporter'], "✅ আপনার রিপোর্ট অনুমোদিত হয়েছে এবং স্ক্যামারকে সব গ্রুপ থেকে ব্যান করা হয়েছে।")
    except: pass
    if hasattr(message_or_call, 'edit_caption'):
        message_or_call.edit_caption(message_or_call.caption + "\n\n✅ অনুমোদিত ও গ্রুপগুলোতে ব্যান করা হয়েছে")
    else:
        bot.reply_to(message_or_call, "✅ সংরক্ষিত এবং গ্রুপে ব্যান করা হয়েছে।")

# -------------------- GROUP AUTOMATION --------------------
@bot.message_handler(content_types=['new_chat_members'])
def on_join(message):
    chat_id = message.chat.id
    bot_just_added = False
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            bot_just_added = True
            if not groups_col.find_one({"chat_id": chat_id}):
                groups_col.insert_one({"chat_id": chat_id, "added": time.time()})
            bot.send_message(chat_id,
                "🤖 বট অ্যাড হয়েছে। স্ক্যামার স্ক্যান শুরু হচ্ছে...\n"
                "সম্পূর্ণ স্ক্যান করতে অ্যাডমিন /scan কমান্ড ব্যবহার করুন।")
        else:
            scam = scammers_col.find_one({"id": str(member.id)})
            if scam:
                try:
                    bot.ban_chat_member(chat_id, member.id)
                    link = f"tg://user?id={member.id}"
                    bot.send_message(chat_id,
                        f"🚫 <b>সালা আইছিল টাকা মারতে ভরে দিছি!</b>\n"
                        f"স্ক্যামার: <a href='{link}'>{member.first_name}</a>\n"
                        f"আইডি: <code>{member.id}</code>\n"
                        f"ইউজারনেম: {f'@{member.username}' if member.username else 'N/A'}\n"
                        f"<i>গ্লোবাল ডাটাবেসে ব্ল্যাকলিস্টেড।</i>",
                        parse_mode='HTML')
                except Exception as e:
                    print("Ban error:", e)

    if bot_just_added:
        threading.Thread(target=scan_recent_active_users, args=(chat_id,)).start()

def scan_recent_active_users(chat_id):
    try:
        admins = bot.get_chat_administrators(chat_id)
        for admin in admins:
            uid = admin.user.id
            if scammers_col.find_one({"id": str(uid)}):
                try:
                    bot.ban_chat_member(chat_id, uid)
                    bot.send_message(chat_id, f"🚫 অ্যাডমিনদের মধ্যেও স্ক্যামার পাওয়া গেছে! {uid} ব্যান করা হয়েছে।")
                except: pass
        bot.send_message(chat_id, "✅ প্রাথমিক স্ক্যান সম্পন্ন। আরও স্ক্যান করতে /scan কমান্ড দিন।")
    except Exception as e:
        print(f"Scan error: {e}")

@bot.message_handler(commands=['scan'])
def scan_command(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ শুধু গ্রুপ এডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return

    bot.reply_to(message, "🔍 স্ক্যান শুরু হচ্ছে...")
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        banned = 0
        for admin in admins:
            uid = admin.user.id
            if scammers_col.find_one({"id": str(uid)}):
                try:
                    bot.ban_chat_member(message.chat.id, uid)
                    banned += 1
                except: pass
        bot.reply_to(message, f"✅ স্ক্যান সম্পন্ন। {banned} জন স্ক্যামার ব্যান করা হয়েছে।")
    except Exception as e:
        bot.reply_to(message, f"স্ক্যান করতে সমস্যা: {e}")

@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'], content_types=['text'])
def group_text_handler(message):
    text = message.text.lower()
    keywords = ['scam', 'scammer', 'টাকা মারছে', 'টাকা মারে', 'প্রতারক', 'টাকা দিছে না', 'ঠগ']

    if any(kw in text for kw in keywords):
        mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚫 Report Scammer", url=f"https://t.me/{BOT_USERNAME[1:]}?start=report"))
        bot.reply_to(message,
            f"{mention} ⚠️ স্ক্যাম আলোচনা সনাক্ত হয়েছে।\nপ্রমাণ থাকলে রিপোর্ট করুন।",
            parse_mode='HTML', reply_markup=markup)

    if f"@{BOT_USERNAME[1:]}" in text:
        bot.reply_to(message, "🤖 আমি এন্টি-স্ক্যাম বট। রিপোর্ট করতে প্রাইভেটে আসুন।")

@bot.message_handler(commands=['unban'])
def unban_command(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ শুধু গ্রুপ এডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    try:
        target = message.text.split()[1]
        bot.unban_chat_member(message.chat.id, target)
        scammers_col.delete_one({"id": target})
        bot.reply_to(message, f"✅ {target} আনব্যান ও ডাটাবেস থেকে সরানো হয়েছে।")
    except Exception as e:
        bot.reply_to(message, f"ত্রুটি: {e}")

# -------------------- TRACK GROUPS --------------------
@bot.message_handler(content_types=['left_chat_member'])
def on_bot_removed(message):
    if message.left_chat_member.id == bot.get_me().id:
        groups_col.delete_one({"chat_id": message.chat.id})

# -------------------- RUN --------------------
if __name__ == "__main__":
    # Ensure owner is in admins collection
    if not admins_col.find_one({"user_id": OWNER_ID}):
        admins_col.insert_one({"user_id": OWNER_ID})
    print("Bot starting...")
    threading.Thread(target=run_flask, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(10)
