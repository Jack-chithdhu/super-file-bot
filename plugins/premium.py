#(©)CodeXBotz - Enhanced by Claude
# Premium Subscription System

import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot import Bot
from config import ADMINS, OWNER_ID, PREMIUM_DURATION_DAYS
from database.database import (add_premium, remove_premium, is_premium,
                                get_premium_info, list_premium_users)


# ─────────────────────────────────────────────────────────────────────────────
#  /premium  — user checks own status
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('premium') & filters.private)
async def premium_status(client: Client, message: Message):
    user_id = message.from_user.id
    info    = await get_premium_info(user_id)

    if info:
        expiry   = info['expiry']
        granted  = info.get('granted', expiry)
        days_left = (expiry - datetime.utcnow()).days
        await message.reply(
            f"💎 <b>Premium Status</b>\n\n"
            f"✅ <b>Active</b>\n"
            f"📅 Granted: <code>{granted.strftime('%Y-%m-%d')}</code>\n"
            f"⏳ Expires: <code>{expiry.strftime('%Y-%m-%d')}</code>\n"
            f"📆 Days left: <b>{days_left}</b>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔒 Close", callback_data="close")
            ]])
        )
    else:
        await message.reply(
            "💎 <b>Premium Status</b>\n\n"
            "❌ You do not have a premium subscription.\n\n"
            "Contact the admin to get premium access and enjoy:\n"
            "• 🚀 Priority file delivery\n"
            "• 🔓 Access to exclusive content\n"
            "• ⚡ Faster response times",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔒 Close", callback_data="close")
            ]])
        )


# ─────────────────────────────────────────────────────────────────────────────
#  /addpremium <user_id> [days]  — admin command
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('addpremium') & filters.private & filters.user(ADMINS))
async def add_premium_user(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply(
            "ℹ️ <b>Usage:</b>\n<code>/addpremium &lt;user_id&gt; [days]</code>\n\n"
            f"Default duration: <b>{PREMIUM_DURATION_DAYS} days</b>"
        )
        return

    try:
        target_id = int(args[0])
        days      = int(args[1]) if len(args) > 1 else PREMIUM_DURATION_DAYS
    except ValueError:
        await message.reply("❌ Invalid user_id or days. Both must be integers.")
        return

    expiry = datetime.utcnow() + timedelta(days=days)
    await add_premium(target_id, expiry)

    await message.reply(
        f"✅ <b>Premium granted!</b>\n\n"
        f"👤 User ID: <code>{target_id}</code>\n"
        f"📆 Duration: <b>{days} days</b>\n"
        f"⏳ Expires: <code>{expiry.strftime('%Y-%m-%d')}</code>"
    )

    # Notify the user if possible
    try:
        await client.send_message(
            chat_id=target_id,
            text=(
                f"🎉 <b>You have been granted Premium!</b>\n\n"
                f"📆 Duration: <b>{days} days</b>\n"
                f"⏳ Expires: <code>{expiry.strftime('%Y-%m-%d')}</code>\n\n"
                f"Enjoy your premium access! 💎"
            )
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  /removepremium <user_id>  — admin command
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('removepremium') & filters.private & filters.user(ADMINS))
async def remove_premium_user(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/removepremium &lt;user_id&gt;</code>")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.reply("❌ Invalid user_id.")
        return

    await remove_premium(target_id)
    await message.reply(f"✅ Premium removed for user <code>{target_id}</code>.")

    try:
        await client.send_message(
            chat_id=target_id,
            text="ℹ️ Your premium subscription has been removed by an admin."
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  /listpremium  — admin command
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('listpremium') & filters.private & filters.user(ADMINS))
async def list_premium(client: Client, message: Message):
    users = await list_premium_users()
    if not users:
        await message.reply("📋 No active premium users.")
        return

    lines = ["💎 <b>Active Premium Users</b>\n"]
    for u in users:
        days_left = (u['expiry'] - datetime.utcnow()).days
        lines.append(
            f"• <code>{u['_id']}</code> — expires <code>{u['expiry'].strftime('%Y-%m-%d')}</code> "
            f"({days_left}d left)"
        )
    await message.reply("\n".join(lines))
