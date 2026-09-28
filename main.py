import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# ----------------- ENVIRONMENT VARIABLES -----------------
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Aapka Admin ID aur Telegram Username
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "YourUsername")

# Aapka Private Storage Channel ID
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))
DATABASE_URI = os.environ.get("DATABASE_URI", "")

# 2 GB Free Size Limit (Bytes me)
MAX_FREE_SIZE = 2 * 1024 * 1024 * 1024 

app = Client("rename_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ----------------- MONGO DB SETUP -----------------
mongo_client = MongoClient(DATABASE_URI)
db = mongo_client["PublicRenameBotDB"]
vip_col = db["vip_users"]

user_rename_state = {}

def is_vip(user_id):
    if user_id == ADMIN_ID:
        return True
    return vip_col.find_one({"user_id": user_id}) is not None

# ----------------- COMMANDS & HANDLERS -----------------

@app.on_message(filters.private & filters.command("start"))
async def start_handler(client, message: Message):
    await message.reply_text(
        f"👋 **Welcome {message.from_user.first_name}!**\n\n"
        "Me Fast **Rename & Custom Thumbnail Bot** hu.\n\n"
        "📌 **Features:**\n"
        "• Photo bhej kar Custom Poster Save karein.\n"
        "• File/Video bhej kar Naya Naam likhein.\n"
        "• Free Limit: Up to **2 GB** per file.\n"
        "• VIP Members: Unlimited file size renaming!\n\n"
        "💡 Plan check karne ke liye `/plan` likhein."
    )

@app.on_message(filters.private & filters.command("plan"))
async def plan_handler(client, message: Message):
    user_id = message.from_user.id
    if is_vip(user_id):
        await message.reply_text("💎 **Status:** `VIP Member` (Unlimited 4GB File Access)")
    else:
        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("💳 Contact Admin for VIP", url=f"https://t.me/{ADMIN_USERNAME}")
        ]])
        await message.reply_text(
            "👤 **Status:** `Free User`\n\n"
            "📌 **Limit:** Max 2 GB per file.\n"
            "💬 2 GB se badi files ke liye VIP plan lein.",
            reply_markup=btn
        )

# ----------------- ADMIN VIP CONTROLS -----------------

@app.on_message(filters.private & filters.command("addvip") & filters.user(ADMIN_ID))
async def add_vip(client, message: Message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text("⚠️ **Usage:** `/addvip USER_ID`")
            return
        target_id = int(parts[1])
        if not vip_col.find_one({"user_id": target_id}):
            vip_col.insert_one({"user_id": target_id, "added_at": time.time()})
            await message.reply_text(f"✅ User `{target_id}` added to VIP list!")
            try:
                await client.send_message(target_id, "🎉 **Badhai Ho! Aapka VIP Plan Activate Ho Gaya Hai.**")
            except:
                pass
        else:
            await message.reply_text("ℹ️ User pehle se VIP hai.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.private & filters.command("rmvip") & filters.user(ADMIN_ID))
async def remove_vip(client, message: Message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text("⚠️ **Usage:** `/rmvip USER_ID`")
            return
        target_id = int(parts[1])
        if vip_col.find_one({"user_id": target_id}):
            vip_col.delete_one({"user_id": target_id})
            await message.reply_text(f"🔴 User `{target_id}` removed from VIP list.")
        else:
            await message.reply_text("ℹ️ User VIP list me nahi hai.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ----------------- THUMBNAIL SYSTEM -----------------

@app.on_message(filters.private & filters.photo)
async def save_thumb(client, message: Message):
    user_id = message.from_user.id
    msg = await message.reply_text("⏳ Saving Thumbnail...")
    thumb_path = f"thumb_{user_id}.jpg"
    await message.download(file_name=thumb_path)
    await msg.edit_text("<b>Thumbnail Saved Successfully ✅</b>")

@app.on_message(filters.private & filters.command("del_thumb"))
async def del_thumb(client, message: Message):
    user_id = message.from_user.id
    thumb_path = f"thumb_{user_id}.jpg"
    if os.path.exists(thumb_path):
        os.remove(thumb_path)
        await message.reply_text("<b>Thumbnail Deleted Successfully 🗑️</b>")
    else:
        await message.reply_text("<b>No Saved Thumbnail Found!</b>")

# ----------------- RENAME & FILE PROCESSING -----------------

@app.on_message(filters.private & (filters.document | filters.video))
async def receive_file(client, message: Message):
    file = message.document or message.video
    user_id = message.from_user.id

    # 2 GB Check for non-VIP users
    if file.file_size > MAX_FREE_SIZE and not is_vip(user_id):
        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("💳 Buy VIP / Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")
        ]])
        await message.reply_text(
            "⚠️ **File Size Limit Exceeded!**\n\n"
            "Free users sirf **2 GB** tak ki file rename kar sakte hain.\n"
            "2 GB se badi file ke liye VIP Plan buy karein.",
            reply_markup=btn
        )
        return

    user_rename_state[user_id] = message
    await message.reply_text(
        f"📁 **Current File:** `{file.file_name or 'video.mp4'}`\n\n"
        "✍️ **Ab is file ka NAYA NAAM likh kar bhejo:**"
    )

@app.on_message(filters.private & filters.text & ~filters.command(["start", "plan", "addvip", "rmvip", "del_thumb"]))
async def execute_rename(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_rename_state:
        return

    orig_message = user_rename_state.pop(user_id)
    new_name = message.text.strip()
    status = await message.reply_text("🚀 **Downloading File to Server...**")
    file_path = None

    try:
        file_path = await orig_message.download(file_name=new_name)
        await status.edit_text("🖼️ **Applying Poster & Uploading...**")

        thumb_path = f"thumb_{user_id}.jpg" if os.path.exists(f"thumb_{user_id}.jpg") else None
        caption_text = f"🎬 **{new_name}**\n\n⚡ Renamed by @{client.me.username}"

        # 1. User PM me send karna
        sent_doc = await client.send_document(
            chat_id=user_id,
            document=file_path,
            thumb=thumb_path,
            caption=caption_text
        )

        # 2. Secretly Aapke Storage Channel me Copy karna
        await sent_doc.copy(
            chat_id=CHANNEL_ID,
            caption=f"📥 **Auto Saved Movie:**\n`{new_name}`\n👤 **By User:** `{user_id}`"
        )
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ **Error:** {e}")
    finally:
        # File delete kar memory khali karna
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    app.run()
