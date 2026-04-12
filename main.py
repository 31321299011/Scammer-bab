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
API_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770  # আপনার চ্যাট আইডি
CHANNEL_USERNAME = '@earning_channel24'
CHANNEL_URL = 'https://t.me/earning_channel24'

bot = telebot.TeleBot(API_TOKEN)
server = Flask(__name__)

# --- রেন্ডার পোর্ট বাইন্ডিং (Fixes "No open ports detected") ---
@server.route('/')
def home():
    return "Scammer Ban Bot is active!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)

# --- ডাটাবেস সেটআপ ---
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

# --- ইউটিলিটি ফাংশন ---
def check_join(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return True # বট এডমিন না থাকলে চেক বাইপাস

def is_scammer(user_id=None, username=None, bkash_list=None):
    conn = sqlite3.connect('scammers.db')
    cursor = conn.cursor()
    res = None
    if user_id:
        res = cursor.execute("SELECT * FROM scammers WHERE chat_id=?", (user_id,)).fetchone()
    if not res and username:
        res = cursor.execute("SELECT * FROM scammers WHERE username=?", (username.lower(),)).fetchone()
    if not res and bkash_list:
        for num in bkash_list:
            res = cursor.execute("SELECT * FROM scammers WHERE bkash LIKE ?", (f'%{num}%',)).fetchone()
            if res: break
    conn.close()
    return res

def is_admin(user_id):
    if user_id == OWNER_ID: return True
    conn = sqlite3.connect('scammers.db')
    res = conn.execute("SELECT user_id FROM bot_admins WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return res is not None

# --- অটো ডিটেকশন ও ব্যান ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'new_chat_members'])
def auto_ban_handler(message):
    # স্ট্যাটাস সেভ (ব্রডকাস্টের জন্য)
    conn = sqlite3.connect('scammers.db')
    conn.execute("INSERT OR IGNORE INTO stats (id) VALUES (?)", (message.chat.id,))
    conn.commit()
    conn.close()

    # নতুন মেম্বার জয়েন করলে চেক
    if message.content_type == 'new_chat_members':
        for user in message.new_chat_members:
            if is_scammer(user_id=user.id, username=user.username):
                try:
                    bot.ban_chat_member(message.chat.id, user.id)
                    bot.send_message(message.chat.id, f"সালা আইছিল টাকা মারতে, ভরে দিছি! 🚫\n\nScammer: @{user.username}\nID: `{user.id}`\n\nDeveloper by @jhgmaing + @bot_developer_io")
                except: pass
        return

    # টেক্সট মেসেজ ডিটেকশন
    if message.text:
        text = message.text.lower()
        bkash_nums = re.findall(r'01[3-9]\d{8}', text)
        user = message.from_user
        
        # স্ক্যামার চেক
        scam_data = is_scammer(user_id=user.id, username=user.username, bkash_list=bkash_nums)
        if scam_data:
            try:
                bot.ban_chat_member(message.chat.id, user.id)
                bot.send_message(message.chat.id, f"সালা আইছিল টাকা মারতে, ভরে দিছি! 🚫\n\nScammer: @{user.username}\nID: `{user.id}`\nপ্রমানিত স্ক্যামার ডাটাবেসে পাওয়া গেছে। 🔥")
                return
            except: pass

        # বোট মেনশন করলে রেসপন্স
        if f"@{bot.get_me().username}" in text:
            bot.reply_to(message, "আমি লাইভ আছি! এই গ্রুপে কোনো স্ক্যামার ডুকলে বা টাকা মারার চেষ্টা করলে সাথে সাথে কিক দেওয়া হবে। 🔥")

        # স্ক্যাম কী-ওয়ার্ড চেক
        keywords = ['টাকা মারছে', 'scam', 'টাকা মারে', 'স্ক্যামার', 'পেমেন্ট দেয় না']
        if any(key in text for key in keywords):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("রিপোর্ট (Proof Submit)", url=f"https://t.me/{bot.get_me().username}?start=report"))
            bot.reply_to(message, "⚠️ এই ইউজার কি স্ক্যাম করেছে? প্রমান থাকলে নিচের বাটনে ক্লিক করে রিপোর্ট দিন।", reply_markup=markup)

# --- প্রাইভেট চ্যাট কমান্ডস ---
@bot.message_handler(commands=['start'], chat_types=['private'])
def start(message):
    if "/start report" in message.text:
        start_report(message)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("Report Scammer 🚩", callback_data="report"),
               types.InlineKeyboardButton("Help ❓", callback_data="help"))
    
    bot.send_message(message.chat.id, f"স্বাগতম! আমি @{bot.get_me().username}।\nস্ক্যামার মুক্ত টেলিগ্রাম গড়তে আমরা কাজ করছি।\n\nDeveloper: @jhgmaing & @bot_developer_io", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "report":
        if not check_join(call.from_user.id):
            bot.answer_callback_query(call.id, "আগে চ্যানেলে জয়েন করুন!", show_alert=True)
            return
        start_report(call.message)
    elif call.data == "help":
        bot.send_message(call.message.chat.id, "বটটিকে আপনার গ্রুপে এডমিন করুন। কোনো স্ক্যামার জয়েন করলেই বোট অটো ব্যান করবে।")
    elif call.data.startswith("approve_"):
        if call.from_user.id != OWNER_ID: return
        _, sid, suser, bkash = call.data.split("_")
        conn = sqlite3.connect('scammers.db')
        conn.execute("INSERT OR REPLACE INTO scammers VALUES (?, ?, ?)", (sid, suser, bkash))
        conn.commit()
        conn.close()
        bot.edit_message_text(f"✅ Scammer Added to DB!\nTarget: {sid if sid != '0' else suser}", call.message.chat.id, call.message.message_id)

# --- রিপোর্ট সাবমিশন ফ্লো ---
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
    bot.send_message(message.chat.id, "✅ আপনার রিপোর্ট জমা হয়েছে। এডমিন প্রমান দেখে ব্যবস্থা নিবে।")
    
    markup = types.InlineKeyboardMarkup()
    scam_id = target if target.isdigit() else "0"
    scam_user = target.replace("@", "").lower() if not target.isdigit() else "none"
    markup.add(types.InlineKeyboardButton("Approve Scammer ✅", callback_data=f"approve_{scam_id}_{scam_user}_{bkash}"))
    
    bot.send_message(OWNER_ID, f"🔔 **New Scam Report**\n\nTarget: {target}\nbKash: {bkash}\nReporter: @{message.from_user.username}", reply_markup=markup)

# --- এডমিন কমান্ডস ---
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

@bot.message_handler(commands=['unban'])
def unban(message):
    if is_admin(message.from_user.id):
        try:
            target = message.text.split()[1]
            conn = sqlite3.connect('scammers.db')
            conn.execute("DELETE FROM scammers WHERE chat_id=? OR username=?", (target, target.replace("@", "").lower()))
            conn.commit()
            conn.close()
            bot.reply_to(message, f"User {target} has been unbanned from Database.")
        except: pass

# --- বট স্টার্ট ---
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    bot.remove_webhook()
    print("Bot is starting...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            time.sleep(5)
