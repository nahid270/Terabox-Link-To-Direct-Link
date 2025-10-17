from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading
import requests
import asyncio
import os 

# --- চূড়ান্ত কনফিগারেশন লোড করা ---
# Note: সেশন স্ট্রিং ব্যবহার করলে এটিই ক্লায়েন্টের নাম হিসেবে কাজ করবে এবং সেশন ফাইল এড়ানো যাবে।
SESSION_STRING = os.environ.get("SESSION_STRING", None)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7991711310:AAHIZbDdINXt9haVibV-sBLsq2N4S-hyxDQ")

# API ID/Hash সরাসরি ব্যবহার করা হচ্ছে (যদিও এগুলি সেশন স্ট্রিং এ এমবেডেড থাকে, Pyrogram সেফটির জন্য চায়)
API_ID = int(os.environ.get("API_ID", 28870226))
API_HASH = os.environ.get("API_HASH", "a5b1ff3f75941649bf5bc159782f0f00") 

# ক্লায়েন্ট নেম নির্বাচন: যদি SESSION_STRING থাকে, তবে সেটি ব্যবহার করা হবে। 
# অন্যথায় ডিফল্ট নাম ব্যবহার করা হবে (যা ফাইল সেভ করার চেষ্টা করবে)।
CLIENT_NAME_OR_STRING = SESSION_STRING if SESSION_STRING else "terabox_downloader_bot"


# --- Pyrogram এবং Flask সেটআপ ---
app = Flask(__name__)

bot = Client(
    CLIENT_NAME_OR_STRING, 
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ... (বাকি handler এবং flask রুট অপরিবর্তিত থাকবে) ...
# ... (আপনার start_handler, get_video_handler এবং home ফাংশনগুলো যেমন আছে তেমনই থাকবে) ...

# --- ৩. প্রোগ্রাম শুরু করা (চূড়ান্ত ত্রুটিমুক্ত লজিক) ---

if __name__ == "__main__":
    
    def start_bot():
        """Pyrogram কে একটি আলাদা থ্রেডে, ম্যানুয়াল asyncio লুপে চালানো।"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_pyrogram():
            try:
                if not CLIENT_NAME_OR_STRING:
                    print("⚠️ WARNING: SESSION_STRING not found. Relying on file system save.")
                    
                await bot.start()
                print("✅ [STATUS] Pyrogram bot connected successfully.")
                
                # বটকে অনির্দিষ্টকাল ধরে চালু রাখা
                await asyncio.Future() 
                
            except Exception as e:
                print(f"❌ [FATAL ERROR] Pyrogram connection error: {e}")
            finally:
                await bot.stop()
                print("🛑 [STATUS] Pyrogram bot stopped.")

        print("🔄 [SETUP] Pyrogram bot setup complete. Starting loop...")
        loop.run_until_complete(run_pyrogram())
        
    # বটকে একটি আলাদা থ্রেডে চালানো
    threading.Thread(target=start_bot, name='PyrogramThread').start()
    
    # ফ্লাস্ক অ্যাপকে মূল থ্রেডে শুরু করা
    print("🚀 [STATUS] Flask web server started on port 8080.")
    app.run(host="0.0.0.0", port=8080)
