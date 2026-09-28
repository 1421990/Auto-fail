import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# ----------------- CONFIGURATION -----------------
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Aapka Telegram User ID (Command chalane ke liye)
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "YourUsername")

# Aapka Main Storage Channel ID
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))
DATABASE_URI = os.environ.get("DATABASE_URI", "")

# 2 GB Size Limit for Free Users
MAX_FREE_SIZE = 2 * 1024 * 1024 * 1024 

bot = Client("rename_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ----------------- MONGO DB SETUP -----------------
mongo_client = MongoClient(DATABASE_URI)
db = mongo_client["ArjunRenameBotDB"]
vip_col = db["vip_users"]

user_thumbnails = {}
user_rename_state = {}

# Helper function to check VIP
def is_vip_user(user_id):
    if user_id == ADMIN_ID:
        return True
    return vip_col.find_one({"user_id": user_id}) is not None

# ----------------- ADMIN VIP CONTROL COMMANDS -----------------
@bot.on_message(filters.private & filters.command("addvip") & filters.user(ADMIN_ID))
async def add_vip_handler(client, message: Message):
    try:
        cmd_parts = message.text.split()
        if len(cmd_parts) < 2:
            await message.reply_text("⚠️ **Usage:** `/addvip USER_ID`")
            return
            
        target_id = int(cmd_parts[1])
        if not vip_col.find_one({"user_id": target_id}):
            vip_col.insert_one({"user_id": target_id, "added_on": time.time()})
            await message.reply_text(f"✅ **User `{target_id}` is now a VIP Member!**")
            # Notify user
            try:
                await client.send_message(target_id, "🎉 **Badhai Ho! Aapka VIP Plan Activate Ho Gaya Hai.**\n\nAb aap unlimited aur 2GB se badi files bhi rename kar sakte ho!")
            except:
                pass
        else:
            await message.reply_text("ℹ️ Ye user pehle se VIP hai.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@bot.on_message(filters.private & filters.command("rmvip") & filters.user(ADMIN_ID))
async def remove_vip_handler(client, message: Message):
    try:
        cmd_parts = message.text.split()
        if len(cmd_parts) < 2:
            await message.reply_text("⚠️ **Usage:** `/rmvip USER_ID`")
            return
            
        target_id = int(cmd_parts[1])
        if vip_col.find_one({"user_id": target_id}):
            vip_col.delete_one({"user_id": target_id})
            await message.reply_text(f"🔴 **User `{target_id}` VIP list se hata diya gaya hai.**")
        else:
            await message.reply_text("ℹ️ Ye user VIP list me nahi hai.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@bot.on_message(filters.private & filters.command("plan"))
async def check_plan(client, message: Message):
    user_id = message.from_user.id
    if is_vip_user(user_id):
        await message.reply_text("🌟 **Aapka Status:** `VIP Member` 💎\n\n✅ Unlimited File Size Renaming Allowed!")
    else:
        await message.reply_text("👤 **Aapka Status:** `Free User`\n\n📌 **Limit:** Max 2 GB per file.\n💡 VIP lene ke liye Admin ko contact karein.")

# ----------------- START & FILE HANDLING -----------------
@bot.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    await message.reply_text(
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        "Me 4K Quality **Rename & Custom Thumbnail Bot** hu.\n\n"
        "📸 Direct photo bhej kar Custom Poster save karein.\n"
        "📁 File bhej kar Rename karein.\n"
        "📊 `/plan` se apna VIP status dekhein."
    )

@bot.on_message(filters.private & filters.photo)
async def save_thumb(client, message: Message):
    user_id = message.from_user.id
    msg = await message.reply_text("⏳ Saving Thumbnail...")
    thumb_path = f"thumb_{user_id}.jpg"
    await message.download(file_name=thumb_path)
    user_thumbnails[user_id] = thumb_path
    await msg.edit_text("<b>Hey Bhai!\n\nThumbnail Saved Successfully ✅</b>")

@bot.on_message(filters.private & (filters.document | filters.video))
async def handle_file(client, message: Message):
    file = message.document or message.video
    user_id = message.from_user.id
    
    # VIP Check for > 2GB Files
    if file.file_size > MAX_FREE_SIZE and not is_vip_user(user_id):
        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("💳 Buy VIP Plan / Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")
        ]])
        await message.reply_text(
            "⚠️ **File Size Limit Exceeded!**\n\n"
            "Free users sirf **2 GB** tak ki file rename kar sakte hain.\n"
            "2 GB se badi file ke liye **VIP Plan** buy karein.",
            reply_markup=btn
        )
        return

    user_rename_state[user_id] = message
    await message.reply_text(
        f"📁 **Current File Name:** `{file.file_name or 'video.mp4'}`\n\n"
        "✍️ **Ab is file ka NAYA NAAM likh kar bhejo:**"
    )

@bot.on_message(filters.private & filters.text & ~filters.command(["start", "del_thumb", "plan", "addvip", "rmvip"]))
async def process_rename(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_rename_state:
        return

    orig_message = user_rename_state.pop(user_id)
    new_file_name = message.text.strip()
    status = await message.reply_text("🚀 **Processing & Downloading...**")
    
    try:
        file_path = await orig_message.download(file_name=new_file_name)
        await status.edit_text("🖼️ **Applying Custom Thumbnail & Uploading...**")
        
        thumb_path = f"thumb_{user_id}.jpg" if os.path.exists(f"thumb_{user_id}.jpg") else None
        caption_text = f"🎬 **{new_file_name}**\n\n⚡ Renamed by @{client.me.username}"

        # Send to User
        user_sent_msg = await client.send_document(
            chat_id=user_id,
            document=file_path,
            thumb=thumb_path,
            caption=caption_text
        )

        # Send Copy to Admin Storage Channel
        await user_sent_msg.copy(
            chat_id=CHANNEL_ID,
            caption=f"📥 **Auto Saved Movie:**\n`{new_file_name}`"
        )
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ **Error:** {e}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    bot.run()
