# main.py
import telebot
from telebot import types
import json
import os
import threading
import time
from flask import Flask
import re

# -------------------- CONFIGURATION --------------------
API_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770
CHANNEL_USERNAME = "@earning_channel24"
BOT_USERNAME = "@jhgmaing"
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
        "user_report_step": {}      # step only: 'id','bikash','evidence'
    }

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

db = load_db()

# Temporary data for report flow (to keep step tracking clean)
report_temp = {}   # user_id -> {'scammer_id':..., 'username':..., 'bikash':..., 'photos':[]}

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
    if user_id not in db['users']:
        db['users'].append(user_id)
        save_db(db)

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
@bot.message_handler(func=lambda m: m.chat.type == 'private', content_types=['text', 'photo'])
def private_message_handler(message):
    user_id = message.from_user.id
    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔄 Check Join", callback_data="check_join"))
        bot.reply_to(message, f"❌ চ্যানেল জয়েন আবশ্যক: {CHANNEL_USERNAME}", reply_markup=markup)
        return

    # Check if user is in report flow
    step = db['user_report_step'].get(str(user_id))
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

    # If not in flow, handle text commands / buttons
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
        # unexpected photo outside flow
        bot.reply_to(message, "দয়া করে আগে Report Scammer বাটনে ক্লিক করুন।")

# -------------------- REPORT STEPS (FIXED) --------------------
def start_report_step1(message):
    user_id = message.from_user.id
    db['user_report_step'][str(user_id)] = 'awaiting_scammer_id'
    report_temp.pop(user_id, None)  # clear old temp
    save_db(db)
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
    db['user_report_step'][str(user_id)] = 'awaiting_bikash'
    save_db(db)
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
    db['user_report_step'][str(user_id)] = 'awaiting_evidence'
    save_db(db)
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
        db['user_report_step'].pop(str(user_id), None)
        save_db(db)
        return

    # Save report
    report_id = f"{user_id}_{int(time.time())}"
    report_data = {
        'reporter': user_id,
        'scammer_id': data.get('scammer_id'),
        'username': data.get('username'),
        'bikash': data.get('bikash'),
        'caption': f"প্রমাণ ছবি সংখ্যা: {len(data['photos'])}",
        'evidence_files': data['photos'],
        'timestamp': time.time()
    }
    db['pending_reports'][report_id] = report_data
    db['user_report_step'].pop(str(user_id), None)
    save_db(db)

    # Notify admins
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{report_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{report_id}")
    )
    admin_text = (
        f"🔔 <b>নতুন রিপোর্ট</b>\n"
        f"👤 রিপোর্টার: <code>{user_id}</code>\n"
        f"🆔 স্ক্যামার আইডি: {report_data['scammer_id'] or 'N/A'}\n"
        f"📛 ইউজারনেম: {report_data['username'] or 'N/A'}\n"
        f"💳 বিকাশ: {report_data['bikash'] or 'N/A'}\n"
        f"🖼 ছবি: {len(data['photos'])} টি"
    )
    for admin_id in db['admins']:
        try:
            # send first photo with caption, rest as media group if multiple
            if len(data['photos']) == 1:
                bot.send_photo(admin_id, data['photos'][0], caption=admin_text, reply_markup=admin_markup)
            else:
                # send first as caption, then rest as album
                bot.send_photo(admin_id, data['photos'][0], caption=admin_text, reply_markup=admin_markup)
                media_group = [types.InputMediaPhoto(media=pid) for pid in data['photos'][1:]]
                if media_group:
                    bot.send_media_group(admin_id, media_group)
        except Exception as e:
            bot.send_message(admin_id, admin_text + "\n(ছবি পাঠাতে সমস্যা)", reply_markup=admin_markup)

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
        "• গ্রুপ এডমিন /unban কমান্ড দিয়ে ভুল ব্যান তুলতে পারবেন।"
    )
    bot.reply_to(message, help_text, reply_markup=main_menu_keyboard(message.from_user.id))

def show_status(message):
    user_id = message.from_user.id
    total_reports = sum(1 for r in db['pending_reports'].values() if r.get('reporter') == user_id)
    is_scammer = any(str(s['id']) == str(user_id) for s in db['scammers'])
    status = (
        f"👤 <b>আপনার স্ট্যাটাস</b>\n"
        f"├ ইউজার আইডি: <code>{user_id}</code>\n"
        f"├ জমাকৃত রিপোর্ট: {total_reports}\n"
        f"└ স্ক্যামার তালিকায়: {'হ্যাঁ' if is_scammer else 'না'}"
    )
    bot.reply_to(message, status, reply_markup=main_menu_keyboard(user_id))

# -------------------- ADMIN PANEL (INLINE) --------------------
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
        return

    if call.data == "list_scammers":
        scammers = db['scammers'][:30]
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
    before = len(db['scammers'])
    db['scammers'] = [s for s in db['scammers'] if str(s['id']) != sid]
    after = len(db['scammers'])
    save_db(db)
    bot.reply_to(message, f"{'✅ সরানো হয়েছে' if before>after else '❌ পাওয়া যায়নি'}")

def process_broadcast(message):
    if not is_bot_admin(message.from_user.id): return
    text = message.text
    count_users = 0
    count_groups = 0
    for uid in db['users']:
        try:
            bot.send_message(uid, f"📢 ব্রডকাস্ট\n\n{text}")
            count_users += 1
        except: pass
    for gid in db['groups']:
        try:
            bot.send_message(gid, f"📢 ব্রডকাস্ট\n\n{text}")
            count_groups += 1
        except: pass
    total_scammers = len(db['scammers'])
    bot.reply_to(message,
        f"✅ ব্রডকাস্ট সম্পন্ন!\n\n"
        f"👥 মোট ইউজার: {len(db['users'])}\n"
        f"💬 মোট গ্রুপ: {len(db['groups'])}\n"
        f"📨 পৌঁছেছে ইউজার: {count_users}\n"
        f"📢 পৌঁছেছে গ্রুপ: {count_groups}\n"
        f"🚫 মোট স্ক্যামার: {total_scammers}"
    )

def process_add_admin(message):
    if message.from_user.id != OWNER_ID: return
    try:
        new_id = int(message.text.strip())
        if new_id not in db['admins']:
            db['admins'].append(new_id)
            save_db(db)
            bot.reply_to(message, f"✅ {new_id} এডমিন হয়েছে।")
        else:
            bot.reply_to(message, "ইতিমধ্যে এডমিন!")
    except:
        bot.reply_to(message, "ভুল ফরম্যাট!")

# -------------------- APPROVAL CALLBACK --------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def handle_approval(call):
    bot.answer_callback_query(call.id)
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "আপনি অনুমোদিত নন!", show_alert=True)
        return

    action, report_id = call.data.split('_', 1)
    report = db['pending_reports'].get(report_id)
    if not report:
        bot.edit_message_caption("রিপোর্ট আর নেই।", call.message.chat.id, call.message.message_id)
        return

    if action == "rej":
        bot.edit_message_caption(call.message.caption + "\n\n❌ রিজেক্ট করা হয়েছে",
                                 call.message.chat.id, call.message.message_id)
        try:
            bot.send_message(report['reporter'], "❌ আপনার রিপোর্ট গৃহীত হয়নি।")
        except: pass
        del db['pending_reports'][report_id]
        save_db(db)
        return

    # Approve
    if not report.get('scammer_id'):
        msg = bot.send_message(call.message.chat.id, f"রিপোর্ট #{report_id}\nস্ক্যামারের Chat ID লিখুন:")
        bot.register_next_step_handler(msg, lambda m: manual_id_then_save(m, report_id, call.message))
        return

    save_scammer_from_report(report, call.message, call.from_user.id)
    del db['pending_reports'][report_id]
    save_db(db)

def manual_id_then_save(message, report_id, original_msg):
    if not is_bot_admin(message.from_user.id): return
    sid, uname = extract_id_from_text(message.text.strip())
    if not sid:
        bot.reply_to(message, "❌ বৈধ ID নয়!")
        return
    report = db['pending_reports'].get(report_id)
    if not report:
        bot.reply_to(message, "রিপোর্ট মেয়াদোত্তীর্ণ")
        return
    report['scammer_id'] = sid
    report['username'] = uname or report.get('username')
    save_scammer_from_report(report, original_msg, message.from_user.id)
    del db['pending_reports'][report_id]
    save_db(db)

def save_scammer_from_report(report, message_or_call, admin_id):
    scam_data = {
        "id": report['scammer_id'],
        "username": report.get('username'),
        "bikash": report.get('bikash'),
        "details": f"প্রমাণ ছবি: {len(report.get('evidence_files', []))} টি",
        "added_by": admin_id
    }
    if not any(str(s['id']) == str(scam_data['id']) for s in db['scammers']):
        db['scammers'].append(scam_data)
        save_db(db)
    try:
        bot.send_message(report['reporter'], "✅ আপনার রিপোর্ট অনুমোদিত হয়েছে।")
    except: pass
    if hasattr(message_or_call, 'edit_caption'):
        message_or_call.edit_caption(message_or_call.caption + "\n\n✅ অনুমোদিত")
    else:
        bot.reply_to(message_or_call, "✅ সংরক্ষিত।")

# -------------------- GROUP AUTOMATION (NO REPLY KEYBOARD) --------------------
@bot.message_handler(content_types=['new_chat_members'])
def on_join(message):
    chat_id = message.chat.id
    for member in message.new_chat_members:
        scam = next((s for s in db['scammers'] if str(s['id']) == str(member.id)), None)
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
        db['scammers'] = [s for s in db['scammers'] if str(s['id']) != str(target)]
        save_db(db)
        bot.reply_to(message, f"✅ {target} আনব্যান ও ডাটাবেস থেকে সরানো হয়েছে।")
    except Exception as e:
        bot.reply_to(message, f"ত্রুটি: {e}")

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
            if message.chat.id in db['groups']:
                db['groups'].remove(message.chat.id)
                save_db(db)

# -------------------- RUN --------------------
if __name__ == "__main__":
    print("Bot starting...")
    threading.Thread(target=run_flask, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(10)
