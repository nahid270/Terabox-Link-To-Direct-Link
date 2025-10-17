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
# এই মানগুলো রেন্ডার এনভায়রনমেন্ট ভেরিয়েবল থেকে লোড হওয়া আবশ্যক।

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
PORT = int(os.environ.get("PORT", 8080))
TERABOX_API_URL = "https://terabox-api.vercel.app/api?url="


# --- ৩. কনফিগারেশন বৈধতা যাচাই (Mandatory Check) ---

if not BOT_TOKEN or not API_ID or not API_HASH:
    logger.critical("FATAL: BOT_TOKEN, API_ID, and API_HASH must be set in Environment Variables.")
    sys.exit(1)

# সেশন স্ট্রিং ব্যবহার বাধ্যতামূলক করা হলো, যা Render এর জন্য সেরা
if not SESSION_STRING:
    logger.warning("WARNING: SESSION_STRING not found. Bot might face issues with re-authorization on restart.")
    logger.warning("Please run a session generator script locally and set SESSION_STRING in Render.")
    CLIENT_NAME = "terabox_bot_session"
else:
    # সেশন স্ট্রিং থাকলে এটি ক্লায়েন্টের নাম হিসেবে কাজ করবে
    CLIENT_NAME = SESSION_STRING

# --- ৪. ক্লায়েন্ট ইনিশিয়ালাইজেশন ---
try:
    bot = Client(
        CLIENT_NAME, 
        api_id=int(API_ID),
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
    logger.info("Pyrogram Client initialized.")
except Exception as e:
    logger.critical(f"Initialization Failed: {e}")
    sys.exit(1)

# Flask সেটআপ
app = Flask(__name__)


# --- ৫. ফ্লাস্ক রুট (Health Check) ---
@app.route('/')
def home():
    """হোস্টিং প্ল্যাটফর্মের জন্য সার্ভার স্ট্যাটাস চেক"""
    return "✅ Terabox Watch Bot is Running Successfully!"


# --- ৬. API লজিক ফাংশন (Synchronous API Call) ---

async def get_terabox_link(link: str):
    """Terabox API কল করে সরাসরি ডাউনলোড লিংক বের করে।"""
    api_url = f"{TERABOX_API_URL}{link}"
    
    # requests synchronously ব্যবহার করা হয়, কিন্তু Pyrogram async context এ এটি ঠিক আছে
    try:
        res = requests.get(api_url, timeout=15).json()

        if res.get("success") and res.get("downloadLink"):
            logger.info(f"Link extracted successfully for: {link}")
            return res["downloadLink"]
        else:
            return None
            
    except requests.exceptions.RequestException:
        logger.error("Network or API timeout error occurred.")
        return "NETWORK_ERROR"
    except Exception as e:
        logger.error(f"Unknown error during API call: {e}")
        return "UNKNOWN_ERROR"


# --- ৭. Pyrogram হ্যান্ডলার্স ---

@bot.on_message(filters.command("start"))
async def start_handler(_, msg):
    """/start কমান্ডের উত্তর দেয়"""
    logger.info(f"Received /start from user {msg.from_user.id}")
    await msg.reply_text(
        "👋 **স্বাগতম! আমি Terabox Watch Bot!**\n\n"
        "আমার কাজ খুবই সোজা:\n"
        "➡️ শুধু আমাকে একটি **বৈধ Terabox লিংক** পাঠান।\n"
        "আমি সাথে সাথে আপনাকে সরাসরি ভিডিও দেখার লিংক তৈরি করে দেব 🔥\n\n"
        "এখনই চেষ্টা করুন!",
        disable_web_page_preview=True
    )

@bot.on_message(filters.text & ~filters.command("start"))
async def get_video_handler(_, msg):
    link = msg.text.strip()
    
    if "terabox" not in link.lower():
        return await msg.reply_text("❌ দয়া করে একটি বৈধ Terabox লিংক দিন।")

    logger.info(f"Processing link from user {msg.from_user.id}: {link}")
    waiting_msg = await msg.reply_text("⏳ আপনার লিংক প্রসেস করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
    
    video_url = await get_terabox_link(link)
    
    # এরর হ্যান্ডলিং এবং রিপ্লাই
    if video_url == "NETWORK_ERROR":
        text = "⚠️ API এর সাথে যোগাযোগ করা যাচ্ছে না বা এটি সময়মত সাড়া দিচ্ছে না। কিছুক্ষণ পর আবার চেষ্টা করুন।"
    elif video_url == "UNKNOWN_ERROR":
        text = "❌ একটি অপ্রত্যাশিত ভুল হয়েছে। সার্ভার লগ চেক করুন।"
    elif video_url:
        # সফল হলে
        text = "✅ **সফল!** ভিডিও রেডি! এখনই দেখতে পারো 👇"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Watch Now", url=video_url)]]
        )
    else:
        # API লিংক দিতে ব্যর্থ হলে
        text = "⚠️ ভিডিও বের করা যায়নি। সার্ভারের সমস্যা হতে পারে বা লিংকটি অবৈধ/ডিলিট করা হয়েছে।"
    
    # মেসেজ এডিট করা
    await waiting_msg.edit_text(text, reply_markup=reply_markup if 'reply_markup' in locals() else None)


# --- ৮. মাল্টিথ্রেডিং এবং স্টার্টআপ লজিক ---

if __name__ == "__main__":
    
    def start_pyrogram_thread():
        """Pyrogram কে একটি আলাদা থ্রেডে, ম্যানুয়াল asyncio লুপে চালানো।"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_pyrogram():
            try:
                await bot.start()
                logger.info("✅ [STATUS] Pyrogram bot online and ready to handle updates.")
                
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
