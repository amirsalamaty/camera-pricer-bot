"""
Camera Pricer Bot - Professional Edition
Telegram bot for camera pricing with full admin control
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ---------- Logging Setup ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------- Import Telebot ----------
try:
    from telebot import TeleBot
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
    logger.info("SUCCESS: telebot imported successfully")
except ImportError as e:
    logger.error(f"FAILED: Could not import telebot: {e}")
    logger.error("Run: pip install pyTelegramBotAPI python-dotenv")
    sys.exit(1)

# ---------- Load Environment Variables ----------
load_dotenv()
logger.info("Loading environment variables...")

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "")

if not API_TOKEN:
    logger.error("FATAL: TELEGRAM_BOT_TOKEN not found in .env file!")
    sys.exit(1)

logger.info(f"SUCCESS: Token loaded (ends with: ...{API_TOKEN[-10:]})")

ADMIN_IDS = []
if CHAT_IDS:
    try:
        ADMIN_IDS = [int(x.strip()) for x in CHAT_IDS.split(",") if x.strip()]
        logger.info(f"SUCCESS: Admin IDs loaded: {ADMIN_IDS}")
    except ValueError as e:
        logger.error(f"ERROR: Invalid TELEGRAM_CHAT_IDS format: {e}")

bot = TeleBot(API_TOKEN)
logger.info("SUCCESS: Bot instance created")

# ---------- Data File Paths ----------
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
PRODUCTS_FILE = DATA_DIR / "products.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
USERS_FILE = DATA_DIR / "users.json"
logger.info(f"Data directory: {DATA_DIR}")

# ---------- Default Settings ----------
DEFAULT_PRODUCTS = {
    "R6 II BODY": 1610,
    "R7 18-150": 1190,
    "RP 24-105": 860,
    "R10 18-150": 960,
    "R8 24-50": 1080,
    "R50 18-45": 600,
    "A7 M4 BODY": 1650,
    "A7iii Body": 1050,
    "6400 16-50": 710,
}

DEFAULT_SETTINGS = {
    "dirham_rate": 3.67,
    "base_markup": 20000000,
    "percentages": [0.03, 0.04, 0.05, 0.06, 0.10],
    "round_to": -6,  # گرد کردن به میلیون
}

# ---------- Data Management Functions ----------
def load_json(filepath, default):
    """Load JSON file or return default value"""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
    return default.copy() if isinstance(default, dict) else default[:]

def save_json(filepath, data):
    """Save data to JSON file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")
        return False

def load_products():
    return load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)

def save_products(products):
    return save_json(PRODUCTS_FILE, products)

def load_settings():
    return load_json(SETTINGS_FILE, DEFAULT_SETTINGS)

def save_settings(settings):
    return save_json(SETTINGS_FILE, settings)

def load_users():
    return load_json(USERS_FILE, {"allowed": ADMIN_IDS, "admins": ADMIN_IDS})

def save_users(users):
    return save_json(USERS_FILE, users)

# ---------- Access Control ----------
def is_allowed(user_id):
    users = load_users()
    return user_id in users.get("allowed", []) or user_id in users.get("admins", [])

def is_admin(user_id):
    users = load_users()
    return user_id in users.get("admins", [])

# ---------- Keyboards ----------
def main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("📊 لیست محصولات"),
        KeyboardButton("💰 محاسبه قیمت"),
        KeyboardButton("⚙️ تنظیمات"),
        KeyboardButton("📈 آمار"),
        KeyboardButton("❓ راهنما")
    )
    return markup

def admin_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product"),
        InlineKeyboardButton("✏️ ویرایش محصول", callback_data="edit_product"),
        InlineKeyboardButton("🗑️ حذف محصول", callback_data="delete_product"),
        InlineKeyboardButton("👥 مدیریت کاربران", callback_data="manage_users"),
        InlineKeyboardButton("⚙️ تنظیمات پیشرفته", callback_data="advanced_settings"),
        InlineKeyboardButton("🔄 ریست به پیش‌فرض", callback_data="reset_defaults")
    )
    return markup

def settings_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💵 تغییر نرخ درهم", callback_data="set_dirham"),
        InlineKeyboardButton("📊 تغییر درصدها", callback_data="set_percentages"),
        InlineKeyboardButton("💰 تغییر مارکاپ پایه", callback_data="set_markup"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")
    )
    return markup

# ---------- User States ----------
user_states = {}

# ---------- Command Handlers ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    
    if not is_allowed(user_id):
        bot.reply_to(message, 
            f"⛔ شما اجازه دسترسی ندارید.\n"
            f"🆔 آیدی شما: `{user_id}`\n"
            f"این آیدی را به ادمین ارسال کنید.",
            parse_mode="Markdown"
        )
        logger.warning(f"Unauthorized access attempt: {user_id}")
        return
    
    welcome_text = f"""
🎉 *خوش آمدید به ربات قیمت‌گذاری دوربین!*

👤 کاربر: `{user_id}`
{'👑 سطح: ادمین' if is_admin(user_id) else '👤 سطح: کاربر عادی'}

📌 *دستورات سریع:*
• برای محاسبه قیمت، نرخ دلار را ارسال کنید
• از دکمه‌های زیر استفاده کنید

⏰ آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    bot.reply_to(message, welcome_text, parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(commands=['help'])
def send_help(message):
    if not is_allowed(message.chat.id):
        return
    
    help_text = """
📖 *راهنمای کامل ربات*

*🔢 محاسبه قیمت:*
فقط نرخ دلار را ارسال کنید (مثلاً: 58500)

*📋 دستورات:*
/start - شروع مجدد
/help - راهنما
/products - لیست محصولات
/settings - تنظیمات
/stats - آمار

*👑 دستورات ادمین:*
/admin - پنل مدیریت
/adduser [ID] - افزودن کاربر
/removeuser [ID] - حذف کاربر
/addproduct [نام] [قیمت] - افزودن محصول
/delproduct [نام] - حذف محصول

*📊 فرمول محاسبه:*
`(قیمت_دلار × ۳.۶۷ × نرخ_تبدیل) + ۲۰,۰۰۰,۰۰۰`
"""
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "⛔ فقط ادمین‌ها دسترسی دارند.")
        return
    
    bot.reply_to(message, "👑 *پنل مدیریت*\nیک گزینه انتخاب کنید:", 
                 parse_mode="Markdown", reply_markup=admin_keyboard())

@bot.message_handler(commands=['products'])
def list_products(message):
    if not is_allowed(message.chat.id):
        return
    
    products = load_products()
    if not products:
        bot.reply_to(message, "📭 هیچ محصولی ثبت نشده است.")
        return
    
    text = "📦 *لیست محصولات:*\n\n"
    for i, (name, price) in enumerate(products.items(), 1):
        text += f"{i}. *{name}* → ${price:,}\n"
    
    text += f"\n📊 تعداد کل: {len(products)} محصول"
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['settings'])
def show_settings(message):
    if not is_allowed(message.chat.id):
        return
    
    settings = load_settings()
    text = f"""
⚙️ *تنظیمات فعلی:*

💵 نرخ درهم: `{settings['dirham_rate']}`
💰 مارکاپ پایه: `{settings['base_markup']:,}` تومان
📊 درصدها: `{', '.join([f'{int(p*100)}%' for p in settings['percentages']])}`
🔢 گرد کردن: `{abs(settings['round_to'])}` رقم
"""
    
    if is_admin(message.chat.id):
        bot.reply_to(message, text, parse_mode="Markdown", reply_markup=settings_keyboard())
    else:
        bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if not is_allowed(message.chat.id):
        return
    
    products = load_products()
    users = load_users()
    
    text = f"""
📈 *آمار ربات:*

📦 تعداد محصولات: {len(products)}
👥 کاربران مجاز: {len(users.get('allowed', []))}
👑 ادمین‌ها: {len(users.get('admins', []))}
⏰ زمان سرور: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['adduser'])
def add_user_cmd(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "⛔ فقط ادمین‌ها دسترسی دارند.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ فرمت صحیح: `/adduser [ID]`", parse_mode="Markdown")
            return
        
        new_user_id = int(parts[1])
        users = load_users()
        
        if new_user_id in users.get("allowed", []):
            bot.reply_to(message, "⚠️ این کاربر قبلاً اضافه شده است.")
            return
        
        users.setdefault("allowed", []).append(new_user_id)
        save_users(users)
        bot.reply_to(message, f"✅ کاربر `{new_user_id}` با موفقیت اضافه شد.", parse_mode="Markdown")
        logger.info(f"New user added: {new_user_id} by {message.chat.id}")
        
    except ValueError:
        bot.reply_to(message, "❌ آیدی باید عدد باشد.")

@bot.message_handler(commands=['removeuser'])
def remove_user_cmd(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "⛔ فقط ادمین‌ها دسترسی دارند.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ فرمت صحیح: `/removeuser [ID]`", parse_mode="Markdown")
            return
        
        user_id = int(parts[1])
        users = load_users()
        
        if user_id in users.get("admins", []):
            bot.reply_to(message, "⚠️ نمی‌توانید ادمین را حذف کنید.")
            return
        
        if user_id not in users.get("allowed", []):
            bot.reply_to(message, "⚠️ این کاربر در لیست نیست.")
            return
        
        users["allowed"].remove(user_id)
        save_users(users)
        bot.reply_to(message, f"✅ کاربر `{user_id}` حذف شد.", parse_mode="Markdown")
        logger.info(f"User removed: {user_id} by {message.chat.id}")
        
    except ValueError:
        bot.reply_to(message, "❌ آیدی باید عدد باشد.")

@bot.message_handler(commands=['addproduct'])
def add_product_cmd(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "⛔ فقط ادمین‌ها دسترسی دارند.")
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ فرمت صحیح: `/addproduct [نام] [قیمت]`\nمثال: `/addproduct R5_BODY 2500`", 
                        parse_mode="Markdown")
            return
        
        name = parts[1].replace("_", " ")
        price = float(parts[2])
        
        products = load_products()
        products[name] = price
        save_products(products)
        
        bot.reply_to(message, f"✅ محصول اضافه شد:\n*{name}* → ${price:,.0f}", parse_mode="Markdown")
        logger.info(f"New product added: {name} = ${price} by {message.chat.id}")
        
    except ValueError:
        bot.reply_to(message, "❌ قیمت باید عدد باشد.")

@bot.message_handler(commands=['delproduct'])
def delete_product_cmd(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "⛔ فقط ادمین‌ها دسترسی دارند.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ فرمت صحیح: `/delproduct [نام]`", parse_mode="Markdown")
        return
    
    name = parts[1].replace("_", " ")
    products = load_products()
    
    if name not in products:
        bot.reply_to(message, f"⚠️ محصول '{name}' یافت نشد.")
        return
    
    del products[name]
    save_products(products)
    bot.reply_to(message, f"✅ محصول *{name}* حذف شد.", parse_mode="Markdown")
    logger.info(f"Product deleted: {name} by {message.chat.id}")

@bot.message_handler(commands=['users'])
def list_users(message):
    if not is_admin(message.chat.id):
        return
    
    users = load_users()
    text = "👥 *لیست کاربران:*\n\n"
    
    text += "👑 *ادمین‌ها:*\n"
    for uid in users.get("admins", []):
        text += f"  • `{uid}`\n"
    
    text += "\n👤 *کاربران عادی:*\n"
    for uid in users.get("allowed", []):
        if uid not in users.get("admins", []):
            text += f"  • `{uid}`\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

# ---------- Text Button Handlers ----------
@bot.message_handler(func=lambda m: m.text in ["📊 لیست محصولات", "💰 محاسبه قیمت", "⚙️ تنظیمات", "📈 آمار", "❓ راهنما"])
def handle_menu_buttons(message):
    if not is_allowed(message.chat.id):
        return
    
    if message.text == "📊 لیست محصولات":
        list_products(message)
    elif message.text == "💰 محاسبه قیمت":
        bot.reply_to(message, "💵 لطفاً نرخ دلار را ارسال کنید:\n(مثال: 58500)")
        user_states[message.chat.id] = "waiting_rate"
    elif message.text == "⚙️ تنظیمات":
        show_settings(message)
    elif message.text == "📈 آمار":
        show_stats(message)
    elif message.text == "❓ راهنما":
        send_help(message)

# ---------- Callback Query Handler ----------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    if call.data == "add_product":
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, 
            "➕ *افزودن محصول جدید*\n\n"
            "نام و قیمت را به این فرمت ارسال کنید:\n"
            "`نام محصول | قیمت_دلار`\n\n"
            "مثال: `Canon R5 BODY | 2500`",
            parse_mode="Markdown"
        )
        user_states[user_id] = "adding_product"
    
    elif call.data == "edit_product":
        bot.answer_callback_query(call.id)
        products = load_products()
        markup = InlineKeyboardMarkup(row_width=2)
        for name in products:
            markup.add(InlineKeyboardButton(name, callback_data=f"edit_{name}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin"))
        bot.edit_message_text("✏️ محصول مورد نظر را انتخاب کنید:", 
                             call.message.chat.id, call.message.message_id,
                             reply_markup=markup)
    
    elif call.data.startswith("edit_"):
        product_name = call.data[5:]
        bot.answer_callback_query(call.id)
        products = load_products()
        if product_name in products:
            bot.send_message(user_id,
                f"✏️ *ویرایش محصول*\n\n"
                f"محصول: *{product_name}*\n"
                f"قیمت فعلی: `${products[product_name]:,}`\n\n"
                f"قیمت جدید را به دلار ارسال کنید:",
                parse_mode="Markdown"
            )
            user_states[user_id] = f"editing_{product_name}"
    
    elif call.data == "delete_product":
        bot.answer_callback_query(call.id)
        products = load_products()
        markup = InlineKeyboardMarkup(row_width=2)
        for name in products:
            markup.add(InlineKeyboardButton(f"🗑️ {name}", callback_data=f"del_{name}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin"))
        bot.edit_message_text("🗑️ محصول مورد نظر برای حذف را انتخاب کنید:", 
                             call.message.chat.id, call.message.message_id,
                             reply_markup=markup)
    
    elif call.data.startswith("del_"):
        product_name = call.data[4:]
        products = load_products()
        if product_name in products:
            del products[product_name]
            save_products(products)
            bot.answer_callback_query(call.id, f"✅ {product_name} حذف شد!")
            bot.edit_message_text(f"✅ محصول *{product_name}* با موفقیت حذف شد.", 
                                 call.message.chat.id, call.message.message_id,
                                 parse_mode="Markdown")
    
    elif call.data == "set_dirham":
        bot.answer_callback_query(call.id)
        settings = load_settings()
        bot.send_message(user_id,
            f"💵 *تغییر نرخ درهم*\n\n"
            f"نرخ فعلی: `{settings['dirham_rate']}`\n\n"
            f"نرخ جدید را ارسال کنید:",
            parse_mode="Markdown"
        )
        user_states[user_id] = "setting_dirham"
    
    elif call.data == "set_markup":
        bot.answer_callback_query(call.id)
        settings = load_settings()
        bot.send_message(user_id,
            f"💰 *تغییر مارکاپ پایه*\n\n"
            f"مارکاپ فعلی: `{settings['base_markup']:,}` تومان\n\n"
            f"مارکاپ جدید را به تومان ارسال کنید:",
            parse_mode="Markdown"
        )
        user_states[user_id] = "setting_markup"
    
    elif call.data == "set_percentages":
        bot.answer_callback_query(call.id)
        settings = load_settings()
        current = ', '.join([f'{int(p*100)}%' for p in settings['percentages']])
        bot.send_message(user_id,
            f"📊 *تغییر درصدها*\n\n"
            f"درصدهای فعلی: `{current}`\n\n"
            f"درصدهای جدید را با کاما جدا کنید:\n"
            f"مثال: `3, 4, 5, 6, 10`",
            parse_mode="Markdown"
        )
        user_states[user_id] = "setting_percentages"
    
    elif call.data == "manage_users":
        bot.answer_callback_query(call.id)
        users = load_users()
        text = "👥 *مدیریت کاربران*\n\n"
        text += f"تعداد ادمین: {len(users.get('admins', []))}\n"
        text += f"تعداد کاربران: {len(users.get('allowed', []))}\n\n"
        text += "دستورات:\n"
        text += "`/adduser [ID]` - افزودن\n"
        text += "`/removeuser [ID]` - حذف\n"
        text += "`/users` - لیست کاربران"
        bot.send_message(user_id, text, parse_mode="Markdown")
    
    elif call.data == "reset_defaults":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ بله، ریست شود", callback_data="confirm_reset"),
            InlineKeyboardButton("❌ خیر", callback_data="back_admin")
        )
        bot.edit_message_text("⚠️ آیا مطمئن هستید؟\nتمام محصولات و تنظیمات به حالت پیش‌فرض برمی‌گردند.",
                             call.message.chat.id, call.message.message_id,
                             reply_markup=markup)
    
    elif call.data == "confirm_reset":
        save_products(DEFAULT_PRODUCTS)
        save_settings(DEFAULT_SETTINGS)
        bot.answer_callback_query(call.id, "✅ ریست انجام شد!")
        bot.edit_message_text("✅ تمام تنظیمات به حالت پیش‌فرض برگشتند.",
                             call.message.chat.id, call.message.message_id)
    
    elif call.data == "back_admin":
        bot.answer_callback_query(call.id)
        bot.edit_message_text("👑 *پنل مدیریت*\nیک گزینه انتخاب کنید:",
                             call.message.chat.id, call.message.message_id,
                             parse_mode="Markdown", reply_markup=admin_keyboard())
    
    elif call.data == "back_main":
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ---------- Main Message Handler ----------
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.chat.id
    
    if not is_allowed(user_id):
        bot.reply_to(message, 
            f"⛔ شما اجازه دسترسی ندارید.\n"
            f"🆔 آیدی شما: `{user_id}`",
            parse_mode="Markdown"
        )
        return
    
    text = message.text.strip()
    state = user_states.get(user_id)
    
    # ---------- Special States ----------
    if state == "adding_product":
        try:
            if "|" not in text:
                bot.reply_to(message, "❌ فرمت نادرست. از `|` برای جدا کردن استفاده کنید.")
                return
            
            name, price = text.split("|")
            name = name.strip()
            price = float(price.strip())
            
            products = load_products()
            products[name] = price
            save_products(products)
            
            del user_states[user_id]
            bot.reply_to(message, f"✅ محصول *{name}* با قیمت ${price:,.0f} اضافه شد.", 
                        parse_mode="Markdown")
            logger.info(f"New product added: {name} = ${price}")
        except ValueError:
            bot.reply_to(message, "❌ قیمت باید عدد باشد.")
        return
    
    elif state and state.startswith("editing_"):
        try:
            product_name = state[8:]
            new_price = float(text)
            
            products = load_products()
            if product_name in products:
                old_price = products[product_name]
                products[product_name] = new_price
                save_products(products)
                
                del user_states[user_id]
                bot.reply_to(message, 
                    f"✅ قیمت *{product_name}* تغییر کرد:\n"
                    f"`${old_price:,.0f}` → `${new_price:,.0f}`",
                    parse_mode="Markdown"
                )
        except ValueError:
            bot.reply_to(message, "❌ قیمت باید عدد باشد.")
        return
    
    elif state == "setting_dirham":
        try:
            new_rate = float(text)
            settings = load_settings()
            settings['dirham_rate'] = new_rate
            save_settings(settings)
            
            del user_states[user_id]
            bot.reply_to(message, f"✅ نرخ درهم تغییر کرد به: `{new_rate}`", parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "❌ نرخ باید عدد باشد.")
        return
    
    elif state == "setting_markup":
        try:
            new_markup = float(text.replace(",", ""))
            settings = load_settings()
            settings['base_markup'] = new_markup
            save_settings(settings)
            
            del user_states[user_id]
            bot.reply_to(message, f"✅ مارکاپ تغییر کرد به: `{new_markup:,.0f}` تومان", parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "❌ مارکاپ باید عدد باشد.")
        return
    
    elif state == "setting_percentages":
        try:
            percentages = [float(p.strip().replace("%", "")) / 100 for p in text.split(",")]
            settings = load_settings()
            settings['percentages'] = percentages
            save_settings(settings)
            
            del user_states[user_id]
            pct_str = ', '.join([f'{int(p*100)}%' for p in percentages])
            bot.reply_to(message, f"✅ درصدها تغییر کرد به: `{pct_str}`", parse_mode="Markdown")
        except:
            bot.reply_to(message, "❌ فرمت نادرست. مثال: `3, 4, 5, 6, 10`")
        return
    
    # ---------- Price Calculation ----------
    try:
        rate = float(text.replace(",", ""))
        calculate_prices(message, rate)
    except ValueError:
        bot.reply_to(message, 
            "❌ پیام نامعتبر.\n\n"
            "• برای محاسبه قیمت، نرخ دلار را ارسال کنید\n"
            "• یا از منوی زیر استفاده کنید:",
            reply_markup=main_keyboard()
        )

def calculate_prices(message, rate):
    """محاسبه و نمایش قیمت‌ها"""
    products = load_products()
    settings = load_settings()
    
    if not products:
        bot.reply_to(message, "📭 هیچ محصولی ثبت نشده است.")
        return
    
    dirham_rate = settings['dirham_rate']
    base_markup = settings['base_markup']
    percentages = settings['percentages']
    round_to = settings['round_to']
    
    result = f"📊 *نرخ تبدیل:* `{rate:,.0f}` تومان\n"
    result += f"💵 *نرخ درهم:* `{dirham_rate}`\n"
    result += "━" * 25 + "\n\n"
    
    for name, base_price in products.items():
        # Formula: (USD price × dirham rate × toman rate) + markup
        price = ((base_price * dirham_rate) * rate) + base_markup
        
        result += f"🔹 *{name}* @${base_price:,}\n"
        
        for pct in percentages:
            calc = price * (1 + pct)
            calc = round(calc, round_to)
            result += f"    +{int(pct*100)}% → `{calc:,.0f}`\n"
        
        result += "\n"
    
    result += "━" * 25 + "\n"
    result += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # تقسیم پیام اگر خیلی طولانی باشد
    if len(result) > 4000:
        parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
        for part in parts:
            bot.send_message(message.chat.id, part, parse_mode="Markdown")
    else:
        bot.reply_to(message, result, parse_mode="Markdown")
    
    logger.info(f"Price calculation done with rate {rate} by {message.chat.id}")

# ---------- Bot Runner ----------
def send_startup_message():
    """Send startup notification to all admins"""
    users = load_users()
    admins = users.get("admins", ADMIN_IDS)
    
    startup_text = f"""
🤖 *Bot Started Successfully!*

⏰ Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
📦 Products: {len(load_products())}
👥 Users: {len(users.get('allowed', []))}

✅ Bot is now online and ready!
"""
    
    for admin_id in admins:
        try:
            bot.send_message(admin_id, startup_text, parse_mode="Markdown")
            logger.info(f"Startup message sent to admin: {admin_id}")
        except Exception as e:
            logger.error(f"Failed to send startup message to {admin_id}: {e}")

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("STARTING Camera Pricer Bot...")
    logger.info("=" * 50)
    
    # Create default files if not exist
    if not PRODUCTS_FILE.exists():
        save_products(DEFAULT_PRODUCTS)
        logger.info("Created default products.json")
    
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        logger.info("Created default settings.json")
    
    if not USERS_FILE.exists():
        save_users({"allowed": ADMIN_IDS, "admins": ADMIN_IDS})
        logger.info("Created default users.json")
    
    logger.info(f"Admin IDs: {ADMIN_IDS}")
    logger.info(f"Products loaded: {len(load_products())}")
    
    # Test bot connection
    try:
        bot_info = bot.get_me()
        logger.info(f"SUCCESS: Connected as @{bot_info.username}")
    except Exception as e:
        logger.error(f"FATAL: Could not connect to Telegram: {e}")
        sys.exit(1)
    
    # Send startup message to admins
    logger.info("Sending startup messages to admins...")
    send_startup_message()
    
    logger.info("=" * 50)
    logger.info("Bot is now RUNNING! Waiting for messages...")
    logger.info("=" * 50)
    
    # Start polling with auto-restart
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            logger.info("Restarting in 5 seconds...")
            import time
            time.sleep(5)
