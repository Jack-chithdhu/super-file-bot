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
                    FORCE_SUB_CHANNEL, FREE_DAILY_LIMIT)
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

    # ── Captcha check for new users ────────────────────────────────────────
    captcha_enabled = await get_setting('captcha_enabled')
    if captcha_enabled is None:
        captcha_enabled = True
    if captcha_enabled and user_id not in ADMINS:
        from plugins.captcha import send_captcha, captcha_just_passed
        # Skip if user just passed captcha (called directly after verification)
        if user_id in captcha_just_passed:
            captcha_just_passed.discard(user_id)
        else:
            original = message.text[7:].strip() if len(message.text) > 7 else ""
            sent = await send_captcha(client, user_id, message.from_user.first_name, original)
            if sent:
                return  # Wait for captcha to be solved

    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception:
            pass

    text = message.text
    if len(text) > 7:
        # ── File delivery ──────────────────────────────────────────────────
        try:
            base64_string = text.split(" ", 1)[1]
        except Exception:
            return

        # Daily limit check
        premium_mode = await get_setting('premium_mode')
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

        apply_autodelete = (
            AUTO_DELETE_TIME and AUTO_DELETE_TIME > 0
            and premium_mode and not user_is_premium
        )

        track_msgs = []
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

            if apply_autodelete:
                try:
                    copied = await msg.copy(
                        chat_id=user_id, caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        protect_content=PROTECT_CONTENT
                    )
                    if copied:
                        track_msgs.append(copied)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    try:
                        copied = await msg.copy(
                            chat_id=user_id, caption=caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                            protect_content=PROTECT_CONTENT
                        )
                        if copied:
                            track_msgs.append(copied)
                    except Exception:
                        pass
                except Exception:
                    pass
            else:
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

        if track_msgs:
            delete_notice = await client.send_message(
                chat_id=user_id,
                text=(
                    f"⚠️ <b>Auto-Delete Notice</b>\n\n"
                    f"⏳ These files will be deleted in <b>{AUTO_DELETE_TIME}s</b>\n"
                    f"💾 Save them before time runs out!\n\n"
                    f"💎 Upgrade to Premium to keep files forever."
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💎 Get Premium", callback_data="premium_info")
                ]])
            )
            asyncio.create_task(delete_file(track_msgs, client, delete_notice, user_id=user_id))
        elif user_is_premium and AUTO_DELETE_TIME and AUTO_DELETE_TIME > 0 and premium_mode:
            await client.send_message(
                chat_id=user_id,
                text="💎 <b>Premium Perk Active!</b>\nYour files will never be auto-deleted. Enjoy! ✨"
            )

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
@Bot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    if bool(JOIN_REQUEST_ENABLE):
        invite     = await client.create_chat_invite_link(
            chat_id=FORCE_SUB_CHANNEL, creates_join_request=True)
        button_url = invite.invite_link
    else:
        button_url = client.invitelink

    buttons = [[InlineKeyboardButton("📢 Join Channel", url=button_url)]]
    try:
        buttons.append([
            InlineKeyboardButton(
                "🔄 Try Again",
                url=f"https://t.me/{client.username}?start={message.command[1]}"
            )
        ])
    except IndexError:
        pass

    await message.reply(
        text=FORCE_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name or "",
            username=None if not message.from_user.username else "@" + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True, disable_web_page_preview=True
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
