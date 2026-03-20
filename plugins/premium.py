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

    from database.database import get_payment_info, get_payment_qr, get_setting

    if info:
        expiry    = info['expiry']
        granted   = info.get('granted', expiry)
        days_left = (expiry - datetime.utcnow()).days
        total     = 30
        filled    = min(int((days_left / total) * 10), 10)
        bar       = "█" * filled + "░" * (10 - filled)

        text = (
            f"╔══════════════════════╗\n"
            f"       💎  <b>PREMIUM STATUS</b>\n"
            f"╚══════════════════════╝\n\n"
            f"✅ <b>Status:</b> Active\n"
            f"📅 <b>Granted:</b> {granted.strftime('%d %b %Y')}\n"
            f"⏳ <b>Expires:</b> {expiry.strftime('%d %b %Y')}\n"
            f"📆 <b>Days Left:</b> <b>{days_left}</b>\n\n"
            f"[{bar}] {days_left}d\n\n"
            f"🎁 <b>Your Perks:</b>\n"
            f"  ♾️ Unlimited downloads\n"
            f"  🔓 Skip force subscribe\n"
            f"  🗂 Files never deleted\n"
            f"  ⚡ Priority delivery"
        )
        await message.reply(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔒 Close", callback_data="close")
            ]])
        )
    else:
        payment_info = await get_payment_info()
        qr_file_id   = await get_payment_qr()
        price        = await get_setting('premium_price') or 'Not set'
        days         = await get_setting('premium_duration') or 30
        upi          = payment_info.get('upi', 'Not set')
        bank         = payment_info.get('bank', 'Not set')
        note         = payment_info.get('note', 'Send screenshot after payment')

        text = (
            f"💎 <b>GET PREMIUM</b>\n"
            f"💰 <b>Price: ₹{price}</b> for {days} days\n\n"
            f"🚀 <b>Premium Benefits:</b>\n"
            f"  ♾️ Unlimited daily downloads\n"
            f"  🔒 Bypass force subscribe\n"
            f"  🗂 Files never auto-deleted\n"
            f"  ⚡ Priority file delivery\n"
            f"  🔔 Expiry reminders\n\n"
            f"💳 <b>Payment Details:</b>\n"
            f"  📱 UPI: <code>{upi}</code>\n\n"
            f"<b>How to subscribe:</b>\n"
            f"1️⃣ Scan QR or use payment details above\n"
            f"2️⃣ Tap ✅ <b>I've Paid</b> below\n"
            f"3️⃣ Send your payment screenshot to admin\n"
            f"4️⃣ Admin activates your premium! ✨"
        )

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ I've Paid", callback_data="ive_paid")],
            [InlineKeyboardButton("💬 Contact Admin", callback_data="open_support")],
            [InlineKeyboardButton("🔒 Close", callback_data="close")]
        ])

        # Send text first, then QR separately if available
        await message.reply(text, reply_markup=markup, quote=True)
        if qr_file_id:
            try:
                await message.reply_photo(
                    photo=qr_file_id,
                    caption="📱 Scan to pay",
                    quote=True
                )
            except Exception:
                pass


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
