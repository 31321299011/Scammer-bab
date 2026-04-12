import telebot
from telebot import types
import json
import os
import threading
from flask import Flask

# --- CONFIGURATION ---
API_TOKEN = '8667512297:REPLACE_TOKEN'
OWNER_ID = 8194390770
CHANNEL_USERNAME = "@earning_channel24"
BOT_USERNAME = "jhgmaing"

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# --- DATABASE ---
DB_FILE = 'database.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {"scammers": [], "admins": [OWNER_ID], "groups": [], "users": [], "reports": []}

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

db = load_db()

# --- HELPERS ---
def is_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def is_admin(user_id):
    return user_id in db['admins'] or user_id == OWNER_ID

def get_user_link(user):
    return f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

# --- FLASK ---
@app.route('/')
def index():
    return "Bot Running"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id

    if uid not in db['users']:
        db['users'].append(uid)
        save_db()

    if not is_joined(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Join Channel", url="https://t.me/earning_channel24"),
            types.InlineKeyboardButton("Check Join", callback_data="check_join")
        )
        bot.send_message(message.chat.id, "❌ আগে চ্যানেলে join করুন", reply_markup=markup)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚫 Report", "📊 Status")
    markup.row("📖 Help")

    bot.send_message(message.chat.id,
                     "👋 Anti-Scam Bot Ready\nDeveloper: @jhgmaing + @bot_developer_io",
                     reply_markup=markup)

# --- JOIN CHECK ---
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(call):
    if is_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified")
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ এখনও join করেন নাই")

# --- HELP ---
@bot.message_handler(func=lambda m: m.text == "📖 Help")
def help_menu(message):
    bot.send_message(message.chat.id,
                     "📖 Help:\nReport scammer, auto-ban, admin control, proof system active.")

# --- REPORT SYSTEM ---
@bot.message_handler(func=lambda m: m.text == "🚫 Report")
def report_start(message):
    if not is_joined(message.from_user.id):
        bot.reply_to(message, "❌ আগে channel join")
        return
    bot.reply_to(message, "Scammer ID / username + proof (photo) + optional bkash দিন")
    bot.register_next_step_handler(message, process_report)

def process_report(message):
    if not message.photo:
        bot.reply_to(message, "❌ screenshot লাগবে")
        return

    file_id = message.photo[-1].file_id
    caption = message.caption or "No details"

    report_id = len(db['reports']) + 1

    db['reports'].append({
        "id": report_id,
        "from": message.from_user.id,
        "caption": caption,
        "file": file_id
    })
    save_db()

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Approve", callback_data=f"approve_{report_id}"),
        types.InlineKeyboardButton("Reject", callback_data=f"reject_{report_id}")
    )

    bot.send_photo(OWNER_ID, file_id,
                   caption=f"📩 REPORT #{report_id}\n{caption}",
                   reply_markup=markup)

    bot.reply_to(message, "✅ Report submitted")

# --- APPROVAL ---
@bot.callback_query_handler(func=lambda c: c.data.startswith(("approve_", "reject_")))
def decision(call):
    if not is_admin(call.from_user.id):
        return

    action, rid = call.data.split("_")
    rid = int(rid)

    report = next((r for r in db['reports'] if r['id'] == rid), None)
    if not report:
        return

    if action == "approve":
        bot.send_message(call.message.chat.id, "Send scammer ID এখন")
        bot.register_next_step_handler(call.message, save_scammer, report)
    else:
        bot.edit_message_caption("❌ Rejected", call.message.chat.id, call.message.message_id)

def save_scammer(message, report):
    sid = message.text.strip()

    db['scammers'].append({
        "id": sid,
        "details": report['caption']
    })
    save_db()

    bot.reply_to(message, f"✅ Saved scammer {sid}")

# --- GROUP JOIN BAN ---
@bot.message_handler(content_types=['new_chat_members'])
def auto_ban(message):
    if message.chat.id not in db['groups']:
        db['groups'].append(message.chat.id)
        save_db()

    for user in message.new_chat_members:
        for scam in db['scammers']:
            if str(user.id) == str(scam['id']):
                bot.ban_chat_member(message.chat.id, user.id)
                bot.send_message(message.chat.id,
                                 f"🚫 Scam detected\nID: {user.id}\nLink: tg://user?id={user.id}")

# --- GROUP MESSAGE DETECT ---
@bot.message_handler(func=lambda m: True)
def group_watch(message):
    if message.chat.type in ['group', 'supergroup']:
        text = message.text.lower() if message.text else ""

        keywords = ["scam", "টাকা মারছে", "scammer"]

        if any(k in text for k in keywords):
            bot.reply_to(message,
                         f"{get_user_link(message.from_user)} ⚠️ proof submit করুন bot inbox এ")

        if BOT_USERNAME in text:
            bot.reply_to(message, "🤖 Active Anti-Scam Bot")

# --- BROADCAST ---
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != OWNER_ID:
        return

    msg = message.text.replace('/broadcast', '').strip()

    total = 0

    for u in db['users']:
        try:
            bot.send_message(u, msg)
            total += 1
        except:
            pass

    for g in db['groups']:
        try:
            bot.send_message(g, msg)
        except:
            pass

    bot.reply_to(message, f"✅ Sent to {total} users")

# --- ADD ADMIN ---
@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if message.from_user.id != OWNER_ID:
        return

    uid = int(message.text.split()[1])
    db['admins'].append(uid)
    save_db()

    bot.reply_to(message, "✅ Admin added")

# --- UNBAN ---
@bot.message_handler(commands=['unban'])
def unban(message):
    try:
        uid = int(message.text.split()[1])
        bot.unban_chat_member(message.chat.id, uid)

        db['scammers'] = [s for s in db['scammers'] if str(s['id']) != str(uid)]
        save_db()

        bot.reply_to(message, "✅ Unbanned + removed from DB")
    except:
        bot.reply_to(message, "Usage: /unban user_id")

# --- RUN ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    print("Bot Running...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
