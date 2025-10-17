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
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID") # Chat ID স্ট্রিং হিসেবে লোড হবে
PORT = int(os.environ.get("PORT", 8080))

TERABOX_API_URL = "https://terabox-api.vercel.app/api?url="
CLIENT_NAME = "terabox_bot_session" 


# --- ৩. কনফিগারেশন বৈধতা যাচাই ---
if not all([BOT_TOKEN, API_ID, API_HASH]):
    logger.critical("FATAL: BOT_TOKEN, API_ID, and API_HASH must be set.")
    sys.exit(1)

try:
    API_ID_INT = int(API_ID)
except ValueError:
    logger.critical("FATAL: API_ID must be a valid integer.")
    sys.exit(1)


# --- ৪. ক্লায়েন্ট ইনিশিয়ালাইজেশন ---
app = Flask(__name__)

try:
    if SESSION_STRING:
        bot = Client(
            CLIENT_NAME, 
            api_id=API_ID_INT,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            session_string=SESSION_STRING
        )
    else:
        bot = Client(
            CLIENT_NAME, 
            api_id=API_ID_INT,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
    logger.info("Pyrogram Client initialized.")

except Exception as e:
    logger.critical(f"Client initialization failed: {e}")
    sys.exit(1)


# --- ৫. লগ চ্যানেল ফাংশন (ID ফিক্স) ---

async def log_to_channel(text: str, level: str = 'INFO'):
    """গুরুত্বপূর্ণ মেসেজ লগ চ্যানেলে পাঠায়"""
    if LOG_CHANNEL_ID:
        try:
            # ID সরাসরি স্ট্রিং হিসেবে পাস করা হচ্ছে Peer ID Invalid এড়াতে
            await bot.send_message(
                LOG_CHANNEL_ID, # এখানে স্ট্রিং বা ইনটিজার যেকোনোটি কাজ করা উচিত
                f"[{level}] {text}",
                disable_notification=True
            )
        except Exception as e:
            # যদি Peer ID Invalid এরর আসে, তা এখানে ধরা পড়বে
            logger.error(f"Failed to send log to channel ({LOG_CHANNEL_ID}): {e}")


# --- ৬. ফ্লাস্ক রুট ---
@app.route('/')
def home():
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
    user_info = f"User: {msg.from_user.id} ({msg.from_user.first_name})"
    
    await log_to_channel(f"Received /start from {user_info}", level='EVENT')
    
    await msg.reply_text(
        "👋 **স্বাগতম! আমি Terabox Watch Bot!**\n\n"
        "আমাকে শুধু একটা **বৈধ Terabox লিংক** পাঠান।\n"
        "আমি সাথে সাথে আপনাকে সরাসরি ভিডিও দেখার লিংক তৈরি করে দেব 🔥"
    )

@bot.on_message(filters.text & ~filters.command("start"))
async def get_video_handler(_, msg):
    link = msg.text.strip()
    user_info = f"User: {msg.from_user.id} ({msg.from_user.first_name})"
    
    await log_to_channel(f"Received link: `{link}` from {user_info}", level='REQUEST')
    
    if "terabox" not in link.lower():
        return await msg.reply_text("❌ দয়া করে একটি বৈধ Terabox লিংক দিন।")

    waiting_msg = await msg.reply_text("⏳ আপনার লিংক প্রসেস করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
    
    video_url = await get_terabox_link(link)
    reply_markup = None
    
    if video_url == "NETWORK_ERROR":
        text = "⚠️ API এর সাথে যোগাযোগ করা যাচ্ছে না বা এটি সময়মত সাড়া দিচ্ছে না। কিছুক্ষণ পর আবার চেষ্টা করুন।"
    elif video_url == "UNKNOWN_ERROR":
        text = "❌ একটি অপ্রত্যাশিত ভুল হয়েছে। সার্ভার লগ চেক করুন।"
    elif video_url:
        text = "✅ **সফল!** ভিডিও রেডি! এখনই দেখতে পারো 👇"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Watch Now", url=video_url)]]
        )
        await log_to_channel(f"Successfully extracted URL for {user_info}.", level='SUCCESS')
    else:
        text = "⚠️ ভিডিও বের করা যায়নি। সার্ভারের সমস্যা হতে পারে বা লিংকটি অবৈধ/ডিলিট করা হয়েছে।"
        await log_to_channel(f"Extraction failed for {user_info}: {link}", level='WARNING')
    
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
                    await log_to_channel(
                        f"🟢 **BOT ONLINE!** Successfully connected and ready to process links.",
                        level='INFO'
                    )
                
                # বটকে অনির্দিষ্টকাল ধরে চালু রাখা
                await asyncio.Future() 
                
            except Exception as e:
                logger.error(f"❌ [PYROGRAM THREAD ERROR] Failure: {e}")
            finally:
                # bot.stop() কে অপসারণ করা হয়েছে যাতে RuntimeError না আসে।
                logger.info("🛑 [STATUS] Pyrogram thread terminated.")
                
        loop.run_until_complete(run_pyrogram())
        
    # বটকে একটি আলাদা থ্রেডে চালানো
    threading.Thread(target=start_pyrogram_thread, name='PyrogramThread').start()
    
    # ফ্লাস্ক অ্যাপকে মূল থ্রেডে শুরু করা
    logger.info("🚀 [STATUS] Flask web server starting...")
    app.run(host="0.0.0.0", port=PORT)
