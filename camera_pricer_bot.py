"""
Camera Pricer Bot - Professional Edition v2.0
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
    "round_to": -6,
}

# ---------- Data Management Functions ----------
def load_json(filepath, default):
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
    return default.copy() if isinstance(default, dict) else default[:]

def save_json(filepath, data):
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
def main_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("📊 لیست محصولات"),
        KeyboardButton("💰 محاسبه قیمت"),
    )
    markup.add(
        KeyboardButton("⚙️ تنظیمات"),
        KeyboardButton("📈 آمار"),
    )
    if is_admin(user_id):
        markup.add(KeyboardButton("👑 پنل ادمین"))
    markup.add(KeyboardButton("❓ راهنما"))
    return markup

def admin_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product"),
        InlineKeyboardButton("✏️ ویرایش قیمت", callback_data="edit_product"),
    )
    markup.add(
        InlineKeyboardButton("🗑️ حذف محصول", callback_data="delete_product"),
        InlineKeyboardButton("📋 لیست محصولات", callback_data="list_products"),
    )
    markup.add(
        InlineKeyboardButton("💰 تغییر مارکاپ", callback_data="set_markup"),
        InlineKeyboardButton("💵 نرخ درهم", callback_data="set_dirham"),
    )
    markup.add(
        InlineKeyboardButton("📊 تغییر درصدها", callback_data="set_percentages"),
        InlineKeyboardButton("👥 کاربران", callback_data="manage_users"),
    )
    markup.add(
        InlineKeyboardButton("🔄 ریست به پیش‌فرض", callback_data="reset_defaults"),
    )
    return markup

def quick_actions_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ افزودن دیگر", callback_data="add_product"),
        InlineKeyboardButton("✏️ ویرایش", callback_data="edit_product"),
    )
    markup.add(
        InlineKeyboardButton("🗑️ حذف", callback_data="delete_product"),
        InlineKeyboardButton("📋 لیست", callback_data="list_products"),
    )
    markup.add(
        InlineKeyboardButton("🔙 پنل ادمین", callback_data="back_admin"),
    )
    return markup

def back_to_admin_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_admin"))
    return markup

def settings_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💵 تغییر نرخ درهم", callback_data="set_dirham"),
        InlineKeyboardButton("📊 تغییر درصدها", callback_data="set_percentages"),
        InlineKeyboardButton("💰 تغییر مارکاپ پایه", callback_data="set_markup"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin")
    )
    return markup

# ---------- User States ----------
user_states = {}

# ---------- Format Helpers ----------
def format_number(num):
    return f"{num:,.0f}"

def format_price_table(products, settings, rate):
    dirham_rate = settings['dirham_rate']
    base_markup = settings['base_markup']
    percentages = settings['percentages']
    round_to = settings['round_to']
    
    result = "╔══════════════════════════════╗\n"
    result += "║  📊 *جدول قیمت دوربین*\n"
    result += "╠══════════════════════════════╣\n"
    result += f"║ 💵 دلار: `{format_number(rate)}`\n"
    result += f"║ 🏷️ درهم: `{dirham_rate}`\n"
    result += f"║ 📦 مارکاپ: `{format_number(base_markup)}`\n"
    result += "╚══════════════════════════════╝\n\n"
    
    for name, base_price in products.items():
        price = ((base_price * dirham_rate) * rate) + base_markup
        
        result += f"┌────────────────────────\n"
        result += f"│ 📷 *{name}*  •  `${base_price:,}`\n"
        result += f"├────────────────────────\n"
        
        for pct in percentages:
            calc = price * (1 + pct)
            calc = round(calc, round_to)
            if pct <= 0.03:
                emoji = "🟢"
            elif pct <= 0.05:
                emoji = "🟡"
            elif pct <= 0.06:
                emoji = "🟠"
            else:
                emoji = "🔴"
            result += f"│ {emoji} {int(pct*100):2d}% → `{format_number(calc)}`\n"
        
        result += f"└────────────────────────\n\n"
    
    result += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    return result

def format_products_list(products):
    if not products:
        return "📭 هیچ محصولی ثبت نشده است."
    
    result = "╔══════════════════════════════╗\n"
    result += "║      📦 *لیست محصولات*\n"
    result += "╠══════════════════════════════╣\n"
    
    for i, (name, price) in enumerate(products.items(), 1):
        result += f"║ {i}. *{name}*\n"
        result += f"║    💵 `${price:,}`\n"
        if i < len(products):
            result += "║ ─────────────────────\n"
    
    result += "╠══════════════════════════════╣\n"
    result += f"║ 📊 مجموع: *{len(products)}* محصول\n"
    result += "╚══════════════════════════════╝"
    
    return result

# ---------- Command Handlers ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    
    if not is_allowed(user_id):
        bot.reply_to(message, 
            f"⛔ شما دسترسی ندارید.\n🆔 آیدی: `{user_id}`",
            parse_mode="Markdown"
        )
        logger.warning(f"Unauthorized: {user_id}")
        return
    
    admin_badge = "👑 ادمین" if is_admin(user_id) else "👤 کاربر"
    
    welcome_text = f"""
╔══════════════════════════════╗
║  🎉 *خوش آمدید!*
╠══════════════════════════════╣
║  🆔 `{user_id}`
║  🏷️ {admin_badge}
╠══════════════════════════════╣
║  💡 نرخ دلار را بفرستید
╚══════════════════════════════╝
"""
    bot.reply_to(message, welcome_text, parse_mode="Markdown", reply_markup=main_keyboard(user_id))

@bot.message_handler(commands=['help'])
def send_help(message):
    if not is_allowed(message.chat.id):
        return
    
    help_text = """
╔══════════════════════════════╗
║      📖 *راهنما*
╠══════════════════════════════╣
║ 
║ *محاسبه قیمت:*
║ نرخ دلار را بفرستید
║ مثال: `58500`
║ 
║ *فرمول:*
║ `(دلار × درهم × نرخ) + مارکاپ`
║ 
╚══════════════════════════════╝
"""
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "⛔ دسترسی ندارید.")
        return
    show_admin_panel(message.chat.id)

def show_admin_panel(chat_id, message_id=None):
    settings = load_settings()
    products = load_products()
    
    text = f"""
╔══════════════════════════════╗
║      👑 *پنل مدیریت*
╠══════════════════════════════╣
║ 📦 محصولات: *{len(products)}*
║ 💰 مارکاپ: `{format_number(settings['base_markup'])}`
║ 💵 درهم: `{settings['dirham_rate']}`
║ 📊 درصدها: `{', '.join([f"{int(p*100)}%" for p in settings['percentages']])}`
╚══════════════════════════════╝
"""
    
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, 
                             parse_mode="Markdown", reply_markup=admin_keyboard())
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=admin_keyboard())

@bot.message_handler(commands=['products'])
def list_products_cmd(message):
    if not is_allowed(message.chat.id):
        return
    products = load_products()
    text = format_products_list(products)
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['settings'])
def show_settings(message):
    if not is_allowed(message.chat.id):
        return
    
    settings = load_settings()
    text = f"""
╔══════════════════════════════╗
║      ⚙️ *تنظیمات*
╠══════════════════════════════╣
║ 💵 درهم: `{settings['dirham_rate']}`
║ 💰 مارکاپ: `{format_number(settings['base_markup'])}`
║ 📊 درصدها: `{', '.join([f'{int(p*100)}%' for p in settings['percentages']])}`
╚══════════════════════════════╝
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
    settings = load_settings()
    
    text = f"""
╔══════════════════════════════╗
║      📈 *آمار*
╠══════════════════════════════╣
║ 📦 محصولات: *{len(products)}*
║ 👥 کاربران: *{len(users.get('allowed', []))}*
║ 👑 ادمین‌ها: *{len(users.get('admins', []))}*
╠══════════════════════════════╣
║ 💰 مارکاپ: `{format_number(settings['base_markup'])}`
║ ⏰ {datetime.now().strftime('%H:%M:%S')}
╚══════════════════════════════╝
"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['adduser'])
def add_user_cmd(message):
    if not is_admin(message.chat.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ `/adduser [ID]`", parse_mode="Markdown")
            return
        
        new_user_id = int(parts[1])
        users = load_users()
        
        if new_user_id in users.get("allowed", []):
            bot.reply_to(message, "⚠️ قبلاً اضافه شده.")
            return
        
        users.setdefault("allowed", []).append(new_user_id)
        save_users(users)
        bot.reply_to(message, f"✅ کاربر `{new_user_id}` اضافه شد.", parse_mode="Markdown")
        logger.info(f"User added: {new_user_id}")
        
    except ValueError:
        bot.reply_to(message, "❌ آیدی باید عدد باشد.")

@bot.message_handler(commands=['removeuser'])
def remove_user_cmd(message):
    if not is_admin(message.chat.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ `/removeuser [ID]`", parse_mode="Markdown")
            return
        
        user_id = int(parts[1])
        users = load_users()
        
        if user_id in users.get("admins", []):
            bot.reply_to(message, "⚠️ ادمین قابل حذف نیست.")
            return
        
        if user_id not in users.get("allowed", []):
            bot.reply_to(message, "⚠️ کاربر یافت نشد.")
            return
        
        users["allowed"].remove(user_id)
        save_users(users)
        bot.reply_to(message, f"✅ کاربر `{user_id}` حذف شد.", parse_mode="Markdown")
        logger.info(f"User removed: {user_id}")
        
    except ValueError:
        bot.reply_to(message, "❌ آیدی باید عدد باشد.")

@bot.message_handler(commands=['users'])
def list_users(message):
    if not is_admin(message.chat.id):
        return
    
    users = load_users()
    text = "╔══════════════════════════════╗\n"
    text += "║      👥 *کاربران*\n"
    text += "╠══════════════════════════════╣\n"
    text += "║ *👑 ادمین‌ها:*\n"
    for uid in users.get("admins", []):
        text += f"║   `{uid}`\n"
    text += "║ ─────────────────────\n"
    text += "║ *👤 کاربران:*\n"
    for uid in users.get("allowed", []):
        if uid not in users.get("admins", []):
            text += f"║   `{uid}`\n"
    text += "╚══════════════════════════════╝"
    
    bot.reply_to(message, text, parse_mode="Markdown")

# ---------- Text Button Handlers ----------
@bot.message_handler(func=lambda m: m.text in ["📊 لیست محصولات", "💰 محاسبه قیمت", "⚙️ تنظیمات", "📈 آمار", "❓ راهنما", "👑 پنل ادمین"])
def handle_menu_buttons(message):
    if not is_allowed(message.chat.id):
        return
    
    if message.text == "📊 لیست محصولات":
        list_products_cmd(message)
    elif message.text == "💰 محاسبه قیمت":
        bot.reply_to(message, "💵 نرخ دلار را بفرستید:\nمثال: `58500`", parse_mode="Markdown")
    elif message.text == "⚙️ تنظیمات":
        show_settings(message)
    elif message.text == "📈 آمار":
        show_stats(message)
    elif message.text == "❓ راهنما":
        send_help(message)
    elif message.text == "👑 پنل ادمین":
        if is_admin(message.chat.id):
            show_admin_panel(message.chat.id)
        else:
            bot.reply_to(message, "⛔ دسترسی ندارید.")

# ---------- Callback Query Handler ----------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    # Add Product
    if call.data == "add_product":
        bot.answer_callback_query(call.id)
        text = "➕ *افزودن محصول*\n\nبه این فرمت بفرستید:\n`نام | قیمت`\n\nمثال:\n`Canon R5 | 2500`"
        bot.edit_message_text(text, user_id, message_id, 
                             parse_mode="Markdown", reply_markup=back_to_admin_keyboard())
        user_states[user_id] = "adding_product"
    
    # Edit Product
    elif call.data == "edit_product":
        bot.answer_callback_query(call.id)
        products = load_products()
        
        if not products:
            bot.edit_message_text("📭 محصولی نیست.", user_id, message_id,
                                 reply_markup=back_to_admin_keyboard())
            return
        
        markup = InlineKeyboardMarkup(row_width=1)
        for name, price in products.items():
            markup.add(InlineKeyboardButton(f"✏️ {name} (${price})", callback_data=f"edit_{name}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin"))
        
        bot.edit_message_text("✏️ *انتخاب کنید:*", user_id, message_id,
                             parse_mode="Markdown", reply_markup=markup)
    
    elif call.data.startswith("edit_"):
        product_name = call.data[5:]
        bot.answer_callback_query(call.id)
        products = load_products()
        
        if product_name in products:
            text = f"✏️ *{product_name}*\n💵 فعلی: `${products[product_name]:,}`\n\nقیمت جدید:"
            bot.edit_message_text(text, user_id, message_id,
                                 parse_mode="Markdown", reply_markup=back_to_admin_keyboard())
            user_states[user_id] = f"editing_{product_name}"
    
    # Delete Product
    elif call.data == "delete_product":
        bot.answer_callback_query(call.id)
        products = load_products()
        
        if not products:
            bot.edit_message_text("📭 محصولی نیست.", user_id, message_id,
                                 reply_markup=back_to_admin_keyboard())
            return
        
        markup = InlineKeyboardMarkup(row_width=1)
        for name, price in products.items():
            markup.add(InlineKeyboardButton(f"🗑️ {name} (${price})", callback_data=f"del_{name}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin"))
        
        bot.edit_message_text("🗑️ *برای حذف انتخاب کنید:*", user_id, message_id,
                             parse_mode="Markdown", reply_markup=markup)
    
    elif call.data.startswith("del_"):
        product_name = call.data[4:]
        products = load_products()
        
        if product_name in products:
            del products[product_name]
            save_products(products)
            bot.answer_callback_query(call.id, f"✅ {product_name} حذف شد!")
            
            if products:
                markup = InlineKeyboardMarkup(row_width=1)
                for name, price in products.items():
                    markup.add(InlineKeyboardButton(f"🗑️ {name} (${price})", callback_data=f"del_{name}"))
                markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_admin"))
                bot.edit_message_text(f"✅ *{product_name}* حذف شد.\n\n🗑️ *حذف دیگر:*", 
                                     user_id, message_id, parse_mode="Markdown", reply_markup=markup)
            else:
                bot.edit_message_text("✅ حذف شد. لیست خالی است.", 
                                     user_id, message_id, reply_markup=quick_actions_keyboard())
            
            logger.info(f"Deleted: {product_name}")
    
    # List Products
    elif call.data == "list_products":
        bot.answer_callback_query(call.id)
        products = load_products()
        text = format_products_list(products)
        bot.edit_message_text(text, user_id, message_id,
                             parse_mode="Markdown", reply_markup=quick_actions_keyboard())
    
    # Settings
    elif call.data == "set_markup":
        bot.answer_callback_query(call.id)
        settings = load_settings()
        text = f"💰 *مارکاپ*\n\nفعلی: `{format_number(settings['base_markup'])}`\n\nمقدار جدید:"
        bot.edit_message_text(text, user_id, message_id,
                             parse_mode="Markdown", reply_markup=back_to_admin_keyboard())
        user_states[user_id] = "setting_markup"
    
    elif call.data == "set_dirham":
        bot.answer_callback_query(call.id)
        settings = load_settings()
        text = f"💵 *نرخ درهم*\n\nفعلی: `{settings['dirham_rate']}`\n\nمقدار جدید:"
        bot.edit_message_text(text, user_id, message_id,
                             parse_mode="Markdown", reply_markup=back_to_admin_keyboard())
        user_states[user_id] = "setting_dirham"
    
    elif call.data == "set_percentages":
        bot.answer_callback_query(call.id)
        settings = load_settings()
        current = ', '.join([f'{int(p*100)}%' for p in settings['percentages']])
        text = f"📊 *درصدها*\n\nفعلی: `{current}`\n\nجدید (با کاما):\nمثال: `3, 4, 5, 6, 10`"
        bot.edit_message_text(text, user_id, message_id,
                             parse_mode="Markdown", reply_markup=back_to_admin_keyboard())
        user_states[user_id] = "setting_percentages"
    
    # User Management
    elif call.data == "manage_users":
        bot.answer_callback_query(call.id)
        users = load_users()
        text = f"👥 *کاربران*\n\n👑 ادمین: {len(users.get('admins', []))}\n👤 کاربر: {len(users.get('allowed', []))}\n\n"
        text += "دستورات:\n`/adduser ID`\n`/removeuser ID`\n`/users`"
        bot.edit_message_text(text, user_id, message_id,
                             parse_mode="Markdown", reply_markup=back_to_admin_keyboard())
    
    # Reset
    elif call.data == "reset_defaults":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ بله", callback_data="confirm_reset"),
            InlineKeyboardButton("❌ خیر", callback_data="back_admin")
        )
        bot.edit_message_text("⚠️ *ریست کامل؟*\nهمه چیز پاک می‌شود!",
                             user_id, message_id, parse_mode="Markdown", reply_markup=markup)
    
    elif call.data == "confirm_reset":
        save_products(DEFAULT_PRODUCTS)
        save_settings(DEFAULT_SETTINGS)
        bot.answer_callback_query(call.id, "✅ ریست شد!")
        show_admin_panel(user_id, message_id)
        logger.info(f"Reset by {user_id}")
    
    # Back
    elif call.data == "back_admin":
        bot.answer_callback_query(call.id)
        user_states.pop(user_id, None)
        show_admin_panel(user_id, message_id)

# ---------- Main Message Handler ----------
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.chat.id
    
    if not is_allowed(user_id):
        bot.reply_to(message, f"⛔ دسترسی ندارید.\n🆔 `{user_id}`", parse_mode="Markdown")
        return
    
    text = message.text.strip()
    state = user_states.get(user_id)
    
    # Adding Product
    if state == "adding_product":
        try:
            if "|" not in text:
                bot.reply_to(message, "❌ از `|` استفاده کنید.\nمثال: `Canon R5 | 2500`", parse_mode="Markdown")
                return
            
            name, price = text.split("|")
            name = name.strip()
            price = float(price.strip())
            
            products = load_products()
            products[name] = price
            save_products(products)
            
            del user_states[user_id]
            bot.reply_to(message, f"✅ *{name}* اضافه شد!\n💵 `${price:,.0f}`",
                        parse_mode="Markdown", reply_markup=quick_actions_keyboard())
            logger.info(f"Added: {name} = ${price}")
            
        except ValueError:
            bot.reply_to(message, "❌ قیمت باید عدد باشد.")
        return
    
    # Editing Product
    elif state and state.startswith("editing_"):
        try:
            product_name = state[8:]
            new_price = float(text.replace(",", ""))
            
            products = load_products()
            if product_name in products:
                old_price = products[product_name]
                products[product_name] = new_price
                save_products(products)
                
                del user_states[user_id]
                bot.reply_to(message, f"✅ *{product_name}*\n`${old_price:,.0f}` → `${new_price:,.0f}`",
                            parse_mode="Markdown", reply_markup=quick_actions_keyboard())
                logger.info(f"Updated: {product_name} ${old_price} -> ${new_price}")
                
        except ValueError:
            bot.reply_to(message, "❌ قیمت باید عدد باشد.")
        return
    
    # Settings
    elif state == "setting_dirham":
        try:
            new_rate = float(text)
            settings = load_settings()
            old = settings['dirham_rate']
            settings['dirham_rate'] = new_rate
            save_settings(settings)
            del user_states[user_id]
            bot.reply_to(message, f"✅ درهم: `{old}` → `{new_rate}`", 
                        parse_mode="Markdown", reply_markup=quick_actions_keyboard())
        except ValueError:
            bot.reply_to(message, "❌ عدد وارد کنید.")
        return
    
    elif state == "setting_markup":
        try:
            new_markup = float(text.replace(",", ""))
            settings = load_settings()
            old = settings['base_markup']
            settings['base_markup'] = new_markup
            save_settings(settings)
            del user_states[user_id]
            bot.reply_to(message, f"✅ مارکاپ:\n`{format_number(old)}` → `{format_number(new_markup)}`", 
                        parse_mode="Markdown", reply_markup=quick_actions_keyboard())
        except ValueError:
            bot.reply_to(message, "❌ عدد وارد کنید.")
        return
    
    elif state == "setting_percentages":
        try:
            percentages = [float(p.strip().replace("%", "")) / 100 for p in text.split(",")]
            settings = load_settings()
            settings['percentages'] = percentages
            save_settings(settings)
            del user_states[user_id]
            pct_str = ', '.join([f'{int(p*100)}%' for p in percentages])
            bot.reply_to(message, f"✅ درصدها: `{pct_str}`", 
                        parse_mode="Markdown", reply_markup=quick_actions_keyboard())
        except:
            bot.reply_to(message, "❌ مثال: `3, 4, 5, 6, 10`", parse_mode="Markdown")
        return
    
    # Price Calculation
    try:
        rate = float(text.replace(",", ""))
        products = load_products()
        settings = load_settings()
        
        if not products:
            bot.reply_to(message, "📭 محصولی ثبت نشده.")
            return
        
        result = format_price_table(products, settings, rate)
        
        if len(result) > 4000:
            parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
            for part in parts:
                bot.send_message(message.chat.id, part, parse_mode="Markdown")
        else:
            bot.reply_to(message, result, parse_mode="Markdown")
        
        logger.info(f"Calc: rate={rate} by {user_id}")
        
    except ValueError:
        bot.reply_to(message, "💡 نرخ دلار را بفرستید.\nمثال: `58500`",
                    parse_mode="Markdown", reply_markup=main_keyboard(user_id))

# ---------- Bot Runner ----------
def send_startup_message():
    users = load_users()
    admins = users.get("admins", ADMIN_IDS)
    products = load_products()
    settings = load_settings()
    
    text = f"""
╔══════════════════════════════╗
║  🤖 *Bot Started!*
╠══════════════════════════════╣
║ ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}
║ 📦 Products: {len(products)}
║ 💰 Markup: {format_number(settings['base_markup'])}
║ ✅ Ready!
╚══════════════════════════════╝
"""
    
    for admin_id in admins:
        try:
            bot.send_message(admin_id, text, parse_mode="Markdown", reply_markup=main_keyboard(admin_id))
            logger.info(f"Startup sent to: {admin_id}")
        except Exception as e:
            logger.error(f"Failed startup to {admin_id}: {e}")

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("STARTING Camera Pricer Bot v2.0...")
    logger.info("=" * 50)
    
    if not PRODUCTS_FILE.exists():
        save_products(DEFAULT_PRODUCTS)
        logger.info("Created products.json")
    
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        logger.info("Created settings.json")
    
    if not USERS_FILE.exists():
        save_users({"allowed": ADMIN_IDS, "admins": ADMIN_IDS})
        logger.info("Created users.json")
    
    logger.info(f"Admin IDs: {ADMIN_IDS}")
    logger.info(f"Products: {len(load_products())}")
    
    try:
        bot_info = bot.get_me()
        logger.info(f"SUCCESS: @{bot_info.username}")
    except Exception as e:
        logger.error(f"FATAL: {e}")
        sys.exit(1)
    
    send_startup_message()
    
    logger.info("=" * 50)
    logger.info("Bot RUNNING!")
    logger.info("=" * 50)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            logger.error(f"Error: {e}")
            import time
            time.sleep(5)
