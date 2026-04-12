import telebot
from telebot import types
import json
import os
import threading
from flask import Flask

# --- CONFIGURATION ---
API_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770
CHANNEL_USERNAME = "@earning_channel24"
BOT_USERNAME = "@jhgmaing" # আপনার বটের ইউজারনেম এখানে দিন

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- DATABASE SETUP ---
DB_FILE = 'database.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {"scammers": [], "admins": [OWNER_ID], "groups": [], "users": []}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

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

# --- FLASK FOR RENDER ---
@app.route('/')
def index():
    return "Bot is Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- BOT LOGIC ---

# Start Command
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in db['users']:
        db['users'].append(user_id)
        save_db(db)
        
    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        markup.add(types.InlineKeyboardButton("Check Join", callback_data="check_join"))
        bot.send_message(message.chat.id, f"❌ আপনি আমাদের চ্যানেলে জয়েন নেই। দয়া করে জয়েন করুন।\n\nChannel: {CHANNEL_USERNAME}", reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Report Scammer 🚫", callback_data="report_scam"),
        types.InlineKeyboardButton("Help ❓", callback_data="help_cmd"),
        types.InlineKeyboardButton("My Status 👤", callback_data="my_status")
    )
    bot.send_message(message.chat.id, "👋 স্বাগতম! আমি একটি প্রফেশনাল এন্টি-স্ক্যাম বট।\nনিচের বাটন গুলো ব্যবহার করুন।\n\nDeveloper: @jhgmaing & @bot_developer_io", reply_markup=markup)

# Help Callback
@bot.callback_query_handler(func=lambda call: call.data == "help_cmd")
def help_cb(call):
    help_text = (
        "📖 **বট হেল্প মেনু**\n\n"
        "1️⃣ কোনো ইউজার স্ক্যাম করলে /report কমান্ড দিন (বটের ইনবক্সে)।\n"
        "2️⃣ গ্রুপে কেউ 'scam' বা 'টাকা মারছে' লিখলে বট তাকে মেনশন দিবে।\n"
        "3️⃣ স্ক্যামারের বিকাশ নাম্বার ডাটাবেসে থাকলে তাকে অটো ব্যান করা হবে।\n"
        "4️⃣ এডমিনরা স্ক্যামারদের আনব্যান বা রিমুভ করতে পারবে।"
    )
    bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id)

# Report Logic
@bot.callback_query_handler(func=lambda call: call.data == "report_scam")
def report_init(call):
    bot.send_message(call.message.chat.id, "স্ক্যামারের Chat ID বা Username দিন এবং সাথে তার বিকাশ নাম্বার (যদি থাকে) এবং প্রমান (ছবি) পাঠান এক সাথে।")
    bot.register_next_step_handler(call.message, process_report)

def process_report(message):
    if not message.photo:
        bot.reply_to(message, "❌ অবশ্যই প্রমান স্বরূপ ছবি (Screenshot) দিতে হবে। আবার চেষ্টা করুন।")
        return
    
    file_id = message.photo[-1].file_id
    caption = message.caption if message.caption else "No Details Provided"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Approve ✅", callback_data=f"app_{message.from_user.id}"),
        types.InlineKeyboardButton("Reject ❌", callback_data=f"rej_{message.from_user.id}")
    )
    
    # Send to Owner for approval
    bot.send_photo(OWNER_ID, file_id, caption=f"🔔 **New Report Received**\nFrom: {message.from_user.id}\nDetails: {caption}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ আপনার রিপোর্ট এডমিনদের কাছে পাঠানো হয়েছে। যাচাই বাছাই করে তাকে ডাটাবেসে এড করা হবে।")

# Approval Handling
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def admin_decision(call):
    if not is_admin(call.from_user.id): return
    
    action, user_reported_id = call.data.split('_')
    
    if action == "app":
        # logic to extract info from caption and save to db
        # Here we assume admin manually adds scammer ID if approved
        bot.send_message(call.message.chat.id, "সফলভাবে এপ্রুভ হয়েছে। এখন স্ক্যামারের Chat ID দিন ডাটাবেসে সেভ করার জন্য:")
        bot.register_next_step_handler(call.message, lambda m: save_scammer(m, call.message.caption))
    else:
        bot.send_message(call.message.chat.id, "রিপোর্টটি রিজেক্ট করা হয়েছে।")

def save_scammer(message, details):
    scammer_id = message.text
    new_scam = {"id": scammer_id, "details": details}
    db['scammers'].append(new_scam)
    save_db(db)
    bot.reply_to(message, f"✅ Scammer {scammer_id} ডাটাবেসে সেভ হয়েছে এবং সব গ্রুপ থেকে ব্যান করা হবে।")

# --- GROUP AUTOMATION ---

@bot.message_handler(content_types=['new_chat_members'])
def on_join(message):
    for member in message.new_chat_members:
        # Check if scammer
        is_scam = any(str(s['id']) == str(member.id) for s in db['scammers'])
        if is_scam:
            bot.ban_chat_member(message.chat.id, member.id)
            bot.send_message(message.chat.id, f"🚫 **সালা আইছিল টাকা মারতে ভরে দিছি!**\n\nস্ক্যামার আইডি: `{member.id}`\nলিঙ্ক: tg://user?id={member.id}\nএকে আমাদের গ্লোবাল ডাটাবেসে পাওয়া গেছে।")

@bot.message_handler(func=lambda m: True)
def handle_group_msg(message):
    # Only act in groups
    if message.chat.type in ['group', 'supergroup']:
        text = message.text.lower() if message.text else ""
        
        # Scammer Keywords
        keywords = ['scam', 'scammer', 'টাকা মারছে', 'টাকা মারে', 'প্রতারক', 'টাকা দিছে না']
        if any(word in text for word in keywords):
            bot.reply_to(message, "⚠️ **সতর্কতা:** এই ইউজার স্ক্যামার নিয়ে কথা বলছে। আপনারা যদি কোনো স্ক্যামের শিকার হন তবে দ্রুত @jhgmaing বটে প্রমান জমা দিন।")

        # Admin Mention check
        if f"@{bot.get_me().username}" in text or message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
            bot.reply_to(message, "আমি একটি এন্টি-স্ক্যাম বট। আমাকে কাজ করতে দিন। কোনো স্ক্যামারের আইডি ও প্রমান থাকলে ইনবক্সে জমা দিন।")

# --- ADMIN COMMANDS ---

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if not is_admin(message.from_user.id): return
    msg_text = message.text.replace('/broadcast', '').strip()
    if not msg_text:
        bot.reply_to(message, "বক্স খালি! কি মেসেজ দিবেন তা লিখুন।")
        return
    
    count = 0
    for user in db['users']:
        try:
            bot.send_message(user, f"📣 **BROADCAST**\n\n{msg_text}")
            count += 1
        except: continue
    bot.reply_to(message, f"✅ {count} জন ইউজারের কাছে মেসেজ পাঠানো হয়েছে।")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if message.from_user.id != OWNER_ID: return
    new_admin = message.text.split()[1]
    db['admins'].append(int(new_admin))
    save_db(db)
    bot.reply_to(message, "✅ নতুন এডমিন যুক্ত করা হয়েছে।")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    # Any group admin can unban via bot
    try:
        user_id = message.text.split()[1]
        bot.unban_chat_member(message.chat.id, user_id)
        # remove from scammer db if exists
        db['scammers'] = [s for s in db['scammers'] if str(s['id']) != str(user_id)]
        save_db(db)
        bot.reply_to(message, f"✅ ইউজার {user_id} কে আনব্যান করা হয়েছে এবং ডাটাবেস থেকে সরানো হয়েছে।")
    except:
        bot.reply_to(message, "ব্যবহার: /unban user_id")

# --- RUN BOT ---
if __name__ == "__main__":
    print("Bot is starting...")
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
