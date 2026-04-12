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
BOT_USERNAME = "@jhgmaing"

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# --- DATABASE SETUP ---
DB_FILE = 'scam_database.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {"scammers": [], "admins": [OWNER_ID], "groups": [], "users": [], "bikash_list": []}

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

# --- KEYBOARDS (সব বক্স বাটন হবে বটের ভিতর) ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚫 Report Scammer", "📊 My Status")
    markup.row("ℹ️ Help", "📢 Channel")
    if is_admin(user_id):
        markup.row("🛠 Admin Control Panel")
    return markup

def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📜 List All Scammers", callback_data="adm_list"),
        types.InlineKeyboardButton("➕ Add Admin", callback_data="adm_add"),
        types.InlineKeyboardButton("❌ Remove Scammer", callback_data="adm_rem_scam"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc")
    )
    return markup

# --- FLASK FOR RENDER ---
@app.route('/')
def index(): return "Bot is Running 10000000% Fine!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- BOT LOGIC ---

# Start Command
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # Save User
    if user_id not in db['users']:
        db['users'].append(user_id)
        save_db(db)
        
    # Check Channel Join
    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(types.InlineKeyboardButton("Check Join ✅", callback_data="check_channel_join"))
        bot.send_message(message.chat.id, f"❌ <b>আপনি আমাদের চ্যানেলে জয়েন নেই!</b>\nবট ব্যবহার করতে অবশ্যই {CHANNEL_USERNAME} চ্যানেলে জয়েন থাকা লাগবে। জয়েন হয়ে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)
        return

    # If already joined, send main menu box buttons
    bot.send_message(message.chat.id, "👋 <b>স্বাগতম এন্টি-স্ক্যাম বোটে!</b>\nনিচের বক্স বাটনগুলো ব্যবহার করুন। কোনো মুখস্থ কমান্ড দেওয়া লাগবে না।\n\nDeveloper by @jhgmaing + @bot_developer_io", reply_markup=main_menu(user_id))

# --- REPORT SYSTEM (Step by Step) ---
@bot.message_handler(func=lambda m: m.text == "🚫 Report Scammer")
def report_scam_start(message):
    if not is_joined(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "👤 স্ক্যামারের Chat ID অথবা Username দিন (ইউজারনেম দিলেও আমরা চ্যাট আইডি বের করে নিব):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_scammer_id)

def process_scammer_id(message):
    scammer_id_or_user = message.text
    msg = bot.send_message(message.chat.id, "💸 স্ক্যামারের বিকাশ নাম্বার দিন (যদি থাকে, না থাকলে 'No' লিখুন):")
    bot.register_next_step_handler(msg, process_scammer_bikash, scammer_id_or_user)

def process_scammer_bikash(message, scammer_id_or_user):
    bikash = message.text
    msg = bot.send_message(message.chat.id, "📸 প্রমাণ স্বরূপ স্ক্যামের স্ক্রিনশট বা ফটো পাঠান (ছবি না দিলে রিপোর্ট সাবমিট হবে না):")
    bot.register_next_step_handler(msg, process_scammer_proof, scammer_id_or_user, bikash)

def process_scammer_proof(message, scammer_id_or_user, bikash):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ আপনি ছবি পাঠাননি। রিপোর্ট বাতিল করা হলো। আবার চেষ্টা করুন।", reply_markup=main_menu(message.from_user.id))
        return
    
    file_id = message.photo[-1].file_id # ফাস্ট কাজের জন্য শুধু ফাইল আইডি নিব
    
    # Admin approval message setup
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Approve ✅", callback_data=f"appv_{message.from_user.id}"),
        types.InlineKeyboardButton("Reject ❌", callback_data=f"rejt_{message.from_user.id}")
    )
    
    caption = f"🔔 <b>নতুন স্ক্যামার রিপোর্ট!</b>\n\n" \
              f"👤 <b>রিপোর্টার ID:</b> <code>{message.from_user.id}</code>\n" \
              f"🎯 <b>স্ক্যামার ID/User:</b> <code>{scammer_id_or_user}</code>\n" \
              f"💰 <b>বিকাশ নাম্বার:</b> <code>{bikash}</code>"
              
    bot.send_photo(OWNER_ID, file_id, caption=caption, reply_markup=markup)
    bot.send_message(message.chat.id, "✅ আপনার প্রমাণ এডমিন প্যানেলে পাঠানো হয়েছে। এডমিন চেক করে তাকে ডাটাবেসে সেভ করবে।", reply_markup=main_menu(message.from_user.id))

# --- GROUP MONITORING & AUTO BAN (1 Second) ---

@bot.message_handler(content_types=['new_chat_members'])
def auto_ban_on_join(message):
    if message.chat.id not in db['groups']:
        db['groups'].append(message.chat.id)
        save_db(db)
        
    for member in message.new_chat_members:
        # ডাটাবেসে চেক করা
        is_scam = False
        for scammer in db['scammers']:
            if str(scammer['id']) == str(member.id) or (member.username and member.username == scammer['username']):
                is_scam = True
                break
                
        if is_scam:
            bot.ban_chat_member(message.chat.id, member.id)
            user_link = f"<a href='tg://user?id={member.id}'>{member.first_name}</a>"
            username_show = f"@{member.username}" if member.username else "No Username"
            
            # তোমার দেওয়া হুবহু মেসেজ
            bot.send_message(
                message.chat.id, 
                f"🚫 <b>সালা আইছিল টাকা মারতে ভরে দিছি</b>\n\n"
                f"👤 <b>স্ক্যামার লিংক:</b> {user_link}\n"
                f"🆔 <b>চ্যাট আইডি:</b> <code>{member.id}</code>\n"
                f"🏷 <b>ইউজারনেম:</b> {username_show}"
            )

@bot.message_handler(func=lambda m: True, content_types=['text'])
def group_text_handler(message):
    # শুধু গ্রুপে কাজ করবে
    if message.chat.type in ['group', 'supergroup']:
        text = message.text.lower()
        
        # ১. স্ক্যাম কি-ওয়ার্ড ডিটেক্ট এবং মেনশন
        keywords = ['scam', 'টাকা মারা', 'টাকা মেরে দিছে', 'scammer', 'টাকা মারে', 'প্রতারক']
        if any(word in text for word in keywords):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Submit Proof 🚫", url=f"https://t.me/{BOT_USERNAME[1:]}"))
            
            bot.reply_to(
                message, 
                f"⚠️ <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a> আপনি যদি কোনো স্ক্যামের শিকার হন, তবে প্রমাণসহ বটের ইনবক্সে গিয়ে রিপোর্ট করুন।", 
                reply_markup=markup
            )

        # ২. বিকাশ নাম্বার ম্যাচিং অটো ব্যান
        for scam_num in db['bikash_list']:
            if scam_num in message.text:
                bot.ban_chat_member(message.chat.id, message.from_user.id)
                bot.send_message(message.chat.id, f"🚫 এই গ্রুপে স্ক্যামারদের বিকাশ নাম্বার শেয়ার করা নিষেধ! ইউজারকে ডাটাবেস অনুযায়ী অটো ব্যান করা হলো।")
                return

        # ৩. বটকে মেনশন দিলে রেসপন্স
        if f"@{bot.get_me().username}" in message.text:
            bot.reply_to(message, "আমি একটি প্রোফেশনাল এন্টি-স্ক্যাম বট। কারো বিরুদ্ধে প্রমাণ দিতে সরাসরি বটের ইনবক্সে যান।")

# --- GROUP ADMIN /UNBAN ---
@bot.message_handler(commands=['unban'])
def group_unban(message):
    # শুধু গ্রুপ এডমিনরা বটের মাধ্যমে তাদের গ্রুপে কাওকে আনব্যান করতে পারবে
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status in ['administrator', 'creator'] or message.from_user.id == OWNER_ID:
            user_id = message.text.split()[1]
            bot.unban_chat_member(message.chat.id, user_id)
            bot.reply_to(message, f"✅ ইউজার <code>{user_id}</code> কে গ্রুপ থেকে আনব্যান করা হয়েছে।")
        else:
            bot.reply_to(message, "❌ আপনি এই গ্রুপের এডমিন নন।")
    except Exception as e:
        bot.reply_to(message, "ব্যবহার: /unban user_id")

# --- CALLBACK CONTROLS (কোনো বাটন ফাঁকা যাবে না) ---

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # ১. চ্যানেল জয়েন চেক
    if call.data == "check_channel_join":
        if is_joined(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, "✅ ধন্যবাদ! আপনি আমাদের চ্যানেলে জয়েন হয়েছেন।", reply_markup=main_menu(call.from_user.id))
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো জয়েন করেননি!", show_alert=True)
            
    # ২. এডমিন প্যানেল বাটনসমূহ
    elif call.data == "adm_list":
        if not is_admin(call.from_user.id): return
        text = "🚫 <b>টোটাল স্ক্যামার লিস্ট:</b>\n\n"
        for s in db['scammers'][:20]: # ডাটাবেসের প্রথম ২০ জন
            text += f"ID: <code>{s['id']}</code> | User: {s['username']}\n"
        bot.send_message(call.message.chat.id, text)
        bot.answer_callback_query(call.id)

    elif call.data == "adm_rem_scam":
        if not is_admin(call.from_user.id): return
        msg = bot.send_message(call.message.chat.id, "❌ যে স্ক্যামারের চ্যাট আইডি রিমুভ করতে চান তা দিন:")
        bot.register_next_step_handler(msg, process_remove_scammer)
        bot.answer_callback_query(call.id)

    elif call.data == "adm_add":
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "শুধুমাত্র মেইন বোট কন্ট্রোলার এই কাজ করতে পারবে!", show_alert=True)
            return
        msg = bot.send_message(call.message.chat.id, "➕ নতুন এডমিনের চ্যাট আইডি দিন:")
        bot.register_next_step_handler(msg, process_add_admin)
        bot.answer_callback_query(call.id)

    elif call.data == "adm_bc":
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "শুধুমাত্র মেইন ওনার ব্রডকাস্ট করতে পারবে!", show_alert=True)
            return
        msg = bot.send_message(call.message.chat.id, "📢 ব্রডকাস্টের মেসেজটি লিখুন (এটি সকল ইউজার ও গ্রুপে যাবে):")
        bot.register_next_step_handler(msg, process_broadcast)
        bot.answer_callback_query(call.id)

    # ৩. এপ্রুভ এবং রিজেক্ট সিস্টেম
    elif call.data.startswith(('appv_', 'rejt_')):
        if not is_admin(call.from_user.id): return
        action, reporter_id = call.data.split('_')
        
        if action == "appv":
            msg = bot.send_message(call.message.chat.id, "✅ এপ্রুভ সফল। এখন স্ক্যামারের Chat ID টি দিন ডাটাবেসে সেভ করার জন্য:")
            # আমরা এডমিনের কাছ থেকে সঠিক চ্যাট আইডি নিয়ে ডাটাবেসে সেভ করব
            bot.register_next_step_handler(msg, lambda m: save_scammer_to_db(m, reporter_id))
        else:
            bot.send_message(call.message.chat.id, "❌ রিপোর্টটি বাতিল করা হয়েছে।")
            bot.send_message(reporter_id, "❌ আপনার দেওয়া রিপোর্টটি এডমিন বাতিল করেছে।")
            
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)

# --- SAVE SCAMMER PROCESS ---
def save_scammer_to_db(message, reporter_id):
    scammer_id = message.text.strip()
    # এডমিন চাইলে ইউজারনেমও দিতে পারে
    db['scammers'].append({"id": scammer_id, "username": "N/A"})
    save_db(db)
    bot.reply_to(message, f"✅ স্ক্যামার <code>{scammer_id}</code> ডাটাবেসে সফলভাবে সেভ করা হয়েছে।")
    bot.send_message(reporter_id, "🎉 অভিনন্দন! আপনার দেওয়া রিপোর্টটি এডমিন এপ্রুভ করেছে।")

def process_remove_scammer(message):
    target = message.text.strip()
    db['scammers'] = [s for s in db['scammers'] if str(s['id']) != target]
    save_db(db)
    bot.reply_to(message, f"✅ আইডি <code>{target}</code> স্ক্যামার ডাটাবেস থেকে রিমুভ করা হয়েছে।")

def process_add_admin(message):
    new_admin = int(message.text.strip())
    if new_admin not in db['admins']:
        db['admins'].append(new_admin)
        save_db(db)
        bot.reply_to(message, f"✅ ইউজার <code>{new_admin}</code> এখন থেকে বটের এডমিন।")

def process_broadcast(message):
    text = message.text
    # ১. সকল ইউজারকে মেসেজ
    u_count = 0
    for u in db['users']:
        try:
            bot.send_message(u, f"📢 <b>Broadcast Message:</b>\n\n{text}")
            u_count += 1
        except: continue
        
    # ২. সকল গ্রুপে মেসেজ
    g_count = 0
    for g in db['groups']:
        try:
            bot.send_message(g, f"📢 <b>Global Announcement:</b>\n\n{text}")
            g_count += 1
        except: continue
        
    bot.send_message(message.chat.id, f"✅ ব্রডকাস্ট সম্পূর্ণ হয়েছে!\nগ্রুপে গিয়েছে: {g_count} টি\nইউজার পেয়েছে: {u_count} জন")

# --- OTHER BOX BUTTON FUNCTIONS ---
@bot.message_handler(func=lambda m: m.text == "📊 My Status")
def my_status(message):
    status = "Admin 🛠" if is_admin(message.from_user.id) else "Member 👤"
    bot.send_message(message.chat.id, f"👤 <b>আপনার প্রোফাইল:</b>\n\nনাম: {message.from_user.first_name}\nচ্যাট আইডি: <code>{message.from_user.id}</code>\nস্ট্যাটাস: {status}")

@bot.message_handler(func=lambda m: m.text == "ℹ️ Help")
def help_menu(message):
    bot.send_message(message.chat.id, "📖 <b>বট হেল্প গাইড:</b>\n\n১. গ্রুপে বটটিকে এডমিন দিন এবং ডিলিট/ব্যান পারমিশন অন করুন।\n২. কেউ স্ক্যাম করলে বটের ইনবক্সে প্রমান দিন।\n৩. গ্রুপে কেউ স্ক্যাম কী-ওয়ার্ড লিখলে বট তাকে মেনশন দিবে।")

@bot.message_handler(func=lambda m: m.text == "🛠 Admin Control Panel")
def admin_panel(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "🎛 <b>এডমিন প্যানেল:</b>\nনিচের বাটনগুলো ব্যবহার করুন।", reply_markup=admin_keyboard())

# --- RUN BOT ---
if __name__ == "__main__":
    print("Bot is Starting 10000000%...")
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
