import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import sqlite3
import re
import requests
import threading
import time
from datetime import datetime
import json
import os
from flask import Flask, request

# Initialize bot and database
BOT_TOKEN = "8667512297:AAErWpDz5wWqkvJw5HqpS31F-rzvXNRAkrQ"
MAIN_ADMIN_ID = 8194390770
CHANNEL_USERNAME = "earning_channel24"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    
    # Table for scammers
    c.execute('''CREATE TABLE IF NOT EXISTS scammers
                 (user_id TEXT PRIMARY KEY, 
                  username TEXT,
                  bikas_number TEXT,
                  proof TEXT,
                  reported_by TEXT,
                  timestamp TEXT,
                  approved INTEGER DEFAULT 0)''')
    
    # Table for banned users in groups
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users
                 (user_id TEXT PRIMARY KEY,
                  group_id TEXT,
                  reason TEXT,
                  timestamp TEXT)''')
    
    # Table for group admins
    c.execute('''CREATE TABLE IF NOT EXISTS group_admins
                 (user_id TEXT PRIMARY KEY,
                  group_id TEXT,
                  added_by TEXT,
                  timestamp TEXT)''')
    
    # Table for bot controllers (main admins)
    c.execute('''CREATE TABLE IF NOT EXISTS bot_controllers
                 (user_id TEXT PRIMARY KEY,
                  added_by TEXT,
                  timestamp TEXT)''')
    
    # Add main admin to controllers
    c.execute("INSERT OR IGNORE INTO bot_controllers (user_id, added_by, timestamp) VALUES (?, ?, ?)",
              (str(MAIN_ADMIN_ID), "system", datetime.now().isoformat()))
    
    # Table for active groups
    c.execute('''CREATE TABLE IF NOT EXISTS active_groups
                 (group_id TEXT PRIMARY KEY,
                  group_title TEXT,
                  added_by TEXT,
                  timestamp TEXT)''')
    
    # Table for user join status to channel
    c.execute('''CREATE TABLE IF NOT EXISTS channel_joined
                 (user_id TEXT PRIMARY KEY,
                  joined INTEGER DEFAULT 0)''')
    
    conn.commit()
    conn.close()

init_db()

# Helper functions
def is_admin(user_id):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM bot_controllers WHERE user_id = ?", (str(user_id),))
    result = c.fetchone()
    conn.close()
    return result is not None

def is_group_admin(group_id, user_id):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM group_admins WHERE user_id = ? AND group_id = ?", (str(user_id), str(group_id)))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_group_admin(group_id, user_id, added_by):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO group_admins (user_id, group_id, added_by, timestamp) VALUES (?, ?, ?, ?)",
              (str(user_id), str(group_id), str(added_by), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def remove_group_admin(group_id, user_id):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM group_admins WHERE user_id = ? AND group_id = ?", (str(user_id), str(group_id)))
    conn.commit()
    conn.close()

def add_banned_user(user_id, group_id, reason):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO banned_users (user_id, group_id, reason, timestamp) VALUES (?, ?, ?, ?)",
              (str(user_id), str(group_id), reason, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def remove_banned_user(user_id, group_id):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM banned_users WHERE user_id = ? AND group_id = ?", (str(user_id), str(group_id)))
    conn.commit()
    conn.close()

def is_banned(user_id, group_id):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM banned_users WHERE user_id = ? AND group_id = ?", (str(user_id), str(group_id)))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_scammer(user_id, username, bikas_number, proof, reported_by):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO scammers (user_id, username, bikas_number, proof, reported_by, timestamp, approved) VALUES (?, ?, ?, ?, ?, ?, 0)",
              (str(user_id), username, bikas_number, proof, str(reported_by), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def approve_scammer(user_id):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE scammers SET approved = 1 WHERE user_id = ?", (str(user_id),))
    conn.commit()
    conn.close()

def reject_scammer(user_id):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM scammers WHERE user_id = ?", (str(user_id),))
    conn.commit()
    conn.close()

def get_scammer_info(user_id):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM scammers WHERE user_id = ?", (str(user_id),))
    result = c.fetchone()
    conn.close()
    return result

def search_by_bikas(bikas_number):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM scammers WHERE bikas_number = ? AND approved = 1", (bikas_number,))
    result = c.fetchall()
    conn.close()
    return result

def get_all_scammers():
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM scammers WHERE approved = 1")
    result = c.fetchall()
    conn.close()
    return result

def add_active_group(group_id, group_title):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO active_groups (group_id, group_title, added_by, timestamp) VALUES (?, ?, ?, ?)",
              (str(group_id), group_title, "bot", datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_groups():
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT group_id FROM active_groups")
    result = c.fetchall()
    conn.close()
    return [row[0] for row in result]

def check_channel_join(user_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        if member.status in ['member', 'administrator', 'creator']:
            conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO channel_joined (user_id, joined) VALUES (?, 1)", (str(user_id),))
            conn.commit()
            conn.close()
            return True
        return False
    except:
        return False

def mark_joined(user_id):
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO channel_joined (user_id, joined) VALUES (?, 1)", (str(user_id),))
    conn.commit()
    conn.close()

# Main keyboard
def main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_report = InlineKeyboardButton("🚨 Report Scammer", callback_data="report_scammer")
    btn_scammers = InlineKeyboardButton("📋 Scammer List", callback_data="scammer_list")
    btn_help = InlineKeyboardButton("❓ Help", callback_data="help")
    btn_check = InlineKeyboardButton("✅ Check Channel", callback_data="check_channel")
    
    keyboard.add(btn_report, btn_scammers)
    keyboard.add(btn_help, btn_check)
    
    if is_admin(str(MAIN_ADMIN_ID)):
        btn_admin = InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")
        keyboard.add(btn_admin)
    
    return keyboard

def admin_panel_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_add_admin = InlineKeyboardButton("👑 Add Controller", callback_data="add_controller")
    btn_remove_admin = InlineKeyboardButton("🔨 Remove Controller", callback_data="remove_controller")
    btn_pending = InlineKeyboardButton("⏳ Pending Reports", callback_data="pending_reports")
    btn_broadcast = InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")
    btn_stats = InlineKeyboardButton("📊 Statistics", callback_data="stats")
    btn_back = InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
    
    keyboard.add(btn_add_admin, btn_remove_admin)
    keyboard.add(btn_pending, btn_broadcast)
    keyboard.add(btn_stats, btn_back)
    
    return keyboard

# Command handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    group_id = message.chat.id
    
    # Check if in group
    if message.chat.type in ['group', 'supergroup']:
        add_active_group(group_id, message.chat.title)
        welcome_text = f"🤖 Scammer Detector Bot is active in this group!\n\nSend /help to see all commands."
        bot.reply_to(message, welcome_text)
        return
    
    # Private chat
    welcome_text = f"""
🎯 **Welcome to Scammer Detector Bot**

**Developer:** @jhgmaing + @bot_developer_io

**Features:**
✅ Report scammers with proof
✅ Auto-ban scammers from groups
✅ Global scammer database
✅ Bikash number tracking
✅ Group protection system

**Please join our channel first:**
👉 @{CHANNEL_USERNAME}

Then use the buttons below to continue.
    """
    
    bot.send_message(user_id, welcome_text, parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
🎯 **Scammer Detector Bot - Help Menu**

**Available Commands:**
/start - Start the bot
/help - Show this help menu
/report - Report a scammer (in group)
/unban @username - Unban a user (group admins only)

**How to report scammers:**
1. Click on "Report Scammer" button
2. Provide username, proof, and optional Bikash number
3. Wait for admin approval

**Group Protection:**
- Bot automatically scans new members
- Scammers are banned instantly
- Admins can unban using /unban

**For Admin:**
Use the admin panel to manage controllers, approve reports, and broadcast messages.

**Channel Required:** @{CHANNEL_USERNAME}

💡 *Tip:* Mention the bot in group with "scam" or "scammer" keywords for instant response!
    """
    
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(commands=['unban'])
def unban_command(message):
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ This command only works in groups!")
        return
    
    user_id = message.from_user.id
    group_id = message.chat.id
    
    # Check if user is group admin or bot controller
    if not is_group_admin(group_id, user_id) and not is_admin(user_id):
        bot.reply_to(message, "❌ Only group admins can use this command!")
        return
    
    try:
        username = message.text.split()[1]
        username = username.replace('@', '')
        
        # Get user info
        user_info = bot.get_chat_member(group_id, f"@{username}")
        target_id = user_info.user.id
        
        # Remove from banned list
        remove_banned_user(target_id, group_id)
        
        # Unban in group
        bot.unban_chat_member(group_id, target_id)
        
        bot.reply_to(message, f"✅ User @{username} has been unbanned!")
    except:
        bot.reply_to(message, "❌ Usage: /unban @username")

@bot.message_handler(commands=['report'])
def report_command(message):
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ Please use the report button in private chat with bot!")
        return
    
    user_id = message.from_user.id
    
    if not check_channel_join(user_id):
        bot.reply_to(message, f"❌ Please join @{CHANNEL_USERNAME} first to report scammers!")
        return
    
    bot.reply_to(message, "📝 Please send me the username of the scammer (with @) in private message.")
    bot.send_message(user_id, "📝 Please send the scammer's username (with @):")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    user_id = message.from_user.id
    
    if not is_admin(str(user_id)):
        bot.reply_to(message, "❌ Only bot controllers can use this command!")
        return
    
    msg = bot.reply_to(message, "📢 Send me the message to broadcast to all users and groups:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    user_id = message.from_user.id
    broadcast_text = message.text
    
    bot.send_message(user_id, "⏳ Broadcasting message to all users and groups...")
    
    # Get all groups
    groups = get_all_groups()
    success_count = 0
    
    for group_id in groups:
        try:
            bot.send_message(int(group_id), f"📢 **Broadcast Message**\n\n{broadcast_text}", parse_mode="Markdown")
            success_count += 1
            time.sleep(0.5)
        except:
            pass
    
    bot.send_message(user_id, f"✅ Broadcast sent to {success_count} groups!")

# Message handler for group messages
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def group_message_handler(message):
    group_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.lower() if message.text else ""
    
    # Check for scam keywords
    scam_keywords = ['scam', 'scammer', 'প্রতারক', 'ঠক', 'টাকা মেরে দিছে', 'টাকা মারা', 'fraud']
    
    if any(keyword in text for keyword in scam_keywords):
        # Mention the scammer
        mention = f"[{message.from_user.first_name}](tg://user?id={user_id})"
        response = f"⚠️ {mention} mentioned scam!\n\nPlease report with proof using /report command."
        bot.reply_to(message, response, parse_mode="Markdown")

# New member handler
@bot.message_handler(content_types=['new_chat_members'])
def new_member_handler(message):
    for new_member in message.new_chat_members:
        if new_member.id == bot.get_me().id:
            # Bot added to group
            add_active_group(message.chat.id, message.chat.title)
            bot.send_message(message.chat.id, 
                           f"✅ Scammer Detector Bot is active!\n\nSend /help to see commands.\n\nDeveloper: @jhgmaing + @bot_developer_io")
            continue
        
        # Check if new member is a scammer
        scammer_info = get_scammer_info(str(new_member.id))
        if scammer_info and scammer_info[6] == 1:  # Approved scammer
            try:
                bot.ban_chat_member(message.chat.id, new_member.id)
                bot.send_message(message.chat.id, 
                               f"🚨 **SCAMMER DETECTED & BANNED!**\n\n"
                               f"User: [{new_member.first_name}](tg://user?id={new_member.id})\n"
                               f"Username: @{new_member.username if new_member.username else 'N/A'}\n"
                               f"User ID: {new_member.id}\n\n"
                               f"This user is in our scammer database!",
                               parse_mode="Markdown")
                
                # Add to banned list
                add_banned_user(str(new_member.id), str(message.chat.id), "Scammer detected in database")
            except:
                pass

# Callback query handler
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    if call.data == "back_to_main":
        bot.edit_message_text("Main Menu:", call.message.chat.id, call.message.message_id, 
                            reply_markup=main_keyboard())
    
    elif call.data == "check_channel":
        if check_channel_join(user_id):
            bot.answer_callback_query(call.id, "✅ You have joined the channel!")
            mark_joined(user_id)
        else:
            bot.answer_callback_query(call.id, f"❌ Please join @{CHANNEL_USERNAME} first!", show_alert=True)
    
    elif call.data == "help":
        help_text = """
🎯 **Help Menu**

**How to use:**
1. Join @{CHANNEL_USERNAME}
2. Click Report Scammer button
3. Provide username, proof, and Bikash number

**Commands:**
/start - Start bot
/help - Show help
/report - Report scammer (in groups)
/unban @user - Unban user (admins only)

**Features:**
- Auto-ban scammers in groups
- Global scammer database
- Bikash number tracking
- Admin control panel
        """
        bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id, 
                            reply_markup=main_keyboard())
    
    elif call.data == "scammer_list":
        scammers = get_all_scammers()
        if not scammers:
            bot.answer_callback_query(call.id, "No scammers in database yet!")
            return
        
        text = "📋 **Scammer Database**\n\n"
        for scammer in scammers[:10]:  # Show first 10
            text += f"👤 User ID: {scammer[0]}\n"
            text += f"Username: @{scammer[1] if scammer[1] else 'N/A'}\n"
            text += f"Bikash: {scammer[2] if scammer[2] else 'N/A'}\n"
            text += f"Reported: {scammer[4]}\n"
            text += f"Time: {scammer[5]}\n\n"
        
        if len(scammers) > 10:
            text += f"\n... and {len(scammers) - 10} more scammers"
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                            parse_mode="Markdown", reply_markup=main_keyboard())
    
    elif call.data == "report_scammer":
        if not check_channel_join(user_id):
            bot.answer_callback_query(call.id, f"❌ Please join @{CHANNEL_USERNAME} first!", show_alert=True)
            return
        
        msg = bot.send_message(call.message.chat.id, "📝 Send the scammer's username (with @):")
        bot.register_next_step_handler(msg, get_scammer_username, user_id, call.message.chat.id, call.message.message_id)
    
    elif call.data == "admin_panel":
        if not is_admin(str(user_id)):
            bot.answer_callback_query(call.id, "❌ You are not authorized!", show_alert=True)
            return
        
        bot.edit_message_text("⚙️ **Admin Panel**\n\nChoose an option:", 
                            call.message.chat.id, call.message.message_id,
                            parse_mode="Markdown", reply_markup=admin_panel_keyboard())
    
    elif call.data == "add_controller":
        if not is_admin(str(user_id)):
            bot.answer_callback_query(call.id, "❌ You are not authorized!", show_alert=True)
            return
        
        msg = bot.send_message(call.message.chat.id, "👑 Send the user ID to add as controller:")
        bot.register_next_step_handler(msg, add_controller_process, user_id, call.message.chat.id, call.message.message_id)
    
    elif call.data == "remove_controller":
        if not is_admin(str(user_id)):
            bot.answer_callback_query(call.id, "❌ You are not authorized!", show_alert=True)
            return
        
        msg = bot.send_message(call.message.chat.id, "🔨 Send the user ID to remove from controllers:")
        bot.register_next_step_handler(msg, remove_controller_process, user_id, call.message.chat.id, call.message.message_id)
    
    elif call.data == "pending_reports":
        if not is_admin(str(user_id)):
            bot.answer_callback_query(call.id, "❌ You are not authorized!", show_alert=True)
            return
        
        conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT * FROM scammers WHERE approved = 0")
        pending = c.fetchall()
        conn.close()
        
        if not pending:
            bot.answer_callback_query(call.id, "No pending reports!")
            return
        
        text = "⏳ **Pending Reports**\n\n"
        for p in pending:
            text += f"User ID: {p[0]}\n"
            text += f"Username: @{p[1] if p[1] else 'N/A'}\n"
            text += f"Bikash: {p[2] if p[2] else 'N/A'}\n"
            text += f"Reported by: {p[4]}\n"
            text += f"Time: {p[5]}\n\n"
            
            # Add approve/reject buttons for each
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{p[0]}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{p[0]}")
            )
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=keyboard)
            text = ""
        
        bot.edit_message_text("✅ Done!", call.message.chat.id, call.message.message_id, 
                            reply_markup=admin_panel_keyboard())
    
    elif call.data == "broadcast":
        if not is_admin(str(user_id)):
            bot.answer_callback_query(call.id, "❌ You are not authorized!", show_alert=True)
            return
        
        msg = bot.send_message(call.message.chat.id, "📢 Send the broadcast message:")
        bot.register_next_step_handler(msg, process_broadcast_from_admin, call.message.chat.id, call.message.message_id)
    
    elif call.data == "stats":
        if not is_admin(str(user_id)):
            bot.answer_callback_query(call.id, "❌ You are not authorized!", show_alert=True)
            return
        
        conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM scammers WHERE approved = 1")
        total_scammers = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM scammers WHERE approved = 0")
        pending_reports = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM active_groups")
        total_groups = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM bot_controllers")
        total_controllers = c.fetchone()[0]
        conn.close()
        
        stats_text = f"""
📊 **Bot Statistics**

🚨 Total Scammers: {total_scammers}
⏳ Pending Reports: {pending_reports}
👥 Active Groups: {total_groups}
👑 Bot Controllers: {total_controllers}

**Developer:** @jhgmaing + @bot_developer_io
        """
        
        bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id,
                            parse_mode="Markdown", reply_markup=admin_panel_keyboard())
    
    elif call.data.startswith("approve_"):
        if not is_admin(str(user_id)):
            bot.answer_callback_query(call.id, "❌ You are not authorized!", show_alert=True)
            return
        
        scammer_id = call.data.split("_")[1]
        approve_scammer(scammer_id)
        
        # Ban from all groups
        groups = get_all_groups()
        for group_id in groups:
            try:
                bot.ban_chat_member(int(group_id), int(scammer_id))
            except:
                pass
        
        bot.answer_callback_query(call.id, "✅ Scammer approved and banned from all groups!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif call.data.startswith("reject_"):
        if not is_admin(str(user_id)):
            bot.answer_callback_query(call.id, "❌ You are not authorized!", show_alert=True)
            return
        
        scammer_id = call.data.split("_")[1]
        reject_scammer(scammer_id)
        bot.answer_callback_query(call.id, "❌ Report rejected and removed!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

def get_scammer_username(message, reporter_id, chat_id, msg_id):
    username = message.text.strip()
    
    if not username.startswith('@'):
        bot.send_message(chat_id, "❌ Username must start with @. Please try again.")
        return
    
    # Store username and ask for proof
    bot.send_message(chat_id, "📸 Now send the proof (screenshot or image):")
    bot.register_next_step_handler(message, get_scammer_proof, username, reporter_id, chat_id, msg_id)

def get_scammer_proof(message, username, reporter_id, chat_id, msg_id):
    if not message.photo:
        bot.send_message(chat_id, "❌ Please send an image as proof!")
        return
    
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # Save proof
    proof_path = f"proofs/{username}_{datetime.now().timestamp()}.jpg"
    os.makedirs("proofs", exist_ok=True)
    with open(proof_path, 'wb') as f:
        f.write(downloaded_file)
    
    # Ask for Bikash number
    bot.send_message(chat_id, "💰 Send Bikash number (or type 'skip'):")
    bot.register_next_step_handler(message, get_bikash_number, username, proof_path, reporter_id, chat_id, msg_id)

def get_bikash_number(message, username, proof_path, reporter_id, chat_id, msg_id):
    bikash = message.text.strip()
    
    if bikash.lower() == 'skip':
        bikash = ''
    
    # Get user ID from username
    try:
        # Try to get user info
        user_info = bot.get_chat(username)
        user_id = user_info.id
    except:
        user_id = username
    
    # Save to database
    add_scammer(user_id, username, bikash, proof_path, reporter_id)
    
    # Notify admins
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT user_id FROM bot_controllers")
    admins = c.fetchall()
    conn.close()
    
    for admin in admins:
        try:
            bot.send_message(int(admin[0]), 
                           f"🆕 New scammer report!\n\nUsername: {username}\nBikash: {bikash if bikash else 'N/A'}\nReported by: {reporter_id}\n\nUse admin panel to approve/reject.")
        except:
            pass
    
    bot.send_message(chat_id, "✅ Report submitted! Admins will review it soon.", reply_markup=main_keyboard())
    bot.delete_message(chat_id, msg_id)

def add_controller_process(message, admin_id, chat_id, msg_id):
    new_controller = message.text.strip()
    
    if not new_controller.isdigit():
        bot.send_message(chat_id, "❌ Invalid user ID! Please send a numeric ID.")
        return
    
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO bot_controllers (user_id, added_by, timestamp) VALUES (?, ?, ?)",
              (new_controller, str(admin_id), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    bot.send_message(chat_id, f"✅ User {new_controller} added as controller!", reply_markup=admin_panel_keyboard())
    bot.delete_message(chat_id, msg_id)

def remove_controller_process(message, admin_id, chat_id, msg_id):
    controller_id = message.text.strip()
    
    if not controller_id.isdigit():
        bot.send_message(chat_id, "❌ Invalid user ID!")
        return
    
    if controller_id == str(MAIN_ADMIN_ID):
        bot.send_message(chat_id, "❌ Cannot remove main admin!")
        return
    
    conn = sqlite3.connect('scammer_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM bot_controllers WHERE user_id = ?", (controller_id,))
    conn.commit()
    conn.close()
    
    bot.send_message(chat_id, f"✅ User {controller_id} removed from controllers!", reply_markup=admin_panel_keyboard())
    bot.delete_message(chat_id, msg_id)

def process_broadcast_from_admin(message, chat_id, msg_id):
    broadcast_text = message.text
    
    groups = get_all_groups()
    success_count = 0
    
    for group_id in groups:
        try:
            bot.send_message(int(group_id), f"📢 **Broadcast from Admin**\n\n{broadcast_text}", parse_mode="Markdown")
            success_count += 1
            time.sleep(0.5)
        except:
            pass
    
    bot.send_message(chat_id, f"✅ Broadcast sent to {success_count} groups!", reply_markup=admin_panel_keyboard())
    bot.delete_message(chat_id, msg_id)

# Flask webhook for Render
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '!', 200

@app.route('/')
def index():
    return 'Scammer Detector Bot is running!'

if __name__ == '__main__':
    # Remove webhook and start polling
    bot.remove_webhook()
    
    # Start polling in thread
    def run_bot():
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
