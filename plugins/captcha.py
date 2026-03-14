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

    # Check if captcha was reset recently — force re-verify for all
    last_reset = await get_setting('captcha_last_reset')
    if last_reset and user_id in verified_users:
        # Check if user verified before the last reset
        reset_time = datetime.fromisoformat(last_reset)
        verify_time = verified_users_time.get(user_id)
        if verify_time and verify_time < reset_time:
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

    # Only new users (not in DB yet) need captcha
    return not await present_user(user_id)


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

    # Mark as verified
    verified_users.add(user_id)
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

    # Trigger start flow directly by calling start_command
    await asyncio.sleep(1)
    original_text = data.get('original_text', '')
    try:
        from plugins.start import start_command
        # Send /start so Pyrogram processes it normally through the handler
        fake_text = f"/start {original_text}" if original_text else "/start"
        sent = await client.send_message(chat_id=user_id, text=fake_text)
        # Now call start_command directly with that message
        await start_command(client, sent)
    except Exception as e:
        # Fallback: just send the start message manually
        try:
            await client.send_message(chat_id=user_id, text="/start")
        except Exception:
            pass
