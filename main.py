import telebot
from telebot import types
import json
import os
import threading
import time
from flask import Flask

# ========================= CONFIGURATION =========================
API_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770
CHANNEL_USERNAME = "@earning_channel24"  # চ্যানেল জয়েন চেকের জন্য
BOT_USERNAME = "@jhgmaing"  # আপনার বটের ইউজারনেম (যদি পরিবর্তন হয় তাহলে আপডেট করবেন)

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# ========================= DATABASE =========================
DB_FILE = 'database.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "scammers": [],      # [{"user_id": int, "username": str, "bikash": str, "proof_details": str, "added_by": int, "timestamp": str}]
        "admins": [OWNER_ID],
        "groups": [],        # গ্রুপ চ্যাট আইডি সেভ করার জন্য (ভবিষ্যতে ব্যবহার)
        "users": []          # যারা /start করেছে
    }

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# ========================= HELPERS =========================
def is_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def is_bot_admin(user_id):
    return user_id in db['admins'] or user_id == OWNER_ID

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

# ========================= FLASK FOR RENDER =========================
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
    bot.send_message(
        message.chat.id,
        "👋 স্বাগতম! আমি প্রফেশনাল এন্টি-স্ক্যাম বট।\n\n"
        "• স্ক্যামার দেখলে প্রমাণসহ রিপোর্ট করুন\n"
        "• গ্রুপে স্ক্যামার অটো ব্যান হবে\n"
        "• বিকাশ নাম্বার মিললে অটো ব্যান\n\n"
        "Developer: @jhgmaing + @bot_developer_io",
        reply_markup=markup
    )

# Join Check
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    if is_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ আপনি চ্যানেলে জয়েন করেছেন!", show_alert=True)
        start(call.message)  # মেনু দেখাবে
    else:
        bot.answer_callback_query(call.id, "❌ এখনো জয়েন করেননি।", show_alert=True)

# Help
@bot.callback_query_handler(func=lambda call: call.data == "help_cmd")
def help_cb(call):
    text = (
        "📖 **বট হেল্প**\n\n"
        "• স্ক্যামার রিপোর্ট করতে → Report Scammer বাটন চাপুন\n"
        "• প্রমাণ অবশ্যই ছবি (স্ক্রিনশট) দিতে হবে\n"
        "• গ্রুপে 'scam', 'টাকা মারছে' ইত্যাদি লিখলে বট সতর্ক করবে\n"
        "• অ্যাডমিনরা /unban করতে পারবেন\n"
        "• শুধুমাত্র চ্যানেলে জয়েন থাকলে বট ব্যবহার করা যাবে"
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')

# My Status
@bot.callback_query_handler(func=lambda call: call.data == "my_status")
def my_status(call):
    total_scammers = len(db['scammers'])
    bot.answer_callback_query(call.id, f"📊 মোট স্ক্যামার: {total_scammers}\nআপনার আইডি: {call.from_user.id}", show_alert=True)

# ========================= REPORT SYSTEM =========================
@bot.callback_query_handler(func=lambda call: call.data == "report_scam")
def report_init(call):
    if not is_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "চ্যানেলে জয়েন করুন প্রথমে!", show_alert=True)
        return
    bot.send_message(call.message.chat.id, 
        "🔍 স্ক্যামারের তথ্য দিন:\n"
        "• Chat ID অথবা @username\n"
        "• বিকাশ নাম্বার (যদি থাকে)\n"
        "• বিস্তারিত কারণ\n\n"
        "**ছবি (প্রমাণ) অবশ্যই পাঠাবেন**")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_report_step1)

def process_report_step1(message):
    if not message.photo:
        bot.reply_to(message, "❌ প্রমাণের ছবি দিতে হবে। আবার চেষ্টা করুন।")
        return

    file_id = message.photo[-1].file_id
    caption = message.caption or "কোনো ক্যাপশন নেই"

    # Extract possible user_id or username from caption
    user_input = caption.split('\n')[0] if '\n' in caption else caption

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_report_{message.from_user.id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_report_{message.from_user.id}")
    )

    admin_msg = bot.send_photo(
        OWNER_ID,
        file_id,
        caption=f"🆕 **নতুন স্ক্যাম রিপোর্ট**\n\n"
                f"রিপোর্টার: {message.from_user.id}\n"
                f"তথ্য: {caption}\n\n"
                f"অ্যাডমিন এপ্রুভ/রিজেক্ট করুন।",
        reply_markup=markup
    )
    bot.send_message(message.chat.id, "✅ আপনার রিপোর্ট অ্যাডমিনদের কাছে পাঠানো হয়েছে। ধন্যবাদ!")

# Approval / Rejection
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_report_', 'reject_report_')))
def handle_report_decision(call):
    if not is_bot_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "আপনি অ্যাডমিন নন!", show_alert=True)
        return

    action, reporter_id = call.data.split('_')[2], call.data.split('_')[3]  # wait, better parse

    if call.data.startswith("reject_report_"):
        bot.edit_message_caption("❌ রিপোর্ট রিজেক্ট করা হয়েছে।", call.message.chat.id, call.message.message_id)
        bot.send_message(int(reporter_id) if reporter_id.isdigit() else OWNER_ID, "❌ আপনার রিপোর্ট রিজেক্ট হয়েছে।")
        return

    # Approve flow
    bot.edit_message_caption("✅ এপ্রুভ হয়েছে। এখন স্ক্যামারের Chat ID দিন (অথবা @username):", call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, lambda m: save_scammer_after_approve(m, call.message.caption, call.from_user.id))

def save_scammer_after_approve(message, original_caption, approved_by):
    try:
        input_text = message.text.strip()
        user_id = None
        username = None

        if input_text.startswith('@'):
            username = input_text
            # Note: Telegram bot সরাসরি username থেকে ID পায় না সহজে। তাই user_id চাইলে ম্যানুয়ালি দিতে হবে।
            bot.reply_to(message, "⚠️ @username দিলে পরে ID দিয়ে আপডেট করুন। এখন Chat ID দিন:")
            return
        else:
            user_id = int(input_text)

        bikash = None
        # Try to extract bikash from original caption (simple way)
        if "বিকাশ" in original_caption.lower() or "bkash" in original_caption.lower():
            # rough extraction - admin can edit later
            bikash = "extracted_manually"

        add_scammer(user_id, username, bikash, original_caption, approved_by)
        bot.reply_to(message, f"✅ স্ক্যামার {user_id} ডাটাবেসে যোগ করা হয়েছে।\nসব গ্রুপে অটো ব্যান হবে।")
    except:
        bot.reply_to(message, "❌ ভুল Chat ID। আবার চেষ্টা করুন।")

# ========================= GROUP FEATURES =========================
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        if is_scammer(member.id):
            try:
                bot.ban_chat_member(message.chat.id, member.id)
                link = f"tg://user?id={member.id}"
                username = f"@{member.username}" if member.username else "No username"
                bot.send_message(
                    message.chat.id,
                    f"🚫 **সালা আইছিল টাকা মারতে! ভরে দিছি 🔥**\n\n"
                    f"**ইউজার:** {username}\n"
                    f"**Chat ID:** `{member.id}`\n"
                    f"**লিঙ্ক:** {link}\n"
                    f"গ্লোবাল ডাটাবেসে পাওয়া গেছে।"
                )
            except:
                pass

# Keyword detection + mention response
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    if message.chat.type not in ['group', 'supergroup']:
        return

    text = (message.text or "").lower()

    # Scam keywords
    scam_keywords = ['scam', 'scammer', 'টাকা মারছে', 'টাকা মারে', 'টাকা মেরে', 'প্রতারক', 'ঠকাইছে', 'scm', 'বিকাশ মেরে']
    if any(kw in text for kw in scam_keywords):
        bot.reply_to(
            message,
            "⚠️ **স্ক্যাম সংক্রান্ত কথা চলছে।**\n"
            "প্রমাণ থাকলে বটের ইনবক্সে Report Scammer বাটনে ক্লিক করে জমা দিন।"
        )

    # Bot mention
    bot_mention = f"@{bot.get_me().username}"
    if bot_mention in (message.text or "") or (message.entities and any(e.type == 'mention' for e in message.entities)):
        bot.reply_to(
            message,
            "✅ আমি এন্টি-স্ক্যাম বট।\n"
            "স্ক্যামার দেখলে প্রমাণসহ রিপোর্ট করুন।\n"
            "গ্রুপে স্ক্যামার অটো ব্যান হয়।"
        )

# ========================= ADMIN COMMANDS =========================
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if not is_bot_admin(message.from_user.id):
        return
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.reply_to(message, "মেসেজ লিখুন!")
        return

    count = 0
    for uid in db['users'][:]:  # copy to avoid modification issues
        try:
            bot.send_message(uid, f"📣 **ব্রডকাস্ট**\n\n{text}")
            count += 1
            time.sleep(0.05)  # rate limit safe
        except:
            pass
    bot.reply_to(message, f"✅ {count} জনের কাছে ব্রডকাস্ট পাঠানো হয়েছে।")

@bot.message_handler(commands=['addadmin'])
def add_admin_cmd(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        new_id = int(message.text.split()[1])
        if new_id not in db['admins']:
            db['admins'].append(new_id)
            save_db(db)
            bot.reply_to(message, f"✅ {new_id} কে অ্যাডমিন করা হয়েছে।")
    except:
        bot.reply_to(message, "ব্যবহার: /addadmin <chat_id>")

@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "শুধু গ্রুপে এই কমান্ড চলবে।")
        return
    try:
        target = int(message.text.split()[1])
        bot.unban_chat_member(message.chat.id, target, only_if_banned=True)
        # Remove from scammer db
        db['scammers'] = [s for s in db['scammers'] if str(s['user_id']) != str(target)]
        save_db(db)
        bot.reply_to(message, f"✅ {target} আনব্যান + ডাটাবেস থেকে রিমুভ করা হয়েছে।")
    except:
        bot.reply_to(message, "ব্যবহার: /unban <user_id>")

@bot.message_handler(commands=['removescammer'])
def remove_scammer_cmd(message):
    if not is_bot_admin(message.from_user.id):
        return
    try:
        sid = int(message.text.split()[1])
        db['scammers'] = [s for s in db['scammers'] if s['user_id'] != sid]
        save_db(db)
        bot.reply_to(message, f"✅ Scammer {sid} ডাটাবেস থেকে সরানো হয়েছে।")
    except:
        bot.reply_to(message, "ব্যবহার: /removescammer <user_id>")

# ========================= RUN =========================
if __name__ == "__main__":
    print("🚀 Anti-Scam Bot Starting... (Professional Version)")
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling(none_stop=True)
