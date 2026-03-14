#(©)CodeXBotz - Enhanced by Claude
# Announcement System — Owner Only

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import OWNER_ID
from database.database import full_userbase, del_user

# ─────────────────────────────────────────────────────────────────────────────
#  /announce — open panel OR send replied message
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('announce') & filters.private & filters.user(OWNER_ID))
async def announce_cmd(client: Client, message: Message):
    # If replying to a text message — send it directly
    if message.reply_to_message and message.reply_to_message.text:
        await _send_announcement(client, message, message.reply_to_message.text)
        return

    # Otherwise show compose panel
    users = await full_userbase()
    await message.reply(
        "╔══════════════════════════╗\n"
        "     📣  <b>ANNOUNCEMENT</b>\n"
        "╚══════════════════════════╝\n\n"
        f"👥 <b>Total recipients:</b> {len(users)} users\n\n"
        "📝 <b>How to send:</b>\n"
        "Reply to any text message with /announce\n\n"
        "<b>OR</b> tap the button below to compose now:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Compose Announcement", callback_data="ann_compose")],
            [InlineKeyboardButton("🔒 Close",                callback_data="close")],
        ])
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Callback: compose announcement inline
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^ann_compose$") & filters.user(OWNER_ID))
async def ann_compose(client: Client, query: CallbackQuery):
    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "     📣  <b>COMPOSE</b>\n"
        "╚══════════════════════════╝\n\n"
        "✏️ Type your announcement message now.\n\n"
        "HTML formatting supported:\n"
        "• <code>&lt;b&gt;bold&lt;/b&gt;</code>\n"
        "• <code>&lt;i&gt;italic&lt;/i&gt;</code>\n"
        "• <code>&lt;a href='url'&gt;link&lt;/a&gt;</code>\n\n"
        "<i>⏰ You have 5 minutes to type.</i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="close")
        ]])
    )
    await query.answer()

    try:
        resp = await client.ask(
            query.from_user.id, "",
            filters=filters.text, timeout=300
        )
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "⏰ Timed out. Use /announce to try again.")
        return

    # Store pending announcement in memory
    if not hasattr(client, 'pending_announcement'):
        client.pending_announcement = {}
    client.pending_announcement[query.from_user.id] = resp.text

    # Show preview
    await client.send_message(
        chat_id=query.from_user.id,
        text=(
            "╔══════════════════════════╗\n"
            "     👀  <b>PREVIEW</b>\n"
            "╚══════════════════════════╝\n\n"
            + resp.text +
            "\n\n─────────────────────\n"
            "<i>This is how users will see it.</i>"
        ),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Send Now", callback_data="ann_confirm"),
                InlineKeyboardButton("❌ Cancel",   callback_data="ann_cancel"),
            ]
        ])
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Confirm & send
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^ann_confirm$") & filters.user(OWNER_ID))
async def ann_confirm(client: Client, query: CallbackQuery):
    if not hasattr(client, 'pending_announcement'):
        client.pending_announcement = {}

    text = client.pending_announcement.get(query.from_user.id)
    if not text:
        await query.answer("❌ No announcement found. Use /announce again.", show_alert=True)
        return

    del client.pending_announcement[query.from_user.id]
    await query.message.edit_reply_markup(None)
    await _send_announcement(client, query.message, text)


@Bot.on_callback_query(filters.regex(r"^ann_cancel$") & filters.user(OWNER_ID))
async def ann_cancel(client: Client, query: CallbackQuery):
    if hasattr(client, 'pending_announcement'):
        client.pending_announcement.pop(query.from_user.id, None)
    await query.message.edit_text("❌ <b>Announcement cancelled.</b>")
    await query.answer("Cancelled.")


# ─────────────────────────────────────────────────────────────────────────────
#  Core send function
# ─────────────────────────────────────────────────────────────────────────────
async def _send_announcement(client: Client, message, text: str):
    users   = await full_userbase()
    total   = len(users)
    sent    = blocked = deleted = failed = 0

    ann_text = (
        "📣 <b>ANNOUNCEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        + text +
        "\n\n━━━━━━━━━━━━━━━━━━━━━━"
    )

    progress = await client.send_message(
        chat_id=message.chat.id,
        text=(
            f"╔══════════════════════════╗\n"
            f"     📣  <b>SENDING...</b>\n"
            f"╚══════════════════════════╝\n\n"
            f"👥 Total: <b>{total}</b> users\n"
            f"[░░░░░░░░░░] 0%"
        )
    )

    for i, user_id in enumerate(users, 1):
        try:
            await client.send_message(chat_id=user_id, text=ann_text)
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await client.send_message(chat_id=user_id, text=ann_text)
                sent += 1
            except Exception:
                failed += 1
        except UserIsBlocked:
            await del_user(user_id); blocked += 1
        except InputUserDeactivated:
            await del_user(user_id); deleted += 1
        except Exception:
            failed += 1

        if i % 50 == 0:
            try:
                pct    = int((i / total) * 100)
                filled = int(pct / 10)
                bar    = "█" * filled + "░" * (10 - filled)
                await progress.edit(
                    f"╔══════════════════════════╗\n"
                    f"     📣  <b>SENDING...</b>\n"
                    f"╚══════════════════════════╝\n\n"
                    f"[{bar}] {pct}%\n"
                    f"👥 {i}/{total}\n"
                    f"✅ {sent}  🚫 {blocked}  🗑 {deleted}  ❌ {failed}"
                )
            except Exception:
                pass

    await progress.edit(
        f"╔══════════════════════════╗\n"
        f"   📣  <b>ANNOUNCEMENT SENT</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"👥 <b>Total:</b> <code>{total}</code>\n"
        f"✅ <b>Delivered:</b> <code>{sent}</code>\n"
        f"🚫 <b>Blocked:</b> <code>{blocked}</code>\n"
        f"🗑 <b>Deleted:</b> <code>{deleted}</code>\n"
        f"❌ <b>Failed:</b> <code>{failed}</code>\n\n"
        f"<i>Blocked/deleted users removed from database.</i>"
    )
