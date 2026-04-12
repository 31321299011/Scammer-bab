import telebot
import sqlite3
import requests
import random
import time
import threading
import os
import re
from telebot import types
from flask import Flask

# --- কনফিগারেশন ---
API_TOKEN = '8667512297:AAGuoVhNna0mIQOUs23-SQ7OdWDShH2jnRk'
OWNER_ID = 8194390770 
CHANNEL_USERNAME = '@earning_channel24'
CHANNEL_URL = 'https://t.me/earning_channel24'

bot = telebot.TeleBot(API_TOKEN)
server = Flask(__name__)

# --- রেন্ডার ফিক্স (Health Check) ---
@server.route('/')
def home():
    return "Bot is Active!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)

# --- ডাটাবেস সেটআপ ---
def init_db():
    conn = sqlite3.connect('scam_db.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS scammers 
                      (chat_id INTEGER PRIMARY KEY, username TEXT, bkash TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS bot_admins (user_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()

# --- ইউটিলিটি ফাংশন ---
def check_join(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return True # বট এডমিন না থাকলে চেক স্কিপ করবে

def is_scammer(user_id=None, username=None, bkash_list=None):
    conn = sqlite3.connect('scam_db.db')
    cursor = conn.cursor()
    res = None
    if user_id:
        res = cursor.execute("SELECT * FROM scammers WHERE chat_id=?", (user_id,)).fetchone()
    if not res and username:
        res = cursor.execute("SELECT * FROM scammers WHERE username=?", (username.replace("@", "").lower(),)).fetchone()
    if not res and bkash_list:
        for num in bkash_list:
            res = cursor.execute("SELECT * FROM scammers WHERE bkash LIKE ?", (f'%{num}%',)).fetchone()
            if res: break
    conn.close()
    return res

def is_admin(user_id):
    if user_id == OWNER_ID: return True
    conn = sqlite3.connect('scam_db.db')
    res = cursor = conn.execute("SELECT user_id FROM bot_admins WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return res is not None

# --- অটো ব্যান ও ডিটেকশন ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'new_chat_members'])
def handle_all_messages(message):
    # স্ট্যাটাস সেভ
    conn = sqlite3.connect('scam_db.db')
    conn.execute("INSERT OR IGNORE INTO stats (id) VALUES (?)", (message.chat.id,))
    conn.commit()
    conn.close()

    # নতুন মেম্বার জয়েন করলে চেক
    if message.content_type == 'new_chat_members':
        for user in message.new_chat_members:
            if is_scammer(user_id=user.id, username=user.username):
                bot.ban_chat_member(message.chat.id, user.id)
                bot.send_message(message.chat.id, f"সালা আইছিল টাকা মারতে, ভরে দিছি! 🚫\n\nScammer: @{user.username}\nID: `{user.id}`\n\nবট থাকতে স্ক্যামিং চলবে না! 🔥")
        return

    # টেক্সট মেসেজ চেক
    if message.text:
        # বিকার নাম্বার বের করা
        bkash_nums = re.findall(r'01[3-9]\d{8}', message.text)
        user = message.from_user
        
        # স্ক্যামার চেক
        scam_data = is_scammer(user_id=user.id, username=user.username, bkash_list=bkash_nums)
        if scam_data:
            try:
                bot.ban_chat_member(message.chat.id, user.id)
                bot.send_message(message.chat.id, f"সালা আইছিল টাকা মারতে, ভরে দিছি! 🚫\n\nScammer: @{user.username}\nID: `{user.id}`\n\nপ্রমানিত স্ক্যামার ডাটাবেসে পাওয়া গেছে।")
                return
            except: pass

        # বোট মেনশন করলে রেসপন্স
        if f"@{bot.get_me().username}" in message.text:
            bot.reply_to(message, "আমি সজাগ আছি! এই গ্রুপে কোনো স্ক্যামার ডুকলে বা টাকা মারার চেষ্টা করলে সাথে সাথে ভরে দেওয়া হবে। 🔥")

        # স্ক্যাম কী-ওয়ার্ড চেক
        keys = ['টাকা মারছে', 'scam', 'স্ক্যামার', 'টাকা দেয় না']
        if any(x in message.text.lower() for x in keys):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("রিপোর্ট করুন (Proof)", url=f"https://t.me/{bot.get_me().username}?start=report"))
            bot.reply_to(message, "এই ইউজার কি স্ক্যাম করেছে? প্রমান থাকলে নিচের বাটনে ক্লিক করে রিপোর্ট দিন।", reply_markup=markup)

# --- প্রাইভেট কমান্ডস ---
@bot.message_handler(commands=['start'], chat_types=['private'])
def start(message):
    if message.text == "/start report":
        submit_report(message)
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("Report Scammer 🚩", callback_data="report"),
               types.InlineKeyboardButton("Help ❓", callback_data="help"))
    
    bot.send_message(message.chat.id, f"স্বাগতম! আমি @{bot.get_me().username}।\nস্ক্যামার মুক্ত টেলিগ্রাম গড়তে আমরা কাজ করছি।\n\nDeveloper: @jhgmaing & @bot_developer_io", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "report":
        if not check_join(call.from_user.id):
            bot.answer_callback_query(call.id, "আগে চ্যানেলে জয়েন করুন!", show_alert=True)
            return
        submit_report(call.message)
    elif call.data == "help":
        bot.send_message(call.message.chat.id, "বটটিকে গ্রুপে এডমিন করুন। স্ক্যামার জয়েন করলে বোট অটো ব্যান করবে।")

def submit_report(message):
    bot.send_message(message.chat.id, "স্ক্যামারের Chat ID অথবা Username দিন:")
    bot.register_next_step_handler(message, process_target)

def process_target(message):
    target = message.text
    bot.send_message(message.chat.id, "স্ক্যামের প্রমান দিন (Screenshot/Photo):")
    bot.register_next_step_handler(message, process_proof, target)

def process_proof(message, target):
    bot.send_message(message.chat.id, "স্ক্যামারের বিকাশ নাম্বার দিন (না থাকলে No লিখুন):")
    bot.register_next_step_handler(message, process_final, target)

def process_final(message, target):
    bkash = message.text
    bot.send_message(message.chat.id, "✅ আপনার রিপোর্ট জমা হয়েছে। এডমিন প্রমান দেখে ব্যবস্থা নিবে।")
    
    # এডমিন এপ্রুভাল মেসেজ
    markup = types.InlineKeyboardMarkup()
    sid = target if target.isdigit() else "0"
    suser = target.replace("@", "").lower() if not target.isdigit() else "none"
    markup.add(types.InlineKeyboardButton("Approve Scammer ✅", callback_data=f"app_{sid}_{suser}_{bkash}"))
    
    bot.send_message(OWNER_ID, f"🔔 **New Report**\nTarget: {target}\nbKash: {bkash}\nReporter: @{message.from_user.username}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("app_"))
def approve_scam(call):
    if call.from_user.id != OWNER_ID: return
    _, sid, suser, bkash = call.data.split("_")
    
    conn = sqlite3.connect('scam_db.db')
    conn.execute("INSERT OR REPLACE INTO scammers VALUES (?, ?, ?)", (sid, suser, bkash))
    conn.commit()
    conn.close()
    
    bot.edit_message_text(f"✅ Scammer Added to DB!\nTarget: {sid if sid != '0' else suser}", call.message.chat.id, call.message.message_id)

# --- এডমিন কমান্ডস ---
@bot.message_handler(commands=['broadcast'], chat_types=['private'])
def broadcast(message):
    if message.from_user.id == OWNER_ID:
        text = message.text.replace("/broadcast ", "")
        conn = sqlite3.connect('scam_db.db')
        ids = conn.execute("SELECT id FROM stats").fetchall()
        conn.close()
        
        success = 0
        for i in ids:
            try:
                bot.send_message(i[0], text)
                success += 1
                time.sleep(0.1)
            except: pass
        bot.send_message(message.chat.id, f"Broadcast complete to {success} users/groups.")

@bot.message_handler(commands=['unban'])
def unban(message):
    if is_admin(message.from_user.id):
        try:
            target = message.text.split()[1]
            conn = sqlite3.connect('scam_db.db')
            conn.execute("DELETE FROM scammers WHERE chat_id=? OR username=?", (target, target.replace("@", "").lower()))
            conn.commit()
            conn.close()
            bot.reply_to(message, "User unbanned from DB.")
        except: pass

# --- স্টার্ট পোলিং ---
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    print("Bot is starting...")
    bot.remove_webhook()
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            time.sleep(5)
