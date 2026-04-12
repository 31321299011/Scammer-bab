# main.py
import telebot
from telebot import types
import json
import os
import threading
import time
from flask import Flask, request
import re

# -------------------- CONFIGURATION --------------------
API_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770
CHANNEL_USERNAME = "@earning_channel24"
BOT_USERNAME = "@jhgmaing"          # আপনার বটের ইউজারনেম
CHANNEL_ID = -1001234567890         # (optional) আপনার চ্যানেলের numeric id, না থাকলে সমস্যা নেই
CHANNEL_URL = f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"

bot = telebot.TeleBot(API_TOKEN, parse_mode='HTML')
app = Flask(__name__)

# -------------------- DATABASE --------------------
DB_FILE = 'database.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "scammers": [],
        "admins": [OWNER_ID],
        "groups": [],
        "users": [],
        "pending_reports": {},
        "user_states": {}
    }

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

db = load_db()

# -------------------- HELPERS --------------------
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
        admins = bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False

def get_user_link(user):
    if user.username:
        return f"@{user.username}"
    else:
        return f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

def extract_id_from_text(text):
    # Try to extract numeric ID or username
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

# -------------------- FLASK (Render) --------------------
@app.route('/')
def index():
    return "Anti-Scam Bot is Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# -------------------- BOT: START & JOIN CHECK --------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    if user_id not in db['users']:
        db['users'].append(user_id)
        save_db(db)

    # Auto join check
    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔄 Check Join", callback_data="check_join"))
        bot.send_message(message.chat.id,
            f"❌ আপনি আমাদের চ্যানেলে জয়েন করেননি!\nদয়া করে চ্যানেলটি জয়েন করুন: {CHANNEL_USERNAME}",
            reply_markup=markup)
        return

    show_main_menu(message.chat.id, user_id, message.message_id)

def show_main_menu(chat_id, user_id, msg_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🚫 Report Scammer", callback_data="report_scam"),
        types.InlineKeyboardButton("❓ Help", callback_data="help_menu")
    )
    markup.add(
        types.InlineKeyboardButton("📊 My Status", callback_data="my_status")
    )
    if is_bot_admin(user_id):
        markup.add(types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))

    text = (
        "👋 স্বাগতম! আমি <b>প্রফেশনাল এন্টি-স্ক্যাম বট</b>\n"
        "নিচের বাটন ব্যবহার করে স্ক্যামার রিপোর্ট করুন।\n\n"
        "<i>Developed by @jhgmaing & @bot_developer_io</i>"
    )
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)
        except:
            bot.send_message(chat_id, text, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    bot.answer_callback_query(call.id)
    if is_joined(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id, call.from_user.id)
    else:
        bot.answer_callback_query(call.id, "আপনি এখনও চ্যানেল জয়েন করেননি!", show_alert=True)

# -------------------- HELP & STATUS --------------------
@bot.callback_query_handler(func=lambda call: call.data == "help_menu")
def help_callback(call):
    bot.answer_callback_query(call.id)
    text = (
        "📖 <b>হেল্প মেনু</b>\n\n"
        "• স্ক্যামার রিপোর্ট করতে <b>Report Scammer</b> বাটনে ক্লিক করুন।\n"
        "• স্ক্যামারের Chat ID / @username এবং বিকাশ নাম্বার দিন।\n"
        "• তারপর স্ক্রিনশট (প্রমাণ) আপলোড করুন।\n"
        "• এডমিন প্রমাণ যাচাই করে স্ক্যামারকে গ্লোবাল ডাটাবেসে যুক্ত করবেন।\n"
        "• ডাটাবেসে থাকা স্ক্যামার যেকোনো গ্রুপে জয়েন করলে অটো-ব্যান হবে।\n"
        "• গ্রুপ এডমিন /unban কমান্ড দিয়ে ভুলবশত ব্যান উঠাতে পারবেন।\n\n"
        "<i>যেকোনো সমস্যায় @bot_developer_io</i>"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "my_status")
def my_status_callback(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    total_reports = sum(1 for r in db.get('pending_reports', {}).values() if r.get('reporter') == user_id)
    is_scammer = any(str(s.get('id')) == str(user_id) for s in db['scammers'])
    text = (
        f"👤 <b>আপনার স্ট্যাটাস</b>\n"
        f"├ ইউজার আইডি: <code>{user_id}</code>\n"
        f"├ জমাকৃত রিপোর্ট: {total_reports}\n"
        f"└ স্ক্যামার লিস্টেড: {'হ্যাঁ' if is_scammer else 'না'}\n\n"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start(call):
    bot.answer_callback_query(call.id)
    show_main_menu(call.message.chat.id, call.from_user.id, call.message.message_id)

# -------------------- REPORT SCAMMER (Multi-step) --------------------
user_temp = {}  # temporary storage for report steps

@bot.callback_query_handler(func=lambda call: call.data == "report_scam")
def report_start(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔄 Check Join", callback_data="check_join"))
        bot.edit_message_text("❌ রিপোর্ট করতে চ্যানেল জয়েন আবশ্যক!", call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    # Clear any old temp
    user_temp.pop(user_id, None)
    msg = bot.send_message(call.message.chat.id,
        "🔍 <b>স্ক্যামারের Chat ID অথবা @username লিখুন:</b>\n(যদি না জানা থাকে তাহলে <code>skip</code> লিখুন)",
        parse_mode='HTML')
    bot.register_next_step_handler(msg, process_scammer_id)

def process_scammer_id(message):
    user_id = message.from_user.id
    text = message.text.strip()
    if text.lower() == 'skip':
        scammer_id = None
        username = None
    else:
        sid, uname = extract_id_from_text(text)
        scammer_id = sid
        username = uname

    user_temp[user_id] = {'scammer_id': scammer_id, 'username': username}
    msg = bot.reply_to(message,
        "💰 <b>স্ক্যামারের বিকাশ নাম্বার (যদি থাকে) লিখুন:</b>\n(না থাকলে <code>skip</code> লিখুন)",
        parse_mode='HTML')
    bot.register_next_step_handler(msg, process_bikash)

def process_bikash(message):
    user_id = message.from_user.id
    bikash = message.text.strip()
    if bikash.lower() == 'skip':
        bikash = None
    user_temp[user_id]['bikash'] = bikash

    msg = bot.reply_to(message,
        "🖼 <b>এখন স্ক্যামের প্রমাণস্বরূপ স্ক্রিনশট/ছবি পাঠান:</b>\n(একটি ছবি অবশ্যই দিতে হবে)",
        parse_mode='HTML')
    bot.register_next_step_handler(msg, process_evidence)

def process_evidence(message):
    user_id = message.from_user.id
    if not message.photo:
        msg = bot.reply_to(message, "❌ দয়া করে একটি ছবি পাঠান!")
        bot.register_next_step_handler(msg, process_evidence)
        return

    file_id = message.photo[-1].file_id
    caption = message.caption if message.caption else "No additional info"

    # Save pending report
    report_id = f"{user_id}_{int(time.time())}"
    report_data = {
        'reporter': user_id,
        'scammer_id': user_temp[user_id].get('scammer_id'),
        'username': user_temp[user_id].get('username'),
        'bikash': user_temp[user_id].get('bikash'),
        'caption': caption,
        'evidence_file_id': file_id,
        'timestamp': time.time()
    }
    db['pending_reports'][report_id] = report_data
    save_db(db)

    # Notify admins
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{report_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{report_id}")
    )
    admin_text = (
        "🔔 <b>নতুন স্ক্যাম রিপোর্ট</b>\n"
        f"👤 রিপোর্টার: <code>{user_id}</code>\n"
        f"🆔 স্ক্যামার আইডি: {report_data['scammer_id'] or 'N/A'}\n"
        f"📛 ইউজারনেম: {report_data['username'] or 'N/A'}\n"
        f"💳 বিকাশ: {report_data['bikash'] or 'N/A'}\n"
        f"📝 বিবরণ: {caption}"
    )
    for admin_id in db['admins']:
        try:
            bot.send_photo(admin_id, file_id, caption=admin_text, reply_markup=admin_markup)
        except:
            bot.send_message(admin_id, admin_text + "\n(ছবি পাঠানো যায়নি)", reply_markup=admin_markup)

    bot.send_message(message.chat.id,
        "✅ আপনার রিপোর্ট এডমিনদের কাছে পাঠানো হয়েছে। যাচাই শেষে ব্যবস্থা নেওয়া হবে।")
    # clear temp
    user_temp.pop(user_id, None)
    show_main_menu(message.chat.id, user_id)

# -------------------- ADMIN APPROVAL --------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def handle_approval(call):
    bot.answer_callback_query(call.id)
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "আপনি অনুমোদিত নন!", show_alert=True)
        return

    action, report_id = call.data.split('_', 1)
    report = db['pending_reports'].get(report_id)
    if not report:
        bot.edit_message_caption("রিপোর্টটি আর বিদ্যমান নেই।", call.message.chat.id, call.message.message_id)
        return

    if action == "rej":
        bot.edit_message_caption(call.message.caption + "\n\n❌ <b>রিজেক্ট করা হয়েছে</b>",
                                 call.message.chat.id, call.message.message_id, parse_mode='HTML')
        # Notify reporter
        try:
            bot.send_message(report['reporter'], "❌ আপনার জমাকৃত রিপোর্টটি যাচাই শেষে গৃহীত হয়নি।")
        except: pass
        del db['pending_reports'][report_id]
        save_db(db)
        return

    # Approve: ask for final scammer ID if missing
    if report.get('scammer_id'):
        # Directly save
        save_scammer_from_report(report, call)
    else:
        # Ask admin to provide scammer ID
        msg = bot.send_message(call.message.chat.id,
            f"রিপোর্ট #{report_id}\nস্ক্যামারের সঠিক Chat ID / @username লিখুন:")
        bot.register_next_step_handler(msg, lambda m: manual_scammer_id(m, report_id, call.message))

def manual_scammer_id(message, report_id, original_msg):
    admin_id = message.from_user.id
    if not is_bot_admin(admin_id):
        return
    text = message.text.strip()
    sid, uname = extract_id_from_text(text)
    if not sid:
        bot.reply_to(message, "❌ বৈধ Chat ID / username পাওয়া যায়নি! আবার চেষ্টা করুন।")
        return

    report = db['pending_reports'].get(report_id)
    if not report:
        bot.reply_to(message, "রিপোর্ট মেয়াদোত্তীর্ণ।")
        return
    report['scammer_id'] = sid
    report['username'] = uname or report.get('username')
    db['pending_reports'][report_id] = report
    save_db(db)
    save_scammer_from_report(report, original_msg)

def save_scammer_from_report(report, call_or_msg):
    # Extract info
    scam_data = {
        "id": report['scammer_id'],
        "username": report.get('username'),
        "bikash": report.get('bikash'),
        "details": report.get('caption', ''),
        "evidence_file_id": report.get('evidence_file_id'),
        "added_by": call_or_msg.from_user.id if hasattr(call_or_msg, 'from_user') else OWNER_ID
    }
    # Avoid duplicate
    if not any(str(s['id']) == str(scam_data['id']) for s in db['scammers']):
        db['scammers'].append(scam_data)
        save_db(db)

    # Delete from pending
    if isinstance(call_or_msg, types.CallbackQuery):
        report_id = call_or_msg.data.split('_',1)[1]
        if report_id in db['pending_reports']:
            del db['pending_reports'][report_id]
        bot.edit_message_caption(call_or_msg.message.caption + "\n\n✅ <b>অনুমোদিত ও ডাটাবেসে সংরক্ষিত</b>",
                                 call_or_msg.message.chat.id, call_or_msg.message.message_id, parse_mode='HTML')
        try:
            bot.send_message(report['reporter'], "✅ আপনার রিপোর্টটি অনুমোদিত হয়েছে। স্ক্যামারকে গ্লোবাল ডাটাবেসে যুক্ত করা হয়েছে।")
        except: pass
    else:
        # manual addition
        bot.reply_to(call_or_msg, f"✅ স্ক্যামার {scam_data['id']} সংরক্ষিত হয়েছে।")

    save_db(db)

# -------------------- ADMIN PANEL (INLINE) --------------------
@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel(call):
    bot.answer_callback_query(call.id)
    if not is_bot_admin(call.from_user.id):
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 স্ক্যামার লিস্ট", callback_data="list_scammers"),
        types.InlineKeyboardButton("❌ রিমুভ স্ক্যামার", callback_data="remove_scammer_prompt")
    )
    markup.add(
        types.InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="broadcast_prompt"),
        types.InlineKeyboardButton("➕ অ্যাড এডমিন", callback_data="add_admin_prompt")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start"))
    bot.edit_message_text("⚙️ <b>অ্যাডমিন প্যানেল</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "list_scammers")
def list_scammers(call):
    bot.answer_callback_query(call.id)
    if not is_bot_admin(call.from_user.id): return
    scammers = db['scammers']
    if not scammers:
        text = "কোনো স্ক্যামার নেই।"
    else:
        text = "<b>📋 গ্লোবাল স্ক্যামার লিস্ট:</b>\n"
        for s in scammers[:20]:
            text += f"• <code>{s['id']}</code> {s.get('username','')} - {s.get('bikash','')}\n"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "remove_scammer_prompt")
def remove_scammer_prompt(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "যে স্ক্যামারের Chat ID রিমুভ করতে চান তা লিখুন:")
    bot.register_next_step_handler(msg, process_remove_scammer)

def process_remove_scammer(message):
    if not is_bot_admin(message.from_user.id): return
    sid = message.text.strip()
    before = len(db['scammers'])
    db['scammers'] = [s for s in db['scammers'] if str(s['id']) != sid]
    after = len(db['scammers'])
    save_db(db)
    if before > after:
        bot.reply_to(message, f"✅ {sid} ডাটাবেস থেকে সরানো হয়েছে।")
    else:
        bot.reply_to(message, "❌ স্ক্যামার পাওয়া যায়নি।")

@bot.callback_query_handler(func=lambda call: call.data == "broadcast_prompt")
def broadcast_prompt(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "যে মেসেজ ব্রডকাস্ট করতে চান তা লিখুন:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if not is_bot_admin(message.from_user.id): return
    text = message.text
    count_users = 0
    count_groups = 0
    for uid in db['users']:
        try:
            bot.send_message(uid, f"📢 <b>ব্রডকাস্ট</b>\n\n{text}")
            count_users += 1
        except: pass
    for gid in db['groups']:
        try:
            bot.send_message(gid, f"📢 <b>ব্রডকাস্ট</b>\n\n{text}")
            count_groups += 1
        except: pass
    bot.reply_to(message, f"✅ ব্রডকাস্ট সম্পন্ন!\nইউজার: {count_users}\nগ্রুপ: {count_groups}")

@bot.callback_query_handler(func=lambda call: call.data == "add_admin_prompt")
def add_admin_prompt(call):
    bot.answer_callback_query(call.id)
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "শুধুমাত্র মেইন ওনার এটি করতে পারবেন!", show_alert=True)
        return
    msg = bot.send_message(call.message.chat.id, "নতুন এডমিনের Chat ID লিখুন:")
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(message):
    if message.from_user.id != OWNER_ID: return
    try:
        new_id = int(message.text.strip())
        if new_id not in db['admins']:
            db['admins'].append(new_id)
            save_db(db)
            bot.reply_to(message, f"✅ {new_id} এডমিন হিসেবে যুক্ত হয়েছে।")
        else:
            bot.reply_to(message, "ইতিমধ্যে এডমিন!")
    except:
        bot.reply_to(message, "ভুল ফরম্যাট!")

# -------------------- GROUP AUTOMATION --------------------
@bot.message_handler(content_types=['new_chat_members'])
def on_user_join(message):
    chat_id = message.chat.id
    for member in message.new_chat_members:
        # Check if scammer by ID or bikash
        scam = next((s for s in db['scammers'] if str(s['id']) == str(member.id)), None)
        if not scam:
            # Also check if any bikash matches? we don't have bikash from user profile
            pass
        if scam:
            try:
                bot.ban_chat_member(chat_id, member.id)
                link = f"tg://user?id={member.id}"
                bot.send_message(chat_id,
                    f"🚫 <b>সালা আইছিল টাকা মারতে ভরে দিছি!</b>\n\n"
                    f"স্ক্যামার: <a href='{link}'>{member.first_name}</a>\n"
                    f"আইডি: <code>{member.id}</code>\n"
                    f"ইউজারনেম: {f'@{member.username}' if member.username else 'N/A'}\n"
                    f"<i>গ্লোবাল ডাটাবেসে ব্ল্যাকলিস্টেড।</i>",
                    parse_mode='HTML')
            except Exception as e:
                print("Ban error:", e)

@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'])
def group_message_handler(message):
    text = message.text or ""
    lower_text = text.lower()
    keywords = ['scam', 'scammer', 'টাকা মারছে', 'টাকা মারে', 'প্রতারক', 'টাকা দিছে না', 'ঠগ', 'ধোঁকা']

    if any(kw in lower_text for kw in keywords):
        mention = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚫 Report Scammer", url=f"https://t.me/{BOT_USERNAME[1:]}?start=report"))
        bot.reply_to(message,
            f"{mention} ⚠️ সতর্কতা: স্ক্যাম সম্পর্কিত আলোচনা শনাক্ত হয়েছে।\n"
            "আপনার কাছে প্রমাণ থাকলে নিচের বাটনে ক্লিক করে রিপোর্ট করুন।",
            parse_mode='HTML', reply_markup=markup)

    # Bot mention
    if f"@{BOT_USERNAME[1:]}" in text or (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id):
        bot.reply_to(message,
            "🤖 আমি এন্টি-স্ক্যাম বট। স্ক্যামারের তথ্য থাকলে প্রাইভেটে এসে /start দিন।")

# Unban command for group admins
@bot.message_handler(commands=['unban'])
def unban_command(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    user_id = message.from_user.id
    if not is_group_admin(message.chat.id, user_id):
        bot.reply_to(message, "❌ শুধুমাত্র গ্রুপ এডমিন এই কমান্ড ব্যবহার করতে পারবেন!")
        return
    try:
        target = message.text.split()[1]
        # unban
        bot.unban_chat_member(message.chat.id, target)
        # Remove from scammer DB
        db['scammers'] = [s for s in db['scammers'] if str(s['id']) != str(target)]
        save_db(db)
        bot.reply_to(message, f"✅ {target} কে আনব্যান করা হয়েছে এবং ডাটাবেস থেকে সরানো হয়েছে।")
    except Exception as e:
        bot.reply_to(message, f"ত্রুটি: {str(e)}")

# -------------------- GROUP TRACKING --------------------
@bot.message_handler(content_types=['group_chat_created', 'new_chat_members', 'left_chat_member'])
def track_groups(message):
    if message.chat.type in ['group', 'supergroup']:
        chat_id = message.chat.id
        if chat_id not in db['groups']:
            db['groups'].append(chat_id)
            save_db(db)
    if message.content_type == 'left_chat_member':
        if message.left_chat_member.id == bot.get_me().id:
            # Bot removed from group
            if message.chat.id in db['groups']:
                db['groups'].remove(message.chat.id)
                save_db(db)

# -------------------- RUN --------------------
if __name__ == "__main__":
    print("Bot is starting...")
    # Start Flask in a separate thread
    threading.Thread(target=run_flask, daemon=True).start()
    # Start polling
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(10)
