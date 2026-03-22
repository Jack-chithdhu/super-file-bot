#(©)CodeXBotz - Enhanced by Claude

from config import CHANNEL_ID

import base64
import re
import asyncio
import logging
from pyrogram import filters
from pyrogram.errors import FloodWait
from config import ADMINS, AUTO_DELETE_TIME, AUTO_DEL_SUCCESS_MSG

# ── Force Subscribe check — delegates entirely to force_sub.py ───────────────
async def is_subscribed(filter, client, update):
    from plugins.force_sub import check_subscription
    return await check_subscription(client, update.from_user.id)

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
