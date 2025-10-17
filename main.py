from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading
import requests
import asyncio # asyncio লুপ ফিক্স করার জন্য আবশ্যক

# ↓↓↓ এখানে তোমার বট টোকেন বসাও ↓↓↓
BOT_TOKEN = "7991711310:AAHIZbDdINXt9haVibV-sBLsq2N4S-hyxDQ"

# --- Pyrogram এবং Flask সেটআপ ---
app = Flask(__name__)
# Client সেশন নেম: terabox_downloader_bot
bot = Client("terabox_downloader_bot", bot_token=BOT_TOKEN)

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
    
    # ইনপুট যাচাই
    if "terabox" not in link.lower():
        return await msg.reply_text("❌ দয়া করে একটি বৈধ Terabox লিংক দিন।")

    # ব্যবহারকারীকে অপেক্ষার বার্তা পাঠানো
    # পাইরোগ্ৰাম এডিটিং এর জন্য মেসেজ অবজেক্টকে সেভ করে রাখা হয়
    waiting_msg = await msg.reply_text("⏳ আপনার লিংক প্রসেস করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
    
    try:
        # API এর মাধ্যমে লিংক থেকে ভিডিও বের করা
        api_url = f"https://terabox-api.vercel.app/api?url={link}"
        
        # requests ব্যবহার করে API কল করা
        res = requests.get(api_url, timeout=15).json()

        if res.get("success") and res.get("downloadLink"):
            video_url = res["downloadLink"]
            
            # সফল হলে মেসেজ এডিট করা
            await waiting_msg.edit_text(
                "✅ **সফল!** ভিডিও রেডি! এখনই দেখতে পারো 👇",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("▶️ Watch Now", url=video_url)]]
                )
            )
        else:
            # API লিংক দিতে ব্যর্থ হলে
            await waiting_msg.edit_text(
                "⚠️ ভিডিও বের করা যায়নি। সার্ভারের সমস্যা হতে পারে বা লিংকটি অবৈধ/ডিলিট করা হয়েছে।"
            )
            
    except requests.exceptions.RequestException:
        # নেটওয়ার্ক বা API টাইমআউট সংক্রান্ত এরর
        await waiting_msg.edit_text(
            "⚠️ API এর সাথে যোগাযোগ করা যাচ্ছে না বা এটি সময়মত সাড়া দিচ্ছে না। কিছুক্ষণ পর আবার চেষ্টা করুন।"
        )
    except Exception as e:
        # অন্য কোনো অপ্রত্যাশিত এরর
        await waiting_msg.edit_text(
            f"❌ একটি অপ্রত্যাশিত ভুল হয়েছে:\n`{type(e).__name__}: {e}`"
        )

# --- ৩. প্রোগ্রাম শুরু করা (Flask এবং Pyrogram একসাথে - ত্রুটিমুক্ত) ---

if __name__ == "__main__":
    
    def start_bot():
        """এই ফাংশনটি নতুন থ্রেডে async লুপ তৈরি করে Pyrogram কে শুরু করে।"""
        # নতুন থ্রেডের জন্য একটি নতুন ইভেন্ট লুপ তৈরি করা
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        print("🤖 Pyrogram bot starting...")
        # সেই লুপে Pyrogram বটকে চালানো
        bot.run()
        
    # বটকে একটি আলাদা থ্রেডে চালানো
    threading.Thread(target=start_bot, name='PyrogramThread').start()
    
    # ফ্লাস্ক অ্যাপকে মূল থ্রেডে শুরু করা
    print("🚀 Flask web server started on port 8080.")
    app.run(host="0.0.0.0", port=8080)
