#(©)CodeXBotz - Enhanced by Claude
#
# force_sub.py — single source of truth for all force-subscribe logic.
#
# Every other module (helper_func, start, captcha) imports from here.
# No force-sub logic lives anywhere else.

from __future__ import annotations

import logging
from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMINS, FORCE_SUB_CHANNEL, FORCE_MSG, JOIN_REQUEST_ENABLE

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_active_channel() -> int | None:
    """Return the active force-sub channel ID (DB takes priority over env)."""
    from database.database import get_setting
    db_val = await get_setting('force_sub_channel')
    ch = db_val or FORCE_SUB_CHANNEL
    log.info(f"_get_active_channel: db_val={db_val!r}, env={FORCE_SUB_CHANNEL!r}, using={ch!r}")
    if not ch:
        return None
    try:
        return int(ch)
    except (ValueError, TypeError):
        return None


async def _resolve_peer(client: Client, channel_id: int) -> None:
    """Pre-warm Pyrogram's peer cache for a channel using access_hash=0.
    Safe to call before get_chat_member — silently ignores failures."""
    try:
        from pyrogram.raw.functions.channels import GetChannels
        from pyrogram.raw.types import InputChannel
        bare = int(str(channel_id).replace('-100', ''))
        result = await client.invoke(
            GetChannels(id=[InputChannel(channel_id=bare, access_hash=0)])
        )
        if result and result.chats:
            await client.storage.update_peers([
                (bare, result.chats[0].access_hash, 'channel', None, None)
            ])
    except Exception as e:
        log.debug(f"_resolve_peer({channel_id}): {e}")


async def _is_join_request_mode() -> tuple[bool, bool]:
    """Returns (join_request_enabled, join_request_access)."""
    from database.database import get_setting
    jr_on     = bool(await get_setting('join_request_enabled') or False)
    jr_access = bool(await get_setting('join_request_access') or False)
    # Also respect the legacy env flag
    if JOIN_REQUEST_ENABLE:
        jr_on = True
    return jr_on, jr_access


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

async def get_invite_link(client: Client) -> str | None:
    """Return the best available invite link for the active force-sub channel.

    Priority:
    1. If join-request mode is on  → create a fresh join-request invite link
    2. channel.invite_link from get_chat()
    3. client.invitelink (set at startup, may be stale — last resort)
    4. Fallback t.me/c/ deep link
    """
    channel_id = await _get_active_channel()
    if not channel_id:
        return None

    await _resolve_peer(client, channel_id)

    jr_on, jr_access = await _is_join_request_mode()

    if jr_on or jr_access:
        try:
            link = await client.create_chat_invite_link(
                chat_id=channel_id, creates_join_request=True
            )
            return link.invite_link
        except Exception as e:
            log.warning(f"create_chat_invite_link failed: {e}")

    try:
        chat = await client.get_chat(channel_id)
        if chat.invite_link:
            return chat.invite_link
        # Bot is admin — export a permanent link
        return await client.export_chat_invite_link(channel_id)
    except Exception as e:
        log.warning(f"get_chat invite link failed: {e}")

    # Last resort: startup-cached link
    cached = getattr(client, 'invitelink', None)
    if cached:
        return cached

    return f"https://t.me/c/{str(channel_id).replace('-100', '')}"


async def check_subscription(client: Client, user_id: int) -> bool:
    if user_id in ADMINS:
        return True

    channel_id = await _get_active_channel()
    if not channel_id:
        log.info(f"check_subscription: no force-sub channel configured — letting user {user_id} through")
        return True

    log.info(f"check_subscription: checking user {user_id} against channel {channel_id}")

    from database.database import is_premium
    if await is_premium(user_id):
        log.info(f"check_subscription: user {user_id} is premium — bypass")
        return True

    _, jr_access = await _is_join_request_mode()
    if jr_access:
        try:
            from database.database import get_pending_requests
            pending = await get_pending_requests(limit=1000)
            if any(r['user_id'] == user_id for r in pending):
                log.info(f"check_subscription: user {user_id} has pending join request — bypass")
                return True
        except Exception:
            pass

    await _resolve_peer(client, channel_id)
    try:
        member = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
    except UserNotParticipant:
        log.info(f"check_subscription: user {user_id} is NOT a member of {channel_id}")
        return False
    except Exception as e:
        log.warning(f"check_subscription: get_chat_member error for user {user_id}: {e}")
        return False  # Fail closed — block the user, don't silently let them through

    result = member.status in (
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.RESTRICTED,
    )
    log.info(f"check_subscription: user {user_id} status={member.status} → {'pass' if result else 'block'}")
    return result


async def send_force_sub_message(client: Client, target, payload: str = "") -> None:
    """Send the 'please join' message to a user.

    `target` can be a Message or a CallbackQuery (or anything with
    .from_user and a way to reply). We handle both cases.
    """
    from pyrogram.types import Message, CallbackQuery

    user   = target.from_user
    invite = await get_invite_link(client)
    if not invite:
        return

    try_again_url = f"https://t.me/{client.username}?start={payload or 'start'}"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=invite)],
        [InlineKeyboardButton("🔄 Try Again",    url=try_again_url)],
    ])

    text = FORCE_MSG.format(
        first   = user.first_name,
        last    = user.last_name or "",
        username= None if not user.username else "@" + user.username,
        mention = user.mention,
        id      = user.id,
    )

    if isinstance(target, Message):
        await target.reply(text, reply_markup=buttons,
                           quote=True, disable_web_page_preview=True)
    elif isinstance(target, CallbackQuery):
        await client.send_message(
            chat_id=user.id, text=text,
            reply_markup=buttons, disable_web_page_preview=True
        )
    else:
        await client.send_message(
            chat_id=user.id, text=text,
            reply_markup=buttons, disable_web_page_preview=True
        )
