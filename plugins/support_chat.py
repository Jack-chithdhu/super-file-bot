#(©)CodeXBotz - Enhanced by Claude
# Admin ↔ User Support Chat Panel

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot import Bot
from config import ADMINS, OWNER_ID
from database.database import (
    open_chat_session, close_chat_session, get_chat_session,
    get_all_active_chats, get_session_by_user, get_bot_admins,
    get_setting, set_setting
)

# ── In-memory support request queue ──────────────────────────────────────────
# {user_id: {'name': str, 'notif_msg_ids': {admin_id: msg_id}}}
support_queue = {}

# ─────────────────────────────────────────────────────────────────────────────
#  /support — user opens a chat session with admin
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('support') & filters.private)
async def support_cmd(client: Client, message: Message):
    user_id    = message.from_user.id
    all_admins = list(set(ADMINS + await get_bot_admins()))

    if user_id in all_admins:
        await message.reply(
            "⚙️ <b>You are an admin!</b>\n\n"
            "Use /activechats to see active support sessions.\n"
            "Use /chatto <code>&lt;user_id&gt;</code> to chat with a user."
        )
        return

    # Check support system enabled
    support_on = await get_setting('support_enabled')
    if support_on is None:
        support_on = True
    if not support_on:
        custom_msg = await get_setting('support_off_message') or (
            "❌ <b>Support is currently unavailable.</b>\n\n"
            "Please try again later."
        )
        await message.reply(custom_msg)
        return

    # Check if already in session
    session = await get_chat_session(user_id)
    if session:
        await message.reply(
            "💬 <b>You already have an active support session.</b>\n\n"
            "Just send your message below.\n"
            "Use /closechat to end.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Close Chat", callback_data="close_my_chat")
            ]])
        )
        return

    # Check queue — don't add duplicate
    if user_id in support_queue:
        await message.reply(
            "⏳ <b>You're already in the queue.</b>\n\n"
            "Please wait for an admin to accept your request."
        )
        return

    await open_chat_session(user_id)

    await message.reply(
        "💬 <b>Support Request Sent!</b>\n\n"
        "An admin will respond shortly. Just type your message below.\n\n"
        "Use /closechat to cancel.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel Request", callback_data="close_my_chat")
        ]])
    )

    # Notify all admins ONCE with accept/decline buttons
    notify_text = (
        f"🔔 <b>New Support Request</b>\n\n"
        f"👤 <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a> "
        f"(<code>{user_id}</code>)\n\n"
        f"Tap below to accept or dismiss."
    )

    notif_ids = {}
    for admin_id in all_admins:
        try:
            sent = await client.send_message(
                chat_id=admin_id,
                text=notify_text,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            f"💬 Accept",
                            callback_data=f"admin_chat_{user_id}"
                        ),
                        InlineKeyboardButton(
                            f"❌ Dismiss",
                            callback_data=f"support_dismiss_{user_id}"
                        ),
                    ]
                ])
            )
            notif_ids[admin_id] = sent.id
        except Exception:
            pass

    # Store in queue
    support_queue[user_id] = {
        'name': message.from_user.first_name,
        'notif_msg_ids': notif_ids
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Dismiss support request
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^support_dismiss_(\d+)$"))
async def support_dismiss(client: Client, query: CallbackQuery):
    all_admins = list(set(ADMINS + await get_bot_admins()))
    if query.from_user.id not in all_admins:
        await query.answer("❌ Not an admin.", show_alert=True)
        return

    user_id = int(query.data.split("_")[2])

    # Close session and remove from queue
    await close_chat_session(user_id)
    queue_data = support_queue.pop(user_id, None)

    # Edit all admin notifications to show dismissed
    if queue_data:
        for admin_id, msg_id in queue_data['notif_msg_ids'].items():
            try:
                await client.edit_message_text(
                    chat_id=admin_id,
                    message_id=msg_id,
                    text=f"❌ <b>Support request dismissed</b>\n\nUser: <code>{user_id}</code>",
                )
            except Exception:
                pass

    # Notify user
    try:
        await client.send_message(
            chat_id=user_id,
            text=(
                "ℹ️ <b>Support request dismissed.</b>\n\n"
                "The admin is currently unavailable. Please try again later."
            )
        )
    except Exception:
        pass

    await query.answer("✅ Request dismissed.")


# ─────────────────────────────────────────────────────────────────────────────
#  /chatto <user_id> — admin starts replying to a specific user
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('chatto') & filters.private & filters.user(ADMINS))
async def chat_to_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/chatto &lt;user_id&gt;</code>")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await message.reply("❌ Invalid user_id.")
        return

    session = await get_session_by_user(target_id)
    if not session or not session.get('active'):
        await message.reply(f"❌ No active support session for user <code>{target_id}</code>.")
        return

    if not hasattr(client, 'admin_chat_targets'):
        client.admin_chat_targets = {}
    client.admin_chat_targets[message.from_user.id] = target_id

    await message.reply(
        f"💬 <b>Now chatting with <code>{target_id}</code></b>\n\n"
        f"All your messages will be forwarded.\n"
        f"Use /endchat to stop."
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /endchat — admin stops replying
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('endchat') & filters.private & filters.user(ADMINS))
async def end_chat_admin(client: Client, message: Message):
    if not hasattr(client, 'admin_chat_targets'):
        client.admin_chat_targets = {}
    admin_id = message.from_user.id
    if admin_id not in client.admin_chat_targets:
        await message.reply("❌ You are not in any active chat session.")
        return
    target_id = client.admin_chat_targets.pop(admin_id)
    await message.reply(f"✅ Stopped chatting with <code>{target_id}</code>.")

    # Also close the user session and notify them
    await close_chat_session(target_id)
    support_queue.pop(target_id, None)
    try:
        await client.send_message(
            chat_id=target_id,
            text="ℹ️ <b>Support session ended by admin.</b>\n\nUse /support to start a new session."
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  /closechat — user closes their support session
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('closechat') & filters.private)
async def close_chat_cmd(client: Client, message: Message):
    user_id    = message.from_user.id
    all_admins = list(set(ADMINS + await get_bot_admins()))

    if user_id in all_admins:
        await message.reply("Admins use /endchat to stop replying.")
        return

    session = await get_chat_session(user_id)
    if not session:
        await message.reply("❌ You don't have an active support session.")
        return

    await close_chat_session(user_id)
    support_queue.pop(user_id, None)
    await message.reply("✅ <b>Support session closed.</b>")

    for admin_id in all_admins:
        try:
            await client.send_message(
                chat_id=admin_id,
                text=f"ℹ️ User <code>{user_id}</code> closed their support session."
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  /activechats — admin sees all open sessions
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('activechats') & filters.private & filters.user(ADMINS))
async def active_chats_cmd(client: Client, message: Message):
    await show_admin_chat_panel(client, message)


@Bot.on_message(filters.command('clearallchats') & filters.private & filters.user(ADMINS))
async def clear_all_chats_cmd(client: Client, message: Message):
    from database.database import clear_all_chat_sessions
    await clear_all_chat_sessions()
    support_queue.clear()
    if hasattr(client, 'admin_chat_targets'):
        client.admin_chat_targets.clear()
    await message.reply("✅ <b>All support sessions cleared!</b>\n\nAll active sessions have been force-closed.")


@Bot.on_message(filters.command('clearchat') & filters.private & filters.user(ADMINS))
async def clear_single_chat_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply(
            "ℹ️ <b>Usage:</b> <code>/clearchat &lt;user_id&gt;</code>\n\n"
            "Clears a single user support session."
        )
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await message.reply("❌ Invalid user ID.")
        return

    await close_chat_session(user_id)
    support_queue.pop(user_id, None)

    # Remove from admin chat targets if active
    if hasattr(client, 'admin_chat_targets'):
        for admin_id, target in list(client.admin_chat_targets.items()):
            if target == user_id:
                client.admin_chat_targets.pop(admin_id, None)

    # Notify the user
    try:
        await client.send_message(
            chat_id=user_id,
            text="ℹ️ <b>Your support session has been cleared by admin.</b>\n\nUse /support to start a new session."
        )
    except Exception:
        pass

    await message.reply(f"✅ Support session for <code>{user_id}</code> cleared!")


async def show_admin_chat_panel(client: Client, message: Message):
    sessions = await get_all_active_chats()
    if not sessions:
        await message.reply("💬 <b>No active support sessions.</b>")
        return
    lines   = [f"💬 <b>Active Support Sessions ({len(sessions)})</b>\n"]
    buttons = []
    for s in sessions:
        uid = s['user_id']
        lines.append(f"• User <code>{uid}</code>")
        buttons.append([
            InlineKeyboardButton(f"💬 Chat with {uid}", callback_data=f"admin_chat_{uid}")
        ])
    await message.reply(
        "\n".join(lines) + "\n\nTap to start chatting:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Relay: Admin → User (priority group -1)
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.private & filters.user(ADMINS) & ~filters.command([
    'start','support','closechat','request','mystatus','premium',
    'users','broadcast','batch','genlink','stats','ban','unban',
    'banned','filestats','requests','approverequest','approveall',
    'addpremium','removepremium','listpremium','allrequests',
    'fulfill','decline','chatto','endchat','activechats',
    'addadmin','removeadmin','listadmins','togglepremium','setdailylimit',
    'settings','announce','setpayment','setqr','help','profile',
    'addfile','getfiles','listfiles','deletefile','newcollection','listcollections','filestore','cancel','linkstats',
    'clearjoinrequests','adminhelp'
]), group=-1)
async def relay_admin_to_user(client: Client, message: Message):
    admin_id = message.from_user.id
    if not hasattr(client, 'admin_chat_targets'):
        client.admin_chat_targets = {}
    target_id = client.admin_chat_targets.get(admin_id)
    if not target_id:
        return
    try:
        await message.copy(chat_id=target_id)
        await message.reply("✓ <i>Sent</i>", quote=True)
    except Exception as e:
        await message.reply(f"❌ Failed: {e}", quote=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Relay: User → Admin (priority group -1)
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.private & ~filters.user(ADMINS) & ~filters.command([
    'start','support','closechat','request','mystatus','premium'
]), group=-1)
async def relay_user_to_admin(client: Client, message: Message):
    user_id = message.from_user.id
    session = await get_chat_session(user_id)
    if not session:
        return
    all_admins = list(set(ADMINS + await get_bot_admins()))
    relay_header = (
        f"💬 <b>Message from</b> "
        f"<a href='tg://user?id={user_id}'>{message.from_user.first_name}</a> "
        f"(<code>{user_id}</code>):\n"
    )
    for admin_id in all_admins:
        try:
            await client.send_message(chat_id=admin_id, text=relay_header)
            await message.copy(chat_id=admin_id)
        except Exception:
            pass
    await message.reply("✅ <i>Sent to admin.</i>", quote=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Callbacks
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^admin_chat_(\d+)$"))
async def admin_chat_callback(client: Client, query: CallbackQuery):
    all_admins = list(set(ADMINS + await get_bot_admins()))
    if query.from_user.id not in all_admins:
        await query.answer("❌ Not an admin.", show_alert=True)
        return

    target_id = int(query.data.split("_")[2])
    if not hasattr(client, 'admin_chat_targets'):
        client.admin_chat_targets = {}
    client.admin_chat_targets[query.from_user.id] = target_id

    # Edit all admin notifications to show accepted
    queue_data = support_queue.get(target_id)
    if queue_data:
        for admin_id, msg_id in queue_data['notif_msg_ids'].items():
            try:
                await client.edit_message_text(
                    chat_id=admin_id,
                    message_id=msg_id,
                    text=(
                        f"✅ <b>Request accepted by</b> "
                        f"<a href='tg://user?id={query.from_user.id}'>{query.from_user.first_name}</a>\n\n"
                        f"User: <code>{target_id}</code>"
                    )
                )
            except Exception:
                pass

    await query.answer(f"Now chatting with {target_id}")
    await query.message.reply(
        f"💬 <b>Now chatting with <code>{target_id}</code></b>\n"
        f"All your messages will be forwarded. Use /endchat to stop."
    )

    # Notify user that admin accepted
    try:
        await client.send_message(
            chat_id=target_id,
            text=f"✅ <b>Admin is now with you!</b>\n\nYou can send your message now."
        )
    except Exception:
        pass


@Bot.on_callback_query(filters.regex(r"^close_my_chat$"))
async def close_my_chat_callback(client: Client, query: CallbackQuery):
    user_id    = query.from_user.id
    all_admins = list(set(ADMINS + await get_bot_admins()))
    await close_chat_session(user_id)
    support_queue.pop(user_id, None)
    await query.message.edit_text("✅ <b>Support session closed.</b>")
    for admin_id in all_admins:
        try:
            await client.send_message(
                chat_id=admin_id,
                text=f"ℹ️ User <code>{user_id}</code> closed their support session."
            )
        except Exception:
            pass
    await query.answer("Session closed.")
