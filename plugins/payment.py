#(©)CodeXBotz - Enhanced by Claude
# Premium Payment Flow

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot import Bot
from config import ADMINS, OWNER_ID, PREMIUM_DURATION_DAYS
from database.database import (
    get_payment_info, set_payment_info, get_premium_info, is_premium,
    create_premium_request, get_premium_request, close_premium_request,
    open_chat_session, get_chat_session, get_bot_admins
)

# ─────────────────────────────────────────────────────────────────────────────
#  /setpayment — owner sets payment details
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('setpayment') & filters.private & filters.user(OWNER_ID))
async def set_payment_cmd(client: Client, message: Message):
    args = message.command[1:]

    if not args:
        current = await get_payment_info()
        lines   = [
            "╔══════════════════════╗\n"
            "   💳  <b>PAYMENT SETTINGS</b>\n"
            "╚══════════════════════╝\n"
        ]
        if current:
            for key, val in current.items():
                lines.append(f"<b>{key}:</b> <code>{val}</code>")
        else:
            lines.append("❌ No payment info set yet.")

        lines.append(
            "\n<b>How to set:</b>\n"
            "<code>/setpayment upi yourname@upi</code>\n"
            "<code>/setpayment bank \"Acc: 123456 | IFSC: SBIN001\"</code>\n"
            "<code>/setpayment note \"Contact admin after payment\"</code>\n"
            "<code>/setpayment clear</code> — remove all payment info"
        )
        await message.reply("\n".join(lines))
        return

    key = args[0].lower()

    if key == "clear":
        await set_payment_info({})
        await message.reply("✅ Payment info cleared.")
        return

    if len(args) < 2:
        await message.reply("ℹ️ Usage: <code>/setpayment &lt;key&gt; &lt;value&gt;</code>")
        return

    value   = " ".join(args[1:])
    current = await get_payment_info()
    current[key] = value
    await set_payment_info(current)

    await message.reply(
        f"✅ Payment info updated!\n\n"
        f"<b>{key}:</b> <code>{value}</code>"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /premium — user checks status or sees payment info
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('premium') & filters.private)
async def premium_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    info    = await get_premium_info(user_id)

    if info:
        from datetime import datetime
        days_left  = (info['expiry'] - datetime.utcnow()).days
        expiry_str = info['expiry'].strftime('%d %b %Y')
        filled     = min(int((days_left / 30) * 10), 10)
        bar        = "█" * filled + "░" * (10 - filled)

        await message.reply(
            f"╔══════════════════════╗\n"
            f"       💎  <b>PREMIUM ACTIVE</b>\n"
            f"╚══════════════════════╝\n\n"
            f"✅ <b>Status:</b> Active\n"
            f"⏳ <b>Expires:</b> {expiry_str}\n"
            f"📆 <b>Days Left:</b> <b>{days_left}</b>\n\n"
            f"[{bar}] {days_left}d\n\n"
            f"🎁 <b>Your Perks:</b>\n"
            f"  ♾️ Unlimited downloads\n"
            f"  🔓 Skip force subscribe\n"
            f"  🗂 Files never auto-deleted\n"
            f"  ⚡ Priority delivery",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔒 Close", callback_data="close")
            ]])
        )
    else:
        await _show_premium_purchase_with_qr(client, message)


async def _show_premium_purchase(client, message):
    """Show payment details and buy button."""
    payment = await get_payment_info()

    text = (
        "╔══════════════════════╗\n"
        "       💎  <b>GET PREMIUM</b>\n"
        "╚══════════════════════╝\n\n"
        "🚀 <b>Premium Benefits:</b>\n"
        "  ♾️ Unlimited daily downloads\n"
        "  🔓 Bypass force subscribe\n"
        "  🗂 Files never auto-deleted\n"
        "  ⚡ Priority file delivery\n"
        "  🔔 Expiry reminders\n\n"
    )

    if payment:
        text += "💳 <b>Payment Details:</b>\n"
        for key, val in payment.items():
            if key != 'note':
                text += f"  <b>{key.upper()}:</b> <code>{val}</code>\n"
        if 'note' in payment:
            text += f"\n📝 <i>{payment['note']}</i>\n"
        text += (
            "\n<b>How to subscribe:</b>\n"
            "1️⃣ Make the payment using details above\n"
            "2️⃣ Tap <b>✅ I've Paid</b> below\n"
            "3️⃣ Send your payment screenshot to admin\n"
            "4️⃣ Admin will activate your premium! ✨"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ I've Paid", callback_data="premium_paid")],
            [InlineKeyboardButton("💬 Contact Admin", callback_data="open_support")],
            [InlineKeyboardButton("🔒 Close", callback_data="close")],
        ])
    else:
        text += (
            "💬 <b>To subscribe:</b>\n"
            "Contact the admin directly to get premium access."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Contact Admin", callback_data="open_support")],
            [InlineKeyboardButton("🔒 Close", callback_data="close")],
        ])

    await message.reply(text, reply_markup=markup)


# ─────────────────────────────────────────────────────────────────────────────
#  Callback: user taps "I've Paid"
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^premium_paid$"))
async def premium_paid_callback(client: Client, query: CallbackQuery):
    user_id    = query.from_user.id
    first_name = query.from_user.first_name
    username   = query.from_user.username or "N/A"

    # Check if already premium
    if await is_premium(user_id):
        await query.answer("💎 You already have an active premium!", show_alert=True)
        return

    # Check if already has pending request
    existing = await get_premium_request(user_id)
    if existing:
        await query.answer(
            "⏳ Your payment is already under review! Admin will activate soon.",
            show_alert=True
        )
        return

    # Open support session for screenshot
    session = await get_chat_session(user_id)
    if not session:
        await open_chat_session(user_id)

    # Create premium request
    req_id = await create_premium_request(user_id, username, first_name)

    await query.message.edit_text(
        f"╔══════════════════════╗\n"
        f"   📤  <b>PAYMENT SUBMITTED</b>\n"
        f"╚══════════════════════╝\n\n"
        f"✅ Your payment request has been sent!\n\n"
        f"📸 <b>Next step:</b>\n"
        f"Please send your <b>payment screenshot</b> in this chat right now.\n"
        f"Admin will review and activate your premium.\n\n"
        f"🆔 <b>Request ID:</b> <code>{req_id}</code>\n\n"
        f"<i>⏰ Please send the screenshot now 👇</i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel Request", callback_data="cancel_premium_req")
        ]])
    )
    await query.answer("Please send your payment screenshot!")

    # Notify all admins
    all_admins = list(set(ADMINS + await get_bot_admins()))
    for admin_id in all_admins:
        try:
            await client.send_message(
                chat_id=admin_id,
                text=(
                    f"💰 <b>New Premium Payment Request</b>\n\n"
                    f"🆔 Request ID: <code>{req_id}</code>\n"
                    f"👤 User: <a href='tg://user?id={user_id}'>{first_name}</a> "
                    f"(<code>{user_id}</code>)\n"
                    f"📛 Username: @{username}\n\n"
                    f"📸 User will send payment screenshot via support chat.\n"
                    f"Use /addpremium {user_id} to activate after verification."
                ),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("💎 Activate Premium", callback_data=f"quick_premium_{user_id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_premium_{user_id}"),
                    ],
                    [
                        InlineKeyboardButton(
                            f"💬 Chat with {first_name}",
                            callback_data=f"admin_chat_{user_id}"
                        )
                    ]
                ])
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  Callback: cancel premium request
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cancel_premium_req$"))
async def cancel_premium_req(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    await close_premium_request(user_id)
    await query.message.edit_text(
        "❌ <b>Premium request cancelled.</b>\n\n"
        "Use /premium if you'd like to subscribe again."
    )
    await query.answer("Request cancelled.")


# ─────────────────────────────────────────────────────────────────────────────
#  Callback: admin quick-activates premium from notification
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^quick_premium_(\d+)$"))
async def quick_premium_callback(client: Client, query: CallbackQuery):
    all_admins = list(set(ADMINS + await get_bot_admins()))
    if query.from_user.id not in all_admins:
        await query.answer("❌ Not an admin.", show_alert=True)
        return

    user_id = int(query.data.split("_")[2])

    from datetime import datetime, timedelta
    from database.database import add_premium, remove_premium
    expiry = datetime.utcnow() + timedelta(days=PREMIUM_DURATION_DAYS)
    await add_premium(user_id, expiry)
    await close_premium_request(user_id)

    await query.message.edit_reply_markup(None)
    await query.message.reply(
        f"✅ Premium activated for <code>{user_id}</code> "
        f"({PREMIUM_DURATION_DAYS} days) by {query.from_user.mention}."
    )
    await query.answer("✅ Premium activated!")

    # Notify user
    try:
        await client.send_message(
            chat_id=user_id,
            text=(
                f"╔══════════════════════╗\n"
                f"   🎉  <b>PREMIUM ACTIVATED!</b>\n"
                f"╚══════════════════════╝\n\n"
                f"✅ Your payment has been verified!\n\n"
                f"💎 <b>Premium is now active</b>\n"
                f"📆 Duration: <b>{PREMIUM_DURATION_DAYS} days</b>\n"
                f"⏳ Expires: <b>{expiry.strftime('%d %b %Y')}</b>\n\n"
                f"🎁 Enjoy unlimited downloads & all premium perks!\n"
                f"Thank you for subscribing! 🙏"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💎 View Status", callback_data="premium_info")
            ]])
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  Callback: admin rejects premium request
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^reject_premium_(\d+)$"))
async def reject_premium_callback(client: Client, query: CallbackQuery):
    all_admins = list(set(ADMINS + await get_bot_admins()))
    if query.from_user.id not in all_admins:
        await query.answer("❌ Not an admin.", show_alert=True)
        return

    user_id = int(query.data.split("_")[2])
    await close_premium_request(user_id)
    await query.message.edit_reply_markup(None)
    await query.message.reply(
        f"❌ Premium request for <code>{user_id}</code> rejected by {query.from_user.mention}."
    )
    await query.answer("❌ Rejected.")

    try:
        await client.send_message(
            chat_id=user_id,
            text=(
                f"╔══════════════════════╗\n"
                f"   ❌  <b>PAYMENT REJECTED</b>\n"
                f"╚══════════════════════╝\n\n"
                f"Unfortunately your payment could not be verified.\n\n"
                f"Please contact admin via /support if you believe this is a mistake."
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💬 Contact Admin", callback_data="open_support")
            ]])
        )
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
#  /setqr — owner sets payment QR image
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('setqr') & filters.private & filters.user(OWNER_ID))
async def set_qr_cmd(client: Client, message: Message):
    from database.database import set_payment_qr, clear_payment_qr, get_payment_qr

    # /setqr clear — remove QR
    if len(message.command) > 1 and message.command[1].lower() == 'clear':
        await clear_payment_qr()
        await message.reply("✅ Payment QR image removed.")
        return

    # Must reply to a photo
    if not message.reply_to_message or not message.reply_to_message.photo:
        current_qr = await get_payment_qr()
        await message.reply(
            "╔══════════════════════╗\n"
            "     🖼  <b>PAYMENT QR SETUP</b>\n"
            "╚══════════════════════╝\n\n"
            f"{'✅ QR image is set.' if current_qr else '❌ No QR image set yet.'}\n\n"
            "<b>To set a QR image:</b>\n"
            "1️⃣ Send your QR code image in this chat\n"
            "2️⃣ Reply to that image with <code>/setqr</code>\n\n"
            "<b>To remove:</b>\n"
            "<code>/setqr clear</code>"
        )
        return

    file_id = message.reply_to_message.photo.file_id
    await set_payment_qr(file_id)
    await message.reply(
        "✅ <b>Payment QR image saved!</b>\n\n"
        "It will now appear on the premium payment screen for users.\n"
        "Use <code>/setqr clear</code> to remove it."
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Override _show_premium_purchase to include QR image
# ─────────────────────────────────────────────────────────────────────────────
async def _show_premium_purchase_with_qr(client, message_or_query):
    """Shows payment screen with QR if set."""
    from database.database import get_payment_qr
    payment  = await get_payment_info()
    qr_image = await get_payment_qr()

    text = (
        "╔══════════════════════╗\n"
        "       💎  <b>GET PREMIUM</b>\n"
        "╚══════════════════════╝\n\n"
        "🚀 <b>Premium Benefits:</b>\n"
        "  ♾️ Unlimited daily downloads\n"
        "  🔓 Bypass force subscribe\n"
        "  🗂 Files never auto-deleted\n"
        "  ⚡ Priority file delivery\n"
        "  🔔 Expiry reminders\n\n"
    )

    if payment:
        text += "💳 <b>Payment Details:</b>\n"
        for key, val in payment.items():
            if key != 'note':
                text += f"  <b>{key.upper()}:</b> <code>{val}</code>\n"
        if 'note' in payment:
            text += f"\n📝 <i>{payment['note']}</i>\n"
        text += (
            "\n<b>How to subscribe:</b>\n"
            "1️⃣ Scan QR or use payment details above\n"
            "2️⃣ Tap <b>✅ I've Paid</b> below\n"
            "3️⃣ Send your payment screenshot to admin\n"
            "4️⃣ Admin activates your premium! ✨"
        ) if qr_image else (
            "\n<b>How to subscribe:</b>\n"
            "1️⃣ Make payment using details above\n"
            "2️⃣ Tap <b>✅ I've Paid</b> below\n"
            "3️⃣ Send your payment screenshot to admin\n"
            "4️⃣ Admin activates your premium! ✨"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ I've Paid", callback_data="premium_paid")],
            [InlineKeyboardButton("💬 Contact Admin", callback_data="open_support")],
            [InlineKeyboardButton("🔒 Close", callback_data="close")],
        ])
    else:
        text += (
            "💬 <b>To subscribe:</b>\n"
            "Contact the admin directly to get premium access."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Contact Admin", callback_data="open_support")],
            [InlineKeyboardButton("🔒 Close", callback_data="close")],
        ])

    # Determine if it's a Message or CallbackQuery
    is_callback = hasattr(message_or_query, 'message')
    chat_id     = message_or_query.from_user.id if is_callback else message_or_query.chat.id

    if qr_image:
        await client.send_photo(
            chat_id=chat_id,
            photo=qr_image,
            caption=text,
            reply_markup=markup
        )
        if is_callback:
            try:
                await message_or_query.message.delete()
            except Exception:
                pass
    else:
        if is_callback:
            await message_or_query.message.edit_text(text, reply_markup=markup)
        else:
            await message_or_query.reply(text, reply_markup=markup)
