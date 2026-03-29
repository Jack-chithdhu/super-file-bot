#(©)CodeXBotz - Enhanced by Claude
# GetFiles System — admin stores batch links by request ID / season / quality
#                   users retrieve them with /getfiles <id>

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot import Bot
from config import ADMINS
from database.database import (
    getfiles_add, getfiles_get_seasons, getfiles_get_qualities,
    getfiles_get_link, getfiles_delete_quality, getfiles_delete_season,
    getfiles_delete_all, getfiles_list, get_request_by_id
)

QUALITY_BUTTONS = ["480p", "720p", "1080p", "4K", "✏️ Custom"]

# ─────────────────────────────────────────────────────────────────────────────
#  /addfile <request_id>  — admin stores a batch link
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('addfile') & filters.private)
async def addfile_cmd(client: Client, message: Message):
    import logging
    print(f"[ADDFILE] CALLED by {message.from_user.id} ADMINS={ADMINS}", flush=True)
    logging.getLogger(__name__).info(f"[ADDFILE] triggered by user {message.from_user.id}, ADMINS={ADMINS}")
    if message.from_user.id not in ADMINS:
        await message.reply("❌ Not an admin.")
        return
    args = message.command[1:]
    if not args:
        await message.reply(
            "ℹ️ <b>Usage:</b> <code>/addfile &lt;request_id&gt;</code>\n\n"
            "<i>Example: /addfile 7GE0H6</i>"
        )
        return

    req_id = args[0].upper()
    logging.getLogger(__name__).info(f"[ADDFILE] req_id={req_id}")

    # Check if request exists in DB — if not, still allow (admin may add files manually)
    req = await get_request_by_id(req_id)
    title = req['title'] if req else ""

    user_id = message.from_user.id
    if not hasattr(client, '_addfile'):
        client._addfile = {}

    client._addfile[user_id] = {
        'req_id': req_id,
        'title':  title,
        'step':   'season',
    }

    title_text = f"\n🎬 <b>{title}</b>" if title else ""
    await message.reply(
        f"📁 <b>Add Files</b>\n"
        f"🆔 Request ID: <code>{req_id}</code>{title_text}\n\n"
        f"Which <b>season</b> number?\n"
        f"<i>(Send a number, e.g. 1)</i>\n\n"
        f"Send /cancel to abort."
    )


@Bot.on_message(filters.private & filters.user(ADMINS) & filters.text &
                ~filters.command([
                    'start','addfile','getfiles','listfiles','deletefile',
                    'cancel','filestore','batch','genlink','ban','unban',
                    'fulfill','decline','broadcast','addpremium','removepremium',
                    'listpremium','allrequests','approverequest','approveall',
                    'addadmin','removeadmin','listadmins','togglepremium',
                    'setdailylimit','adminhelp','stats','users','filestats',
                    'requests','chatto','endchat','activechats','clearjoinrequests',
                    'linkstats'
                ]), group=-2)
async def addfile_input(client: Client, message: Message):
    import logging
    user_id = message.from_user.id
    logging.getLogger(__name__).info(f"[ADDFILE_INPUT] user={user_id} text={message.text!r} in_state={hasattr(client, '_addfile') and user_id in getattr(client, '_addfile', {})}")
    if not hasattr(client, '_addfile') or user_id not in client._addfile:
        return

    state = client._addfile[user_id]
    step  = state.get('step')

    # ── Season input ───────────────────────────────────────────────────────
    if step == 'season':
        text = message.text.strip()
        try:
            season = int(text)
            if season < 1:
                raise ValueError
        except ValueError:
            await message.reply("❌ Please send a valid season number (e.g. 1):")
            return

        state['season'] = season
        state['step']   = 'quality'
        client._addfile[user_id] = state

        buttons = [
            [InlineKeyboardButton(q, callback_data=f"af_quality_{q}") for q in QUALITY_BUTTONS[:2]],
            [InlineKeyboardButton(q, callback_data=f"af_quality_{q}") for q in QUALITY_BUTTONS[2:4]],
            [InlineKeyboardButton(QUALITY_BUTTONS[4], callback_data="af_quality_custom")],
            [InlineKeyboardButton("❌ Cancel", callback_data="af_cancel")],
        ]
        await message.reply(
            f"✅ Season <b>{season}</b> set.\n\n"
            f"Now pick the <b>quality</b>:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ── Custom quality input ───────────────────────────────────────────────
    elif step == 'custom_quality':
        quality = message.text.strip()
        if len(quality) < 1:
            await message.reply("❌ Quality too short. Try again:")
            return
        state['quality'] = quality
        state['step']    = 'link'
        client._addfile[user_id] = state
        await message.reply(
            f"✅ Quality: <b>{quality}</b>\n\n"
            f"Now send the <b>batch link</b> for "
            f"Season {state['season']} {quality}:\n"
            f"<i>(e.g. https://t.me/Milliefilebot?start=xxx)</i>"
        )

    # ── Batch link input ───────────────────────────────────────────────────
    elif step == 'link':
        link = message.text.strip()
        if not link.startswith("https://t.me/"):
            await message.reply(
                "❌ Invalid link. Must start with <code>https://t.me/</code>\n"
                "Try again:"
            )
            return

        # Extract file count from batch link if possible
        file_count = 1
        try:
            if "start=" in link:
                from helper_func import decode
                payload = link.split("start=")[1]
                decoded = await decode(payload)
                parts   = decoded.split("-")
                if len(parts) == 3:
                    # batch: get-XXXX-YYYY
                    ch_id = abs(client.db_channel.id)
                    start = int(int(parts[1]) / ch_id)
                    end   = int(int(parts[2]) / ch_id)
                    file_count = abs(end - start) + 1
        except Exception:
            pass

        req_id  = state['req_id']
        season  = state['season']
        quality = state['quality']
        title   = state.get('title', '')

        await getfiles_add(req_id, season, quality, link, file_count, title)
        client._addfile.pop(user_id)

        await message.reply(
            f"╔══════════════════════════╗\n"
            f"   ✅  <b>FILES SAVED</b>\n"
            f"╚══════════════════════════╝\n\n"
            f"🆔 ID: <code>{req_id}</code>\n"
            f"📅 Season: <b>{season}</b>\n"
            f"🎞 Quality: <b>{quality}</b>\n"
            f"📦 Files: <b>{file_count}</b>\n\n"
            f"Users can access with:\n"
            f"<code>/getfiles {req_id}</code>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "➕ Add More",
                    callback_data=f"af_addmore_{req_id}"
                )
            ]])
        )


@Bot.on_callback_query(filters.regex(r"^af_quality_(.+)$") & filters.user(ADMINS))
async def af_quality_cb(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not hasattr(client, '_addfile') or user_id not in client._addfile:
        await query.answer("Session expired. Use /addfile again.", show_alert=True)
        return

    quality_raw = query.data[11:]  # after "af_quality_"

    if quality_raw == "custom":
        client._addfile[user_id]['step'] = 'custom_quality'
        await query.message.edit_text("✏️ Send your <b>custom quality</b> name (e.g. HDRip, WEB-DL):")
        await query.answer()
        return

    state = client._addfile[user_id]
    state['quality'] = quality_raw
    state['step']    = 'link'
    client._addfile[user_id] = state

    await query.message.edit_text(
        f"✅ Quality: <b>{quality_raw}</b>\n\n"
        f"Now send the <b>batch link</b> for "
        f"Season {state['season']} {quality_raw}:\n"
        f"<i>(e.g. https://t.me/Milliefilebot?start=xxx)</i>"
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^af_addmore_(.+)$") & filters.user(ADMINS))
async def af_addmore(client: Client, query: CallbackQuery):
    req_id  = query.data[11:]
    user_id = query.from_user.id
    req     = await get_request_by_id(req_id)
    title   = req['title'] if req else ""

    if not hasattr(client, '_addfile'):
        client._addfile = {}

    client._addfile[user_id] = {
        'req_id': req_id,
        'title':  title,
        'step':   'season',
    }
    await query.message.edit_text(
        f"📁 <b>Add More Files</b>\n"
        f"🆔 ID: <code>{req_id}</code>\n\n"
        f"Which <b>season</b> number?\n"
        f"<i>Send a number, e.g. 2</i>"
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^af_cancel$") & filters.user(ADMINS))
async def af_cancel_cb(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if hasattr(client, '_addfile'):
        client._addfile.pop(user_id, None)
    await query.message.edit_text("❌ Cancelled.")
    await query.answer()


# ─────────────────────────────────────────────────────────────────────────────
#  /getfiles <request_id>  — user retrieves files
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('getfiles') & filters.private)
async def getfiles_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply(
            "ℹ️ <b>Usage:</b> <code>/getfiles &lt;request_id&gt;</code>\n\n"
            "<i>Example: /getfiles 7GE0H6</i>"
        )
        return

    req_id  = args[0].upper()
    seasons = await getfiles_get_seasons(req_id)

    if not seasons:
        await message.reply(
            f"❌ No files found for ID <code>{req_id}</code>.\n\n"
            f"<i>The admin may not have uploaded files yet.</i>"
        )
        return

    req   = await get_request_by_id(req_id)
    title = req['title'] if req else req_id

    buttons = [
        [InlineKeyboardButton(f"📅 Season {s}", callback_data=f"gf_season_{req_id}_{s}")]
        for s in seasons
    ]
    buttons.append([InlineKeyboardButton("🔒 Close", callback_data="close")])

    await message.reply(
        f"╔══════════════════════════╗\n"
        f"   🎬  <b>{title}</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"🆔 ID: <code>{req_id}</code>\n"
        f"📅 {len(seasons)} season(s) available\n\n"
        f"Select a season:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Bot.on_callback_query(filters.regex(r"^gf_season_(.+)_(\d+)$"))
async def gf_season_cb(client: Client, query: CallbackQuery):
    parts   = query.data.split("_")
    # format: gf_season_<req_id>_<season>
    season  = int(parts[-1])
    req_id  = "_".join(parts[2:-1])

    qualities = await getfiles_get_qualities(req_id, season)
    if not qualities:
        await query.answer("No files for this season.", show_alert=True)
        return

    buttons = [
        [InlineKeyboardButton(f"🎞 {q}", callback_data=f"gf_quality_{req_id}_{season}_{q}")]
        for q in qualities
    ]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"gf_back_{req_id}")])

    await query.message.edit_text(
        f"📅 <b>Season {season}</b>\n\n"
        f"Select quality:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^gf_quality_"))
async def gf_quality_cb(client: Client, query: CallbackQuery):
    # format: gf_quality_<req_id>_<season>_<quality>
    data    = query.data[11:]          # strip "gf_quality_"
    parts   = data.split("_")
    quality = parts[-1]
    season  = int(parts[-2])
    req_id  = "_".join(parts[:-2])

    doc = await getfiles_get_link(req_id, season, quality)
    if not doc:
        await query.answer("Files not found.", show_alert=True)
        return

    await query.answer(f"Sending {doc['file_count']} file(s)...")
    await query.message.edit_text(
        f"⏳ <b>Sending files...</b>\n\n"
        f"📅 Season {season} | 🎞 {quality}\n"
        f"📦 {doc['file_count']} file(s)"
    )

    user_id = query.from_user.id
    link    = doc['batch_link']

    # Extract the start payload and trigger file delivery via existing start handler
    try:
        payload = link.split("start=")[1]
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
            await client.send_message(user_id, "❌ Could not decode files. Contact admin.")
            return

        messages = await get_messages(client, ids)
        sent = 0
        for msg in messages:
            caption = (
                CUSTOM_CAPTION.format(
                    previouscaption="" if not msg.caption else msg.caption.html,
                    filename=msg.document.file_name if msg.document else ""
                )
                if bool(CUSTOM_CAPTION) and bool(msg.document)
                else ("" if not msg.caption else msg.caption.html)
            )
            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None
            try:
                await msg.copy(
                    chat_id=user_id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT
                )
                sent += 1
                await asyncio.sleep(0.5)
            except Exception:
                pass

        await client.send_message(
            chat_id=user_id,
            text=(
                f"✅ <b>Done!</b> Sent <b>{sent}</b> file(s)\n\n"
                f"📅 Season {season} | 🎞 {quality}"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to seasons", callback_data=f"gf_back_{req_id}")
            ]])
        )

    except Exception as e:
        await client.send_message(user_id, f"❌ Error delivering files. Contact admin.")
        import logging
        logging.getLogger(__name__).warning(f"gf_quality_cb error: {e}")


@Bot.on_callback_query(filters.regex(r"^gf_back_(.+)$"))
async def gf_back_cb(client: Client, query: CallbackQuery):
    req_id  = query.data[8:]
    seasons = await getfiles_get_seasons(req_id)
    req     = await get_request_by_id(req_id)
    title   = req['title'] if req else req_id

    if not seasons:
        await query.answer("No files found.", show_alert=True)
        return

    buttons = [
        [InlineKeyboardButton(f"📅 Season {s}", callback_data=f"gf_season_{req_id}_{s}")]
        for s in seasons
    ]
    buttons.append([InlineKeyboardButton("🔒 Close", callback_data="close")])

    await query.message.edit_text(
        f"╔══════════════════════════╗\n"
        f"   🎬  <b>{title}</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"🆔 ID: <code>{req_id}</code>\n"
        f"📅 {len(seasons)} season(s) available\n\n"
        f"Select a season:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer()


# ─────────────────────────────────────────────────────────────────────────────
#  /listfiles <request_id>  — admin views all stored files for an ID
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('listfiles') & filters.private & filters.user(ADMINS))
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
    title = req['title'] if req else req_id

    lines = [
        f"📁 <b>{title}</b> — <code>{req_id}</code>\n"
    ]
    current_season = None
    for e in entries:
        if e['season'] != current_season:
            current_season = e['season']
            lines.append(f"\n📅 <b>Season {current_season}</b>")
        lines.append(f"  🎞 {e['quality']} — {e['file_count']} file(s)")

    lines.append(f"\n<i>Use /deletefile {req_id} to manage files.</i>")
    await message.reply("\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
#  /deletefile <request_id>  — admin deletes files
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('deletefile') & filters.private & filters.user(ADMINS))
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
    title = req['title'] if req else req_id

    buttons = [
        [InlineKeyboardButton(f"📅 Season {s}", callback_data=f"df_season_{req_id}_{s}")]
        for s in seasons
    ]
    buttons.append([InlineKeyboardButton(f"🗑 Delete ALL ({req_id})", callback_data=f"df_all_{req_id}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="close")])

    await message.reply(
        f"🗑 <b>Delete Files</b>\n"
        f"🆔 <code>{req_id}</code> — {title}\n\n"
        f"Select what to delete:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Bot.on_callback_query(filters.regex(r"^df_season_(.+)_(\d+)$") & filters.user(ADMINS))
async def df_season_cb(client: Client, query: CallbackQuery):
    parts   = query.data.split("_")
    season  = int(parts[-1])
    req_id  = "_".join(parts[2:-1])

    qualities = await getfiles_get_qualities(req_id, season)
    buttons = [
        [InlineKeyboardButton(f"🗑 {q}", callback_data=f"df_quality_{req_id}_{season}_{q}")]
        for q in qualities
    ]
    buttons.append([InlineKeyboardButton(f"🗑 Delete entire Season {season}", callback_data=f"df_delseason_{req_id}_{season}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"df_back_{req_id}")])

    await query.message.edit_text(
        f"🗑 Season {season} — select quality to delete:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
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

    # Refresh season view
    qualities = await getfiles_get_qualities(req_id, season)
    if not qualities:
        await query.message.edit_text(f"✅ Season {season} is now empty.")
    else:
        buttons = [
            [InlineKeyboardButton(f"🗑 {q}", callback_data=f"df_quality_{req_id}_{season}_{q}")]
            for q in qualities
        ]
        buttons.append([InlineKeyboardButton(f"🗑 Delete entire Season {season}", callback_data=f"df_delseason_{req_id}_{season}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"df_back_{req_id}")])
        await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))


@Bot.on_callback_query(filters.regex(r"^df_delseason_(.+)_(\d+)$") & filters.user(ADMINS))
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
    title   = req['title'] if req else req_id

    buttons = [
        [InlineKeyboardButton(f"📅 Season {s}", callback_data=f"df_season_{req_id}_{s}")]
        for s in seasons
    ]
    buttons.append([InlineKeyboardButton(f"🗑 Delete ALL ({req_id})", callback_data=f"df_all_{req_id}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="close")])

    await query.message.edit_text(
        f"🗑 <b>Delete Files</b>\n"
        f"🆔 <code>{req_id}</code> — {title}\n\n"
        f"Select what to delete:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer()
