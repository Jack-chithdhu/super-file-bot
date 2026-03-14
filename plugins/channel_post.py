#(©)CodeXBotz - Enhanced by Claude
# Only owner and admins can store files

import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from bot import Bot
from config import ADMINS, CHANNEL_ID, DISABLE_CHANNEL_BUTTON, OWNER_ID
from helper_func import encode
from database.database import get_bot_admins


async def get_all_admins() -> list:
    db_admins = await get_bot_admins()
    return list(set(ADMINS + db_admins))


async def _get_active_ch():
    from database.database import get_setting
    db_ch = await get_setting('db_channel_id')
    return int(db_ch) if db_ch else CHANNEL_ID


# ─────────────────────────────────────────────────────────────────────────────
#  Store file — only owner & admins
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.private & filters.user(ADMINS) & ~filters.command([
    'start','users','broadcast','batch','genlink','stats',
    'ban','unban','banned','filestats','requests','approverequest','approveall',
    'addpremium','removepremium','listpremium','allrequests','fulfill','decline',
    'chatto','endchat','activechats','support','closechat','mystatus','request',
    'addadmin','removeadmin','listadmins','togglepremium','setdailylimit','adminhelp','premium',
    'settings','announce','setpayment','setqr','help','profile'
]), group=1)
async def channel_post(client: Client, message: Message):
    # Skip if admin is in active support chat mode
    if hasattr(client, 'admin_chat_targets'):
        if message.from_user.id in client.admin_chat_targets:
            return

    # Skip forwarded messages from owner — likely part of a settings flow
    from config import OWNER_ID
    if message.from_user.id == OWNER_ID and message.forward_from_chat:
        return

    # Skip forwarded messages from channels (used for DB channel setup)
    if message.forward_from_chat or (hasattr(message, 'forward_origin') and message.forward_origin):
        return

    reply_text = await message.reply_text("⏳ <b>Please Wait...</b>", quote=True)
    active_ch = await _get_active_ch()
    try:
        post_message = await message.copy(chat_id=active_ch, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        post_message = await message.copy(chat_id=active_ch, disable_notification=True)
    except Exception as e:
        await reply_text.edit_text(f"❌ <b>Failed to store file.</b>\n<code>{e}</code>")
        return

    converted_id  = post_message.id * abs(active_ch)
    base64_string = await encode(f"get-{converted_id}")
    link          = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")
    ]])

    await reply_text.edit(
        f"✅ <b>File stored!</b>\n\n🔗 {link}",
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

    if not DISABLE_CHANNEL_BUTTON:
        try:
            await post_message.edit_reply_markup(reply_markup)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await post_message.edit_reply_markup(reply_markup)
        except Exception:
            pass


@Bot.on_message(filters.channel & filters.incoming & filters.chat(CHANNEL_ID))
async def new_post(client: Client, message: Message):
    if DISABLE_CHANNEL_BUTTON:
        return

    active_ch     = await _get_active_ch()
    converted_id  = message.id * abs(active_ch)
    base64_string = await encode(f"get-{converted_id}")
    link          = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup  = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")
    ]])

    try:
        await message.edit_reply_markup(reply_markup)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await message.edit_reply_markup(reply_markup)
    except Exception:
        pass
