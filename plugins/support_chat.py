#(©)CodeXBotz - Enhanced by Claude
# Admin ↔ User Support Chat Panel

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot import Bot
from config import ADMINS, OWNER_ID
from database.database import (
    open_chat_session, close_chat_session, get_chat_session,
    get_all_active_chats, get_session_by_user, get_bot_admins
)

# ─────────────────────────────────────────────────────────────────────────────
#  /support — user opens a chat session with admin
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('support') & filters.private)
async def support_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    all_admins = list(set(ADMINS + await get_bot_admins()))

    if user_id in all_admins:
        # Admin used /support — show active chats panel
        await show_admin_chat_panel(client, message)
        return

    # Check if already in session
    session = await get_chat_session(user_id)
    if session:
        await message.reply(
            "💬 <b>You already have an active support session.</b>\n\n"
            "Just send your message and admin will reply.\n"
            "Use /closechat to end the session."
        )
        return

    # Open session
    await open_chat_session(user_id)

    await message.reply(
        "💬 <b>Support Session Opened!</b>\n\n"
        "An admin will respond shortly. Just type your message below.\n\n"
        "Use /closechat to end the session.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Close Chat", callback_data="close_my_chat")
        ]])
    )

    # Notify all admins
    notify_text = (
        f"💬 <b>New Support Request</b>\n\n"
        f"👤 User: <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a> "
        f"(<code>{user_id}</code>)\n\n"
        f"Use /chatto {user_id} to reply."
    )
    for admin_id in all_admins:
        try:
            await client.send_message(
                chat_id=admin_id,
                text=notify_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        f"💬 Chat with {message.from_user.first_name}",
                        callback_data=f"admin_chat_{user_id}"
                    )
                ]])
            )
        except Exception:
            pass


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

    # Store admin's active chat target in memory (bot attribute)
    if not hasattr(client, 'admin_chat_targets'):
        client.admin_chat_targets = {}
    client.admin_chat_targets[message.from_user.id] = target_id

    await message.reply(
        f"💬 <b>Now chatting with user <code>{target_id}</code></b>\n\n"
        f"All your messages will be forwarded to them.\n"
        f"Use /endchat to stop replying to this user."
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /endchat — admin stops replying to current user
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
    await message.reply(f"✅ Stopped chatting with user <code>{target_id}</code>.")


# ─────────────────────────────────────────────────────────────────────────────
#  /closechat — user closes their support session
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('closechat') & filters.private)
async def close_chat_cmd(client: Client, message: Message):
    user_id    = message.from_user.id
    all_admins = list(set(ADMINS + await get_bot_admins()))

    if user_id in all_admins:
        await message.reply("Admins use /endchat to stop replying to a user.")
        return

    session = await get_chat_session(user_id)
    if not session:
        await message.reply("❌ You don't have an active support session.")
        return

    await close_chat_session(user_id)
    await message.reply("✅ <b>Support session closed.</b> Thank you!")

    # Notify admins
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
        "\n".join(lines) + "\n\nClick a button to start chatting:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Relay: Admin → User (only when admin has active chat target)
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.private & filters.user(ADMINS) & ~filters.command([
    'start','support','closechat','request','mystatus','premium',
    'users','broadcast','batch','genlink','stats','ban','unban',
    'banned','filestats','requests','approverequest','approveall',
    'addpremium','removepremium','listpremium','allrequests',
    'fulfill','decline','chatto','endchat','activechats',
    'addadmin','removeadmin','listadmins','togglepremium','setdailylimit',
    'settings','announce','setpayment','setqr','help','profile'
]), group=-1)
async def relay_admin_to_user(client: Client, message: Message):
    admin_id = message.from_user.id
    if not hasattr(client, 'admin_chat_targets'):
        client.admin_chat_targets = {}
    target_id = client.admin_chat_targets.get(admin_id)
    if not target_id:
        # Admin is not in chat mode — let other handlers process this
        return
    try:
        await message.copy(chat_id=target_id)
        await message.reply("✓ <i>Sent</i>", quote=True)
    except Exception as e:
        await message.reply(f"❌ Failed to send: {e}", quote=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Relay: User → Admin (only when user has active support session)
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.private & ~filters.user(ADMINS) & ~filters.command([
    'start','support','closechat','request','mystatus','premium'
]))
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
    await message.reply("✅ <i>Message sent to admin. Please wait for a reply.</i>", quote=True)


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

    await query.answer(f"Now chatting with {target_id}")
    await query.message.reply(
        f"💬 <b>Now chatting with <code>{target_id}</code></b>\n"
        f"All your messages will be forwarded. Use /endchat to stop."
    )


@Bot.on_callback_query(filters.regex(r"^close_my_chat$"))
async def close_my_chat_callback(client: Client, query: CallbackQuery):
    user_id    = query.from_user.id
    all_admins = list(set(ADMINS + await get_bot_admins()))
    await close_chat_session(user_id)
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
