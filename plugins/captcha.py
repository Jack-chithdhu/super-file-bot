#(©)CodeXBotz - Enhanced by Claude
# Emoji Button Captcha System

import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot import Bot
from config import ADMINS

# ── In-memory captcha store: {user_id: {'answer': emoji, 'task': asyncio.Task}} 
captcha_store = {}

# ── Verified users (passed captcha this session) ──────────────────────────────
verified_users = set()
verified_users_time = {}  # user_id -> datetime when verified
# captcha_just_passed is now persisted in MongoDB (see database.captcha_passed_data)
# kept as a local fast-path cache for single-worker setups
captcha_just_passed = set()

# ── Emoji pool ────────────────────────────────────────────────────────────────
EMOJI_POOL = [
    "🍎", "🍊", "🍋", "🍇", "🍓", "🍒", "🥝", "🍑",
    "🐶", "🐱", "🐭", "🐸", "🐯", "🦁", "🐻", "🐼",
    "🚗", "✈️", "🚀", "🚢", "🚂", "🏎️", "🛸", "🚁",
    "⚽", "🏀", "🎸", "🎯", "🎲", "🎮", "🏆", "🎪",
    "🌟", "🌈", "❄️", "🔥", "⚡", "🌊", "🌸", "🍀",
]

CAPTCHA_TIMEOUT = 60  # seconds

# ─────────────────────────────────────────────────────────────────────────────
#  Helper: generate captcha buttons
# ─────────────────────────────────────────────────────────────────────────────
def _generate_captcha(user_id: int) -> tuple:
    """Returns (correct_emoji, InlineKeyboardMarkup)"""
    choices = random.sample(EMOJI_POOL, 4)
    correct = random.choice(choices)
    random.shuffle(choices)

    buttons = [[
        InlineKeyboardButton(e, callback_data=f"captcha_{user_id}_{e}")
        for e in choices
    ]]
    return correct, InlineKeyboardMarkup(buttons)


# ─────────────────────────────────────────────────────────────────────────────
#  Check if user needs captcha
# ─────────────────────────────────────────────────────────────────────────────
async def needs_captcha(user_id: int) -> bool:
    """Returns True if user needs to solve captcha first."""
    if user_id in ADMINS:
        return False

    from database.database import present_user, get_setting
    from datetime import datetime, timedelta

    # Check if captcha was reset — remove from verified if reset happened after verify
    last_reset = await get_setting('captcha_last_reset')
    if last_reset:
        reset_time = datetime.fromisoformat(last_reset)
        verify_time = verified_users_time.get(user_id)
        if verify_time is None or verify_time < reset_time:
            # User verified before reset or never verified — force captcha
            verified_users.discard(user_id)
            verified_users_time.pop(user_id, None)

    # Check expiry period
    exp_days = await get_setting('captcha_expiry_days') or 0
    if exp_days and exp_days > 0 and user_id in verified_users:
        verify_time = verified_users_time.get(user_id)
        if verify_time and datetime.utcnow() - verify_time > timedelta(days=exp_days):
            verified_users.discard(user_id)
            verified_users_time.pop(user_id, None)

    if user_id in verified_users:
        return False

    # Show captcha for ALL users not currently verified (new or existing after reset)
    return True


async def send_captcha(client: Client, user_id: int, first_name: str, original_text: str = ""):
    """Send captcha challenge to user. Returns True if captcha was sent."""
    if not await needs_captcha(user_id):
        return False

    # Cancel existing captcha task if any
    if user_id in captcha_store:
        old = captcha_store[user_id]
        if old.get('task') and not old['task'].done():
            old['task'].cancel()

    correct, markup = _generate_captcha(user_id)

    msg = await client.send_message(
        chat_id=user_id,
        text=(
            f"╔══════════════════════╗\n"
            f"     🤖  <b>CAPTCHA CHECK</b>\n"
            f"╚══════════════════════╝\n\n"
            f"👋 Welcome <b>{first_name}</b>!\n\n"
            f"Before you can use the bot, please verify you're human.\n\n"
            f"👇 <b>Tap the {correct} emoji</b>\n\n"
            f"⏰ You have <b>{CAPTCHA_TIMEOUT} seconds</b>"
        ),
        reply_markup=markup
    )

    # Store captcha data
    captcha_store[user_id] = {
        'answer':       correct,
        'message_id':   msg.id,
        'original_text': original_text,
        'attempts':     0,
    }

    # Start timeout task
    task = asyncio.create_task(_captcha_timeout(client, user_id, msg.id))
    captcha_store[user_id]['task'] = task

    return True


async def _captcha_timeout(client: Client, user_id: int, message_id: int):
    """Auto-fail captcha after timeout."""
    await asyncio.sleep(CAPTCHA_TIMEOUT)
    if user_id in captcha_store:
        captcha_store.pop(user_id, None)
        try:
            await client.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=(
                    f"╔══════════════════════╗\n"
                    f"     ⏰  <b>CAPTCHA EXPIRED</b>\n"
                    f"╚══════════════════════╝\n\n"
                    f"❌ Time's up! You didn't verify in time.\n\n"
                    f"Send /start to try again."
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Try Again", url="https://t.me/")
                ]])
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  Captcha callback handler
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^captcha_(\d+)_(.+)$"))
async def captcha_callback(client: Client, query: CallbackQuery):
    parts     = query.data.split("_", 2)
    target_id = int(parts[1])
    chosen    = parts[2]
    user_id   = query.from_user.id

    # Only the correct user can answer
    if user_id != target_id:
        await query.answer("❌ This captcha is not for you!", show_alert=True)
        return

    data = captcha_store.get(user_id)
    if not data:
        await query.answer("⏰ Captcha expired. Send /start to try again.", show_alert=True)
        return

    # ── Wrong answer ──────────────────────────────────────────────────────
    if chosen != data['answer']:
        data['attempts'] = data.get('attempts', 0) + 1

        # Allow max 3 attempts
        if data['attempts'] >= 3:
            captcha_store.pop(user_id, None)
            if data.get('task') and not data['task'].done():
                data['task'].cancel()
            await query.message.edit_text(
                f"╔══════════════════════╗\n"
                f"     🚫  <b>CAPTCHA FAILED</b>\n"
                f"╚══════════════════════╝\n\n"
                f"❌ Too many wrong attempts!\n\n"
                f"Send /start to get a new captcha."
            )
            await query.answer("❌ Failed! Send /start to try again.", show_alert=True)
            return

        # Regenerate captcha with new emojis
        correct, markup = _generate_captcha(user_id)
        data['answer']  = correct
        remaining       = 3 - data['attempts']

        await query.message.edit_text(
            f"╔══════════════════════╗\n"
            f"     🤖  <b>CAPTCHA CHECK</b>\n"
            f"╚══════════════════════╝\n\n"
            f"❌ <b>Wrong!</b> Try again.\n\n"
            f"👇 <b>Tap the {correct} emoji</b>\n\n"
            f"⚠️ <b>{remaining} attempt{'s' if remaining > 1 else ''} remaining</b>",
            reply_markup=markup
        )
        await query.answer("❌ Wrong emoji! Try again.")
        return

    # ── Correct answer ────────────────────────────────────────────────────
    if data.get('task') and not data['task'].done():
        data['task'].cancel()
    captcha_store.pop(user_id, None)

    # Mark as verified (both in-memory for speed + DB for multi-worker safety)
    verified_users.add(user_id)
    captcha_just_passed.add(user_id)
    from database.database import mark_captcha_passed
    await mark_captcha_passed(user_id)
    from datetime import datetime
    verified_users_time[user_id] = datetime.utcnow()

    await query.message.edit_text(
        f"╔══════════════════════╗\n"
        f"     ✅  <b>VERIFIED!</b>\n"
        f"╚══════════════════════╝\n\n"
        f"🎉 You're verified! Welcome to the bot.\n\n"
        f"<i>Loading your experience...</i>"
    )
    await query.answer("✅ Verified! Welcome!")

    # Delete verified message after 2 seconds
    await asyncio.sleep(2)
    try:
        await query.message.delete()
    except Exception:
        pass

    # Trigger start flow directly after captcha pass
    await asyncio.sleep(1)
    original_text = data.get('original_text', '').strip()
    try:
        if original_text:
            # User came from a file link — check force sub first
            from .force_sub import check_subscription, send_force_sub_message
            if not await check_subscription(client, user_id):
                await send_force_sub_message(client, query, payload=original_text)
                return

            from database.database import record_file_access
            from config import CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT
            from pyrogram.enums import ParseMode
            from helper_func import decode, get_messages

            string   = await decode(original_text)
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
                temp = await client.send_message(chat_id=user_id, text="⏳ <b>Fetching your files...</b>")
                messages = await get_messages(client, list(ids))
                await temp.delete()

                for msg_id in ids:
                    await record_file_access(str(msg_id), user_id)

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
                    except Exception:
                        pass
        else:
            # Plain /start — show welcome screen directly (no fake message needed)
            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            from config import START_MSG, START_PIC
            from database.database import is_premium, present_user, add_user

            # Ensure user is in DB
            if not await present_user(user_id):
                try:
                    await add_user(user_id)
                except Exception:
                    pass

            user_is_premium = await is_premium(user_id)
            first = query.from_user.first_name
            last  = query.from_user.last_name or ""
            uname = query.from_user.username
            mention = query.from_user.mention

            premium_btn = (
                InlineKeyboardButton("💎 Premium ✅", callback_data="premium_info")
                if user_is_premium
                else InlineKeyboardButton("💎 Get Premium", callback_data="premium_info")
            )
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
                first=first, last=last,
                username=None if not uname else "@" + uname,
                mention=mention, id=user_id,
            )
            if START_PIC:
                await client.send_photo(
                    chat_id=user_id,
                    photo=START_PIC,
                    caption=START_MSG.format(**fmt),
                    reply_markup=reply_markup
                )
            else:
                await client.send_message(
                    chat_id=user_id,
                    text=START_MSG.format(**fmt),
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Post-captcha start error: {e}")
