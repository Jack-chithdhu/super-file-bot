#(©)CodeXBotz - Enhanced by Claude
# Admin: Ban/Unban + File Stats Dashboard + Join Requests

import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot import Bot
from config import ADMINS
from database.database import (
    ban_user, unban_user, is_banned, get_ban_info, list_banned_users,
    get_top_files, get_total_file_accesses, get_unique_files_count,
    get_user_count, get_request_count, get_pending_requests,
    approve_join_request
)


# ─────────────────────────────────────────────────────────────────────────────
#  /ban <user_id> [reason]
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('ban') & filters.private & filters.user(ADMINS))
async def ban_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/ban &lt;user_id&gt; [reason]</code>")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.reply("❌ Invalid user_id.")
        return

    reason = " ".join(args[1:]) if len(args) > 1 else "No reason provided"
    await ban_user(target_id, reason)
    await message.reply(
        f"🚫 <b>User Banned</b>\n\n"
        f"👤 ID: <code>{target_id}</code>\n"
        f"📝 Reason: {reason}"
    )

    try:
        await client.send_message(
            chat_id=target_id,
            text=f"🚫 You have been <b>banned</b> from this bot.\n📝 Reason: {reason}"
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  /unban <user_id>
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('unban') & filters.private & filters.user(ADMINS))
async def unban_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/unban &lt;user_id&gt;</code>")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.reply("❌ Invalid user_id.")
        return

    await unban_user(target_id)
    await message.reply(f"✅ User <code>{target_id}</code> has been unbanned.")

    try:
        await client.send_message(
            chat_id=target_id,
            text="✅ You have been <b>unbanned</b>. You can use the bot again."
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  /banned  — list all banned users
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('banned') & filters.private & filters.user(ADMINS))
async def banned_list(client: Client, message: Message):
    users = await list_banned_users()
    if not users:
        await message.reply("📋 No banned users.")
        return

    lines = ["🚫 <b>Banned Users</b>\n"]
    for u in users[:30]:
        ts = u.get('banned_at', datetime.utcnow()).strftime('%Y-%m-%d')
        lines.append(f"• <code>{u['_id']}</code> — {u.get('reason','—')} ({ts})")
    if len(users) > 30:
        lines.append(f"\n…and {len(users)-30} more.")
    await message.reply("\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
#  /filestats  — dashboard
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('filestats') & filters.private & filters.user(ADMINS))
async def file_stats_cmd(client: Client, message: Message):
    msg = await message.reply("📊 <i>Fetching statistics…</i>")

    total_accesses  = await get_total_file_accesses()
    unique_files    = await get_unique_files_count()
    total_users     = await get_user_count()
    top_files       = await get_top_files(5)
    req_counts      = await get_request_count()

    top_lines = []
    for i, f in enumerate(top_files, 1):
        top_lines.append(
            f"  {i}. ID <code>{f['file_id']}</code> — "
            f"<b>{f['access_count']}</b> accesses"
        )
    top_section = "\n".join(top_lines) if top_lines else "  No data yet."

    text = (
        f"📊 <b>File Statistics Dashboard</b>\n"
        f"{'─' * 30}\n\n"
        f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
        f"📂 <b>Unique Files Shared:</b> <code>{unique_files}</code>\n"
        f"📥 <b>Total File Accesses:</b> <code>{total_accesses}</code>\n\n"
        f"📋 <b>Join Requests</b>\n"
        f"  • Pending: <code>{req_counts['pending']}</code>\n"
        f"  • Approved: <code>{req_counts['approved']}</code>\n"
        f"  • Total: <code>{req_counts['total']}</code>\n\n"
        f"🏆 <b>Top 5 Most Accessed Files</b>\n"
        f"{top_section}"
    )

    await msg.edit(text, disable_web_page_preview=True)


# ─────────────────────────────────────────────────────────────────────────────
#  /requests  — view & approve pending join requests
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('requests') & filters.private & filters.user(ADMINS))
async def view_requests(client: Client, message: Message):
    pending = await get_pending_requests(20)
    counts  = await get_request_count()

    if not pending:
        await message.reply(
            f"📋 <b>Join Requests</b>\n\n"
            f"✅ No pending requests.\n"
            f"Total approved: <code>{counts['approved']}</code>"
        )
        return

    lines = [f"📋 <b>Pending Join Requests ({counts['pending']})</b>\n"]
    for r in pending:
        ts = r.get('requested_at', datetime.utcnow()).strftime('%Y-%m-%d %H:%M')
        lines.append(f"• <code>{r['user_id']}</code> — requested {ts}")

    lines.append(
        f"\n<i>Use /approverequest &lt;user_id&gt; to approve one,\n"
        f"or /approveall to approve all pending requests.</i>"
    )
    await message.reply("\n".join(lines))


@Bot.on_message(filters.command('approverequest') & filters.private & filters.user(ADMINS))
async def approve_one(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/approverequest &lt;user_id&gt;</code>")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.reply("❌ Invalid user_id.")
        return

    await approve_join_request(target_id)
    await message.reply(f"✅ Request approved for <code>{target_id}</code>.")

    try:
        await client.send_message(
            chat_id=target_id,
            text="✅ <b>Your join request has been approved!</b>\nYou can now access the bot."
        )
    except Exception:
        pass


@Bot.on_message(filters.command('approveall') & filters.private & filters.user(ADMINS))
async def approve_all(client: Client, message: Message):
    pending = await get_pending_requests(500)
    if not pending:
        await message.reply("✅ No pending requests to approve.")
        return

    msg      = await message.reply(f"⏳ Approving {len(pending)} requests…")
    approved = 0
    for r in pending:
        await approve_join_request(r['user_id'])
        approved += 1
        try:
            await client.send_message(
                chat_id=r['user_id'],
                text="✅ <b>Your join request has been approved!</b>\nYou can now access the bot."
            )
        except Exception:
            pass
        await asyncio.sleep(0.3)

    await msg.edit(f"✅ Approved <b>{approved}</b> join requests.")


# ── Handle Join Requests ───────────────────────────────────────────────────────
@Bot.on_chat_join_request()
async def handle_join_request(client: Client, request):
    """
    Handle join requests:
    - Mode 2 (Access on Request): save to DB only — user gets BOT access but NOT channel access
    - Mode 3 (Auto Approve): save to DB AND approve into channel automatically
    """
    import logging
    log = logging.getLogger(__name__)
    try:
        from database.database import add_join_request, get_setting
        user_id = request.from_user.id

        # Check which mode is active
        auto_approve = await get_setting('join_request_auto_approve') or False
        jr_access    = await get_setting('join_request_access') or False

        log.info(f"Join request from {user_id} | auto_approve={auto_approve} | jr_access={jr_access}")

        if auto_approve:
            # Mode 3 — Auto Approve: approve into channel AND save to DB as approved
            try:
                await client.approve_chat_join_request(
                    chat_id=request.chat.id,
                    user_id=user_id
                )
                from database.database import approve_join_request
                await approve_join_request(user_id)
                log.info(f"Auto-approved {user_id} into channel")
            except Exception as ae:
                log.warning(f"Auto approve error: {ae}")

        elif jr_access:
            # Mode 2 — Access on Request: save as pending only
            # User gets BOT access but channel join is still pending
            await add_join_request(user_id)
            log.info(f"Saved join request for {user_id} as pending (Access on Request mode)")

        else:
            log.info(f"No join request mode active — ignoring request from {user_id}")

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Join request handler error: {e}")


# ── Handle Member Left ─────────────────────────────────────────────────────────
@Bot.on_chat_member_updated()
async def handle_member_left(client: Client, update):
    """Remove user from join requests DB when they leave the channel."""
    try:
        from pyrogram.types import ChatMemberUpdated
        from pyrogram.enums import ChatMemberStatus
        from database.database import get_setting

        # Only handle leaves
        if not update.new_chat_member:
            return
        if update.new_chat_member.status not in [
            ChatMemberStatus.LEFT,
            ChatMemberStatus.BANNED
        ]:
            return

        # Check if this is the force sub channel
        force_sub = await get_setting('force_sub_channel') or 0
        if not force_sub:
            return
        if update.chat.id != int(force_sub):
            return

        # Remove from join requests DB
        user_id = update.new_chat_member.user.id
        from database.database import approve_join_request
        # We use approve to mark as closed so they lose pending status
        from pymongo import MongoClient as _MC
        from config import DB_URI, DB_NAME
        _db = _MC(DB_URI)[DB_NAME]['join_requests']
        _db.delete_one({'user_id': user_id})

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Member left handler error: {e}")
