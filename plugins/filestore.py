#(©)CodeXBotz - Enhanced by Claude
# File Store Mode — Admin/Owner only menu for link and collection management

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot import Bot
from config import ADMINS, OWNER_ID, CHANNEL_ID
from helper_func import encode, get_message_id
from database.database import get_setting

# ─────────────────────────────────────────────────────────────────────────────
#  DB helpers — stored in MongoDB 'filestore' collection
# ─────────────────────────────────────────────────────────────────────────────
def _col():
    from database.database import database
    return database['filestore_links']

def _col_stats():
    from database.database import database
    return database['filestore_stats']

async def _save_link(name: str, link: str, created_by: int, collection: str = "") -> str:
    """Save a named link. Returns its short ID."""
    import time, random, string
    link_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    col = _col()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: col.insert_one({
        'link_id':    link_id,
        'name':       name,
        'link':       link,
        'created_by': created_by,
        'collection': collection,
        'created_at': __import__('datetime').datetime.utcnow(),
    }))
    return link_id

async def _get_all_links(created_by: int = None) -> list:
    col = _col()
    loop = asyncio.get_event_loop()
    query = {'created_by': created_by} if created_by else {}
    return await loop.run_in_executor(None, lambda: list(col.find(query).sort('created_at', -1)))

async def _get_link(link_id: str) -> dict:
    col = _col()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: col.find_one({'link_id': link_id}))

async def _delete_link(link_id: str):
    col = _col()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: col.delete_one({'link_id': link_id}))

async def _get_collections() -> list:
    """Return distinct non-empty collection names."""
    col = _col()
    loop = asyncio.get_event_loop()
    names = await loop.run_in_executor(None, lambda: col.distinct('collection', {'collection': {'$ne': ''}}))
    return names

async def _get_links_in_collection(collection: str) -> list:
    col = _col()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: list(col.find({'collection': collection}).sort('name', 1)))

async def _record_access(link_id: str, user_id: int):
    col = _col_stats()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: col.update_one(
        {'link_id': link_id},
        {'$inc': {'total_access': 1}, '$addToSet': {'unique_users': user_id}},
        upsert=True
    ))

async def _get_stats(link_id: str) -> dict:
    col = _col_stats()
    loop = asyncio.get_event_loop()
    doc = await loop.run_in_executor(None, lambda: col.find_one({'link_id': link_id}))
    if not doc:
        return {'total_access': 0, 'unique_users': []}
    return doc


# ─────────────────────────────────────────────────────────────────────────────
#  /filestore — open the File Store Mode menu
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('filestore') & filters.private & filters.user(ADMINS))
async def filestore_menu(client: Client, message: Message):
    await _send_filestore_home(client, message.chat.id)


async def _send_filestore_home(client, chat_id, message_id=None):
    text = (
        "╔══════════════════════════╗\n"
        "   🗂  <b>FILE STORE MODE</b>\n"
        "╚══════════════════════════╝\n\n"
        "Manage your file links and collections.\n\n"
        "🔗 <b>Links</b> — named single or batch links\n"
        "📦 <b>Collections</b> — grouped links (S1 480p, S1 720p…)\n"
        "📊 <b>Stats</b> — access counts per link\n"
        "⚡ <b>Generate</b> — create new links fast"
    )
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔗 My Links",      callback_data="fs_mylinks"),
            InlineKeyboardButton("📦 Collections",   callback_data="fs_collections"),
        ],
        [
            InlineKeyboardButton("📊 Link Stats",    callback_data="fs_stats_menu"),
            InlineKeyboardButton("⚡ Generate Link", callback_data="fs_generate"),
        ],
        [InlineKeyboardButton("🔒 Close", callback_data="close")],
    ])
    if message_id:
        try:
            await client.edit_message_text(chat_id, message_id, text, reply_markup=markup)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=markup)
    else:
        await client.send_message(chat_id, text, reply_markup=markup)


# ─────────────────────────────────────────────────────────────────────────────
#  My Links
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^fs_mylinks$") & filters.user(ADMINS))
async def fs_mylinks(client: Client, query: CallbackQuery):
    links = await _get_all_links()
    if not links:
        await query.message.edit_text(
            "🔗 <b>My Links</b>\n\nNo links saved yet.\nUse ⚡ Generate Link to create one.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ Generate Link", callback_data="fs_generate")],
                [InlineKeyboardButton("🔙 Back", callback_data="fs_home")],
            ])
        )
        await query.answer()
        return

    # Show paginated list — 8 per page
    buttons = []
    for lnk in links[:8]:
        coll_tag = f" [{lnk['collection']}]" if lnk.get('collection') else ""
        buttons.append([InlineKeyboardButton(
            f"🔗 {lnk['name']}{coll_tag}",
            callback_data=f"fs_link_{lnk['link_id']}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fs_home")])

    await query.message.edit_text(
        f"🔗 <b>Saved Links</b> ({len(links)} total)\n\nTap a link to view or manage it:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^fs_link_(.+)$") & filters.user(ADMINS))
async def fs_link_detail(client: Client, query: CallbackQuery):
    link_id = query.data.split("_", 2)[2]
    lnk = await _get_link(link_id)
    if not lnk:
        await query.answer("Link not found.", show_alert=True)
        return

    stats = await _get_stats(link_id)
    coll  = lnk.get('collection') or "—"

    await query.message.edit_text(
        f"🔗 <b>{lnk['name']}</b>\n\n"
        f"🆔 ID: <code>{link_id}</code>\n"
        f"📦 Collection: {coll}\n"
        f"👁 Accessed: <b>{stats['total_access']}</b> times\n"
        f"👤 Unique users: <b>{len(stats['unique_users'])}</b>\n\n"
        f"🔗 {lnk['link']}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Delete", callback_data=f"fs_del_{link_id}")],
            [InlineKeyboardButton("🔙 Back",   callback_data="fs_mylinks")],
        ]),
        disable_web_page_preview=True
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^fs_del_(.+)$") & filters.user(ADMINS))
async def fs_delete_link(client: Client, query: CallbackQuery):
    link_id = query.data.split("_", 2)[2]
    lnk = await _get_link(link_id)
    if not lnk:
        await query.answer("Already deleted.", show_alert=True)
        return
    await _delete_link(link_id)
    await query.answer(f"✅ '{lnk['name']}' deleted.", show_alert=True)
    await fs_mylinks(client, query)


# ─────────────────────────────────────────────────────────────────────────────
#  Collections
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^fs_collections$") & filters.user(ADMINS))
async def fs_collections(client: Client, query: CallbackQuery):
    collections = await _get_collections()
    if not collections:
        await query.message.edit_text(
            "📦 <b>Collections</b>\n\nNo collections yet.\n"
            "When generating a link, assign it to a collection to group it here.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ Generate Link", callback_data="fs_generate")],
                [InlineKeyboardButton("🔙 Back",          callback_data="fs_home")],
            ])
        )
        await query.answer()
        return

    buttons = [[InlineKeyboardButton(f"📦 {c}", callback_data=f"fs_coll_{c}")] for c in collections]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fs_home")])

    await query.message.edit_text(
        f"📦 <b>Collections</b> ({len(collections)} total)\n\nTap a collection to browse its links:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^fs_coll_(.+)$") & filters.user(ADMINS))
async def fs_collection_detail(client: Client, query: CallbackQuery):
    coll_name = query.data[8:]
    links = await _get_links_in_collection(coll_name)

    if not links:
        await query.answer("Collection is empty.", show_alert=True)
        return

    buttons = []
    for lnk in links:
        buttons.append([InlineKeyboardButton(
            f"🔗 {lnk['name']}",
            callback_data=f"fs_link_{lnk['link_id']}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fs_collections")])

    await query.message.edit_text(
        f"📦 <b>{coll_name}</b> — {len(links)} link(s)",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer()


# ─────────────────────────────────────────────────────────────────────────────
#  Stats Menu
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^fs_stats_menu$") & filters.user(ADMINS))
async def fs_stats_menu(client: Client, query: CallbackQuery):
    links = await _get_all_links()
    if not links:
        await query.message.edit_text(
            "📊 <b>Link Stats</b>\n\nNo links yet.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="fs_home")]])
        )
        await query.answer()
        return

    # Show top 10 by access
    stats_list = []
    for lnk in links:
        s = await _get_stats(lnk['link_id'])
        stats_list.append((lnk['name'], lnk['link_id'], s['total_access'], len(s['unique_users'])))

    stats_list.sort(key=lambda x: x[2], reverse=True)

    lines = ["📊 <b>Link Stats</b> (top by access)\n"]
    for name, lid, total, unique in stats_list[:10]:
        lines.append(f"🔗 <b>{name}</b> — <code>{lid}</code>\n   👁 {total} access · 👤 {unique} unique\n")

    await query.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="fs_home")]])
    )
    await query.answer()


# ─────────────────────────────────────────────────────────────────────────────
#  Generate Link — full guided flow
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^fs_generate$") & filters.user(ADMINS))
async def fs_generate(client: Client, query: CallbackQuery):
    await query.message.edit_text(
        "⚡ <b>Generate Link</b>\n\nWhat type of link?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📄 Single File", callback_data="fs_gen_single"),
                InlineKeyboardButton("📦 Batch Range", callback_data="fs_gen_batch"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="fs_home")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^fs_gen_(single|batch)$") & filters.user(ADMINS))
async def fs_gen_type(client: Client, query: CallbackQuery):
    gen_type = query.data.split("_")[2]  # single or batch
    user_id  = query.from_user.id

    if not hasattr(client, '_fs_gen'):
        client._fs_gen = {}
    client._fs_gen[user_id] = {'type': gen_type}

    await query.message.edit_text(
        f"⚡ <b>{'Single File' if gen_type == 'single' else 'Batch Range'} Link</b>\n\n"
        f"Forward the {'message' if gen_type == 'single' else 'FIRST message'} from the DB Channel, "
        f"or paste its post link.\n\n<i>Or send /cancel to abort.</i>"
    )
    await query.answer()


@Bot.on_message(filters.private & filters.user(ADMINS) &
                (filters.forwarded | filters.text) & ~filters.command([
    'start','filestore','batch','genlink','cancel',
    'ban','unban','fulfill','decline','broadcast','addpremium',
    'removepremium','listpremium','allrequests','approverequest',
    'approveall','addadmin','removeadmin','listadmins',
    'togglepremium','setdailylimit','adminhelp','stats',
    'users','filestats','requests','chatto','endchat','activechats',
    'clearjoinrequests','addfile','getfiles','listfiles','deletefile',
    'linkstats','settings','announce','setpayment','setqr','help','profile'
]), group=2)
async def fs_gen_input(client: Client, message: Message):
    user_id = message.from_user.id

    if not hasattr(client, '_fs_gen') or user_id not in client._fs_gen:
        return  # not in generate flow

    state    = client._fs_gen[user_id]
    gen_type = state.get('type')
    step     = state.get('step', 'first')

    # ── Single file flow ───────────────────────────────────────────────────
    if gen_type == 'single':
        msg_id = await get_message_id(client, message)
        if not msg_id:
            await message.reply("❌ Invalid. Forward from DB Channel or paste a valid post link.")
            return

        base64_string = await encode(f"get-{msg_id * abs(CHANNEL_ID)}")
        link = f"https://t.me/{client.username}?start={base64_string}"

        client._fs_gen[user_id]['link']  = link
        client._fs_gen[user_id]['step']  = 'name'
        await message.reply(
            f"✅ Link ready:\n<code>{link}</code>\n\n"
            "📝 Now send a <b>name</b> for this link (e.g. 'AOT S1 720p'):",
            disable_web_page_preview=True
        )

    # ── Batch flow — first message ─────────────────────────────────────────
    elif gen_type == 'batch' and step == 'first':
        msg_id = await get_message_id(client, message)
        if not msg_id:
            await message.reply("❌ Invalid. Forward from DB Channel or paste a valid post link.")
            return
        client._fs_gen[user_id]['first_id'] = msg_id
        client._fs_gen[user_id]['step']     = 'last'
        await message.reply("✅ First message set.\n\nNow forward the <b>last</b> message or paste its link:")

    # ── Batch flow — last message ──────────────────────────────────────────
    elif gen_type == 'batch' and step == 'last':
        msg_id = await get_message_id(client, message)
        if not msg_id:
            await message.reply("❌ Invalid. Forward from DB Channel or paste a valid post link.")
            return

        f_id = client._fs_gen[user_id]['first_id']
        s_id = msg_id
        count = abs(s_id - f_id) + 1
        string = f"get-{f_id * abs(CHANNEL_ID)}-{s_id * abs(CHANNEL_ID)}"
        base64_string = await encode(string)
        link = f"https://t.me/{client.username}?start={base64_string}"

        client._fs_gen[user_id]['link']  = link
        client._fs_gen[user_id]['count'] = count
        client._fs_gen[user_id]['step']  = 'name'
        await message.reply(
            f"✅ Batch link ready ({count} files):\n<code>{link}</code>\n\n"
            "📝 Now send a <b>name</b> for this link (e.g. 'AOT S1 Ep1-12 720p'):",
            disable_web_page_preview=True
        )

    # ── Name step (both types) ─────────────────────────────────────────────
    elif step == 'name':
        name = message.text.strip()
        if len(name) < 2:
            await message.reply("❌ Name too short. Try again:")
            return
        client._fs_gen[user_id]['name'] = name
        client._fs_gen[user_id]['step'] = 'collection'

        collections = await _get_collections()
        buttons = [[InlineKeyboardButton(c, callback_data=f"fs_assign_coll_{c}")] for c in collections[:8]]
        buttons.append([InlineKeyboardButton("➕ New Collection", callback_data="fs_new_coll")])
        buttons.append([InlineKeyboardButton("⏭ No Collection",  callback_data="fs_no_coll")])

        await message.reply(
            "📦 Assign to a collection? (optional — useful for grouping seasons/qualities)",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ── New collection name step ───────────────────────────────────────────
    elif step == 'new_coll':
        coll_name = message.text.strip()
        if len(coll_name) < 2:
            await message.reply("❌ Name too short. Try again:")
            return
        await _finish_generate(client, message, user_id, coll_name)

    else:
        return


@Bot.on_callback_query(filters.regex(r"^fs_assign_coll_(.+)$") & filters.user(ADMINS))
async def fs_assign_collection(client: Client, query: CallbackQuery):
    user_id   = query.from_user.id
    coll_name = query.data[15:]
    await _finish_generate(client, query, user_id, coll_name)


@Bot.on_callback_query(filters.regex(r"^fs_no_coll$") & filters.user(ADMINS))
async def fs_no_collection(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    await _finish_generate(client, query, user_id, "")


@Bot.on_callback_query(filters.regex(r"^fs_new_coll$") & filters.user(ADMINS))
async def fs_new_collection(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not hasattr(client, '_fs_gen'):
        client._fs_gen = {}
    if user_id not in client._fs_gen:
        await query.answer("Session expired.", show_alert=True)
        return
    client._fs_gen[user_id]['step'] = 'new_coll'
    await query.message.edit_text("📦 Send the <b>new collection name</b> (e.g. 'AOT Complete'):")
    await query.answer()


async def _finish_generate(client, target, user_id: int, coll_name: str):
    if not hasattr(client, '_fs_gen') or user_id not in client._fs_gen:
        return
    state = client._fs_gen.pop(user_id)
    name  = state.get('name', 'Unnamed')
    link  = state.get('link', '')
    count = state.get('count', 1)

    link_id = await _save_link(name, link, user_id, coll_name)

    coll_text = f"\n📦 Collection: <b>{coll_name}</b>" if coll_name else ""
    text = (
        f"╔══════════════════════════╗\n"
        f"   ✅  <b>LINK SAVED</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"🔗 <b>{name}</b>\n"
        f"🆔 ID: <code>{link_id}</code>"
        f"{coll_text}\n"
        f"📦 Files: <b>{count}</b>\n\n"
        f"{link}"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Share", url=f"https://telegram.me/share/url?url={link}")],
        [InlineKeyboardButton("🗂 File Store", callback_data="fs_home")],
    ])

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
        await target.answer()
    else:
        await target.reply(text, reply_markup=markup, disable_web_page_preview=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Back to home callback
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^fs_home$") & filters.user(ADMINS))
async def fs_home(client: Client, query: CallbackQuery):
    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "   🗂  <b>FILE STORE MODE</b>\n"
        "╚══════════════════════════╝\n\n"
        "Manage your file links and collections.\n\n"
        "🔗 <b>Links</b> — named single or batch links\n"
        "📦 <b>Collections</b> — grouped links (S1 480p, S1 720p…)\n"
        "📊 <b>Stats</b> — access counts per link\n"
        "⚡ <b>Generate</b> — create new links fast",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔗 My Links",      callback_data="fs_mylinks"),
                InlineKeyboardButton("📦 Collections",   callback_data="fs_collections"),
            ],
            [
                InlineKeyboardButton("📊 Link Stats",    callback_data="fs_stats_menu"),
                InlineKeyboardButton("⚡ Generate Link", callback_data="fs_generate"),
            ],
            [InlineKeyboardButton("🔒 Close", callback_data="close")],
        ])
    )
    await query.answer()


# ─────────────────────────────────────────────────────────────────────────────
#  /cancel — abort any active generate flow
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('cancel') & filters.private & filters.user(ADMINS))
async def fs_cancel(client: Client, message: Message):
    user_id = message.from_user.id
    if hasattr(client, '_fs_gen') and user_id in client._fs_gen:
        client._fs_gen.pop(user_id)
        await message.reply("❌ Cancelled.")
    else:
        await message.reply("Nothing to cancel.")


# ─────────────────────────────────────────────────────────────────────────────
#  /linkstats <link_id> — quick stat lookup by command
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('linkstats') & filters.private & filters.user(ADMINS))
async def linkstats_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/linkstats &lt;link_id&gt;</code>")
        return
    link_id = args[0].upper()
    lnk = await _get_link(link_id)
    if not lnk:
        await message.reply(f"❌ Link <code>{link_id}</code> not found.")
        return
    stats = await _get_stats(link_id)
    await message.reply(
        f"📊 <b>Stats: {lnk['name']}</b>\n\n"
        f"🆔 ID: <code>{link_id}</code>\n"
        f"📦 Collection: {lnk.get('collection') or '—'}\n"
        f"👁 Total access: <b>{stats['total_access']}</b>\n"
        f"👤 Unique users: <b>{len(stats['unique_users'])}</b>\n\n"
        f"🔗 {lnk['link']}",
        disable_web_page_preview=True
    )
