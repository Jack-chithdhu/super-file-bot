#(©)CodeXBotz - Enhanced by Claude
# Callback Query Handler — Full UI

from pyrogram import __version__, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime

from bot import Bot
from config import OWNER_ID, ADMINS, START_MSG

# ═════════════════════════════════════════════════════════════════════════════
#  MAIN CALLBACK HANDLER
# ═════════════════════════════════════════════════════════════════════════════
@Bot.on_callback_query(filters.regex(r"^(about|premium_info|buy_premium|ive_paid|back_home|close|help_menu|user_profile|my_requests|close_my_chat|open_settings)$"))
async def cb_handler(client: Bot, query: CallbackQuery):
    data    = query.data
    user_id = query.from_user.id

    # ── About ─────────────────────────────────────────────────────────────
    if data == "about":
        await query.message.edit_text(
            text=(
                f"╔══════════════════════╗\n"
                f"       ℹ️  <b>ABOUT BOT</b>\n"
                f"╚══════════════════════╝\n\n"
                f"🤖 <b>File Sharing Bot</b> — Enhanced\n\n"
                f"👨‍💻 <b>Creator:</b> <a href='tg://user?id={OWNER_ID}'>Owner</a>\n"
                f"🐍 <b>Language:</b> Python 3\n"
                f"📚 <b>Library:</b> Pyrogram {__version__}\n"
                f"🗄 <b>Database:</b> MongoDB\n\n"
                f"✨ <b>Features:</b>\n"
                f"  • 🔗 File sharing via special links\n"
                f"  • 💎 Premium subscription system\n"
                f"  • 🎬 Movie & Anime requests\n"
                f"  • 💬 Live admin support chat\n"
                f"  • 🚫 Ban/unban system\n"
                f"  • 📊 File statistics\n\n"
                f"<i>Built with ❤️ for you</i>"
            ),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_home")],
                [InlineKeyboardButton("🔒 Close", callback_data="close")]
            ])
        )

    # ── Premium Info ──────────────────────────────────────────────────────
    elif data == "premium_info":
        from database.database import get_premium_info
        info = await get_premium_info(user_id)

        if info:
            days_left   = (info['expiry'] - datetime.utcnow()).days
            expiry_str  = info['expiry'].strftime('%d %b %Y')
            granted_str = info.get('granted', info['expiry']).strftime('%d %b %Y')

            # Progress bar
            total = 30
            filled = min(int((days_left / total) * 10), 10)
            bar = "█" * filled + "░" * (10 - filled)

            text = (
                f"╔══════════════════════╗\n"
                f"       💎  <b>PREMIUM STATUS</b>\n"
                f"╚══════════════════════╝\n\n"
                f"✅ <b>Status:</b> Active\n"
                f"📅 <b>Granted:</b> {granted_str}\n"
                f"⏳ <b>Expires:</b> {expiry_str}\n"
                f"📆 <b>Days Left:</b> <b>{days_left}</b>\n\n"
                f"[{bar}] {days_left}d\n\n"
                f"🎁 <b>Your Perks:</b>\n"
                f"  ♾️ Unlimited downloads\n"
                f"  🔓 Skip force subscribe\n"
                f"  🗂 Files never auto-deleted\n"
                f"  ⚡ Priority delivery"
            )
        else:
            text = (
                f"╔══════════════════════╗\n"
                f"       💎  <b>GO PREMIUM</b>\n"
                f"╚══════════════════════╝\n\n"
                f"❌ <b>No active subscription</b>\n\n"
                f"<b>Free vs Premium:</b>\n\n"
                f"{'Feature':<20} {'Free':^8} {'Premium':^8}\n"
                f"{'─'*36}\n"
                f"{'Daily downloads':<20} {'20/day':^8} {'∞':^8}\n"
                f"{'Auto-delete':<20} {'✅':^8} {'❌':^8}\n"
                f"{'Force subscribe':<20} {'✅':^8} {'❌':^8}\n"
                f"{'Expiry reminders':<20} {'❌':^8} {'✅':^8}\n\n"
                f"💬 Contact admin to subscribe!"
            )

        # Add Buy Premium button if user is not premium
        if info:
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_home")],
                [InlineKeyboardButton("🔒 Close", callback_data="close")]
            ])
        else:
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_home")],
                [InlineKeyboardButton("🔒 Close", callback_data="close")]
            ])

        await query.message.edit_text(text=text, reply_markup=markup)

    # ── I've Paid ─────────────────────────────────────────────────────────
    elif data == "ive_paid":
        from database.database import create_premium_request
        req_id = await create_premium_request(
            user_id=user_id,
            username=query.from_user.username or "",
            first_name=query.from_user.first_name
        )
        # Notify all admins
        from config import ADMINS as _ADMINS
        from database.database import get_bot_admins
        all_admins = list(set(_ADMINS + await get_bot_admins()))
        for admin_id in all_admins:
            try:
                await client.send_message(
                    chat_id=admin_id,
                    text=(
                        f"💰 <b>New Payment Claim!</b>\n\n"
                        f"👤 <a href='tg://user?id={user_id}'>{query.from_user.first_name}</a> "
                        f"(<code>{user_id}</code>)\n"
                        f"🆔 Request ID: <code>{req_id}</code>\n\n"
                        f"Ask them to send payment screenshot and verify before activating.\n\n"
                        f"To activate: <code>/addpremium {user_id} 30</code>"
                    )
                )
            except Exception:
                pass
        await query.message.edit_text(
            "✅ <b>Payment claim received!</b>\n\n"
            "Please send your payment screenshot to the admin.\n\n"
            "Admin will verify and activate your premium shortly! 💎",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Send Screenshot", callback_data="open_support")],
                [InlineKeyboardButton("🔒 Close", callback_data="close")]
            ])
        )

    # ── Buy Premium ───────────────────────────────────────────────────────
    elif data == "buy_premium":
        from database.database import get_payment_info, get_payment_qr
        payment_info = await get_payment_info()
        qr_file_id   = await get_payment_qr()

        from database.database import get_setting as _gs
        upi    = payment_info.get('upi', 'Not set')
        bank   = payment_info.get('bank', 'Not set')
        note   = payment_info.get('note', 'Send screenshot after payment')
        price  = await _gs('premium_price') or 'Not set'
        days   = await _gs('premium_duration_days') or 30

        text = (
            f"╔══════════════════════╗\n"
            f"       💎  <b>GET PREMIUM</b>\n"
            f"╚══════════════════════╝\n\n"
            f"🚀 <b>Premium Benefits:</b>\n"
            f"  ♾️ Unlimited daily downloads\n"
            f"  🔒 Bypass force subscribe\n"
            f"  🗂 Files never auto-deleted\n"
            f"  ⚡ Priority file delivery\n"
            f"  🔔 Expiry reminders\n\n"
            f"💰 <b>Price:</b> ₹{price} for {days} days\n\n"
            f"💳 <b>Payment Details:</b>\n"
            f"  UPI: <code>{upi}</code>\n"
            f"  🏦 Bank: {bank}\n\n"
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

        if qr_file_id:
            try:
                # Edit message media to show QR without sending new message
                from pyrogram.types import InputMediaPhoto
                await query.message.edit_media(
                    InputMediaPhoto(media=qr_file_id, caption=text),
                    reply_markup=markup
                )
            except Exception:
                # Fallback — just show text with payment details
                await query.message.edit_text(text=text, reply_markup=markup)
        else:
            await query.message.edit_text(text=text, reply_markup=markup)

    # ── Help Menu ─────────────────────────────────────────────────────────
    elif data == "help_menu":
        text = (
            f"╔══════════════════════╗\n"
            f"       📖  <b>HELP MENU</b>\n"
            f"╚══════════════════════╝\n\n"
            f"<b>📂 File Access</b>\n"
            f"  • Get a file link from admin\n"
            f"  • Tap the link to receive the file\n\n"
            f"<b>🎬 Requests</b>\n"
            f"  /request — Request a movie or anime\n"
            f"  /mystatus — Track your request\n\n"
            f"<b>💎 Premium</b>\n"
            f"  /premium — Check your status\n\n"
            f"<b>💬 Support</b>\n"
            f"  /support — Chat with admin\n"
            f"  /closechat — End support session\n\n"
            f"<b>👤 Profile</b>\n"
            f"  /profile — View your stats\n\n"
            f"<i>Tap a button below to get started!</i>"
        )
        await query.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎬 Request", callback_data="request_start"),
                    InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
                ],
                [
                    InlineKeyboardButton("💬 Support", callback_data="open_support"),
                    InlineKeyboardButton("👤 Profile", callback_data="user_profile"),
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="back_home")],
            ])
        )

    # ── User Profile ──────────────────────────────────────────────────────
    elif data == "user_profile":
        from database.database import get_daily_downloads, is_premium, get_setting, get_user_requests
        from config import FREE_DAILY_LIMIT

        premium       = await is_premium(user_id)
        daily_used    = await get_daily_downloads(user_id)
        premium_mode  = await get_setting('premium_mode')
        daily_limit   = await get_setting('free_daily_limit') or FREE_DAILY_LIMIT
        requests      = await get_user_requests(user_id, limit=1)
        last_req      = requests[0] if requests else None

        status_badge  = "💎 Premium" if premium else "🆓 Free"

        if premium or not premium_mode:
            limit_text = "♾️ Unlimited"
            bar        = "██████████"
        else:
            filled     = min(int((daily_used / daily_limit) * 10), 10)
            bar        = "█" * filled + "░" * (10 - filled)
            limit_text = f"{daily_used}/{daily_limit}"

        text = (
            f"╔══════════════════════╗\n"
            f"       👤  <b>YOUR PROFILE</b>\n"
            f"╚══════════════════════╝\n\n"
            f"👋 <b>{query.from_user.first_name}</b>\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"🏅 Status: {status_badge}\n\n"
            f"📥 <b>Today's Downloads:</b>\n"
            f"  [{bar}] {limit_text}\n\n"
        )

        if last_req:
            status_emoji = {'pending': '🕐', 'fulfilled': '✅', 'declined': '❌'}
            text += (
                f"🎬 <b>Last Request:</b>\n"
                f"  {status_emoji.get(last_req['status'], '❓')} "
                f"{last_req['title']} — {last_req['status'].capitalize()}\n\n"
            )

        text += f"<i>Use /request to request content!</i>"

        await query.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎬 My Requests", callback_data="my_requests"),
                    InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="back_home")],
            ])
        )

    # ── My Requests (from profile) ────────────────────────────────────────
    elif data == "my_requests":
        from database.database import get_user_requests
        requests = await get_user_requests(user_id, limit=5)
        status_emoji = {'pending': '🕐', 'fulfilled': '✅', 'declined': '❌'}

        if not requests:
            text = (
                "📋 <b>Your Requests</b>\n\n"
                "You haven't made any requests yet.\n\n"
                "Use /request to submit one!"
            )
        else:
            lines = ["📋 <b>Your Recent Requests</b>\n"]
            for r in requests:
                emoji = status_emoji.get(r['status'], '❓')
                lines.append(
                    f"{emoji} <code>{r['request_id']}</code> — <b>{r['title']}</b>\n"
                    f"   [{r['type'].capitalize()}] {r['status'].capitalize()}"
                )
                if r.get('response') and r['status'] != 'pending':
                    lines.append(f"   💬 <i>{r['response']}</i>")
                lines.append("")
            text = "\n".join(lines)

        await query.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="user_profile")],
            ])
        )

    # ── Back Home ─────────────────────────────────────────────────────────
    elif data == "back_home":
        from database.database import is_premium
        user_is_premium = await is_premium(user_id)
        fmt = dict(
            first=query.from_user.first_name,
            last=query.from_user.last_name or "",
            username=None if not query.from_user.username else "@" + query.from_user.username,
            mention=query.from_user.mention,
            id=user_id,
        )
        premium_btn = (
            InlineKeyboardButton("💎 Premium ✅", callback_data="premium_info")
            if user_is_premium
            else InlineKeyboardButton("💎 Get Premium", callback_data="premium_info")
        )
        await query.message.edit_text(
            text=START_MSG.format(**fmt),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ℹ️ About", callback_data="about"), premium_btn],
                [
                    InlineKeyboardButton("📖 Help", callback_data="help_menu"),
                    InlineKeyboardButton("👤 Profile", callback_data="user_profile"),
                ],
                [
                    InlineKeyboardButton("🎬 Request", callback_data="request_start"),
                    InlineKeyboardButton("💬 Support", callback_data="open_support"),
                ],
                [InlineKeyboardButton("🔒 Close", callback_data="close")]
            ])
        )

    # ── Open Settings ─────────────────────────────────────────────────────────
    elif data == "open_settings":
        from config import OWNER_ID
        if user_id != OWNER_ID and user_id not in ADMINS:
            await query.answer("❌ Only admins can access settings.", show_alert=True)
            return
        await query.answer()
        from plugins.settings import show_main_settings
        await show_main_settings(client, query.message.chat.id)

    # ── Close My Chat (user ends support session) ────────────────────────────
    elif data == "close_my_chat":
        from database.database import close_chat_session
        await close_chat_session(user_id)
        await query.message.edit_text(
            "✅ <b>Support session closed.</b>\n\n"
            "Thanks for reaching out! Use /support anytime to chat again."
        )
        await query.answer("Session closed.")

    # ── Close ─────────────────────────────────────────────────────────────
    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except Exception:
            pass


# ═════════════════════════════════════════════════════════════════════════════
#  OPEN SUPPORT CALLBACK
# ═════════════════════════════════════════════════════════════════════════════
@Bot.on_callback_query(filters.regex(r"^open_support$"))
async def open_support_callback(client, query):
    from database.database import open_chat_session, get_chat_session, get_bot_admins, get_setting
    from plugins.support_chat import support_queue
    user_id   = query.from_user.id
    first_name = query.from_user.first_name

    # Check support enabled
    support_on = await get_setting('support_enabled')
    if support_on is None:
        support_on = True
    if not support_on:
        custom_msg = await get_setting('support_off_message') or "Support is currently unavailable."
        await query.answer(custom_msg, show_alert=True)
        return

    # Check existing session
    session = await get_chat_session(user_id)
    if session:
        await query.answer("You already have an active support session!", show_alert=True)
        return

    # Check queue
    if user_id in support_queue:
        await query.answer("You are already in the queue!", show_alert=True)
        return

    await open_chat_session(user_id)
    await query.message.edit_text(
        "💬 <b>Support Request Sent!</b>\n\n"
        "An admin will respond shortly.\n"
        "Just type your message below.\n\n"
        "Use /closechat to cancel.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel Request", callback_data="close_my_chat")
        ]])
    )

    # Notify admins with Accept/Dismiss buttons
    all_admins = list(set(ADMINS + await get_bot_admins()))
    notify_text = (
        f"🔔 <b>New Support Request</b>\n\n"
        f"👤 <a href='tg://user?id={user_id}'>{first_name}</a> (<code>{user_id}</code>)\n\n"
        f"Tap below to accept or dismiss."
    )
    notif_ids = {}
    for admin_id in all_admins:
        try:
            sent = await client.send_message(
                chat_id=admin_id,
                text=notify_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💬 Accept",  callback_data=f"admin_chat_{user_id}"),
                    InlineKeyboardButton("❌ Dismiss", callback_data=f"support_dismiss_{user_id}"),
                ]])
            )
            notif_ids[admin_id] = sent.id
        except Exception:
            pass

    support_queue[user_id] = {'name': first_name, 'notif_msg_ids': notif_ids}
    await query.answer("Support request sent!")


# ═════════════════════════════════════════════════════════════════════════════
#  REQUEST START CALLBACK (inline button flow)
# ═════════════════════════════════════════════════════════════════════════════
@Bot.on_callback_query(filters.regex(r"^request_start$"))
async def request_start_callback(client, query):
    from database.database import get_user_active_request
    user_id  = query.from_user.id
    existing = await get_user_active_request(user_id)

    if existing:
        status_emoji = {'pending': '🕐', 'fulfilled': '✅', 'declined': '❌'}
        await query.answer(
            f"You already have a pending request: {existing['title']}",
            show_alert=True
        )
        return

    await query.message.edit_text(
        "╔══════════════════════╗\n"
        "       🎬  <b>NEW REQUEST</b>\n"
        "╚══════════════════════╝\n\n"
        "What would you like to request?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 Movie", callback_data="req_type_movie"),
                InlineKeyboardButton("🎌 Anime", callback_data="req_type_anime"),
                InlineKeyboardButton("📺 Series", callback_data="req_type_series"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ])
    )


@Bot.on_callback_query(filters.regex(r"^req_type_(movie|anime|series)$"))
async def req_type_callback(client, query):
    req_type = query.data.split("_")[2]
    emoji    = "🎬" if req_type == "movie" else "🎌"

    await query.message.edit_text(
        f"╔══════════════════════╗\n"
        f"    {emoji}  <b>{req_type.upper()} REQUEST</b>\n"
        f"╚══════════════════════╝\n\n"
        f"✏️ <b>Type the title</b> of the {req_type} you want:\n\n"
        f"<i>Just send it as a message below 👇</i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="back_home")
        ]])
    )

    # Store type in client memory for next message
    if not hasattr(client, 'pending_requests'):
        client.pending_requests = {}
    client.pending_requests[query.from_user.id] = {'type': req_type, 'step': 'title'}
    await query.answer()
