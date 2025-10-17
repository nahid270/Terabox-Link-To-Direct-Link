from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading, requests

BOT_TOKEN = "YOUR_BOT_TOKEN"  # ← এখানে তোমার বট টোকেন বসাও

app = Flask(__name__)
bot = Client("terabox-bot", bot_token=BOT_TOKEN)

@app.route('/')
def home():
    return "✅ Terabox Watch Bot is Running Successfully!"

@bot.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply_text(
        "👋 হ্যালো!\n\n🎬 আমি **Terabox Watch Bot**!\n\nতুমি শুধু আমাকে একটা **Terabox লিংক** পাঠাও, আমি তোমাকে সরাসরি ভিডিও দেখার লিংক দিয়ে দেব 🔥"
    )

@bot.on_message(filters.text & ~filters.command("start"))
async def get_video(_, msg):
    link = msg.text.strip()
    if "terabox" not in link:
        return await msg.reply_text("❌ দয়া করে একটি বৈধ Terabox লিংক পাঠাও!")

    try:
        api = f"https://terabox-api.vercel.app/api?url={link}"
        res = requests.get(api).json()
        if res.get("success") and res.get("downloadLink"):
            video_url = res["downloadLink"]
            await msg.reply_text(
                "🎥 ভিডিও রেডি! এখনই দেখতে পারো 👇",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("▶️ Watch Now", url=video_url)]]
                )
            )
        else:
            await msg.reply_text("⚠️ ভিডিও বের করা যায়নি, আবার চেষ্টা করো।")
    except Exception as e:
        await msg.reply_text(f"⚠️ কিছু একটা ভুল হয়েছে:\n`{e}`")

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.run()).start()
    app.run(host="0.0.0.0", port=8080)
