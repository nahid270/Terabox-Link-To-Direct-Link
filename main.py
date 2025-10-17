import os
import sys
import threading
import asyncio
import logging
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# --- ১. লগিং সেটআপ ---
logging.basicConfig(level=logging.INFO, 
                    format='[%(asctime)s] - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TeraboxBot')


# --- ২. কনফিগারেশন লোড করা ---
# এই মানগুলো Render Environment Variables থেকে লোড হওয়া আবশ্যক।
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID") # নতুন সংযোজন
PORT = int(os.environ.get("PORT", 8080))

# Terabox API Endpoint
TERABOX_API_URL = "https://terabox-api.vercel.app/api?url="

# ক্লায়েন্টের ফাইল সেশন নেম (ফাইল নামের দৈর্ঘ্য সীমিত রাখতে ছোট নাম)
CLIENT_NAME = "terabox_bot_session" 


# --- ৩. কনফিগারেশন বৈধতা যাচাই ---

if not all([BOT_TOKEN, API_ID, API_HASH]):
    logger.critical("FATAL: BOT_TOKEN, API_ID, and API_HASH must be set in Environment Variables.")
    sys.exit(1)

try:
    API_ID_INT = int(API_ID)
    if LOG_CHANNEL_ID:
        LOG_CHANNEL_ID_INT = int(LOG_CHANNEL_ID)
except ValueError:
    logger.critical("FATAL: API_ID or LOG_CHANNEL_ID must be valid integers.")
    sys.exit(1)


# --- ৪. ক্লায়েন্ট ইনিশিয়ালাইজেশন ---

app = Flask(__name__)

try:
    if SESSION_STRING:
        # চূড়ান্ত ফিক্স: সেশন স্ট্রিং থাকলে সেটি সরাসরি প্যারামিটার হিসেবে পাস করা
        bot = Client(
            CLIENT_NAME, 
            api_id=API_ID_INT,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            session_string=SESSION_STRING
        )
        logger.info("Client initialized successfully using SESSION_STRING.")
    else:
        # সেশন স্ট্রিং না থাকলে, Pyrogram কে নিজে ফাইল তৈরি করার সুযোগ দেওয়া
        bot = Client(
            CLIENT_NAME, 
            api_id=API_ID_INT,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
        logger.warning("Client initialized. No SESSION_STRING found, attempting file creation.")

except Exception as e:
    logger.critical(f"Client initialization failed: {e}")
    sys.exit(1)


# --- ৫. লগ চ্যানেল ফাংশন ---

async def log_to_channel(text: str, level: str = 'INFO'):
    """গুরুত্বপূর্ণ মেসেজ লগ চ্যানেলে পাঠায়"""
    if LOG_CHANNEL_ID:
        try:
            await bot.send_message(
                LOG_CHANNEL_ID_INT,
                f"[{level}] {text}",
                disable_notification=True
            )
        except Exception as e:
            logger.error(f"Failed to send log to channel: {e}")


# --- ৬. ফ্লাস্ক রুট ---
@app.route('/')
def home():
    """হোস্টিং প্ল্যাটফর্মের জন্য সার্ভার স্ট্যাটাস চেক"""
    return "✅ Terabox Watch Bot is Running Successfully!"


# --- ৭. API লজিক ফাংশন ---

async def get_terabox_link(link: str):
    """Terabox API কল করে সরাসরি ডাউনলোড লিংক বের করে।"""
    api_url = f"{TERABOX_API_URL}{link}"
    
    try:
        res = requests.get(api_url, timeout=15).json()

        if res.get("success") and res.get("downloadLink"):
            return res["downloadLink"]
        else:
            return None
            
    except requests.exceptions.RequestException:
        return "NETWORK_ERROR"
    except Exception as e:
        logger.error(f"Unknown error during API call: {e}")
        return "UNKNOWN_ERROR"


# --- ৮. Pyrogram হ্যান্ডলার্স ---

@bot.on_message(filters.command("start"))
async def start_handler(_, msg):
    """/start কমান্ডের উত্তর দেয়"""
    user_info = f"User: {msg.from_user.id} ({msg.from_user.first_name})"
    logger.info(f"Received /start from {user_info}")
    
    await log_to_channel(f"Received /start command.\n{user_info}", level='EVENT')
    
    await msg.reply_text(
        "👋 **স্বাগতম! আমি Terabox Watch Bot!**\n\n"
        "আমাকে শুধু একটা **বৈধ Terabox লিংক** পাঠান।\n"
        "আমি সাথে সাথে আপনাকে সরাসরি ভিডিও দেখার লিংক তৈরি করে দেব 🔥\n\n"
        "এখনই চেষ্টা করুন!",
        disable_web_page_preview=True
    )

@bot.on_message(filters.text & ~filters.command("start"))
async def get_video_handler(_, msg):
    link = msg.text.strip()
    user_info = f"User: {msg.from_user.id} ({msg.from_user.first_name})"
    
    await log_to_channel(f"Received link: `{link}`\n{user_info}", level='REQUEST')
    
    if "terabox" not in link.lower():
        return await msg.reply_text("❌ দয়া করে একটি বৈধ Terabox লিংক দিন।")

    waiting_msg = await msg.reply_text("⏳ আপনার লিংক প্রসেস করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
    
    video_url = await get_terabox_link(link)
    reply_markup = None
    
    # এরর হ্যান্ডলিং
    if video_url == "NETWORK_ERROR":
        text = "⚠️ API এর সাথে যোগাযোগ করা যাচ্ছে না বা এটি সময়মত সাড়া দিচ্ছে না। কিছুক্ষণ পর আবার চেষ্টা করুন।"
        await log_to_channel(f"Network Error during API call for {user_info}", level='ERROR')
    elif video_url == "UNKNOWN_ERROR":
        text = "❌ একটি অপ্রত্যাশিত ভুল হয়েছে। সার্ভার লগ চেক করুন।"
        await log_to_channel(f"Unknown Error for {user_info}", level='ERROR')
    elif video_url:
        # সফল হলে
        text = "✅ **সফল!** ভিডিও রেডি! এখনই দেখতে পারো 👇"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Watch Now", url=video_url)]]
        )
        await log_to_channel(f"Successfully extracted URL for {user_info}.", level='SUCCESS')
    else:
        # API লিংক দিতে ব্যর্থ হলে
        text = "⚠️ ভিডিও বের করা যায়নি। সার্ভারের সমস্যা হতে পারে বা লিংকটি অবৈধ/ডিলিট করা হয়েছে।"
        await log_to_channel(f"Extraction failed for {user_info}: {link}", level='WARNING')
    
    # মেসেজ এডিট করা
    await waiting_msg.edit_text(text, reply_markup=reply_markup)


# --- ৯. মাল্টিথ্রেডিং এবং স্টার্টআপ লজিক ---

if __name__ == "__main__":
    
    def start_pyrogram_thread():
        """Pyrogram কে একটি আলাদা থ্রেডে, ম্যানুয়াল asyncio লুপে চালানো।"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_pyrogram():
            try:
                await bot.start()
                logger.info("✅ [STATUS] Pyrogram bot online and ready to handle updates.")
                
                # বট অনলাইনে আসার সাথে সাথেই লগ চ্যানেলে মেসেজ পাঠাও
                if LOG_CHANNEL_ID:
                    await bot.send_message(
                        LOG_CHANNEL_ID_INT,
                        f"🟢 **BOT ONLINE!** Successfully connected and ready to process links.",
                        disable_notification=False
                    )
                
                # বটকে অনির্দিষ্টকাল ধরে চালু রাখা
                await asyncio.Future() 
                
            except Exception as e:
                logger.error(f"❌ [FATAL THREAD ERROR] Pyrogram failure: {e}")
            finally:
                if bot.is_connected:
                    await bot.stop()
                    logger.info("🛑 [STATUS] Pyrogram bot stopped.")
                
        loop.run_until_complete(run_pyrogram())
        
    # বটকে একটি আলাদা থ্রেডে চালানো
    threading.Thread(target=start_pyrogram_thread, name='PyrogramThread').start()
    
    # ফ্লাস্ক অ্যাপকে মূল থ্রেডে শুরু করা
    logger.info("🚀 [STATUS] Flask web server starting...")
    app.run(host="0.0.0.0", port=PORT)
