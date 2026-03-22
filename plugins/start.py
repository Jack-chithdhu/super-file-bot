#(©)CodeXBotz - Enhanced by Claude

import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import (ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION,
                    DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, START_PIC,
                    AUTO_DELETE_TIME, AUTO_DELETE_MSG, JOIN_REQUEST_ENABLE,
                    FORCE_SUB_CHANNEL, FREE_DAILY_LIMIT, SURVIVAL_MODE)
from helper_func import subscribed, banned_user, decode, get_messages, delete_file
from database.database import (add_user, del_user, full_userbase, present_user,
                                is_banned, get_ban_info, record_file_access,
                                is_premium, get_daily_downloads, get_setting)

WAIT_MSG    = "⏳ <b>Processing...</b>"
REPLY_ERROR = "<code>Reply to a message to broadcast it.</code>"

# ─────────────────────────────────────────────────────────────────────────────
#  /start  (subscribed, not banned)
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('start') & filters.private & subscribed & ~banned_user)
async def start_command(client: Client, message: Message):
    user_id         = message.from_user.id
    user_is_premium = await is_premium(user_id)

    # ── SURVIVAL MODE — only file delivery, skip everything else ───────────
    # Check survival mode from DB (set via /settings) or env
    # Owner and admins always bypass survival mode
    survival_mode_db = await get_setting('survival_mode') or False
    if (SURVIVAL_MODE or survival_mode_db) and user_id not in ADMINS:
        text_parts    = message.text.split()
        base64_payload = text_parts[1].strip() if len(text_parts) > 1 else ""
        if base64_payload:
            # Deliver file directly — no captcha, no limit, no force sub
            try:
                string   = await decode(base64_payload)
                argument = string.split("-")
                if len(argument) == 3:
                    start = int(int(argument[1]) / abs(client.db_channel.id))
                    end   = int(int(argument[2]) / abs(client.db_channel.id))
                    ids   = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
                elif len(argument) == 2:
                    ids = [int(int(argument[1]) / abs(client.db_channel.id))]
                else:
                    ids = []
                if ids:
                    messages = await get_messages(client, list(ids))
                    for msg in messages:
                        caption = ("" if not msg.caption else msg.caption.html)
                        try:
                            await msg.copy(
                                chat_id=user_id, caption=caption,
                                parse_mode=ParseMode.HTML,
                                protect_content=PROTECT_CONTENT
                            )
                            await asyncio.sleep(0.5)
                        except FloodWait as e:
                            await asyncio.sleep(e.value)
                            await msg.copy(chat_id=user_id, caption=caption,
                                parse_mode=ParseMode.HTML, protect_content=PROTECT_CONTENT)
                        except Exception:
                            pass
            except Exception:
                pass
        else:
            await message.reply(
                "⚡ <b>Bot is running in minimal mode.</b>\n\n"
                "Only file links work right now.\n"
                "Other features are temporarily disabled.",
                quote=True
            )
        return

    # ── Captcha check for new users ────────────────────────────────────────
    captcha_enabled = await get_setting('captcha_enabled')
    if captcha_enabled is None:
        captcha_enabled = True
    if captcha_enabled and user_id not in ADMINS:
        from plugins.captcha import send_captcha, captcha_just_passed, verified_users
        from database.database import check_captcha_passed, clear_captcha_passed
        # Check in-memory verified set, just_passed flag, and DB (multi-worker safe)
        already_verified = user_id in verified_users
        just_passed = user_id in captcha_just_passed or await check_captcha_passed(user_id)
        if just_passed:
            captcha_just_passed.discard(user_id)
            await clear_captcha_passed(user_id)
        elif not already_verified:
            # Safely extract the payload after /start (handles /start@BotName too)
            parts = message.text.split()
            original = parts[1].strip() if len(parts) > 1 else ""
            sent = await send_captcha(client, user_id, message.from_user.first_name, original)
            if sent:
                return  # Wait for captcha to be solved

    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception:
            pass

    # Safely extract payload — handles /start and /start@BotName formats
    text_parts = message.text.split()
    base64_payload = text_parts[1].strip() if len(text_parts) > 1 else ""

    if base64_payload:
        # Force sub is already checked by the `subscribed` filter above
        # No need to check again here — just proceed to file delivery

        # ── File delivery ──────────────────────────────────────────────────
        try:
            base64_string = base64_payload
        except Exception:
            return

        # Daily limit check
        premium_mode = await get_setting('premium_mode')
        if premium_mode is None:
            premium_mode = True  # default: enforce premium mode
        if premium_mode and not user_is_premium and user_id not in ADMINS:
            daily_limit = await get_setting('free_daily_limit') or FREE_DAILY_LIMIT
            used        = await get_daily_downloads(user_id)
            if used >= daily_limit:
                await message.reply(
                    f"╔══════════════════════╗\n"
                    f"    🚫  <b>LIMIT REACHED</b>\n"
                    f"╚══════════════════════╝\n\n"
                    f"You've used all <b>{daily_limit}</b> free downloads today.\n\n"
                    f"{'█' * 10} {used}/{daily_limit}\n\n"
                    f"⏰ Resets at midnight UTC\n\n"
                    f"💎 <b>Upgrade to Premium</b> for unlimited downloads!\n"
                    f"Contact the admin to subscribe.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💎 Get Premium", callback_data="premium_info")
                    ]])
                )
                return

        string   = await decode(base64_string)
        argument = string.split("-")

        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end   = int(int(argument[2]) / abs(client.db_channel.id))
            except Exception:
                return
            ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except Exception:
                return
        else:
            return

        temp_msg = await message.reply("⏳ <b>Fetching your files...</b>")
        try:
            messages = await get_messages(client, list(ids))
        except Exception:
            await message.reply_text("❌ Something went wrong. Please try again.")
            return
        await temp_msg.delete()

        for msg_id in ids:
            await record_file_access(str(msg_id), user_id)

        # Auto-delete permanently disabled — files are never deleted
        for msg in messages:
            caption = (
                CUSTOM_CAPTION.format(
                    previouscaption="" if not msg.caption else msg.caption.html,
                    filename=msg.document.file_name if msg.document else ""
                )
                if bool(CUSTOM_CAPTION) and bool(msg.document)
                else ("" if not msg.caption else msg.caption.html)
            )
            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None
            try:
                await msg.copy(
                    chat_id=user_id, caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT
                )
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await msg.copy(
                    chat_id=user_id, caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT
                )
            except Exception:
                pass

        return

    # ── Welcome screen ─────────────────────────────────────────────────────
    premium_btn = (
        InlineKeyboardButton("💎 Premium ✅", callback_data="premium_info")
        if user_is_premium
        else InlineKeyboardButton("💎 Get Premium", callback_data="premium_info")
    )

    if user_id in ADMINS:
        # Admin/Owner menu — no Support button, has Settings
        buttons = [
            [InlineKeyboardButton("ℹ️ About", callback_data="about"), premium_btn],
            [
                InlineKeyboardButton("📖 Help",    callback_data="help_menu"),
                InlineKeyboardButton("👤 Profile", callback_data="user_profile"),
            ],
            [InlineKeyboardButton("🎬 Request",   callback_data="request_start")],
            [InlineKeyboardButton("⚙️ Settings",  callback_data="open_settings")],
            [InlineKeyboardButton("🔒 Close",     callback_data="close")],
        ]
    else:
        # Regular user menu — has Support button
        buttons = [
            [InlineKeyboardButton("ℹ️ About", callback_data="about"), premium_btn],
            [
                InlineKeyboardButton("📖 Help",    callback_data="help_menu"),
                InlineKeyboardButton("👤 Profile", callback_data="user_profile"),
            ],
            [
                InlineKeyboardButton("🎬 Request", callback_data="request_start"),
                InlineKeyboardButton("💬 Support", callback_data="open_support"),
            ],
            [InlineKeyboardButton("🔒 Close", callback_data="close")],
        ]

    reply_markup = InlineKeyboardMarkup(buttons)

    fmt = dict(
        first=message.from_user.first_name,
        last=message.from_user.last_name or "",
        username=None if not message.from_user.username else "@" + message.from_user.username,
        mention=message.from_user.mention,
        id=message.from_user.id,
    )

    if START_PIC:
        await message.reply_photo(
            photo=START_PIC, caption=START_MSG.format(**fmt),
            reply_markup=reply_markup, quote=True
        )
    else:
        await message.reply_text(
            text=START_MSG.format(**fmt),
            reply_markup=reply_markup,
            disable_web_page_preview=True, quote=True
        )


# ─────────────────────────────────────────────────────────────────────────────
#  /start → banned
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('start') & filters.private & banned_user)
async def banned_start(client: Client, message: Message):
    info   = await get_ban_info(message.from_user.id)
    reason = info.get('reason', 'No reason provided') if info else 'No reason provided'
    await message.reply(
        f"╔══════════════════════╗\n"
        f"       🚫  <b>BANNED</b>\n"
        f"╚══════════════════════╝\n\n"
        f"You are banned from using this bot.\n\n"
        f"📝 <b>Reason:</b> {reason}\n\n"
        f"<i>Contact the admin if this is a mistake.</i>"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /start → not subscribed
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('start') & filters.private & ~subscribed & ~banned_user)
async def not_joined(client: Client, message: Message):
    from .force_sub import get_invite_link
    invite = await get_invite_link(client)
    if not invite:
        return  # No force sub configured

    payload = message.command[1] if len(message.command) > 1 else "start"
    try_again_url = f"https://t.me/{client.username}?start={payload}"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=invite)],
        [InlineKeyboardButton("🔄 Try Again",    url=try_again_url)],
    ])

    await message.reply(
        text=FORCE_MSG.format(
            first   = message.from_user.first_name,
            last    = message.from_user.last_name or "",
            username= None if not message.from_user.username else "@" + message.from_user.username,
            mention = message.from_user.mention,
            id      = message.from_user.id,
        ),
        reply_markup=buttons,
        quote=True,
        disable_web_page_preview=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /help
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('help') & filters.private)
async def help_cmd(client: Client, message: Message):
    await message.reply(
        "╔══════════════════════╗\n"
        "       📖  <b>HELP MENU</b>\n"
        "╚══════════════════════╝\n\n"
        "<b>📂 File Access</b>\n"
        "  • Get a file link from admin\n"
        "  • Tap the link to receive the file\n\n"
        "<b>🎬 Requests</b>\n"
        "  /request — Request a movie or anime\n"
        "  /mystatus — Track your requests\n\n"
        "<b>💎 Premium</b>\n"
        "  /premium — Check premium status\n\n"
        "<b>💬 Support</b>\n"
        "  /support — Chat with admin\n"
        "  /closechat — End support session\n\n"
        "<b>👤 Profile</b>\n"
        "  /profile — View your stats\n\n"
        "<i>Select an option below:</i>",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 Request", callback_data="request_start"),
                InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
            ],
            [
                InlineKeyboardButton("💬 Support", callback_data="open_support"),
                InlineKeyboardButton("👤 Profile", callback_data="user_profile"),
            ],
            [InlineKeyboardButton("🔒 Close", callback_data="close")]
        ])
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /profile
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('profile') & filters.private)
async def profile_cmd(client: Client, message: Message):
    user_id       = message.from_user.id
    premium       = await is_premium(user_id)
    daily_used    = await get_daily_downloads(user_id)
    premium_mode  = await get_setting('premium_mode')
    daily_limit   = await get_setting('free_daily_limit') or FREE_DAILY_LIMIT
    status_badge  = "💎 Premium" if premium else "🆓 Free"

    from database.database import get_user_requests
    requests = await get_user_requests(user_id, limit=3)

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
        f"👋 <b>{message.from_user.first_name}</b>\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"🏅 <b>Status:</b> {status_badge}\n\n"
        f"📥 <b>Today's Downloads:</b>\n"
        f"  [{bar}] {limit_text}\n\n"
    )

    if requests:
        status_emoji = {'pending': '🕐', 'fulfilled': '✅', 'declined': '❌'}
        text += "🎬 <b>Recent Requests:</b>\n"
        for r in requests:
            text += f"  {status_emoji.get(r['status'],'❓')} {r['title']} — {r['status'].capitalize()}\n"

    await message.reply(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 My Requests", callback_data="my_requests"),
                InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
            ],
            [InlineKeyboardButton("🔒 Close", callback_data="close")]
        ])
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /users & /broadcast
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg   = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await full_userbase()
    await msg.edit(f"👥 <b>{len(users)} users</b> are using this bot.")


@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if not message.reply_to_message:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()
        return

    query         = await full_userbase()
    broadcast_msg = message.reply_to_message
    total         = len(query)
    successful    = blocked = deleted = unsuccessful = 0
    pls_wait      = await message.reply(
        f"📡 <b>Broadcast Starting</b>\n\n"
        f"👥 Total users: <b>{total}</b>\n"
        f"<i>Please wait...</i>"
    )

    for i, chat_id in enumerate(query, 1):
        try:
            await broadcast_msg.copy(chat_id)
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except Exception:
                unsuccessful += 1
        except UserIsBlocked:
            await del_user(chat_id); blocked += 1
        except InputUserDeactivated:
            await del_user(chat_id); deleted += 1
        except Exception:
            unsuccessful += 1

        if i % 50 == 0:
            try:
                pct = int((i / total) * 100)
                filled = int(pct / 10)
                bar    = "█" * filled + "░" * (10 - filled)
                await pls_wait.edit(
                    f"📡 <b>Broadcasting...</b>\n\n"
                    f"[{bar}] {pct}%\n"
                    f"👥 {i}/{total}\n"
                    f"✅ {successful}  🚫 {blocked}  🗑 {deleted}  ❌ {unsuccessful}"
                )
            except Exception:
                pass

    await pls_wait.edit(
        f"╔══════════════════════╗\n"
        f"   📡  <b>BROADCAST DONE</b>\n"
        f"╚══════════════════════╝\n\n"
        f"👥 <b>Total:</b> <code>{total}</code>\n"
        f"✅ <b>Sent:</b> <code>{successful}</code>\n"
        f"🚫 <b>Blocked:</b> <code>{blocked}</code>\n"
        f"🗑 <b>Deleted:</b> <code>{deleted}</code>\n"
        f"❌ <b>Failed:</b> <code>{unsuccessful}</code>"
    )

