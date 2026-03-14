#(©)CodeXBotz - Enhanced by Claude

from config import CHANNEL_ID

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from bot import Bot
from config import ADMINS
from helper_func import encode, get_message_id


# ─────────────────────────────────────────────────────────────────────────────
#  /batch  — link for a range of posts
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('batch'))
async def batch(client: Client, message: Message):
    # ── First message ──────────────────────────────────────────────────────
    while True:
        try:
            first_message = await client.ask(
                text=(
                    "📌 <b>Batch Link Generator</b>\n\n"
                    "Forward the <b>first</b> message from the DB Channel "
                    "(with quotes)\nor send its post link.\n\n"
                    "<i>Timeout: 60s</i>"
                ),
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except asyncio.TimeoutError:
            await message.reply("⏰ Timed out. Use /batch to try again.")
            return
        except Exception:
            return

        f_msg_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        await first_message.reply(
            "❌ <b>Invalid message.</b>\n\nMake sure you forward from the "
            "DB Channel or paste a valid post link.",
            quote=True
        )

    # ── Last message ───────────────────────────────────────────────────────
    while True:
        try:
            second_message = await client.ask(
                text=(
                    "📌 Now forward the <b>last</b> message from the DB Channel "
                    "(with quotes)\nor send its post link.\n\n"
                    "<i>Timeout: 60s</i>"
                ),
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except asyncio.TimeoutError:
            await message.reply("⏰ Timed out. Use /batch to try again.")
            return
        except Exception:
            return

        s_msg_id = await get_message_id(client, second_message)
        if s_msg_id:
            break
        await second_message.reply(
            "❌ <b>Invalid message.</b>\n\nMake sure you forward from the "
            "DB Channel or paste a valid post link.",
            quote=True
        )

    # ── Build link ─────────────────────────────────────────────────────────
    count  = abs(s_msg_id - f_msg_id) + 1
    string = f"get-{f_msg_id * abs(CHANNEL_ID)}-{s_msg_id * abs(CHANNEL_ID)}"
    base64_string = await encode(string)
    link   = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")
    ]])

    await second_message.reply_text(
        f"✅ <b>Batch link created!</b>\n\n"
        f"📦 <b>Posts in link:</b> <code>{count}</code>\n\n"
        f"🔗 {link}",
        quote=True,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /genlink  — link for a single post
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    while True:
        try:
            channel_message = await client.ask(
                text=(
                    "📌 <b>Single Link Generator</b>\n\n"
                    "Forward a message from the DB Channel (with quotes)\n"
                    "or send its post link.\n\n"
                    "<i>Timeout: 60s</i>"
                ),
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except asyncio.TimeoutError:
            await message.reply("⏰ Timed out. Use /genlink to try again.")
            return
        except Exception:
            return

        msg_id = await get_message_id(client, channel_message)
        if msg_id:
            break
        await channel_message.reply(
            "❌ <b>Invalid message.</b>\n\nMake sure you forward from the "
            "DB Channel or paste a valid post link.",
            quote=True
        )

    base64_string = await encode(f"get-{msg_id * abs(CHANNEL_ID)}")
    link          = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")
    ]])

    await channel_message.reply_text(
        f"✅ <b>Link generated!</b>\n\n🔗 {link}",
        quote=True,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
