#(©)CodeXBotz - Enhanced by Claude

from config import CHANNEL_ID

import base64
import re
import asyncio
import logging
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import FORCE_SUB_CHANNEL, ADMINS, AUTO_DELETE_TIME, AUTO_DEL_SUCCESS_MSG
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait

# ── Force Subscribe check (premium users bypass this) ────────────────────────
async def is_subscribed(filter, client, update):
    # Read force sub channel dynamically from DB (set via /settings)
    from database.database import get_setting
    force_sub = await get_setting('force_sub_channel')
    # Fall back to env variable if not set in DB
    if not force_sub:
        force_sub = FORCE_SUB_CHANNEL
    if not force_sub:
        return True

    user_id = update.from_user.id
    if user_id in ADMINS:
        return True

    # Premium users skip force subscribe
    from database.database import is_premium
    if await is_premium(user_id):
        return True

    # Mode 2: Access on Request — user gets bot access as soon as they send a join request
    # The channel join is still pending approval, but bot access is granted immediately
    from database.database import get_setting as _get_setting
    jr_access  = await _get_setting('join_request_access') or False
    jr_enabled = await _get_setting('join_request_enabled') or False
    if jr_access or jr_enabled:
        try:
            from database.database import database as _db
            doc = _db['join_requests'].find_one({'user_id': user_id})
            if doc:  # Any join request (pending or approved) grants bot access
                return True
        except Exception:
            pass

    try:
        member = await client.get_chat_member(chat_id=int(force_sub), user_id=user_id)
    except UserNotParticipant:
        return False
    except Exception as e:
        if 'Peer id invalid' in str(e) or 'peer_id_invalid' in str(e).lower():
            # Resolve peer via raw API and retry
            try:
                from pyrogram.raw.functions.channels import GetChannels
                from pyrogram.raw.types import InputChannel
                bare = int(str(force_sub).replace('-100', ''))
                result = await client.invoke(GetChannels(id=[InputChannel(channel_id=bare, access_hash=0)]))
                if result and result.chats:
                    await client.storage.update_peers([(bare, result.chats[0].access_hash, 'channel', None, None)])
                member = await client.get_chat_member(chat_id=int(force_sub), user_id=user_id)
            except UserNotParticipant:
                return False
            except Exception:
                return True  # Can't check — let user through
        else:
            return True  # Unknown error — let user through
    # Check member status
    if member.status in [
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.RESTRICTED,
    ]:
        return True
    return False


# ── Join Request check ────────────────────────────────────────────────────────
async def is_join_request_approved(client, force_sub: int, user_id: int) -> bool:
    """Check if user's join request has been approved by admin."""
    from database.database import get_setting
    join_req = await get_setting('join_request_enabled') or False
    if not join_req:
        return True  # Not using join requests
    try:
        member = await client.get_chat_member(chat_id=force_sub, user_id=user_id)
        return member.status in [
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        ]
    except UserNotParticipant:
        return False
    except Exception:
        return False

# ── Ban check ─────────────────────────────────────────────────────────────────
async def is_user_banned(filter, client, update):
    from database.database import is_banned
    user_id = update.from_user.id
    if user_id in ADMINS:
        return False
    return await is_banned(user_id)

# ── Encode / Decode ───────────────────────────────────────────────────────────
async def encode(string: str) -> str:
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    return (base64_bytes.decode("ascii")).strip("=")

async def decode(base64_string: str) -> str:
    base64_string = base64_string.strip("=")
    base64_bytes  = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes  = base64.urlsafe_b64decode(base64_bytes)
    return string_bytes.decode("ascii")

# ── Fetch messages from DB channel in batches ─────────────────────────────────
async def get_messages(client, message_ids: list) -> list:
    messages = []
    total    = 0
    while total != len(message_ids):
        batch = message_ids[total:total + 200]
        try:
            msgs = await client.get_messages(
                chat_id=CHANNEL_ID,
                message_ids=batch
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
            msgs = await client.get_messages(
                chat_id=CHANNEL_ID,
                message_ids=batch
            )
        except Exception as ex:
            logging.getLogger(__name__).warning(f"get_messages error: {ex}")
            msgs = []
        total    += len(batch)
        messages += msgs
    return messages

# ── Resolve a message ID from a forwarded post or t.me link ──────────────────
async def get_message_id(client, message) -> int:
    if message.forward_from_chat:
        if message.forward_from_chat.id == CHANNEL_ID:
            return message.forward_from_message_id
        return 0
    elif message.forward_sender_name:
        return 0
    elif message.text:
        matches = re.match(r"https://t\.me/(?:c/)?(.+)/(\d+)", message.text)
        if not matches:
            return 0
        channel_id = matches.group(1)
        msg_id     = int(matches.group(2))
        if channel_id.isdigit():
            if f"-100{channel_id}" == str(CHANNEL_ID):
                return msg_id
        else:
            # channel_id is a username string (e.g. "mychannel") — match by name
            if isinstance(CHANNEL_ID, str) and channel_id == CHANNEL_ID.lstrip("@"):
                return msg_id
    return 0

# ── Human-readable uptime ─────────────────────────────────────────────────────
def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time

# ── Auto-delete helper — PERMANENTLY DISABLED ────────────────────────────────
async def delete_file(messages: list, client, process, user_id: int = None):
    """
    Auto-delete is permanently disabled.
    File links are never deleted for any reason.
    This function is a no-op kept for import compatibility.
    """
    return

# ── Pyrogram filters ──────────────────────────────────────────────────────────
subscribed  = filters.create(is_subscribed)
banned_user = filters.create(is_user_banned)
