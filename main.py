from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading
import requests
import asyncio # যদিও requests ব্যবহার করা হচ্ছে, threading এর সাথে asynchronous operations চালানোর জন্য প্রস্তুত রাখা ভালো।

# ↓↓↓ এখানে তোমার বট টোকেন বসাও ↓↓↓
BOT_TOKEN = "7991711310:AAHIZbDdINXt9haVibV-sBLsq2N4S-hyxDQ" 

# --- Pyrogram এবং Flask সেটআপ ---
app = Flask(__name__)
# Client সেশন নেম: terabox_downloader_bot
bot = Client("terabox_downloader_bot", bot_token=BOT_TOKEN)

# --- ১. ফ্লাস্ক রুট (Health Check) ---
@app.route('/')
def home():
    """চেক করে সার্ভার চলছে কি না"""
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
    waiting_msg = await msg.reply_text("⏳ আপনার লিংক প্রসেস করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
    
    try:
        # API এর মাধ্যমে লিংক থেকে ভিডিও বের করা
        api_url = f"https://terabox-api.vercel.app/api?url={link}"
        
        # requests synchronous হওয়ায়, এটি এই থ্রেডটিকে ব্লক করবে, 
        # কিন্তু যেহেতু Pyrogram অন্য থ্রেডে চলছে, তাই মূল অ্যাপ হ্যাং হবে না।
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
            "⚠️ API এর সাথে যোগাযোগ করা যাচ্ছে না। কিছুক্ষণ পর আবার চেষ্টা করুন।"
        )
    except Exception as e:
        # অন্য কোনো অপ্রত্যাশিত এরর
        await waiting_msg.edit_text(
            f"❌ একটি অপ্রত্যাশিত ভুল হয়েছে:\n`{type(e).__name__}: {e}`"
        )

# --- ৩. প্রোগ্রাম শুরু করা (Flask এবং Pyrogram একসাথে) ---

if __name__ == "__main__":
    # Pyrogram বটকে একটি ব্যাকগ্রাউন্ড থ্রেডে শুরু করা
    # এটি নিশ্চিত করে যে বট টেলিগ্রাম আপডেট শুনতে থাকবে।
    threading.Thread(target=lambda: bot.run()).start()
    
    # ফ্লাস্ক অ্যাপকে মূল থ্রেডে শুরু করা (হোস্টিং প্ল্যাটফর্মের জন্য আবশ্যক)
    print("🚀 Flask web server started on port 8080.")
    app.run(host="0.0.0.0", port=8080)
