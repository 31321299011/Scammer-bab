# main.py (Telegram Channel as Database via Pinned Message)
import telebot
from telebot import types
import json
import threading
import time
from flask import Flask
import traceback

# -------------------- CONFIGURATION --------------------
API_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770
CHANNEL_USERNAME = "@earning_channel24"
BOT_USERNAME = "@scammer_ban_bot"
CHANNEL_URL = f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"

# তোমার ডাটাবেস চ্যানেলের Chat ID
DB_CHANNEL_ID = 3991282017  # পজিটিভ আইডি

bot = telebot.TeleBot(API_TOKEN, parse_mode='HTML')
app = Flask(__name__)

# In-memory database structure
db = {
    "scammers": [],
    "admins": [OWNER_ID],
    "groups": [],
    "users": [],
    "pending_reports": {}
}
user_report_state = {}

# -------------------- DATABASE SYNC (PINNED MESSAGE) --------------------
def save_db():
    """Send database JSON as pinned message to channel"""
    try:
        # Convert db to JSON string
        json_str = json.dumps(db, ensure_ascii=False, indent=2)
        # Send as document if too large, else as text
        if len(json_str) > 3500:
            # Send as file
            msg = bot.send_document(DB_CHANNEL_ID, ('database.json', json_str.encode('utf-8')), caption="📦 Database Backup")
        else:
            msg = bot.send_message(DB_CHANNEL_ID, f"📦 DB:\n<pre>{json_str}</pre>", parse_mode='HTML')
        
        # Unpin previous pinned message (if any)
        try:
            chat = bot.get_chat(DB_CHANNEL_ID)
            if chat.pinned_message:
                bot.unpin_chat_message(DB_CHANNEL_ID, chat.pinned_message.message_id)
        except:
            pass
        
        # Pin new message
        bot.pin_chat_message(DB_CHANNEL_ID, msg.message_id)
        print("[DB] Saved and pinned in channel")
    except Exception as e:
        print(f"[DB] Save error: {e}")

def load_db():
    """Load database from pinned message in channel"""
    global db
    try:
        chat = bot.get_chat(DB_CHANNEL_ID)
        if chat.pinned_message:
            pinned = chat.pinned_message
            if pinned.document:
                # Download and parse JSON
                file_info = bot.get_file(pinned.document.file_id)
                downloaded = bot.download_file(file_info.file_path)
                loaded_db = json.loads(downloaded.decode('utf-8'))
                db = loaded_db
                print("[DB] Loaded from pinned document")
            elif pinned.text:
                # Extract JSON from text (format: 📦 DB:\n<pre>{...}</pre>)
                import re
                match = re.search(r'<pre>(.*?)</pre>', pinned.text, re.DOTALL)
                if match:
                    loaded_db = json.loads(match.group(1))
                    db = loaded_db
                else:
                    # Fallback: whole text after "DB:"
                    json_str = pinned.text.split('DB:',1)[1].strip()
                    loaded_db = json.loads(json_str)
                    db = loaded_db
                print("[DB] Loaded from pinned text")
        else:
            print("[DB] No pinned message, starting fresh")
            save_db()  # Save initial empty db
    except Exception as e:
        print(f"[DB] Load error: {e}")

# Load initial data
load_db()

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
    user_report_state.pop(user_id, None)
    if user_id not in db['users']:
        db['users'].append(user_id)
        save_db()

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

# -------------------- CANCEL --------------------
@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    user_id = message.from_user.id
    if user_id in user_report_state:
        user_report_state.pop(user_id, None)
        bot.reply_to(message, "❌ রিপোর্ট বাতিল করা হয়েছে।", reply_markup=main_menu_keyboard(user_id))
    else:
        bot.reply_to(message, "আপনার কোনো চলমান রিপোর্ট নেই।", reply_markup=main_menu_keyboard(user_id))

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

    if user_id in user_report_state:
        state = user_report_state[user_id]
        step = state.get('step')
        if step == 'awaiting_scammer_id' and message.content_type == 'text':
            receive_scammer_id(message)
            return
        elif step == 'awaiting_bikash' and message.content_type == 'text':
            receive_bikash(message)
            return
        elif step == 'awaiting_evidence':
            if message.content_type == 'photo':
                receive_evidence(message)
                return
            elif message.content_type == 'text' and message.text.strip().lower() == 'done':
                finalize_report(message)
                return
            else:
                bot.reply_to(message,
                    "⚠️ আপনি এখন রিপোর্ট প্রক্রিয়ায় আছেন।\n"
                    "ছবি পাঠান অথবা শেষ হলে <code>done</code> লিখুন।\n"
                    "রিপোর্ট বাতিল করতে /cancel দিন।",
                    parse_mode='HTML')
                return
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

# -------------------- REPORT STEPS --------------------
def start_report_step1(message):
    user_id = message.from_user.id
    user_report_state[user_id] = {'step': 'awaiting_scammer_id'}
    bot.reply_to(message,
        "🔍 <b>স্ক্যামারের Chat ID অথবা @username লিখুন:</b>\n(না জানা থাকলে <code>skip</code> লিখুন)\n\nরিপোর্ট বাতিল করতে /cancel দিন।",
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

    user_report_state[user_id]['scammer_id'] = scammer_id
    user_report_state[user_id]['username'] = username
    user_report_state[user_id]['step'] = 'awaiting_bikash'
    bot.reply_to(message,
        "💰 <b>বিকাশ নাম্বার (যদি থাকে):</b>\n(না থাকলে <code>skip</code>)\n\nবাতিল করতে /cancel",
        parse_mode='HTML'
    )

def receive_bikash(message):
    user_id = message.from_user.id
    bikash = message.text.strip()
    if bikash.lower() == 'skip':
        bikash = None

    user_report_state[user_id]['bikash'] = bikash
    user_report_state[user_id]['step'] = 'awaiting_evidence'
    user_report_state[user_id]['photos'] = []
    bot.reply_to(message,
        "🖼 <b>এখন প্রমাণ হিসেবে এক বা একাধিক ছবি পাঠান।</b>\nসব ছবি পাঠানো শেষ হলে <code>done</code> লিখুন।\n\nবাতিল করতে /cancel",
        parse_mode='HTML'
    )

def receive_evidence(message):
    user_id = message.from_user.id
    if not message.photo:
        bot.reply_to(message, "ছবি পাঠান অথবা 'done' লিখুন।")
        return
    file_id = message.photo[-1].file_id
    user_report_state[user_id]['photos'].append(file_id)
    bot.reply_to(message, f"✅ ছবি গৃহীত হয়েছে ({len(user_report_state[user_id]['photos'])} টি)। আরও পাঠাতে পারেন বা 'done' লিখুন।")

def finalize_report(message):
    user_id = message.from_user.id
    state = user_report_state.pop(user_id, {})
    if not state.get('photos'):
        bot.reply_to(message, "❌ অন্তত একটি ছবি দিতে হবে। আবার চেষ্টা করুন।")
        bot.send_message(user_id, "আপনি আবার রিপোর্ট শুরু করতে 'Report Scammer' বাটনে ক্লিক করুন.", reply_markup=main_menu_keyboard(user_id))
        return

    report_id = f"{user_id}_{int(time.time())}"
    report_data = {
        'reporter': user_id,
        'scammer_id': state.get('scammer_id'),
        'username': state.get('username'),
        'bikash': state.get('bikash'),
        'caption': f"প্রমাণ ছবি সংখ্যা: {len(state['photos'])}",
        'evidence_files': state['photos'],
        'timestamp': time.time()
    }
    db['pending_reports'][report_id] = report_data
    save_db()

    # Notify admins
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{report_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{report_id}")
    )
    admin_text = (
        f"🔔 <b>নতুন রিপোর্ট</b>\n"
        f"👤 রিপোর্টার: <code>{user_id}</code>\n"
        f"🆔 স্ক্যামার আইডি: {state.get('scammer_id') or 'N/A'}\n"
        f"📛 ইউজারনেম: {state.get('username') or 'N/A'}\n"
        f"💳 বিকাশ: {state.get('bikash') or 'N/A'}\n"
        f"🖼 ছবি: {len(state['photos'])} টি"
    )
    for admin_id in db['admins']:
        try:
            if len(state['photos']) == 1:
                bot.send_photo(admin_id, state['photos'][0], caption=admin_text, reply_markup=admin_markup)
            else:
                bot.send_photo(admin_id, state['photos'][0], caption=admin_text, reply_markup=admin_markup)
                media_group = [types.InputMediaPhoto(media=pid) for pid in state['photos'][1:]]
                if media_group:
                    bot.send_media_group(admin_id, media_group)
        except:
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
        "• গ্রুপ এডমিন /unban কমান্ড দিয়ে ভুল ব্যান তুলতে পারবেন।\n"
        "• গ্রুপে বট অ্যাড করলে /scan দিয়ে স্ক্যান করা যায়।\n"
        "• রিপোর্ট করার সময় যেকোনো ধাপে /cancel দিয়ে বাতিল করতে পারবেন।"
    )
    bot.reply_to(message, help_text, reply_markup=main_menu_keyboard(message.from_user.id))

def show_status(message):
    user_id = message.from_user.id
    is_scammer = any(str(s['id']) == str(user_id) for s in db['scammers'])
    status = (
        f"👤 <b>আপনার স্ট্যাটাস</b>\n"
        f"├ ইউজার আইডি: <code>{user_id}</code>\n"
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
    save_db()
    bot.reply_to(message, f"{'✅ সরানো হয়েছে' if before>after else '❌ পাওয়া যায়নি'}")

def process_broadcast(message):
    if not is_bot_admin(message.from_user.id): return
    text = message.text
    count = 0
    for uid in db['users']:
        try:
            bot.send_message(uid, f"📢 ব্রডকাস্ট\n\n{text}")
            count += 1
        except: pass
    bot.reply_to(message, f"✅ {count} জন ইউজারের কাছে পাঠানো হয়েছে।")

def process_add_admin(message):
    if message.from_user.id != OWNER_ID: return
    try:
        new_id = int(message.text.strip())
        if new_id not in db['admins']:
            db['admins'].append(new_id)
            save_db()
            bot.reply_to(message, f"✅ {new_id} এডমিন হয়েছে।")
        else:
            bot.reply_to(message, "ইতিমধ্যে এডমিন!")
    except:
        bot.reply_to(message, "ভুল ফরম্যাট!")

# -------------------- APPROVAL & BAN --------------------
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
        save_db()
        return

    # Approve
    if not report.get('scammer_id'):
        msg = bot.send_message(call.message.chat.id, f"রিপোর্ট #{report_id}\nস্ক্যামারের Chat ID লিখুন:")
        bot.register_next_step_handler(msg, lambda m: manual_id_then_save(m, report_id, call.message))
        return

    save_scammer_from_report(report, call.message, call.from_user.id)
    del db['pending_reports'][report_id]
    save_db()

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
    save_db()

def ban_scammer_in_all_groups(scammer_id):
    for gid in db['groups']:
        try:
            bot.ban_chat_member(gid, scammer_id)
            bot.send_message(gid, f"🚫 স্ক্যামার <code>{scammer_id}</code> কে গ্লোবাল ডাটাবেস থেকে ব্যান করা হয়েছে।")
        except: pass

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
        save_db()
        threading.Thread(target=ban_scammer_in_all_groups, args=(scam_data['id'],)).start()
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
    if chat_id not in db['groups']:
        db['groups'].append(chat_id)
        save_db()

    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            bot.send_message(chat_id,
                "🤖 বট অ্যাড হয়েছে। স্ক্যামার স্ক্যান শুরু হচ্ছে...\n"
                "সম্পূর্ণ স্ক্যান করতে অ্যাডমিন /scan কমান্ড ব্যবহার করুন।")
        else:
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
                except: pass

@bot.message_handler(commands=['scan'])
def scan_command(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ শুধু গ্রুপ এডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return

    bot.reply_to(message, "🔍 স্ক্যান শুরু হচ্ছে...")
    banned = 0
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        for admin in admins:
            if any(str(s['id']) == str(admin.user.id) for s in db['scammers']):
                try:
                    bot.ban_chat_member(message.chat.id, admin.user.id)
                    banned += 1
                except: pass
        bot.reply_to(message, f"✅ স্ক্যান সম্পন্ন। {banned} জন স্ক্যামার ব্যান করা হয়েছে।")
    except: pass

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
        save_db()
        bot.reply_to(message, f"✅ {target} আনব্যান ও ডাটাবেস থেকে সরানো হয়েছে।")
    except: pass

# -------------------- RUN --------------------
if __name__ == "__main__":
    print("Bot starting...")
    bot.remove_webhook()
    threading.Thread(target=run_flask, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
        except Exception as e:
            print(f"Polling error: {e}")
            traceback.print_exc()
            time.sleep(10)
