import os
import re
import json
import telebot
from telebot import types
import time
from datetime import datetime, timedelta

# ================= CONFIGURATION =================
BOT_TOKEN = "8461271950:AAFcn-zNZK66FqQ_AEBUb4gbSvJhr47t6gE"
ADMIN_ID = 7806554013  # আপনার Chat ID
PREMIUM_CONTACT = "@Rollaxtt"

USER_MAX_SIZE = 500 * 1024 * 1024  # 500 MB
PREMIUM_MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
DB_FILE = "users.json"

bot = telebot.TeleBot(BOT_TOKEN)
user_temp_data = {}

# ================= DATABASE =================
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user(chat_id):
    db = load_db()
    cid = str(chat_id)
    if cid not in db:
        db[cid] = {
            "tier": "Admin" if chat_id == ADMIN_ID else "Free",
            "daily_searches": 0,
            "last_reset": datetime.now().strftime("%Y-%m-%d"),
            "premium_expiry": None,
            "total_extracts": 0,
            "files_processed": 0
        }
        save_db(db)
    else:
        # চেক করা প্রিমিয়ামের মেয়াদ শেষ kina
        if db[cid]["tier"] == "Premium" and db[cid]["premium_expiry"]:
            expiry = datetime.strptime(db[cid]["premium_expiry"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expiry:
                db[cid]["tier"] = "Free"
                db[cid]["premium_expiry"] = None
                save_db(db)
                
        # ডেইলি রিসেট চেক
        today = datetime.now().strftime("%Y-%m-%d")
        if db[cid]["last_reset"] != today:
            db[cid]["daily_searches"] = 0
            db[cid]["last_reset"] = today
            save_db(db)
            
    return db[cid]

def update_user_stats(chat_id, extracted_count):
    db = load_db()
    cid = str(chat_id)
    if cid in db:
        db[cid]["daily_searches"] += 1
        db[cid]["total_extracts"] += extracted_count
        db[cid]["files_processed"] += 1
        save_db(db)

# ================= HELPER FUNCTIONS =================
def cleanup_user_files(chat_id):
    if chat_id in user_temp_data:
        for key in ['file_path', 'formatted_data']:
            if key in user_temp_data[chat_id] and os.path.exists(user_temp_data[chat_id][key]):
                try:
                    os.remove(user_temp_data[chat_id][key])
                except:
                    pass
        del user_temp_data[chat_id]

def format_ulp_line(line):
    line = line.strip()
    if not line: return None
    url_pattern = re.compile(r'https?://[^\s]+')
    
    if re.match(url_pattern, line):
        clean_line = url_pattern.sub('', line).strip(':').strip()
        parts = clean_line.split(':')
        if len(parts) >= 2: return f"{parts[0]}:{parts[1]}"
    elif '@' in line:
        parts = line.split(':')
        if len(parts) >= 2: return f"{parts[0]}:{parts[1]}"
    return line

def process_file(file_path, keywords, output_format):
    results = []
    total_lines = 0
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            total_lines += 1
            if keywords:
                if not any(kw.lower() in line.lower() for kw in keywords):
                    continue
            
            if output_format == 'combo':
                parsed = format_ulp_line(line)
                if parsed: results.append(parsed)
            elif output_format == 'email':
                if '@' in line:
                    email_part = line.split(':')[0]
                    pass_part = line.split(':')[1] if len(line.split(':')) > 1 else ''
                    if '@' in email_part: results.append(f"{email_part}:{pass_part}")
            elif output_format == 'full':
                results.append(line)
    return results, total_lines

# ================= MAIN MENU UI =================
def get_main_menu_text(chat_id):
    user = get_user(chat_id)
    cid = str(chat_id)
    
    if chat_id == ADMIN_ID:
        tier_icon = "👑"
        daily_left = "Unlimited (Admin)"
        max_file = "Unlimited"
    elif user['tier'] == "Premium":
        tier_icon = "💎"
        daily_left = "Unlimited"
        max_file = "2GB"
    else:
        tier_icon = "🆓"
        daily_left = f"{5 - user['daily_searches']}/5 remaining"
        max_file = "500MB"

    return (
        f"📁 **ULP Log Extractor**\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"👤 **User:** `{chat_id}`\n"
        f"{tier_icon} **Tier:** {user['tier']}\n"
        f"🔍 **Daily:** {daily_left}\n"
        f"📦 **Max file:** {max_file}\n\n"
        f"📊 **Extracts:** {user['total_extracts']:,}\n"
        f"📁 **Files:** {user['files_processed']}\n\n"
        f"Upload a ULP/log file to extract combos."
    )

def get_main_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_upload = types.InlineKeyboardButton("📁 Upload ULP", callback_data="menu_upload")
    btn_how = types.InlineKeyboardButton("📋 How to Use", callback_data="menu_how")
    btn_premium = types.InlineKeyboardButton("💎 Premium", callback_data="menu_premium")
    btn_stats = types.InlineKeyboardButton("📊 My Stats", callback_data="menu_stats")
    markup.add(btn_upload)
    markup.add(btn_how, btn_premium)
    markup.add(btn_stats)
    return markup

# ================= HANDLERS =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    cleanup_user_files(chat_id)
    get_user(chat_id) # DB তে ইউজার তৈরি হবে
    
    bot.send_message(
        chat_id, 
        get_main_menu_text(chat_id), 
        reply_markup=get_main_menu_markup(), 
        parse_mode='Markdown'
    )

# ------ Admin Command: /plan ------
@bot.message_handler(commands=['plan'])
def admin_plan(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "⚠️ Usage: `/plan <chat_id> <duration>`\nExample: `/plan 123456789 1D` or `/plan 123456789 1M`\nDurations: 1D (1 Day), 1W (1 Week), 1M (1 Month)", parse_mode='Markdown')
        return
    
    target_id = args[1]
    duration = args[2].upper()
    
    db = load_db()
    if target_id not in db:
        db[target_id] = {
            "tier": "Premium", "daily_searches": 0, 
            "last_reset": datetime.now().strftime("%Y-%m-%d"),
            "premium_expiry": None, "total_extracts": 0, "files_processed": 0
        }
    
    now = datetime.now()
    if duration == "1D":
        expiry = now + timedelta(days=1)
    elif duration == "1W":
        expiry = now + timedelta(weeks=1)
    elif duration == "1M":
        expiry = now + timedelta(days=30)
    else:
        bot.reply_to(message, "❌ Invalid duration. Use 1D, 1W, or 1M.")
        return
    
    db[target_id]["tier"] = "Premium"
    db[target_id]["premium_expiry"] = expiry.strftime("%Y-%m-%d %H:%M:%S")
    save_db(db)
    
    bot.reply_to(message, f"✅ Successfully upgraded user `{target_id}` to Premium for `{duration}`.\nExpiry: {expiry.strftime('%Y-%m-%d %H:%M:%S')}", parse_mode='Markdown')
    try:
        bot.send_message(target_id, f"🎉 **Congratulations!**\nYou have been upgraded to **Premium** by Admin for {duration}.\nYou can now upload files up to 2GB and unlimited searches.", parse_mode='Markdown')
    except:
        pass

# ------ Inline Menu Callbacks ------
@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_menu(call):
    chat_id = call.message.chat.id
    
    if call.data == "menu_upload":
        bot.answer_callback_query(call.id, "Please attach your file directly to the chat.")
        bot.send_message(chat_id, "📁 **Upload File:**\nSend your ULP/Log file directly here as a document.")
        
    elif call.data == "menu_how":
        how_text = (
            "📋 **How to Use:**\n\n"
            "1. Send a `.txt` file containing your ULP logs.\n"
            "2. Choose to Search by Keyword or Process All.\n"
            "3. Select the format (Combo, Email, Full Lines).\n"
            "4. Bot will send the extracted file back to you.\n\n"
            "**Supported Formats:**\n"
            "`URL:user:pass`\n"
            "`email:pass:URL`"
        )
        bot.edit_message_text(how_text, chat_id, call.message.message_id, reply_markup=get_main_menu_markup(), parse_mode='Markdown')
        
    elif call.data == "menu_premium":
        premium_text = (
            "💎 **Premium Plan**\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            "🔒 **You are on the Free plan.**\n\n"
            "**Premium Features:**\n"
            "✅ Upload files up to 2GB\n"
            "✅ Unlimited daily searches\n"
            "✅ Priority processing\n\n"
            "**Free Plan:**\n"
            "• Max file size: 500MB\n"
            "• 5 searches per day\n\n"
            f"💰 **Contact** {PREMIUM_CONTACT} **to purchase**"
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_contact = types.InlineKeyboardButton(f"📩 Contact {PREMIUM_CONTACT}", url=f"https://t.me/{PREMIUM_CONTACT.replace('@', '')}")
        btn_back = types.InlineKeyboardButton("🔙 Back", callback_data="menu_back")
        markup.add(btn_contact, btn_back)
        
        bot.edit_message_text(premium_text, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        
    elif call.data == "menu_stats":
        user = get_user(chat_id)
        stats_text = (
            f"📊 **My Stats**\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"👤 **Tier:** {user['tier']}\n"
            f"🔍 **Searches Today:** {user['daily_searches']}\n"
            f"📊 **Total Extracts:** {user['total_extracts']:,}\n"
            f"📁 **Files Processed:** {user['files_processed']}\n"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_back"))
        bot.edit_message_text(stats_text, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        
    elif call.data == "menu_back":
        bot.edit_message_text(
            get_main_menu_text(chat_id), 
            chat_id, call.message.message_id, 
            reply_markup=get_main_menu_markup(), 
            parse_mode='Markdown'
        )

# ------ File Handling ------
@bot.message_handler(content_types=['document'])
def handle_document(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    file_size = message.document.file_size
    
    # সাইজ চেক
    if chat_id == ADMIN_ID:
        max_size = float('inf')
    elif user['tier'] == "Premium":
        max_size = PREMIUM_MAX_SIZE
    else:
        max_size = USER_MAX_SIZE
        
    if file_size > max_size:
        bot.reply_to(message, f"❌ **File too large!**\nMax limit for your tier is {max_size / (1024*1024):.0f}MB.")
        return
        
    # লিমিট চেক (Admin এবং Premium এর জন্য আনলিমিটেড)
    if chat_id != ADMIN_ID and user['tier'] == "Free" and user['daily_searches'] >= 5:
        bot.reply_to(message, f"❌ **Daily limit reached!** (5/5 used).\nPlease upgrade to Premium by contacting {PREMIUM_CONTACT}.")
        return

    bot.reply_to(message, "⏳ Downloading file...")
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_path = f"temp_{chat_id}_{int(time.time())}.txt"
    
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)
    
    cleanup_user_files(chat_id)
    user_temp_data[chat_id] = {'file_path': file_path}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_search = types.InlineKeyboardButton("🔍 Search by Keyword", callback_data="search_kw")
    btn_process = types.InlineKeyboardButton("🔄 Process All (No Filter)", callback_data="process_all")
    btn_cancel = types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_all")
    markup.add(btn_search, btn_process, btn_cancel)
    
    bot.send_message(
        chat_id, 
        f"✅ **File Uploaded**\n\n📄 {message.document.file_name}\n📦 Size: {file_size / 1024 / 1024:.2f} MB\n\nChoose an action below:", 
        reply_markup=markup, 
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    
    if call.data == "cancel_all":
        cleanup_user_files(chat_id)
        bot.edit_message_text("❌ Cancelled. File deleted.", chat_id, call.message.message_id)
        return

    if chat_id not in user_temp_data or 'file_path' not in user_temp_data[chat_id]:
        bot.answer_callback_query(call.id, "❌ File not found or session expired. Please upload again.")
        return

    if call.data == "search_kw":
        msg = bot.send_message(chat_id, "🔍 **Search:** Enter keywords separated by comma (e.g. netflix, spotify, disney):", parse_mode='Markdown')
        bot.register_next_step_handler(msg, get_keywords)
        
    elif call.data == "process_all":
        show_format_selection(chat_id, keywords=None)

def get_keywords(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    if text.lower() == 'cancel':
        cleanup_user_files(chat_id)
        bot.send_message(chat_id, "❌ Cancelled.")
        return
        
    keywords = [kw.strip().lower() for kw in text.split(',') if kw.strip()]
    if not keywords:
        bot.send_message(chat_id, "❌ No valid keywords entered.")
        return
        
    show_format_selection(chat_id, keywords)

def show_format_selection(chat_id, keywords):
    user_temp_data[chat_id]['keywords'] = keywords
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📧 Combo (user:pass)", callback_data="fmt_combo")
    btn2 = types.InlineKeyboardButton("📧 Email Only (email:pass)", callback_data="fmt_email")
    btn3 = types.InlineKeyboardButton("📄 Full Lines (with URL)", callback_data="fmt_full")
    btn4 = types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_all")
    markup.add(btn1, btn2, btn3, btn4)
    
    kw_text = "No Filter" if not keywords else f"`{', '.join(keywords)}`"
    
    bot.send_message(
        chat_id, 
        f"🔍 **Search:** {kw_text}\n\nSelect output format:", 
        reply_markup=markup, 
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('fmt_'))
def process_and_send(call):
    chat_id = call.message.chat.id
    fmt = call.data.replace('fmt_', '')
    
    data = user_temp_data.get(chat_id)
    if not data or 'file_path' not in data:
        bot.answer_callback_query(call.id, "Session expired.")
        return

    bot.edit_message_text("⏳ Processing file...", chat_id, call.message.message_id)
    
    try:
        results, total_lines = process_file(data['file_path'], data.get('keywords'), fmt)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error processing file: {e}")
        return

    if not results:
        bot.send_message(chat_id, "❌ No matches found for your criteria.")
        cleanup_user_files(chat_id)
        return

    # ডুপ্লিকেট রিমুভ
    results = list(dict.fromkeys(results))
    
    # স্ট্যাটস আপডেট
    update_user_stats(chat_id, len(results))
    
    result_filename = f"result_{chat_id}.txt"
    with open(result_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))
        
    user_temp_data[chat_id]['formatted_data'] = result_filename
    
    with open(result_filename, 'rb') as f:
        bot.send_document(
            chat_id, 
            f, 
            caption=f"✅ **Processed!**\n📊 Total Lines Scanned: {total_lines}\n✅ Found: {len(results)}"
        )
        
    cleanup_user_files(chat_id)
    
    # মেইন মেনু আবার পাঠানো
    bot.send_message(chat_id, "Main Menu:", reply_markup=get_main_menu_markup())

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    # যদি কেউ টেক্সট দেয়, তাকে মেইন মেনু দেখানো
    bot.send_message(message.chat.id, get_main_menu_text(message.chat.id), reply_markup=get_main_menu_markup(), parse_mode='Markdown')

# ================= START BOT =================
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()