#(©)CodeXBotz - Enhanced by Claude
# Movie & Anime Request System — with inline button UI

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait

from bot import Bot
from config import ADMINS, REQUEST_CHANNEL_ID
from database.database import (
    create_movie_request, get_user_active_request, get_request_by_id,
    fulfill_request, decline_request, get_all_requests, get_user_requests,
    get_bot_admins
)

# ─────────────────────────────────────────────────────────────────────────────
#  /request command
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('request') & filters.private)
async def request_cmd(client: Client, message: Message):
    user_id  = message.from_user.id
    existing = await get_user_active_request(user_id)

    if existing:
        status_emoji = {'pending': '🕐', 'fulfilled': '✅', 'declined': '❌'}
        await message.reply(
            f"╔══════════════════════╗\n"
            f"    ⚠️  <b>ACTIVE REQUEST</b>\n"
            f"╚══════════════════════╝\n\n"
            f"You already have a pending request!\n\n"
            f"🆔 <b>ID:</b> <code>{existing['request_id']}</code>\n"
            f"🎬 <b>Title:</b> {existing['title']}\n"
            f"📁 <b>Type:</b> {existing['type'].capitalize()}\n"
            f"🕐 <b>Status:</b> Pending\n\n"
            f"<i>Wait for it to be fulfilled before making a new one.</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 My Requests", callback_data="my_requests")
            ]])
        )
        return

    await message.reply(
        "╔══════════════════════╗\n"
        "       🎬  <b>NEW REQUEST</b>\n"
        "╚══════════════════════╝\n\n"
        "What would you like to request?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 Movie", callback_data="req_type_movie"),
                InlineKeyboardButton("🎌 Anime", callback_data="req_type_anime"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Handle title input after type is selected via inline button
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.private & filters.text & ~filters.command([
    'start','request','mystatus','premium','support','closechat','help','profile',
    'users','broadcast','batch','genlink','stats','ban','unban','banned',
    'filestats','requests','approverequest','approveall','addpremium',
    'removepremium','listpremium','allrequests','fulfill','decline',
    'chatto','endchat','activechats','addadmin','removeadmin',
    'listadmins','togglepremium','setdailylimit','adminhelp',
    'addfile','getfiles','listfiles','deletefile','filestore',
    'cancel','linkstats','clearjoinrequests'
]))
async def handle_request_title(client: Client, message: Message):
    user_id = message.from_user.id

    if not hasattr(client, 'pending_requests'):
        client.pending_requests = {}

    pending = client.pending_requests.get(user_id)
    if not pending:
        return  # not in request flow, let other handlers deal with it

    step     = pending.get('step')
    req_type = pending.get('type')
    emoji    = "🎬" if req_type == "movie" else ("🎌" if req_type == "anime" else "📺")

    if step == 'title':
        title = message.text.strip()
        if len(title) < 2:
            await message.reply("❌ Title too short. Please type a valid title.")
            return

        pending['title'] = title
        pending['step']  = 'note'
        client.pending_requests[user_id] = pending

        await message.reply(
            f"╔══════════════════════╗\n"
            f"    {emoji}  <b>{req_type.upper()} REQUEST</b>\n"
            f"╚══════════════════════╝\n\n"
            f"✅ Title: <b>{title}</b>\n\n"
            f"📝 Any extra details?\n"
            f"<i>(e.g. season, year, language)</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏭ Skip", callback_data="req_skip_note"),
                InlineKeyboardButton("❌ Cancel", callback_data="req_cancel"),
            ]])
        )

    elif step == 'note':
        note  = message.text.strip()
        title = pending.get('title', '')
        await _submit_request(client, message, user_id, req_type, title, note)
        del client.pending_requests[user_id]


async def _submit_request(client, message, user_id, req_type, title, note):
    emoji  = "🎬" if req_type == "movie" else "🎌"
    req_id = await create_movie_request(user_id, title, req_type, note)

    await message.reply(
        f"╔══════════════════════╗\n"
        f"   ✅  <b>REQUEST SUBMITTED</b>\n"
        f"╚══════════════════════╝\n\n"
        f"{emoji} <b>Type:</b> {req_type.capitalize()}\n"
        f"🎬 <b>Title:</b> {title}\n"
        f"📝 <b>Note:</b> {note or 'None'}\n"
        f"🆔 <b>Request ID:</b> <code>{req_id}</code>\n\n"
        f"<i>We'll notify you when it's ready! 🔔</i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 Track Status", callback_data="my_requests")
        ]])
    )

    # Notify admins
    admin_text = (
        f"📥 <b>New {req_type.capitalize()} Request</b>\n\n"
        f"🆔 ID: <code>{req_id}</code>\n"
        f"👤 User: <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a> "
        f"(<code>{user_id}</code>)\n"
        f"{emoji} Title: <b>{title}</b>\n"
        f"📝 Note: {note or 'None'}"
    )
    action_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Fulfill", callback_data=f"req_fulfill_{req_id}"),
        InlineKeyboardButton("❌ Decline", callback_data=f"req_decline_{req_id}"),
    ]])

    all_admins = list(set(ADMINS + await get_bot_admins()))
    for admin_id in all_admins:
        try:
            await client.send_message(chat_id=admin_id, text=admin_text, reply_markup=action_markup)
        except Exception:
            pass

    if REQUEST_CHANNEL_ID:
        try:
            await client.send_message(chat_id=REQUEST_CHANNEL_ID, text=admin_text, reply_markup=action_markup)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  Callbacks for note skip/cancel
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^req_skip_note$"))
async def skip_note(client, query):
    user_id = query.from_user.id
    if not hasattr(client, 'pending_requests'):
        client.pending_requests = {}
    pending  = client.pending_requests.get(user_id, {})
    req_type = pending.get('type', 'movie')
    title    = pending.get('title', '')

    if not title:
        await query.answer("Session expired. Use /request to start again.", show_alert=True)
        return

    await query.message.delete()
    await _submit_request(client, query.message, user_id, req_type, title, "")
    client.pending_requests.pop(user_id, None)


@Bot.on_callback_query(filters.regex(r"^req_cancel$"))
async def cancel_request(client, query):
    user_id = query.from_user.id
    if hasattr(client, 'pending_requests'):
        client.pending_requests.pop(user_id, None)
    await query.message.edit_text("❌ Request cancelled.")
    await query.answer("Cancelled.")


# ─────────────────────────────────────────────────────────────────────────────
#  /mystatus
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('mystatus') & filters.private)
async def my_status(client: Client, message: Message):
    user_id  = message.from_user.id
    requests = await get_user_requests(user_id, limit=5)
    status_emoji = {'pending': '🕐', 'fulfilled': '✅', 'declined': '❌'}

    if not requests:
        await message.reply(
            "📋 <b>Your Requests</b>\n\nNo requests yet.\nUse /request to submit one!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎬 Make a Request", callback_data="request_start")
            ]])
        )
        return

    lines = [
        "╔══════════════════════╗\n"
        "    📋  <b>YOUR REQUESTS</b>\n"
        "╚══════════════════════╝\n"
    ]
    for r in requests:
        emoji = status_emoji.get(r['status'], '❓')
        lines.append(
            f"{emoji} <code>{r['request_id']}</code> — <b>{r['title']}</b>\n"
            f"   [{r['type'].capitalize()}] {r['status'].capitalize()}"
        )
        if r.get('response') and r['status'] != 'pending':
            lines.append(f"   💬 <i>{r['response']}</i>")
        lines.append("")

    await message.reply(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🎬 New Request", callback_data="request_start")
        ]])
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Admin: /allrequests, /fulfill, /decline + inline callbacks
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('allrequests') & filters.private & filters.user(ADMINS))
async def all_requests(client: Client, message: Message):
    args   = message.command[1:]
    status = args[0] if args and args[0] in ['pending','fulfilled','declined'] else None
    reqs   = await get_all_requests(status=status, limit=20)
    status_emoji = {'pending': '🕐', 'fulfilled': '✅', 'declined': '❌'}

    if not reqs:
        await message.reply("📋 No requests found.")
        return

    lines = [f"╔══════════════════════╗\n📋 <b>REQUESTS</b>\n╚══════════════════════╝\n"]
    for r in reqs:
        emoji = status_emoji.get(r['status'], '❓')
        lines.append(
            f"{emoji} <code>{r['request_id']}</code> — <b>{r['title']}</b>\n"
            f"   [{r['type'].capitalize()}] User <code>{r['user_id']}</code>"
        )
    lines.append("\n<i>/fulfill &lt;id&gt; or /decline &lt;id&gt; &lt;reason&gt;</i>")
    await message.reply("\n".join(lines))


@Bot.on_message(filters.command('fulfill') & filters.private & filters.user(ADMINS))
async def fulfill_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/fulfill &lt;req_id&gt; [note]</code>")
        return
    req_id = args[0].upper()
    note   = " ".join(args[1:]) if len(args) > 1 else "Your request has been fulfilled!"
    req    = await get_request_by_id(req_id)
    if not req:
        await message.reply(f"❌ Request <code>{req_id}</code> not found.")
        return
    if req['status'] != 'pending':
        await message.reply(f"⚠️ Already <b>{req['status']}</b>.")
        return
    await fulfill_request(req_id, note)
    await message.reply(f"✅ Request <code>{req_id}</code> fulfilled.")
    try:
        await client.send_message(
            chat_id=req['user_id'],
            text=(
                f"╔══════════════════════╗\n"
                f"   🎉  <b>REQUEST FULFILLED</b>\n"
                f"╚══════════════════════╝\n\n"
                f"🆔 ID: <code>{req_id}</code>\n"
                f"🎬 Title: <b>{req['title']}</b>\n\n"
                f"📢 {note}\n\n"
                f"Use the button below to get your files:"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📥 Get Files", callback_data=f"gf_back_{req_id}")
            ]])
        )
    except Exception:
        pass


@Bot.on_message(filters.command('decline') & filters.private & filters.user(ADMINS))
async def decline_cmd(client: Client, message: Message):
    args = message.command[1:]
    if len(args) < 2:
        await message.reply("ℹ️ <b>Usage:</b> <code>/decline &lt;req_id&gt; &lt;reason&gt;</code>")
        return
    req_id = args[0].upper()
    reason = " ".join(args[1:])
    req    = await get_request_by_id(req_id)
    if not req:
        await message.reply(f"❌ Request <code>{req_id}</code> not found.")
        return
    await decline_request(req_id, reason)
    await message.reply(f"✅ Request <code>{req_id}</code> declined.")
    try:
        await client.send_message(
            chat_id=req['user_id'],
            text=(
                f"╔══════════════════════╗\n"
                f"    ❌  <b>REQUEST DECLINED</b>\n"
                f"╚══════════════════════╝\n\n"
                f"🆔 ID: <code>{req_id}</code>\n"
                f"🎬 Title: <b>{req['title']}</b>\n\n"
                f"📝 Reason: {reason}"
            )
        )
    except Exception:
        pass


@Bot.on_callback_query(filters.regex(r"^req_(fulfill|decline)_(.+)$"))
async def req_callback(client: Client, query: CallbackQuery):
    all_admins = list(set(ADMINS + await get_bot_admins()))
    if query.from_user.id not in all_admins:
        await query.answer("❌ Not an admin.", show_alert=True)
        return

    parts  = query.data.split("_", 2)
    action = parts[1]
    req_id = parts[2]
    req    = await get_request_by_id(req_id)

    if not req:
        await query.answer("Request not found.", show_alert=True)
        return
    if req['status'] != 'pending':
        await query.answer(f"Already {req['status']}.", show_alert=True)
        return

    if action == "fulfill":
        await fulfill_request(req_id, "Your request has been fulfilled!")
        await query.message.edit_reply_markup(None)
        await query.message.reply(f"✅ Fulfilled by {query.from_user.mention}")
        try:
            await client.send_message(
                chat_id=req['user_id'],
                text=(
                    f"╔══════════════════════╗\n"
                    f"   🎉  <b>REQUEST FULFILLED</b>\n"
                    f"╚══════════════════════╝\n\n"
                    f"🆔 ID: <code>{req_id}</code>\n"
                    f"🎬 Title: <b>{req['title']}</b>\n\n"
                    f"Your files are ready! 🎊\n\n"
                    f"Use the button below to get your files:"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📥 Get Files", switch_inline_query_current_chat=f"/getfiles {req_id}")
                ],[
                    InlineKeyboardButton("📥 /getfiles " + req_id, callback_data=f"gf_back_{req_id}")
                ]])
            )
        except Exception:
            pass
        await query.answer("✅ Fulfilled!")

    elif action == "decline":
        await query.answer("Send the decline reason in chat.")
        try:
            reason_msg = await client.ask(
                chat_id=query.from_user.id,
                text=f"📝 Enter decline reason for <code>{req_id}</code>:",
                filters=filters.text,
                timeout=60
            )
            reason = reason_msg.text.strip()
        except asyncio.TimeoutError:
            await client.send_message(query.from_user.id, "⏰ Timed out. Use /decline manually.")
            return

        await decline_request(req_id, reason)
        await query.message.edit_reply_markup(None)
        await query.message.reply(f"❌ Declined by {query.from_user.mention}")
        try:
            await client.send_message(
                chat_id=req['user_id'],
                text=(
                    f"╔══════════════════════╗\n"
                    f"    ❌  <b>REQUEST DECLINED</b>\n"
                    f"╚══════════════════════╝\n\n"
                    f"🆔 ID: <code>{req_id}</code>\n"
                    f"🎬 Title: <b>{req['title']}</b>\n\n"
                    f"📝 Reason: {reason}"
                )
            )
        except Exception:
            pass

# ─────────────────────────────────────────────────────────────────────────────
#  Auto-decline scheduler (called from bot.py on startup)
# ─────────────────────────────────────────────────────────────────────────────
async def start_auto_decline_scheduler(client):
    import asyncio
    while True:
        await asyncio.sleep(3600)  # check every hour
        try:
            from database.database import get_setting, get_old_pending_requests, decline_request
            days = await get_setting('auto_decline_days') or 0
            if not days or days <= 0:
                continue
            old_reqs = await get_old_pending_requests(days)
            for req in old_reqs:
                await decline_request(req['request_id'], f"Auto-declined after {days} days")
                try:
                    await client.send_message(
                        chat_id=req['user_id'],
                        text=(
                            f"╔══════════════════════╗\n"
                            f"    ❌  <b>REQUEST DECLINED</b>\n"
                            f"╚══════════════════════╝\n\n"
                            f"🆔 ID: <code>{req['request_id']}</code>\n"
                            f"🎬 Title: <b>{req['title']}</b>\n\n"
                            f"📝 Reason: Auto-declined after {days} days of no response.\n"
                            f"You can make a new request anytime!"
                        ),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🎬 New Request", callback_data="request_start")
                        ]])
                    )
                except Exception:
                    pass
        except Exception:
            pass
