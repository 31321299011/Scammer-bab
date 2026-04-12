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

# --- CONFIGURATION ---
BOT_TOKEN = '8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ'
OWNER_ID = 8194390770
CHANNEL_USERNAME = '@earning_channel24'
CHANNEL_URL = 'https://t.me/earning_channel24'
DEV_TEXT = "Developer by @jhgmaing + @bot_developer_io"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
app = Flask(__name__)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('master_scam.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS scammers (chat_id INTEGER PRIMARY KEY, username TEXT, bkash TEXT, proof_url TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY, type TEXT)')
    conn.commit()
    conn.close()

init_db()

# --- RENDER PORT FIX ---
@app.route('/')
def home(): return "Bot is Online"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- UTILS ---
def is_joined(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return True

def is_mod(user_id):
    if user_id == OWNER_ID: return True
    conn = sqlite3.connect('master_scam.db')
    res = conn.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return res is not None

def get_scammer(target):
    conn = sqlite3.connect('master_scam.db')
    c = conn.cursor()
    # Check by ID, Username, or bKash
    res = c.execute("SELECT * FROM scammers WHERE chat_id=? OR username=? OR bkash LIKE ?", 
                  (target if str(target).isdigit() else 0, str(target).replace("@","").lower(), f'%{target}%')).fetchone()
    conn.close()
    return res

def save_stat(chat_id, chat_type):
    conn = sqlite3.connect('master_scam.db')
    conn.execute("INSERT OR IGNORE INTO stats (id, type) VALUES (?, ?)", (chat_id, chat_type))
    conn.commit()
    conn.close()

# --- SCAMMER AUTO-BAN ---
@bot.message_handler(content_types=['new_chat_members'])
def welcome_check(message):
    for member in message.new_chat_members:
        scammer = get_scammer(member.id) or get_scammer(member.username)
        if scammer:
            try:
                bot.ban_chat_member(message.chat.id, member.id)
                msg = (f"<b>সালা আইছিল টাকা মারতে, ভরে দিছি! 🚫</b>\n\n"
                       f"<b>👤 Scammer:</b> @{member.username}\n"
                       f"<b>🆔 ID:</b> <code>{member.id}</code>\n"
                       f"<b>📂 Status:</b> প্রমানিত স্ক্যামার\n\n"
                       f"{DEV_TEXT}")
                bot.send_message(message.chat.id, msg)
            except: pass

# --- GROUP LOGIC (KEYWORD & DETECTION) ---
@bot.message_handler(func=lambda m: m.chat.type != 'private')
def group_monitor(message):
    save_stat(message.chat.id, 'group')
    if not message.text: return
    
    text = message.text.lower()
    user = message.from_user
    
    # Check if sender is a scammer
    if get_scammer(user.id) or get_scammer(user.username):
        try:
            bot.ban_chat_member(message.chat.id, user.id)
            bot.delete_message(message.chat.id, message.message_id)
            return
        except: pass

    # bKash Number Check
    bkash_nums = re.findall(r'01[3-9]\d{8}', text)
    if bkash_nums:
        for num in bkash_nums:
            if get_scammer(num):
                bot.ban_chat_member(message.chat.id, user.id)
                bot.reply_to(message, f"<b>সালা! এই বিকাশ নম্বরটি ({num}) স্ক্যামার ডাটাবেসে আছে। তোকেও ভরে দিলাম! 🚫</b>")
                return

    # Keyword Detection
    keywords = ['টাকা মারছে', 'scam', 'scammer', 'পেমেন্ট দেয় না', 'টাকা দেয় না', 'fraud', 'মারছে টাকা']
    if any(k in text for k in keywords):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Submit Proof (রিপোর্ট করুন)", url=f"https://t.me/{bot.get_me().username}?start=report"))
        bot.reply_to(message, f"<b>⚠️ @{user.username} এখানে কেউ কি স্ক্যাম করেছে?\nপ্রমান থাকলে নিচের বাটনে ক্লিক করে বটে জমা দিন।</b>", reply_markup=markup)

    # Bot Mention
    if f"@{bot.get_me().username}" in text:
        bot.reply_to(message, f"<b>আমি লাইভ আছি! এই গ্রুপে কোনো স্ক্যামার ডুকলে ১ সেকেন্ডেও টিকবে না। 🔥</b>\n\n{DEV_TEXT}")

# --- PRIVATE COMMANDS ---
@bot.message_handler(commands=['start'], chat_types=['private'])
def start(message):
    save_stat(message.chat.id, 'user')
    if "report" in message.text:
        handle_report_init(message)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🚩 Report Scammer", callback_data="report_flow"),
               types.InlineKeyboardButton("🔍 Check User", callback_data="check_user"),
               types.InlineKeyboardButton("📢 Channel", url=CHANNEL_URL),
               types.InlineKeyboardButton("❓ Help", callback_data="help_info"))
    
    bot.send_message(message.chat.id, f"<b>স্বাগতম! আমি @Scammer_Ban_Bot।</b>\n\nআপনার সাথে কেউ স্ক্যাম করলে এখানে প্রমানসহ রিপোর্ট করুন। আমি তাকে সব গ্রুপ থেকে ব্যান করে দিবো।\n\n{DEV_TEXT}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    if call.data == "report_flow":
        if not is_joined(uid):
            bot.answer_callback_query(call.id, "আগে আমাদের চ্যানেলে জয়েন করুন!", show_alert=True)
            return
        handle_report_init(call.message)
    
    elif call.data == "help_info":
        bot.send_message(call.message.chat.id, "<b>বটটি গ্রুপে অ্যাড করে এডমিন করে দিন।</b>\n\nবট যেকোনো প্রমানিত স্ক্যামার বা স্ক্যাম বিকাশ নম্বর দেখলে অটো ব্যান করবে।")

    elif call.data.startswith("app_"): # Approve
        if not is_mod(uid): return
        _, sid, suser, sbkash = call.data.split("|")
        conn = sqlite3.connect('master_scam.db')
        conn.execute("INSERT OR REPLACE INTO scammers (chat_id, username, bkash, proof_url) VALUES (?, ?, ?, ?)", 
                     (sid, suser, sbkash, "Approved"))
        conn.commit()
        conn.close()
        bot.edit_message_text(f"<b>✅ Approved! Scammer Added to DB.</b>\nID: {sid}", call.message.chat.id, call.message.message_id)
        if int(sid) != 0: 
            try: bot.send_message(sid, "<b>আপনি স্ক্যামার হিসেবে প্রমানিত হয়েছেন। আমাদের সব গ্রুপ থেকে আপনাকে ব্যান করা হয়েছে।</b>")
            except: pass

    elif call.data == "rej_scam": # Reject
        if not is_mod(uid): return
        bot.edit_message_text("<b>❌ Report Rejected. (প্রমান যথেষ্ট নয়)</b>", call.message.chat.id, call.message.message_id)

# --- REPORT FLOW ---
def handle_report_init(message):
    msg = bot.send_message(message.chat.id, "<b>স্ক্যামারের Chat ID অথবা Username দিন:</b>")
    bot.register_next_step_handler(msg, step_proof)

def step_proof(message):
    target = message.text
    msg = bot.send_message(message.chat.id, "<b>স্ক্যামের প্রমান দিন (Screenshot/Photo/Video):</b>")
    bot.register_next_step_handler(msg, step_bkash, target)

def step_bkash(message, target):
    proof = message # Media message
    msg = bot.send_message(message.chat.id, "<b>স্ক্যামারের বিকাশ/নগদ নম্বর দিন (না থাকলে No লিখুন):</b>")
    bot.register_next_step_handler(msg, step_final, target, proof)

def step_final(message, target, proof):
    bkash = message.text
    bot.send_message(message.chat.id, "<b>✅ ধন্যবাদ! আপনার রিপোর্ট এডমিন প্যানেলে পাঠানো হয়েছে।</b>")
    
    # Prep info for admin
    scam_id = target if target.isdigit() else 0
    scam_user = target.replace("@", "").lower() if not target.isdigit() else "none"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve Scammer ✅", callback_data=f"app_{scam_id}|{scam_user}|{bkash}"),
               types.InlineKeyboardButton("Reject ❌", callback_data="rej_scam"))
    
    admin_msg = (f"🔔 <b>New Scam Report</b>\n\n"
                 f"👤 <b>Target:</b> {target}\n"
                 f"💰 <b>bKash:</b> {bkash}\n"
                 f"📩 <b>Reporter:</b> @{message.from_user.username}")
    
    # Send to Owner/Admins
    if proof.content_type == 'photo':
        bot.send_photo(OWNER_ID, proof.photo[-1].file_id, caption=admin_msg, reply_markup=markup)
    elif proof.content_type == 'video':
        bot.send_video(OWNER_ID, proof.video.file_id, caption=admin_msg, reply_markup=markup)
    else:
        bot.send_message(OWNER_ID, admin_msg, reply_markup=markup)

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if message.from_user.id != OWNER_ID: return
    try:
        new_id = int(message.text.split()[1])
        conn = sqlite3.connect('master_scam.db')
        conn.execute("INSERT OR IGNORE INTO admins VALUES (?)", (new_id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"<b>User {new_id} added as Bot Admin.</b>")
    except: pass

@bot.message_handler(commands=['unban', 'remove'])
def remove_scammer(message):
    if not is_mod(message.from_user.id): return
    try:
        target = message.text.split()[1]
        conn = sqlite3.connect('master_scam.db')
        conn.execute("DELETE FROM scammers WHERE chat_id=? OR username=? OR bkash=?", 
                     (target if target.isdigit() else 0, target.replace("@","").lower(), target))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"<b>User/Number {target} removed from Scammer Database.</b>")
    except: pass

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != OWNER_ID: return
    text = message.text.replace("/broadcast ", "")
    if not text: return
    
    conn = sqlite3.connect('master_scam.db')
    targets = conn.execute("SELECT id FROM stats").fetchall()
    conn.close()
    
    success = 0
    bot.send_message(OWNER_ID, f"<b>Broadcast Started for {len(targets)} targets...</b>")
    for t in targets:
        try:
            bot.send_message(t[0], f"📢 <b>Important Notice:</b>\n\n{text}\n\n{DEV_TEXT}")
            success += 1
            time.sleep(0.05)
        except: pass
    bot.send_message(OWNER_ID, f"<b>Broadcast Done! Success: {success}</b>")

# --- START BOT ---
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    bot.remove_webhook()
    print("Bot is Starting...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
