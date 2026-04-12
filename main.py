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
BOT_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770 
CHANNEL_USERNAME = '@earning_channel24'
CHANNEL_URL = 'https://t.me/earning_channel24'

bot = telebot.TeleBot(BOT_TOKEN)
server = Flask(__name__)

# রেন্ডার পোর্ট বাইন্ডিং
@server.route('/')
def home(): return "Bot is Active!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)

# ডাটাবেস
def init_db():
    conn = sqlite3.connect('scammers.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS scammers 
                      (chat_id INTEGER PRIMARY KEY, username TEXT, bkash TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS bot_admins (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()

# মেম্বারশিপ চেক
def check_join(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return True

def is_scammer(user_id=None, username=None, bkash_list=None):
    conn = sqlite3.connect('scammers.db')
    cursor = conn.cursor()
    res = None
    if user_id:
        res = cursor.execute("SELECT * FROM scammers WHERE chat_id=?", (user_id,)).fetchone()
    if not res and username:
        res = cursor.execute("SELECT * FROM scammers WHERE username=?", (str(username).lower(),)).fetchone()
    if not res and bkash_list:
        for num in bkash_list:
            res = cursor.execute("SELECT * FROM scammers WHERE bkash LIKE ?", (f'%{num}%',)).fetchone()
            if res: break
    conn.close()
    return res

# --- ১. ইনবক্স কমান্ড হ্যান্ডলার (সবার আগে থাকবে) ---

@bot.message_handler(commands=['start'], chat_types=['private'])
def start_private(message):
    # স্ট্যাটাস সেভ
    conn = sqlite3.connect('scammers.db')
    conn.execute("INSERT OR IGNORE INTO stats (id) VALUES (?)", (message.chat.id,))
    conn.commit()
    conn.close()

    if "/start report" in message.text:
        start_report(message)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("Report Scammer 🚩", callback_data="report"),
               types.InlineKeyboardButton("Help ❓", callback_data="help"))
    
    bot.send_message(message.chat.id, f"স্বাগতম! আমি @{bot.get_me().username}।\nআপনার ইনবক্সে আমি সচল আছি।\n\nDeveloper: @jhgmaing & @bot_developer_io", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "report")
def report_callback(call):
    if not check_join(call.from_user.id):
        bot.answer_callback_query(call.id, "আগে চ্যানেলে জয়েন করুন!", show_alert=True)
        return
    start_report(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "help")
def help_callback(call):
    bot.send_message(call.message.chat.id, "বটটিকে আপনার বাই-সেল গ্রুপে এডমিন করুন। কেউ স্ক্যাম করার চেষ্টা করলে বা টাকা মারার কথা বললে বট তাকে ডিটেক্ট করবে।")

# রিপোর্ট ফ্লো
def start_report(message):
    bot.send_message(message.chat.id, "স্ক্যামারের Chat ID অথবা Username দিন:")
    bot.register_next_step_handler(message, get_proof)

def get_proof(message):
    target = message.text
    bot.send_message(message.chat.id, "স্ক্যামের প্রমান দিন (Screenshot/Photo):")
    bot.register_next_step_handler(message, get_bkash, target)

def get_bkash(message, target):
    bot.send_message(message.chat.id, "স্ক্যামারের বিকাশ নাম্বার দিন (না থাকলে No লিখুন):")
    bot.register_next_step_handler(message, finish_report, target)

def finish_report(message, target):
    bkash = message.text
    bot.send_message(message.chat.id, "✅ আপনার রিপোর্ট জমা হয়েছে। এডমিন ব্যবস্থা নিবে।")
    
    markup = types.InlineKeyboardMarkup()
    scam_id = target if target.isdigit() else "0"
    scam_user = target.replace("@", "").lower() if not target.isdigit() else "none"
    markup.add(types.InlineKeyboardButton("Approve Scammer ✅", callback_data=f"approve_{scam_id}_{scam_user}_{bkash}"))
    
    bot.send_message(OWNER_ID, f"🔔 **New Report**\nTarget: {target}\nbKash: {bkash}\nReporter: @{message.from_user.username}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_scam(call):
    if call.from_user.id != OWNER_ID: return
    _, sid, suser, bkash = call.data.split("_")
    conn = sqlite3.connect('scammers.db')
    conn.execute("INSERT OR REPLACE INTO scammers VALUES (?, ?, ?)", (sid, suser, bkash))
    conn.commit()
    conn.close()
    bot.edit_message_text(f"✅ Scammer Added to DB!\nID: {sid if sid != '0' else suser}", call.message.chat.id, call.message.message_id)

# এডমিন কমান্ড
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id == OWNER_ID:
        text = message.text.replace("/broadcast ", "")
        conn = sqlite3.connect('scammers.db')
        ids = conn.execute("SELECT id FROM stats").fetchall()
        conn.close()
        for i in ids:
            try: bot.send_message(i[0], text)
            except: pass
        bot.reply_to(message, "Broadcast Complete!")

# --- ২. গ্রুপ হ্যান্ডলার (সবার শেষে থাকবে) ---

@bot.message_handler(func=lambda m: True, content_types=['text', 'new_chat_members'])
def group_auto_handler(message):
    # নতুন মেম্বার চেক
    if message.content_type == 'new_chat_members':
        for user in message.new_chat_members:
            if is_scammer(user_id=user.id, username=user.username):
                try:
                    bot.ban_chat_member(message.chat.id, user.id)
                    bot.send_message(message.chat.id, f"সালা আইছিল টাকা মারতে, ভরে দিছি! 🚫\nScammer: @{user.username}")
                except: pass
        return

    # টেক্সট মেসেজ চেক
    if message.text:
        text = message.text.lower()
        bkash_nums = re.findall(r'01[3-9]\d{8}', text)
        user = message.from_user
        
        # স্ক্যামার ডাটাবেস চেক
        scam_data = is_scammer(user_id=user.id, username=user.username, bkash_list=bkash_nums)
        if scam_data:
            try:
                bot.ban_chat_member(message.chat.id, user.id)
                bot.send_message(message.chat.id, f"সালা আইছিল টাকা মারতে, ভরে দিছি! 🚫\nপ্রমানিত স্ক্যামার ডাটাবেসে পাওয়া গেছে।")
                return
            except: pass

        # বোট মেনশন
        if f"@{bot.get_me().username}" in text:
            bot.reply_to(message, "আমি সজাগ আছি! 🔥")

# --- রান ---
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    bot.remove_webhook()
    print("Bot is Starting...")
    bot.polling(none_stop=True, interval=0, timeout=60)
