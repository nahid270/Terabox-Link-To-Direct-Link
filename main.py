from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading
import requests
import asyncio
import os 

# --- কনফিগারেশন লোড করা (এনভায়রনমেন্ট ভেরিয়েবল বা ডিফল্ট থেকে) ---
# NOTE: সিকিউরিটির জন্য Render সেটিংসে এগুলি যোগ করুন।
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7991711310:AAHIZbDdINXt9haVibV-sBLsq2N4S-hyxDQ")
API_ID = int(os.environ.get("API_ID", 28870226))
API_HASH = os.environ.get("API_HASH", "a5b1ff3f75941649bf5bc159782f0f00") 


# --- Pyrogram এবং Flask সেটআপ ---
app = Flask(__name__)

bot = Client(
    "terabox_downloader_bot", 
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- ১. ফ্লাস্ক রুট (Health Check) ---
@app.route('/')
def home():
    """হোস্টিং প্ল্যাটফর্মের জন্য সার্ভার স্ট্যাটাস চেক"""
    return "✅ Terabox Watch Bot is Running Successfully!"

# --- ২. Pyrogram হ্যান্ডলার্স ---

@bot.on_message(filters.command("start"))
async def start_handler(_, msg):
    """/start কমান্ডের উত্তর দেয়"""
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

    waiting_msg = await msg.reply_text("⏳ আপনার লিংক প্রসেস করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
    
    try:
        api_url = f"https://terabox-api.vercel.app/api?url={link}"
        
        # Note: requests synchronous, but fine since it's in a Pyrogram thread.
        res = requests.get(api_url, timeout=15).json()

        if res.get("success") and res.get("downloadLink"):
            video_url = res["downloadLink"]
            
            await waiting_msg.edit_text(
                "✅ **সফল!** ভিডিও রেডি! এখনই দেখতে পারো 👇",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("▶️ Watch Now", url=video_url)]]
                )
            )
        else:
            await waiting_msg.edit_text(
                "⚠️ ভিডিও বের করা যায়নি। সার্ভারের সমস্যা হতে পারে বা লিংকটি অবৈধ/ডিলিট করা হয়েছে।"
            )
            
    except requests.exceptions.RequestException:
        await waiting_msg.edit_text(
            "⚠️ API এর সাথে যোগাযোগ করা যাচ্ছে না বা এটি সময়মত সাড়া দিচ্ছে না। কিছুক্ষণ পর আবার চেষ্টা করুন।"
        )
    except Exception as e:
        await waiting_msg.edit_text(
            f"❌ একটি অপ্রত্যাশিত ভুল হয়েছে:\n`{type(e).__name__}: {e}`"
        )

# --- ৩. প্রোগ্রাম শুরু করা (চূড়ান্ত ত্রুটিমুক্ত লজিক) ---

if __name__ == "__main__":
    
    def start_bot():
        """Pyrogram কে একটি আলাদা থ্রেডে, ম্যানুয়াল asyncio লুপে চালানো।"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_pyrogram():
            try:
                # বট শুরু করা (কানেক্ট এবং অথোরাইজ করা)
                await bot.start()
                print("🤖 Pyrogram bot connected successfully.")
                
                # বটকে অনির্দিষ্টকাল ধরে চালু রাখা
                # signal.error এড়াতে idle() এর পরিবর্তে Future() ব্যবহার করা হয়েছে
                await asyncio.Future() 
                
            except Exception as e:
                # যদি কোনো fatal error হয়
                print(f"Pyrogram connection error: {e}")
            finally:
                # সব শেষে বট বন্ধ করা
                await bot.stop()
                print("🤖 Pyrogram bot stopped.")

        print("🤖 Pyrogram bot setup complete. Starting loop...")
        loop.run_until_complete(run_pyrogram())
        
    # বটকে একটি আলাদা থ্রেডে চালানো
    threading.Thread(target=start_bot, name='PyrogramThread').start()
    
    # ফ্লাস্ক অ্যাপকে মূল থ্রেডে শুরু করা
    print("🚀 Flask web server started on port 8080.")
    app.run(host="0.0.0.0", port=8080)
