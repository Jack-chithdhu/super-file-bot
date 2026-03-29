#(©)CodeXBotz - Enhanced by Claude
# GetFiles System

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot import Bot
from config import ADMINS
from database.database import (
    getfiles_add, getfiles_get_seasons, getfiles_get_qualities,
    getfiles_get_link, getfiles_delete_quality, getfiles_delete_season,
    getfiles_delete_all, getfiles_list, get_request_by_id,
    collection_create, collection_get_by_number, collection_get_all
)

QUALITY_BUTTONS = ["480p", "720p", "1080p", "4K", "Custom"]


@Bot.on_message(filters.command("addfile") & filters.private & filters.user(ADMINS))
async def addfile_cmd(client: Client, message: Message):
    args = message.command[1:]
    user_id = message.from_user.id

    if args:
        try:
            col_number = int(args[0])
            col = await collection_get_by_number(col_number)
            if not col:
                await message.reply(f"❌ Collection <b>#{col_number}</b> not found.\n\nCreate one first: <code>/newcollection &lt;name&gt;</code>")
                return
            col_name = col["name"]
        except ValueError:
            await message.reply("ℹ️ <b>Usage:</b> <code>/addfile &lt;collection_number&gt;</code>\n\n<i>Example: /addfile 1</i>")
            return
    else:
        collections = await collection_get_all()
        if not collections:
            await message.reply("❌ No collections yet.\n\nCreate one first:\n<code>/newcollection &lt;name&gt;</code>\n\n<i>Example: /newcollection AOT Complete</i>")
            return
        lines = ["📦 <b>Your Collections</b>\n"]
        for c in collections:
            lines.append(f"  <b>#{c['number']}</b> — {c['name']}")
        lines.append("\nSend the collection number:")
        try:
            col_msg = await client.ask(chat_id=user_id, text="\n".join(lines), filters=filters.text, timeout=60)
        except asyncio.TimeoutError:
            await message.reply("⏰ Timed out.")
            return
        if col_msg.text.strip().startswith("/cancel"):
            await col_msg.reply("❌ Cancelled.")
            return
        try:
            col_number = int(col_msg.text.strip())
            col = await collection_get_by_number(col_number)
            if not col:
                await col_msg.reply(f"❌ Collection #{col_number} not found.")
                return
            col_name = col["name"]
        except ValueError:
            await col_msg.reply("❌ Invalid. Send a number.")
            return

    req_id = str(col_number)

    while True:
        try:
            season_msg = await client.ask(
                chat_id=user_id,
                text=f"📁 <b>Add Files</b>\n📦 Collection: <b>#{col_number} — {col_name}</b>\n\nWhich <b>season</b> number?\n<i>(Send a number, e.g. 1)</i>\n\nSend /cancel to abort.",
                filters=filters.text,
                timeout=120
            )
        except asyncio.TimeoutError:
            await message.reply("⏰ Timed out.")
            return
        if season_msg.text.strip().startswith("/cancel"):
            await season_msg.reply("❌ Cancelled.")
            return
        try:
            season = int(season_msg.text.strip())
            if season < 1:
                raise ValueError
            break
        except ValueError:
            await season_msg.reply("❌ Invalid. Send a number like 1, 2, 3:")

    buttons = [
        [InlineKeyboardButton(q, callback_data=f"af_q_{req_id}_{season}_{q}") for q in QUALITY_BUTTONS[:2]],
        [InlineKeyboardButton(q, callback_data=f"af_q_{req_id}_{season}_{q}") for q in QUALITY_BUTTONS[2:4]],
        [InlineKeyboardButton("✏️ Custom Quality", callback_data=f"af_q_{req_id}_{season}_custom")],
        [InlineKeyboardButton("❌ Cancel", callback_data="af_cancel")],
    ]
    await season_msg.reply(
        f"✅ Season <b>{season}</b> set.\n\nNow pick the <b>quality</b>:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Bot.on_callback_query(filters.regex(r"^af_q_") & filters.user(ADMINS))
async def af_quality_cb(client: Client, query: CallbackQuery):
    parts       = query.data.split("_")
    quality_raw = parts[-1]
    season      = int(parts[-2])
    req_id      = "_".join(parts[2:-2])
    user_id     = query.from_user.id
    await query.message.edit_reply_markup(None)

    if quality_raw == "custom":
        try:
            custom_msg = await client.ask(
                chat_id=user_id,
                text="✏️ Send your <b>custom quality</b> name (e.g. HDRip, WEB-DL):",
                filters=filters.text,
                timeout=60
            )
        except asyncio.TimeoutError:
            await query.message.reply("⏰ Timed out.")
            return
        if custom_msg.text.strip().startswith("/cancel"):
            await custom_msg.reply("❌ Cancelled.")
            return
        quality = custom_msg.text.strip()
    else:
        quality = quality_raw

    try:
        link_msg = await client.ask(
            chat_id=user_id,
            text=f"✅ Quality: <b>{quality}</b>\n\nNow send the <b>batch link</b> for Season {season} {quality}:\n<i>(e.g. https://t.me/Milliefilebot?start=xxx)</i>",
            filters=filters.text,
            timeout=120
        )
    except asyncio.TimeoutError:
        await query.message.reply("⏰ Timed out.")
        return

    if link_msg.text.strip().startswith("/cancel"):
        await link_msg.reply("❌ Cancelled.")
        return

    link = link_msg.text.strip()
    if not link.startswith("https://t.me/"):
        await link_msg.reply("❌ Invalid link. Must start with https://t.me/\nUse /addfile to try again.")
        return

    file_count = 1
    try:
        if "start=" in link:
            from helper_func import decode
            payload = link.split("start=")[1]
            decoded = await decode(payload)
            pts = decoded.split("-")
            if len(pts) == 3:
                ch_id = abs(client.db_channel.id)
                s = int(int(pts[1]) / ch_id)
                e = int(int(pts[2]) / ch_id)
                file_count = abs(e - s) + 1
    except Exception:
        pass

    req   = await get_request_by_id(req_id)
    title = req["title"] if req else ""
    await getfiles_add(req_id, season, quality, link, file_count, title)

    await link_msg.reply(
        f"╔══════════════════════════╗\n   ✅  <b>FILES SAVED</b>\n╚══════════════════════════╝\n\n🆔 ID: <code>{req_id}</code>\n📅 Season: <b>{season}</b>\n🎞 Quality: <b>{quality}</b>\n📦 Files: <b>{file_count}</b>\n\nUsers can access with:\n<code>/getfiles {req_id}</code>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add More", callback_data=f"af_addmore_{req_id}")]])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^af_addmore_(.+)$") & filters.user(ADMINS))
async def af_addmore(client: Client, query: CallbackQuery):
    req_id = query.data[11:]
    await query.answer()
    await query.message.edit_reply_markup(None)
    fake = query.message
    fake.text = f"/addfile {req_id}"
    fake.command = ["addfile", req_id]
    await addfile_cmd(client, fake)


@Bot.on_callback_query(filters.regex(r"^af_cancel$") & filters.user(ADMINS))
async def af_cancel_cb(client: Client, query: CallbackQuery):
    await query.message.edit_text("❌ Cancelled.")
    await query.answer()


@Bot.on_message(filters.command("getfiles") & filters.private)
async def getfiles_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/getfiles &lt;id_or_number&gt;</code>\n\n<i>Example: /getfiles 1 or /getfiles 7GE0H6</i>")
        return

    raw = args[0].strip()

    # Resolve: if it's a number, use collection number; otherwise treat as request ID
    try:
        col_number = int(raw)
        col = await collection_get_by_number(col_number)
        if col:
            req_id = str(col_number)
            display_title = f"#{col_number} — {col['name']}"
        else:
            await message.reply(f"❌ Collection <b>#{col_number}</b> not found.")
            return
    except ValueError:
        req_id = raw.upper()
        req = await get_request_by_id(req_id)
        display_title = req["title"] if req else req_id

    seasons = await getfiles_get_seasons(req_id)
    if not seasons:
        await message.reply(f"❌ No files found for <code>{raw}</code>.\n\n<i>Admin may not have uploaded files yet.</i>")
        return
    buttons = [[InlineKeyboardButton(f"📅 Season {s}", callback_data=f"gf_season_{req_id}_{s}")] for s in seasons]
    buttons.append([InlineKeyboardButton("🔒 Close", callback_data="close")])
    await message.reply(
        f"╔══════════════════════════╗\n   🎬  <b>{display_title}</b>\n╚══════════════════════════╝\n\n📅 {len(seasons)} season(s) available\n\nSelect a season:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Bot.on_callback_query(filters.regex(r"^gf_season_(.+)_(\d+)$"))
async def gf_season_cb(client: Client, query: CallbackQuery):
    parts     = query.data.split("_")
    season    = int(parts[-1])
    req_id    = "_".join(parts[2:-1])
    qualities = await getfiles_get_qualities(req_id, season)
    if not qualities:
        await query.answer("No files for this season.", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(f"🎞 {q}", callback_data=f"gf_quality_{req_id}_{season}_{q}")] for q in qualities]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"gf_back_{req_id}")])
    await query.message.edit_text(f"📅 <b>Season {season}</b>\n\nSelect quality:", reply_markup=InlineKeyboardMarkup(buttons))
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^gf_quality_"))
async def gf_quality_cb(client: Client, query: CallbackQuery):
    data    = query.data[11:]
    parts   = data.split("_")
    quality = parts[-1]
    season  = int(parts[-2])
    req_id  = "_".join(parts[:-2])
    doc = await getfiles_get_link(req_id, season, quality)
    if not doc:
        await query.answer("Files not found.", show_alert=True)
        return
    file_count = doc.get("file_count", 1)
    await query.answer(f"Sending {file_count} file(s)...")
    await query.message.edit_text(f"⏳ <b>Sending files...</b>\n\n📅 Season {season} | 🎞 {quality}\n📦 {file_count} file(s)")
    user_id = query.from_user.id
    link    = doc["batch_link"]
    try:
        payload  = link.split("start=")[1]
        from helper_func import decode, get_messages
        from pyrogram.enums import ParseMode
        from config import CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT
        string   = await decode(payload)
        argument = string.split("-")
        if len(argument) == 3:
            start = int(int(argument[1]) / abs(client.db_channel.id))
            end   = int(int(argument[2]) / abs(client.db_channel.id))
            ids   = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
        elif len(argument) == 2:
            ids = [int(int(argument[1]) / abs(client.db_channel.id))]
        else:
            ids = []
        if not ids:
            await client.send_message(user_id, "❌ Could not decode files.")
            return
        messages = await get_messages(client, ids)
        sent = 0
        for msg in messages:
            caption = (CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, filename=msg.document.file_name if msg.document else "") if bool(CUSTOM_CAPTION) and bool(msg.document) else ("" if not msg.caption else msg.caption.html))
            try:
                await msg.copy(chat_id=user_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=msg.reply_markup if DISABLE_CHANNEL_BUTTON else None, protect_content=PROTECT_CONTENT)
                sent += 1
                await asyncio.sleep(0.5)
            except Exception:
                pass
        await client.send_message(
            chat_id=user_id,
            text=f"✅ <b>Done!</b> Sent <b>{sent}</b> file(s)\n\n📅 Season {season} | 🎞 {quality}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"gf_back_{req_id}")]])
        )
    except Exception as e:
        await client.send_message(user_id, "❌ Error delivering files.")
        import logging
        logging.getLogger(__name__).warning(f"gf_quality_cb error: {e}")


@Bot.on_callback_query(filters.regex(r"^gf_back_(.+)$"))
async def gf_back_cb(client: Client, query: CallbackQuery):
    req_id  = query.data[8:]
    seasons = await getfiles_get_seasons(req_id)
    req     = await get_request_by_id(req_id)
    title   = req["title"] if req else req_id
    if not seasons:
        await query.answer("No files found.", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(f"📅 Season {s}", callback_data=f"gf_season_{req_id}_{s}")] for s in seasons]
    buttons.append([InlineKeyboardButton("🔒 Close", callback_data="close")])
    await query.message.edit_text(
        f"╔══════════════════════════╗\n   🎬  <b>{title}</b>\n╚══════════════════════════╝\n\n🆔 ID: <code>{req_id}</code>\n📅 {len(seasons)} season(s) available\n\nSelect a season:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer()


@Bot.on_message(filters.command("listfiles") & filters.private & filters.user(ADMINS))
async def listfiles_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/listfiles &lt;request_id&gt;</code>")
        return
    req_id  = args[0].upper()
    entries = await getfiles_list(req_id)
    if not entries:
        await message.reply(f"❌ No files stored for <code>{req_id}</code>.")
        return
    req   = await get_request_by_id(req_id)
    title = req["title"] if req else req_id
    lines = [f"📁 <b>{title}</b> — <code>{req_id}</code>\n"]
    cur = None
    for e in entries:
        if e["season"] != cur:
            cur = e["season"]
            lines.append(f"\n📅 <b>Season {cur}</b>")
        lines.append(f"  🎞 {e['quality']} — {e['file_count']} file(s)")
    lines.append(f"\n<i>Use /deletefile {req_id} to manage.</i>")
    await message.reply("\n".join(lines))


@Bot.on_message(filters.command("deletefile") & filters.private & filters.user(ADMINS))
async def deletefile_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/deletefile &lt;request_id&gt;</code>")
        return
    req_id  = args[0].upper()
    seasons = await getfiles_get_seasons(req_id)
    if not seasons:
        await message.reply(f"❌ No files stored for <code>{req_id}</code>.")
        return
    req   = await get_request_by_id(req_id)
    title = req["title"] if req else req_id
    buttons = [[InlineKeyboardButton(f"📅 Season {s}", callback_data=f"df_season_{req_id}_{s}")] for s in seasons]
    buttons.append([InlineKeyboardButton("🗑 Delete ALL", callback_data=f"df_all_{req_id}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="close")])
    await message.reply(
        f"🗑 <b>Delete Files</b>\n🆔 <code>{req_id}</code> — {title}\n\nSelect what to delete:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Bot.on_callback_query(filters.regex(r"^df_season_") & filters.user(ADMINS))
async def df_season_cb(client: Client, query: CallbackQuery):
    parts     = query.data.split("_")
    season    = int(parts[-1])
    req_id    = "_".join(parts[2:-1])
    qualities = await getfiles_get_qualities(req_id, season)
    buttons   = [[InlineKeyboardButton(f"🗑 {q}", callback_data=f"df_quality_{req_id}_{season}_{q}")] for q in qualities]
    buttons.append([InlineKeyboardButton(f"🗑 Delete Season {season}", callback_data=f"df_delseason_{req_id}_{season}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"df_back_{req_id}")])
    await query.message.edit_text(f"🗑 Season {season} — select quality:", reply_markup=InlineKeyboardMarkup(buttons))
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^df_quality_") & filters.user(ADMINS))
async def df_quality_cb(client: Client, query: CallbackQuery):
    data    = query.data[11:]
    parts   = data.split("_")
    quality = parts[-1]
    season  = int(parts[-2])
    req_id  = "_".join(parts[:-2])
    await getfiles_delete_quality(req_id, season, quality)
    await query.answer(f"✅ Deleted S{season} {quality}", show_alert=True)
    qualities = await getfiles_get_qualities(req_id, season)
    if not qualities:
        await query.message.edit_text(f"✅ Season {season} is now empty.")
    else:
        buttons = [[InlineKeyboardButton(f"🗑 {q}", callback_data=f"df_quality_{req_id}_{season}_{q}")] for q in qualities]
        buttons.append([InlineKeyboardButton(f"🗑 Delete Season {season}", callback_data=f"df_delseason_{req_id}_{season}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"df_back_{req_id}")])
        await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))


@Bot.on_callback_query(filters.regex(r"^df_delseason_") & filters.user(ADMINS))
async def df_delseason_cb(client: Client, query: CallbackQuery):
    parts  = query.data.split("_")
    season = int(parts[-1])
    req_id = "_".join(parts[2:-1])
    await getfiles_delete_season(req_id, season)
    await query.answer(f"✅ Season {season} deleted.", show_alert=True)
    await query.message.edit_text(f"✅ Season {season} deleted from <code>{req_id}</code>.")


@Bot.on_callback_query(filters.regex(r"^df_all_(.+)$") & filters.user(ADMINS))
async def df_all_cb(client: Client, query: CallbackQuery):
    req_id = query.data[7:]
    await getfiles_delete_all(req_id)
    await query.answer("✅ All files deleted.", show_alert=True)
    await query.message.edit_text(f"✅ All files deleted for <code>{req_id}</code>.")


@Bot.on_callback_query(filters.regex(r"^df_back_(.+)$") & filters.user(ADMINS))
async def df_back_cb(client: Client, query: CallbackQuery):
    req_id  = query.data[8:]
    seasons = await getfiles_get_seasons(req_id)
    req     = await get_request_by_id(req_id)
    title   = req["title"] if req else req_id
    buttons = [[InlineKeyboardButton(f"📅 Season {s}", callback_data=f"df_season_{req_id}_{s}")] for s in seasons]
    buttons.append([InlineKeyboardButton("🗑 Delete ALL", callback_data=f"df_all_{req_id}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="close")])
    await query.message.edit_text(
        f"🗑 <b>Delete Files</b>\n🆔 <code>{req_id}</code> — {title}\n\nSelect what to delete:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer()


# ─────────────────────────────────────────────────────────────────────────────
#  /newcollection <name>  — admin creates a numbered collection
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command("newcollection") & filters.private & filters.user(ADMINS))
async def newcollection_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("ℹ️ <b>Usage:</b> <code>/newcollection &lt;name&gt;</code>\n\n<i>Example: /newcollection AOT Complete</i>")
        return
    name   = " ".join(args).strip()
    number = await collection_create(name, message.from_user.id)
    await message.reply(
        f"╔══════════════════════════╗\n"
        f"   ✅  <b>COLLECTION CREATED</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"📦 <b>{name}</b>\n"
        f"🔢 Number: <b>#{number}</b>\n\n"
        f"Now add files with:\n"
        f"<code>/addfile {number}</code>\n\n"
        f"Users get files with:\n"
        f"<code>/getfiles {number}</code>"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  /listcollections  — show all collections with their numbers
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command("listcollections") & filters.private & filters.user(ADMINS))
async def listcollections_cmd(client: Client, message: Message):
    collections = await collection_get_all()
    if not collections:
        await message.reply("📦 No collections yet.\n\nCreate one: <code>/newcollection &lt;name&gt;</code>")
        return
    lines = ["📦 <b>All Collections</b>\n"]
    for c in collections:
        lines.append(f"  <b>#{c['number']}</b> — {c['name']}")
    lines.append("\n<i>Use /addfile &lt;number&gt; to add files\nUse /getfiles &lt;number&gt; to browse</i>")
    await message.reply("\n".join(lines))
