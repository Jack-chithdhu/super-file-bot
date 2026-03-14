#(©)CodeXBotz - Enhanced by Claude
# Owner Settings Panel — Full Button UI

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot import Bot
from config import OWNER_ID, ADMINS, FREE_DAILY_LIMIT, PREMIUM_DURATION_DAYS
from database.database import (
    get_setting, set_setting, get_payment_info, set_payment_info,
    get_payment_qr, set_payment_qr, clear_payment_qr
)

# ─────────────────────────────────────────────────────────────────────────────
#  /settings — main panel
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_message(filters.command('settings') & filters.private & filters.user([OWNER_ID]))
async def settings_cmd(client: Client, message: Message):
    await show_main_settings(client, message.chat.id)


async def show_main_settings(client, chat_id, message_id=None):
    premium_mode   = await get_setting('premium_mode')
    auto_del       = await get_setting('auto_delete_time') or 0
    captcha_on     = await get_setting('captcha_enabled')
    if captcha_on is None:
        captcha_on = True
    protect        = await get_setting('protect_content')
    if protect is None:
        protect = False
    req_on         = await get_setting('requests_enabled')
    if req_on is None:
        req_on = True

    from config import CHANNEL_ID as _default_ch
    db_ch = await get_setting('db_channel_id') or _default_ch

    support_on = await get_setting('support_enabled')
    if support_on is None: support_on = True
    sup_icon = "✅" if support_on else "❌"
    pm_icon  = "✅" if premium_mode else "❌"
    ad_icon  = "✅" if auto_del and auto_del > 0 else "❌"
    cap_icon = "✅" if captcha_on else "❌"
    pro_icon = "✅" if protect else "❌"
    req_icon = "✅" if req_on else "❌"

    text = (
        "╔══════════════════════════╗\n"
        "   ⚙️  <b>BOT SETTINGS PANEL</b>\n"
        "╚══════════════════════════╝\n\n"
        "Customize your bot as per your need.\n"
        "Tap any setting to configure it.\n\n"
        f"💎 Premium Mode: <b>{pm_icon}</b>  |  "
        f"🤖 Captcha: <b>{cap_icon}</b>  |  "
        f"🔒 Protect: <b>{pro_icon}</b>\n"
        f"🗄 DB Channel: <code>{db_ch}</code>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💎 PREMIUM PLAN",           callback_data="cfg_premium")],
        [InlineKeyboardButton(f"💳 PAYMENT SETTINGS",       callback_data="cfg_payment")],
        [InlineKeyboardButton(f"🤖 CAPTCHA  {cap_icon}",    callback_data="cfg_captcha")],
        [InlineKeyboardButton(f"♻️ AUTO DELETE  {ad_icon}", callback_data="cfg_autodelete")],
        [InlineKeyboardButton(f"🔒 PROTECT CONTENT  {pro_icon}", callback_data="cfg_protect")],
        [InlineKeyboardButton(f"🎬 REQUEST SYSTEM  {req_icon}",  callback_data="cfg_requests")],
        [InlineKeyboardButton(f"📢 FORCE SUBSCRIBE",        callback_data="cfg_forcesub")],
        [InlineKeyboardButton(f"🗄 DB CHANNEL",             callback_data="cfg_dbchannel")],
        [InlineKeyboardButton(f"💬 SUPPORT SYSTEM",          callback_data="cfg_support")],
        [InlineKeyboardButton(f"👋 WELCOME MESSAGE",        callback_data="cfg_welcome")],
        [InlineKeyboardButton(f"📆 DAILY LIMIT",            callback_data="cfg_dailylimit")],
        [InlineKeyboardButton("🔒 CLOSE",                   callback_data="close")],
    ])

    if message_id:
        try:
            await client.edit_message_text(chat_id, message_id, text, reply_markup=markup)
        except Exception:
            await client.send_message(chat_id, text, reply_markup=markup)
    else:
        await client.send_message(chat_id, text, reply_markup=markup)


# ─────────────────────────────────────────────────────────────────────────────
#  Callbacks — each setting opens its own sub-panel
# ─────────────────────────────────────────────────────────────────────────────

# ── 💎 Premium Plan ───────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_premium$") & filters.user(OWNER_ID))
async def cfg_premium(client, query: CallbackQuery):
    premium_mode = await get_setting('premium_mode')
    daily_limit  = await get_setting('free_daily_limit') or FREE_DAILY_LIMIT
    duration     = await get_setting('premium_duration') or PREMIUM_DURATION_DAYS

    pm_icon = "✅ ON" if premium_mode else "❌ OFF"

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "       💎  <b>PREMIUM PLAN</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🔘 <b>Premium Mode:</b> {pm_icon}\n"
        f"📆 <b>Free Daily Limit:</b> {daily_limit} files/day\n"
        f"⏳ <b>Default Duration:</b> {duration} days\n\n"
        "<i>When Premium Mode is OFF — all users get free access with daily limits.</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔴 Turn OFF Premium Mode" if premium_mode else "🟢 Turn ON Premium Mode",
                callback_data="cfg_toggle_premium"
            )],
            [InlineKeyboardButton("📆 Change Daily Limit",   callback_data="cfg_set_dailylimit")],
            [InlineKeyboardButton("⏳ Change Duration",       callback_data="cfg_set_duration")],
            [InlineKeyboardButton("🔙 BACK",                  callback_data="cfg_back")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_toggle_premium$") & filters.user(OWNER_ID))
async def cfg_toggle_premium(client, query: CallbackQuery):
    current = await get_setting('premium_mode')
    new_val = not current
    await set_setting('premium_mode', new_val)
    icon    = "✅ ON" if new_val else "❌ OFF"
    await query.answer(f"Premium Mode: {icon}", show_alert=True)
    await cfg_premium(client, query)


@Bot.on_callback_query(filters.regex(r"^cfg_set_dailylimit$") & filters.user(OWNER_ID))
async def cfg_set_dailylimit(client, query: CallbackQuery):
    await query.message.edit_text(
        "📆 <b>Set Daily Download Limit</b>\n\n"
        "Send the number of files free users can download per day.\n\n"
        "<i>Example: send <code>20</code></i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_premium")
        ]])
    )
    await query.answer()
    try:
        resp = await client.ask(query.from_user.id, "", filters=filters.text, timeout=60)
        limit = int(resp.text.strip())
        await set_setting('free_daily_limit', limit)
        await resp.reply(f"✅ Daily limit set to <b>{limit} files/day</b>")
    except (asyncio.TimeoutError, ValueError):
        await client.send_message(query.from_user.id, "❌ Cancelled or invalid input.")
    await show_main_settings(client, query.from_user.id)


@Bot.on_callback_query(filters.regex(r"^cfg_set_duration$") & filters.user(OWNER_ID))
async def cfg_set_duration(client, query: CallbackQuery):
    await query.message.edit_text(
        "⏳ <b>Set Default Premium Duration</b>\n\n"
        "Send the number of days for default premium.\n\n"
        "<i>Example: send <code>30</code></i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_premium")
        ]])
    )
    await query.answer()
    try:
        resp = await client.ask(query.from_user.id, "", filters=filters.text, timeout=60)
        days = int(resp.text.strip())
        await set_setting('premium_duration', days)
        await resp.reply(f"✅ Default premium duration set to <b>{days} days</b>")
    except (asyncio.TimeoutError, ValueError):
        await client.send_message(query.from_user.id, "❌ Cancelled or invalid input.")
    await show_main_settings(client, query.from_user.id)


# ── 💳 Payment Settings ───────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_payment$") & filters.user(OWNER_ID))
async def cfg_payment(client, query: CallbackQuery):
    payment = await get_payment_info()
    qr      = await get_payment_qr()

    lines = [
        "╔══════════════════════════╗\n"
        "     💳  <b>PAYMENT SETTINGS</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🖼️ <b>QR Image:</b> {'✅ Set' if qr else '❌ Not set'}\n\n"
        "<b>Current Details:</b>\n"
    ]
    if payment:
        for k, v in payment.items():
            lines.append(f"  • <b>{k.upper()}:</b> <code>{v}</code>")
    else:
        lines.append("  ❌ No payment details set")

    await query.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add/Edit UPI",         callback_data="cfg_pay_upi")],
            [InlineKeyboardButton("🏦 Add/Edit Bank",        callback_data="cfg_pay_bank")],
            [InlineKeyboardButton("📝 Add/Edit Note",        callback_data="cfg_pay_note")],
            [InlineKeyboardButton("🖼️ Set QR Image",         callback_data="cfg_pay_qr")],
            [InlineKeyboardButton("🗑️ Clear All Payment Info", callback_data="cfg_pay_clear")],
            [InlineKeyboardButton("🔙 BACK",                  callback_data="cfg_back")],
        ])
    )
    await query.answer()


async def _ask_and_set_payment(client, query, key, prompt):
    await query.message.edit_text(
        f"💳 <b>{prompt}</b>\n\nSend the value now:\n\n"
        "<i>Example shown in prompt above</i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_payment")
        ]])
    )
    await query.answer()
    try:
        resp    = await client.ask(query.from_user.id, "", filters=filters.text, timeout=60)
        current = await get_payment_info()
        current[key] = resp.text.strip()
        await set_payment_info(current)
        await resp.reply(f"✅ <b>{key.upper()}</b> saved: <code>{resp.text.strip()}</code>")
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "❌ Timed out.")
    await show_main_settings(client, query.from_user.id)


@Bot.on_callback_query(filters.regex(r"^cfg_pay_upi$") & filters.user(OWNER_ID))
async def cfg_pay_upi(client, query):
    await _ask_and_set_payment(client, query, "upi", "Enter your UPI ID\ne.g. yourname@upi")

@Bot.on_callback_query(filters.regex(r"^cfg_pay_bank$") & filters.user(OWNER_ID))
async def cfg_pay_bank(client, query):
    await _ask_and_set_payment(client, query, "bank", "Enter Bank Details\ne.g. Acc: 123456 | IFSC: SBIN001")

@Bot.on_callback_query(filters.regex(r"^cfg_pay_note$") & filters.user(OWNER_ID))
async def cfg_pay_note(client, query):
    await _ask_and_set_payment(client, query, "note", "Enter payment note\ne.g. Send screenshot after payment")


@Bot.on_callback_query(filters.regex(r"^cfg_pay_qr$") & filters.user(OWNER_ID))
async def cfg_pay_qr(client, query: CallbackQuery):
    await query.message.edit_text(
        "🖼️ <b>Set Payment QR Image</b>\n\n"
        "Send your QR code image now.\n\n"
        "<i>Just send the photo directly in this chat.</i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🗑️ Remove Current QR", callback_data="cfg_pay_qr_clear"),
            InlineKeyboardButton("❌ Cancel",             callback_data="cfg_payment"),
        ]])
    )
    await query.answer()
    try:
        resp = await client.ask(
            query.from_user.id, "",
            filters=filters.photo, timeout=60
        )
        file_id = resp.photo.file_id
        await set_payment_qr(file_id)
        await resp.reply("✅ QR image saved! It will appear on the premium payment screen.")
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "❌ Timed out. No QR set.")
    await show_main_settings(client, query.from_user.id)


@Bot.on_callback_query(filters.regex(r"^cfg_pay_qr_clear$") & filters.user(OWNER_ID))
async def cfg_pay_qr_clear(client, query):
    await clear_payment_qr()
    await query.answer("✅ QR image removed!", show_alert=True)
    await cfg_payment(client, query)


@Bot.on_callback_query(filters.regex(r"^cfg_pay_clear$") & filters.user(OWNER_ID))
async def cfg_pay_clear(client, query):
    await set_payment_info({})
    await clear_payment_qr()
    await query.answer("✅ All payment info cleared!", show_alert=True)
    await cfg_payment(client, query)


# ── 🤖 Captcha ────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_captcha$") & filters.user(OWNER_ID))
async def cfg_captcha(client, query: CallbackQuery):
    captcha_on = await get_setting('captcha_enabled')
    if captcha_on is None:
        captcha_on = True
    icon       = "✅ ON" if captcha_on else "❌ OFF"
    exp_days   = await get_setting('captcha_expiry_days') or 0
    exp_icon   = f"✅ Every {exp_days} days" if exp_days and exp_days > 0 else "❌ Never"

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "       🤖  <b>CAPTCHA SYSTEM</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🔘 <b>Status:</b> {icon}\n"
        f"⏰ <b>Re-verify Period:</b> {exp_icon}\n\n"
        "When ON — new users must solve an emoji button captcha before accessing the bot.\n\n"
        "• 4 random emojis shown as buttons\n"
        "• 60 second timeout\n"
        "• 3 attempts max",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔴 Turn OFF Captcha" if captcha_on else "🟢 Turn ON Captcha",
                callback_data="cfg_toggle_captcha"
            )],
            [InlineKeyboardButton("⏰ Re-verify Period",     callback_data="cfg_captcha_expiry")],
            [InlineKeyboardButton("🔄 Reset All Users",      callback_data="cfg_captcha_reset_confirm")],
            [InlineKeyboardButton("🔙 BACK",                 callback_data="cfg_back")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_toggle_captcha$") & filters.user(OWNER_ID))
async def cfg_toggle_captcha(client, query):
    current = await get_setting('captcha_enabled')
    if current is None:
        current = True
    new_val = not current
    await set_setting('captcha_enabled', new_val)
    icon = "✅ ON" if new_val else "❌ OFF"
    await query.answer(f"Captcha: {icon}", show_alert=True)
    await cfg_captcha(client, query)


# ── Captcha Re-verify Period ───────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_captcha_expiry$") & filters.user(OWNER_ID))
async def cfg_captcha_expiry(client, query: CallbackQuery):
    days = await get_setting('captcha_expiry_days') or 0
    icon = f"✅ Every {days} days" if days and days > 0 else "❌ Never expires"

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "    ⏰  <b>RE-VERIFY PERIOD</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🔘 <b>Current:</b> {icon}\n\n"
        "Set how often users must re-solve the captcha.\n"
        "<i>Set to 0 or Never to only ask once.</i>",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("7 days",  callback_data="cfg_cap_exp_7"),
                InlineKeyboardButton("15 days", callback_data="cfg_cap_exp_15"),
                InlineKeyboardButton("30 days", callback_data="cfg_cap_exp_30"),
            ],
            [InlineKeyboardButton("✏️ Custom",    callback_data="cfg_cap_exp_custom")],
            [InlineKeyboardButton("🔴 Never",     callback_data="cfg_cap_exp_0")],
            [InlineKeyboardButton("🔙 BACK",      callback_data="cfg_captcha")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_cap_exp_(\d+|custom)$") & filters.user(OWNER_ID))
async def cfg_cap_exp_set(client, query: CallbackQuery):
    val = query.data.split("_")[3]
    if val == "custom":
        await query.message.edit_text(
            "✏️ Send number of days for re-verify period:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="cfg_captcha_expiry")
            ]])
        )
        await query.answer()
        try:
            resp = await client.ask(query.from_user.id, "", filters=filters.text, timeout=60)
            days = int(resp.text.strip())
            await set_setting('captcha_expiry_days', days)
            await resp.reply(f"✅ Re-verify period set to <b>{days} days</b>.")
        except (asyncio.TimeoutError, ValueError):
            await client.send_message(query.from_user.id, "❌ Cancelled or invalid.")
        await show_main_settings(client, query.from_user.id)
    else:
        days = int(val)
        await set_setting('captcha_expiry_days', days)
        msg = "✅ Captcha never expires." if days == 0 else f"✅ Re-verify every {days} days."
        await query.answer(msg, show_alert=True)
        await cfg_captcha_expiry(client, query)


# ── Captcha Reset All Users ────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_captcha_reset_confirm$") & filters.user(OWNER_ID))
async def cfg_captcha_reset_confirm(client, query: CallbackQuery):
    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "    🔄  <b>RESET ALL CAPTCHA</b>\n"
        "╚══════════════════════════╝\n\n"
        "⚠️ <b>This will reset captcha verification for ALL users.</b>\n\n"
        "Every user will need to solve the captcha again on their next /start.\n\n"
        "Are you sure?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, Reset All", callback_data="cfg_captcha_reset_do"),
                InlineKeyboardButton("❌ Cancel",         callback_data="cfg_captcha"),
            ]
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_captcha_reset_do$") & filters.user(OWNER_ID))
async def cfg_captcha_reset_do(client, query: CallbackQuery):
    import plugins.captcha as captcha_module
    from datetime import datetime

    # Use module reference directly to avoid Python import caching issues
    count = len(captcha_module.verified_users)
    captcha_module.verified_users.clear()
    captcha_module.verified_users_time.clear()
    captcha_module.captcha_store.clear()

    # Save reset timestamp — needs_captcha() checks this on every /start
    await set_setting('captcha_last_reset', datetime.utcnow().isoformat())

    await query.answer(f"✅ Reset {count} verified users!", show_alert=True)
    await query.message.edit_text(
        f"✅ <b>Captcha reset complete!</b>\n\n"
        f"<b>{count}</b> verified sessions cleared.\n\n"
        f"All users will need to verify again on next /start."
    )
    await asyncio.sleep(2)
    await cfg_captcha(client, query)


# ── ♻️ Auto Delete ────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_autodelete$") & filters.user(OWNER_ID))
async def cfg_autodelete(client, query: CallbackQuery):
    auto_del = await get_setting('auto_delete_time') or 0
    icon     = f"✅ {auto_del}s" if auto_del and auto_del > 0 else "❌ OFF"

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "       ♻️  <b>AUTO DELETE</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🔘 <b>Status:</b> {icon}\n\n"
        "Files are automatically deleted after the set time.\n"
        "💎 Premium users are always exempt from auto-delete.\n\n"
        "<i>Set to 0 to disable.</i>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏱ Set Delete Time",      callback_data="cfg_set_autodel")],
            [InlineKeyboardButton("🔴 Disable Auto Delete",  callback_data="cfg_disable_autodel")],
            [InlineKeyboardButton("🔙 BACK",                 callback_data="cfg_back")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_set_autodel$") & filters.user(OWNER_ID))
async def cfg_set_autodel(client, query):
    await query.message.edit_text(
        "⏱ <b>Set Auto Delete Time</b>\n\n"
        "Send the number of <b>seconds</b> before files are deleted.\n\n"
        "<i>Example: <code>300</code> = 5 minutes</i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_autodelete")
        ]])
    )
    await query.answer()
    try:
        resp = await client.ask(query.from_user.id, "", filters=filters.text, timeout=60)
        secs = int(resp.text.strip())
        await set_setting('auto_delete_time', secs)
        await resp.reply(f"✅ Auto delete set to <b>{secs} seconds</b>.")
    except (asyncio.TimeoutError, ValueError):
        await client.send_message(query.from_user.id, "❌ Cancelled or invalid.")
    await show_main_settings(client, query.from_user.id)


@Bot.on_callback_query(filters.regex(r"^cfg_disable_autodel$") & filters.user(OWNER_ID))
async def cfg_disable_autodel(client, query):
    await set_setting('auto_delete_time', 0)
    await query.answer("✅ Auto delete disabled!", show_alert=True)
    await cfg_autodelete(client, query)


# ── 🔒 Protect Content ────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_protect$") & filters.user(OWNER_ID))
async def cfg_protect(client, query: CallbackQuery):
    protect = await get_setting('protect_content')
    if protect is None:
        protect = False
    icon = "✅ ON" if protect else "❌ OFF"

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "     🔒  <b>PROTECT CONTENT</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🔘 <b>Status:</b> {icon}\n\n"
        "When ON — users cannot forward files sent by the bot.\n"
        "This protects your content from being shared outside.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔴 Turn OFF Protection" if protect else "🟢 Turn ON Protection",
                callback_data="cfg_toggle_protect"
            )],
            [InlineKeyboardButton("🔙 BACK", callback_data="cfg_back")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_toggle_protect$") & filters.user(OWNER_ID))
async def cfg_toggle_protect(client, query):
    current = await get_setting('protect_content') or False
    new_val = not current
    await set_setting('protect_content', new_val)
    icon = "✅ ON" if new_val else "❌ OFF"
    await query.answer(f"Content Protection: {icon}", show_alert=True)
    await cfg_protect(client, query)


# ── 🎬 Request System ─────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_requests$") & filters.user(OWNER_ID))
async def cfg_requests(client, query: CallbackQuery):
    req_on       = await get_setting('requests_enabled')
    if req_on is None: req_on = True
    req_ch       = await get_setting('request_channel') or "Not set"
    auto_dec     = await get_setting('auto_decline_days') or 0
    custom_msg   = await get_setting('request_custom_msg')
    allowed      = await get_setting('allowed_req_types') or ['movie','anime','series']

    icon     = "✅ ON" if req_on else "❌ OFF"
    ad_icon  = f"✅ {auto_dec}d" if auto_dec and auto_dec > 0 else "❌ OFF"
    cm_icon  = "✅ Set" if custom_msg else "❌ Default"
    types_str = " | ".join([t.capitalize() for t in allowed])

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "     🎬  <b>REQUEST SYSTEM</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🔘 <b>Status:</b> {icon}\n"
        f"📢 <b>Channel:</b> <code>{req_ch}</code>\n"
        f"⏰ <b>Auto-Decline:</b> {ad_icon}\n"
        f"💬 <b>Custom Message:</b> {cm_icon}\n"
        f"📁 <b>Allowed Types:</b> {types_str}\n\n"
        "Users can request Movies, Anime and Series.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔴 Disable Requests" if req_on else "🟢 Enable Requests",
                callback_data="cfg_toggle_requests"
            )],
            [InlineKeyboardButton("📢 Log Channel (Optional)",    callback_data="cfg_set_reqchannel")],
            [InlineKeyboardButton("⏰ Auto-Decline Settings",  callback_data="cfg_auto_decline")],
            [InlineKeyboardButton("💬 Custom Request Message", callback_data="cfg_req_custmsg")],
            [InlineKeyboardButton("📁 Allowed Request Types",  callback_data="cfg_req_types")],
            [InlineKeyboardButton("📋 View Pending Requests",  callback_data="cfg_view_requests_0")],
            [InlineKeyboardButton("🔙 BACK",                   callback_data="cfg_back")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_toggle_requests$") & filters.user(OWNER_ID))
async def cfg_toggle_requests(client, query):
    current = await get_setting('requests_enabled')
    if current is None: current = True
    new_val = not current
    await set_setting('requests_enabled', new_val)
    icon = "✅ ON" if new_val else "❌ OFF"
    await query.answer(f"Request System: {icon}", show_alert=True)
    await cfg_requests(client, query)


@Bot.on_callback_query(filters.regex(r"^cfg_set_reqchannel$") & filters.user(OWNER_ID))
async def cfg_set_reqchannel(client, query):
    await query.message.edit_text(
        "📢 <b>Set Request Channel</b>\n\n"
        "Send the channel ID where requests should be publicly logged.\n"
        "This is optional — admin DM notifications always work without it.\n\n"
        "<i>Example: <code>-100xxxxxxxxxx</code></i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_requests")
        ]])
    )
    await query.answer()
    try:
        resp  = await client.ask(query.from_user.id, "", filters=filters.text, timeout=60)
        ch_id = int(resp.text.strip())
        await set_setting('request_channel', ch_id)
        await resp.reply(f"✅ Request channel set to <code>{ch_id}</code>")
    except (asyncio.TimeoutError, ValueError):
        await client.send_message(query.from_user.id, "❌ Cancelled or invalid.")
    await show_main_settings(client, query.from_user.id)


# ── Auto-Decline Settings ──────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_auto_decline$") & filters.user(OWNER_ID))
async def cfg_auto_decline(client, query: CallbackQuery):
    days = await get_setting('auto_decline_days') or 0
    icon = f"✅ After {days} days" if days and days > 0 else "❌ OFF"
    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "     ⏰  <b>AUTO-DECLINE</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🔘 <b>Status:</b> {icon}\n\n"
        "Pending requests older than X days will be automatically declined\n"
        "and the user will be notified.\n\n"
        "<i>Set to 0 to disable.</i>",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("3 days",  callback_data="cfg_adset_3"),
                InlineKeyboardButton("7 days",  callback_data="cfg_adset_7"),
                InlineKeyboardButton("14 days", callback_data="cfg_adset_14"),
                InlineKeyboardButton("30 days", callback_data="cfg_adset_30"),
            ],
            [InlineKeyboardButton("✏️ Custom Days",        callback_data="cfg_adset_custom")],
            [InlineKeyboardButton("🔴 Disable",            callback_data="cfg_adset_0")],
            [InlineKeyboardButton("🔙 BACK",               callback_data="cfg_requests")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_adset_(\d+|custom)$") & filters.user(OWNER_ID))
async def cfg_adset(client, query: CallbackQuery):
    val = query.data.split("_")[2]
    if val == "custom":
        await query.message.edit_text(
            "✏️ <b>Custom Auto-Decline Days</b>\n\nSend number of days:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="cfg_auto_decline")
            ]])
        )
        await query.answer()
        try:
            resp = await client.ask(query.from_user.id, "", filters=filters.text, timeout=60)
            days = int(resp.text.strip())
            await set_setting('auto_decline_days', days)
            await resp.reply(f"✅ Auto-decline set to <b>{days} days</b>.")
        except (asyncio.TimeoutError, ValueError):
            await client.send_message(query.from_user.id, "❌ Cancelled or invalid.")
        await show_main_settings(client, query.from_user.id)
    else:
        days = int(val)
        await set_setting('auto_decline_days', days)
        msg = f"✅ Auto-decline disabled." if days == 0 else f"✅ Auto-decline set to {days} days."
        await query.answer(msg, show_alert=True)
        await cfg_auto_decline(client, query)


# ── Custom Request Message ─────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_req_custmsg$") & filters.user(OWNER_ID))
async def cfg_req_custmsg(client, query: CallbackQuery):
    current = await get_setting('request_custom_msg') or "Using default message"
    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "  💬  <b>CUSTOM REQUEST MESSAGE</b>\n"
        "╚══════════════════════════╝\n\n"
        f"<b>Current:</b>\n<i>{current[:300]}</i>\n\n"
        "This message is shown to users when they start a request.\n"
        "HTML formatting supported.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Edit Message",    callback_data="cfg_req_custmsg_edit")],
            [InlineKeyboardButton("🔄 Reset Default",   callback_data="cfg_req_custmsg_reset")],
            [InlineKeyboardButton("🔙 BACK",            callback_data="cfg_requests")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_req_custmsg_edit$") & filters.user(OWNER_ID))
async def cfg_req_custmsg_edit(client, query):
    await query.message.edit_text(
        "✏️ <b>Send your custom request message:</b>\n\n"
        "This will be shown when users tap /request.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_req_custmsg")
        ]])
    )
    await query.answer()
    try:
        resp = await client.ask(query.from_user.id, "", filters=filters.text, timeout=120)
        await set_setting('request_custom_msg', resp.text.strip())
        await resp.reply("✅ Custom request message saved!")
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "❌ Timed out.")
    await show_main_settings(client, query.from_user.id)


@Bot.on_callback_query(filters.regex(r"^cfg_req_custmsg_reset$") & filters.user(OWNER_ID))
async def cfg_req_custmsg_reset(client, query):
    await set_setting('request_custom_msg', None)
    await query.answer("✅ Reset to default message!", show_alert=True)
    await cfg_req_custmsg(client, query)


# ── Allowed Request Types ──────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_req_types$") & filters.user(OWNER_ID))
async def cfg_req_types(client, query: CallbackQuery):
    allowed = await get_setting('allowed_req_types') or ['movie', 'anime', 'series']
    m_icon  = "✅" if 'movie'  in allowed else "❌"
    a_icon  = "✅" if 'anime'  in allowed else "❌"
    s_icon  = "✅" if 'series' in allowed else "❌"

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "   📁  <b>ALLOWED REQUEST TYPES</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🎬 <b>Movie:</b>  {m_icon}\n"
        f"🎌 <b>Anime:</b>  {a_icon}\n"
        f"📺 <b>Series:</b> {s_icon}\n\n"
        "Tap to toggle each type on/off.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"🎬 Movie {m_icon}",  callback_data="cfg_rtype_movie"),
                InlineKeyboardButton(f"🎌 Anime {a_icon}",  callback_data="cfg_rtype_anime"),
                InlineKeyboardButton(f"📺 Series {s_icon}", callback_data="cfg_rtype_series"),
            ],
            [InlineKeyboardButton("🔙 BACK", callback_data="cfg_requests")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_rtype_(movie|anime|series)$") & filters.user(OWNER_ID))
async def cfg_rtype_toggle(client, query: CallbackQuery):
    rtype   = query.data.split("_")[2]
    allowed = await get_setting('allowed_req_types') or ['movie', 'anime', 'series']
    if rtype in allowed:
        if len(allowed) == 1:
            await query.answer("❌ At least one type must be enabled!", show_alert=True)
            return
        allowed.remove(rtype)
        msg = f"❌ {rtype.capitalize()} requests disabled."
    else:
        allowed.append(rtype)
        msg = f"✅ {rtype.capitalize()} requests enabled."
    await set_setting('allowed_req_types', allowed)
    await query.answer(msg, show_alert=True)
    await cfg_req_types(client, query)


# ── View & Manage Pending Requests ─────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_view_requests_(\d+)$") & filters.user(OWNER_ID))
async def cfg_view_requests(client, query: CallbackQuery):
    from database.database import get_all_requests, get_request_by_id
    page  = int(query.data.split("_")[3])
    reqs  = await get_all_requests(status='pending', limit=100)
    total = len(reqs)

    if not reqs:
        await query.message.edit_text(
            "📋 <b>Pending Requests</b>\n\n✅ No pending requests!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 BACK", callback_data="cfg_requests")
            ]])
        )
        await query.answer()
        return

    per_page = 5
    start    = page * per_page
    end      = start + per_page
    page_reqs = reqs[start:end]

    lines   = [f"📋 <b>Pending Requests ({total} total)</b>\n"]
    buttons = []

    for r in page_reqs:
        emoji = "🎬" if r['type'] == 'movie' else ("🎌" if r['type'] == 'anime' else "📺")
        lines.append(f"{emoji} <code>{r['request_id']}</code> — <b>{r['title']}</b> (User <code>{r['user_id']}</code>)")
        buttons.append([
            InlineKeyboardButton(f"✅ {r['request_id']}", callback_data=f"cfg_req_fulfill_{r['request_id']}"),
            InlineKeyboardButton(f"❌ {r['request_id']}", callback_data=f"cfg_req_decline_{r['request_id']}"),
        ])

    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"cfg_view_requests_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"cfg_view_requests_{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("🔙 BACK", callback_data="cfg_requests")])

    await query.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_req_fulfill_(.+)$") & filters.user(OWNER_ID))
async def cfg_req_fulfill(client, query: CallbackQuery):
    from database.database import get_request_by_id, fulfill_request
    req_id = query.data.split("_", 3)[3]
    req    = await get_request_by_id(req_id)
    if not req or req['status'] != 'pending':
        await query.answer("Already handled.", show_alert=True)
        return
    await fulfill_request(req_id, "Your request has been fulfilled! Check the bot for new files.")
    try:
        await client.send_message(
            chat_id=req['user_id'],
            text=(
                f"🎉 <b>Request Fulfilled!</b>\n\n"
                f"🆔 ID: <code>{req_id}</code>\n"
                f"🎬 Title: <b>{req['title']}</b>\n\n"
                f"Your request has been fulfilled! Check the bot for new files. 🎊"
            )
        )
    except Exception:
        pass
    await query.answer(f"✅ {req_id} fulfilled!", show_alert=True)
    # Refresh list
    query.data = f"cfg_view_requests_0"
    await cfg_view_requests(client, query)


@Bot.on_callback_query(filters.regex(r"^cfg_req_decline_(.+)$") & filters.user(OWNER_ID))
async def cfg_req_decline(client, query: CallbackQuery):
    from database.database import get_request_by_id, decline_request
    req_id = query.data.split("_", 3)[3]
    req    = await get_request_by_id(req_id)
    if not req or req['status'] != 'pending':
        await query.answer("Already handled.", show_alert=True)
        return
    await decline_request(req_id, "Declined by admin.")
    try:
        await client.send_message(
            chat_id=req['user_id'],
            text=(
                f"❌ <b>Request Declined</b>\n\n"
                f"🆔 ID: <code>{req_id}</code>\n"
                f"🎬 Title: <b>{req['title']}</b>\n\n"
                f"📝 Reason: Declined by admin."
            )
        )
    except Exception:
        pass
    await query.answer(f"❌ {req_id} declined!", show_alert=True)
    query.data = f"cfg_view_requests_0"
    await cfg_view_requests(client, query)


# ── 📢 Force Subscribe ────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_forcesub$") & filters.user(OWNER_ID))
async def cfg_forcesub(client, query: CallbackQuery):
    fs_ch = await get_setting('force_sub_channel') or 0
    jr_on = await get_setting('join_request_enabled') or False
    icon  = "✅ ON" if fs_ch and fs_ch != 0 else "❌ OFF"
    jr_icon = "✅ ON" if jr_on else "❌ OFF"

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "    📢  <b>FORCE SUBSCRIBE</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🔘 <b>Status:</b> {icon}\n"
        f"📋 <b>Channel ID:</b> <code>{fs_ch or 'Not set'}</code>\n"
        f"🙋 <b>Join Request Mode:</b> {jr_icon}\n\n"
        "💎 Premium users always bypass force subscribe.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Set Channel ID",         callback_data="cfg_set_fschannel")],
            [InlineKeyboardButton("🔴 Disable Force Sub",      callback_data="cfg_disable_forcesub")],
            [InlineKeyboardButton(
                "🔴 Disable Join Requests" if jr_on else "🟢 Enable Join Requests",
                callback_data="cfg_toggle_joinreq"
            )],
            [InlineKeyboardButton("🔙 BACK", callback_data="cfg_back")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_set_fschannel$") & filters.user(OWNER_ID))
async def cfg_set_fschannel(client, query):
    await query.message.edit_text(
        "📢 <b>Set Force Subscribe Channel</b>\n\n"
        "Send the channel ID users must join.\n\n"
        "<i>Example: <code>-100xxxxxxxxxx</code></i>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_forcesub")
        ]])
    )
    await query.answer()
    try:
        resp  = await client.ask(query.from_user.id, "", filters=filters.text, timeout=60)
        ch_id = int(resp.text.strip())
        await set_setting('force_sub_channel', ch_id)
        await resp.reply(f"✅ Force subscribe channel set to <code>{ch_id}</code>")
    except (asyncio.TimeoutError, ValueError):
        await client.send_message(query.from_user.id, "❌ Cancelled or invalid.")
    await show_main_settings(client, query.from_user.id)


@Bot.on_callback_query(filters.regex(r"^cfg_disable_forcesub$") & filters.user(OWNER_ID))
async def cfg_disable_forcesub(client, query):
    await set_setting('force_sub_channel', 0)
    await query.answer("✅ Force subscribe disabled!", show_alert=True)
    await cfg_forcesub(client, query)


@Bot.on_callback_query(filters.regex(r"^cfg_toggle_joinreq$") & filters.user(OWNER_ID))
async def cfg_toggle_joinreq(client, query):
    current = await get_setting('join_request_enabled') or False
    new_val = not current
    await set_setting('join_request_enabled', new_val)
    icon = "✅ ON" if new_val else "❌ OFF"
    await query.answer(f"Join Request Mode: {icon}", show_alert=True)
    await cfg_forcesub(client, query)


# ── 👋 Welcome Message ────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_welcome$") & filters.user(OWNER_ID))
async def cfg_welcome(client, query: CallbackQuery):
    custom_msg = await get_setting('custom_start_msg') or "Using default message"

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "     👋  <b>WELCOME MESSAGE</b>\n"
        "╚══════════════════════════╝\n\n"
        f"<b>Current:</b>\n<i>{custom_msg[:200]}</i>\n\n"
        "You can use these placeholders:\n"
        "<code>{first}</code> — First name\n"
        "<code>{last}</code> — Last name\n"
        "<code>{mention}</code> — Mention\n"
        "<code>{id}</code> — User ID\n\n"
        "HTML formatting is supported.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Edit Message",       callback_data="cfg_edit_welcome")],
            [InlineKeyboardButton("🖼️ Set Welcome Image",  callback_data="cfg_set_welcomepic")],
            [InlineKeyboardButton("🔄 Reset to Default",   callback_data="cfg_reset_welcome")],
            [InlineKeyboardButton("🔙 BACK",               callback_data="cfg_back")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_edit_welcome$") & filters.user(OWNER_ID))
async def cfg_edit_welcome(client, query):
    await query.message.edit_text(
        "✏️ <b>Edit Welcome Message</b>\n\n"
        "Send your new welcome message now.\n"
        "Use HTML formatting and placeholders like <code>{first}</code>.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_welcome")
        ]])
    )
    await query.answer()
    try:
        resp = await client.ask(query.from_user.id, "", filters=filters.text, timeout=120)
        await set_setting('custom_start_msg', resp.text.strip())
        await resp.reply("✅ Welcome message updated!")
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "❌ Timed out.")
    await show_main_settings(client, query.from_user.id)


@Bot.on_callback_query(filters.regex(r"^cfg_set_welcomepic$") & filters.user(OWNER_ID))
async def cfg_set_welcomepic(client, query):
    await query.message.edit_text(
        "🖼️ <b>Set Welcome Image</b>\n\n"
        "Send the image you want to show on /start.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_welcome")
        ]])
    )
    await query.answer()
    try:
        resp    = await client.ask(query.from_user.id, "", filters=filters.photo, timeout=60)
        file_id = resp.photo.file_id
        await set_setting('start_pic', file_id)
        await resp.reply("✅ Welcome image saved!")
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "❌ Timed out.")
    await show_main_settings(client, query.from_user.id)


@Bot.on_callback_query(filters.regex(r"^cfg_reset_welcome$") & filters.user(OWNER_ID))
async def cfg_reset_welcome(client, query):
    await set_setting('custom_start_msg', None)
    await set_setting('start_pic', None)
    await query.answer("✅ Welcome message reset to default!", show_alert=True)
    await cfg_welcome(client, query)


# ── 📆 Daily Limit shortcut ───────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_dailylimit$") & filters.user(OWNER_ID))
async def cfg_dailylimit(client, query: CallbackQuery):
    limit = await get_setting('free_daily_limit') or FREE_DAILY_LIMIT
    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "       📆  <b>DAILY LIMIT</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🔘 <b>Current Limit:</b> {limit} files/day\n\n"
        "This applies to free users only.\n"
        "💎 Premium users always have unlimited downloads.\n\n"
        "Send the new limit:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("5/day",  callback_data="cfg_dlset_5"),
                InlineKeyboardButton("10/day", callback_data="cfg_dlset_10"),
                InlineKeyboardButton("20/day", callback_data="cfg_dlset_20"),
                InlineKeyboardButton("50/day", callback_data="cfg_dlset_50"),
            ],
            [InlineKeyboardButton("✏️ Custom", callback_data="cfg_set_dailylimit")],
            [InlineKeyboardButton("🔙 BACK",   callback_data="cfg_back")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_dlset_(\d+)$") & filters.user(OWNER_ID))
async def cfg_dlset_quick(client, query):
    limit = int(query.data.split("_")[2])
    await set_setting('free_daily_limit', limit)
    await query.answer(f"✅ Daily limit set to {limit}/day!", show_alert=True)
    await cfg_dailylimit(client, query)


# ── 🔙 Back to main settings ──────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_back$") & filters.user(OWNER_ID))
async def cfg_back(client, query: CallbackQuery):
    await show_main_settings(client, query.from_user.id, query.message.id)
    await query.answer()

# ── 🗄 DB Channel ──────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_dbchannel$") & filters.user([OWNER_ID]))
async def cfg_dbchannel(client, query: CallbackQuery):
    from config import CHANNEL_ID as _default_ch
    current = await get_setting('db_channel_id') or _default_ch

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "     🗄  <b>DB CHANNEL</b>\n"
        "╚══════════════════════════╝\n\n"
        f"📌 <b>Current:</b> <code>{current}</code>\n\n"
        "This is the private channel where all files are stored.\n\n"
        "⚠️ <b>Important:</b>\n"
        "• Bot must be <b>Admin</b> in the new channel\n"
        "• Forward a message from the new channel to the bot after changing\n"
        "• Old file links will stop working if you change this",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Change Channel", callback_data="cfg_dbchannel_edit")],
            [InlineKeyboardButton("🔙 BACK",           callback_data="cfg_back")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_dbchannel_edit$") & filters.user([OWNER_ID]))
async def cfg_dbchannel_edit(client, query: CallbackQuery):
    await query.message.edit_text(
        "✏️ <b>Change DB Channel</b>\n\n"
        "Choose how to set the channel:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔢 Enter Channel ID", callback_data="cfg_dbchannel_byid")],
            [InlineKeyboardButton("📨 Forward a Message", callback_data="cfg_dbchannel_byforward")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cfg_dbchannel")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_dbchannel_byid$") & filters.user([OWNER_ID]))
async def cfg_dbchannel_byid(client, query: CallbackQuery):
    await query.message.edit_text(
        "🔢 <b>Enter Channel ID</b>\n\n"
        "Send the channel ID:\n\n"
        "<i>Example: <code>-1001234567890</code></i>\n\n"
        "⚠️ Make sure the bot is already Admin in that channel!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_dbchannel")
        ]])
    )
    await query.answer()
    try:
        resp = await client.ask(query.from_user.id, "", filters=filters.text, timeout=60)
        new_id = int(resp.text.strip())
        await set_setting('db_channel_id', new_id)
        import config
        config.CHANNEL_ID = new_id
        await resp.reply(
            f"✅ <b>DB Channel updated!</b>\n\n"
            f"New channel: <code>{new_id}</code>\n\n"
            f"Now forward any message from the new channel to the bot to activate it."
        )
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "❌ Timed out.")
    except ValueError:
        await client.send_message(query.from_user.id, "❌ Invalid channel ID. Must be a number like -1001234567890")
    await show_main_settings(client, query.from_user.id)


@Bot.on_callback_query(filters.regex(r"^cfg_dbchannel_byforward$") & filters.user([OWNER_ID]))
async def cfg_dbchannel_byforward(client, query: CallbackQuery):
    # Set a flag so the forward handler knows to process next forward
    if not hasattr(client, 'waiting_db_forward'):
        client.waiting_db_forward = set()
    client.waiting_db_forward.add(query.from_user.id)

    await query.message.edit_text(
        "📨 <b>Forward a Message</b>\n\n"
        "Forward any message from your DB channel to the bot now.\n\n"
        "⚠️ Make sure the bot is already Admin in that channel!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_dbchannel_cancel_forward")
        ]])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_dbchannel_cancel_forward$") & filters.user([OWNER_ID]))
async def cfg_dbchannel_cancel_forward(client, query: CallbackQuery):
    if hasattr(client, 'waiting_db_forward'):
        client.waiting_db_forward.discard(query.from_user.id)
    await query.answer("Cancelled.")
    await cfg_dbchannel(client, query)


@Bot.on_message(filters.private & filters.user([OWNER_ID]), group=-2)
async def catch_db_forward(client, message: Message):
    if not hasattr(client, 'waiting_db_forward'):
        return
    if message.from_user.id not in client.waiting_db_forward:
        return

    # Check for forwarded channel message
    channel = None
    if hasattr(message, 'forward_origin') and message.forward_origin:
        if hasattr(message.forward_origin, 'chat'):
            channel = message.forward_origin.chat
    if not channel and message.forward_from_chat:
        channel = message.forward_from_chat

    if not channel:
        await message.reply("❌ Could not detect channel. Forward a message from a channel.")
        return

    # Remove from waiting set
    client.waiting_db_forward.discard(message.from_user.id)

    new_id = channel.id
    await set_setting('db_channel_id', new_id)
    if hasattr(channel, 'access_hash') and channel.access_hash:
        await set_setting('channel_access_hash', channel.access_hash)
    import config
    config.CHANNEL_ID = new_id

    await message.reply(
        f"✅ <b>DB Channel updated!</b>\n\n"
        f"Channel: <b>{channel.title}</b>\n"
        f"ID: <code>{new_id}</code>\n\n"
        f"Channel is now active! 🎉"
    )
    await show_main_settings(client, message.chat.id)

# ── 💬 Support System ─────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r"^cfg_support$") & filters.user([OWNER_ID]))
async def cfg_support(client, query: CallbackQuery):
    support_on = await get_setting('support_enabled')
    if support_on is None:
        support_on = True
    icon    = "✅ ON" if support_on else "❌ OFF"
    off_msg = await get_setting('support_off_message') or "Using default message"

    await query.message.edit_text(
        "╔══════════════════════════╗\n"
        "     💬  <b>SUPPORT SYSTEM</b>\n"
        "╚══════════════════════════╝\n\n"
        f"🔘 <b>Status:</b> {icon}\n"
        f"📝 <b>Off Message:</b> <i>{off_msg[:100]}</i>\n\n"
        "When OFF — users who tap Support will get a custom message instead.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔴 Turn OFF Support" if support_on else "🟢 Turn ON Support",
                callback_data="cfg_toggle_support"
            )],
            [InlineKeyboardButton("📝 Set Off Message", callback_data="cfg_support_offmsg")],
            [InlineKeyboardButton("🔙 BACK",            callback_data="cfg_back")],
        ])
    )
    await query.answer()


@Bot.on_callback_query(filters.regex(r"^cfg_toggle_support$") & filters.user([OWNER_ID]))
async def cfg_toggle_support(client, query):
    current = await get_setting('support_enabled')
    if current is None:
        current = True
    new_val = not current
    await set_setting('support_enabled', new_val)
    icon = "✅ ON" if new_val else "❌ OFF"
    await query.answer(f"Support: {icon}", show_alert=True)
    await cfg_support(client, query)


@Bot.on_callback_query(filters.regex(r"^cfg_support_offmsg$") & filters.user([OWNER_ID]))
async def cfg_support_offmsg(client, query: CallbackQuery):
    await query.message.edit_text(
        "📝 <b>Set Support Off Message</b>\n\n"
        "Send the message users will see when support is OFF.\n\n"
        "HTML formatting supported.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cfg_support")
        ]])
    )
    await query.answer()
    try:
        resp = await client.ask(query.from_user.id, "", filters=filters.text, timeout=120)
        await set_setting('support_off_message', resp.text.strip())
        await resp.reply("✅ Support off message saved!")
    except asyncio.TimeoutError:
        await client.send_message(query.from_user.id, "❌ Timed out.")
    await show_main_settings(client, query.from_user.id)
