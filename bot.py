#(©)CodeXBotz - Enhanced by Claude

from aiohttp import web
from plugins import web_server

import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime

from config import API_HASH, APP_ID, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, FORCE_SUB_CHANNEL, CHANNEL_ID, PORT, SESSION_STRING

ascii_art = """
░█████╗░░█████╗░██████╗░███████╗██╗░░██╗██████╗░░█████╗░████████╗███████╗
██╔══██╗██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗╚══██╔══╝╚════██║
██║░░╚═╝██║░░██║██║░░██║█████╗░░░╚███╔╝░██████╦╝██║░░██║░░░██║░░░░░███╔═╝
██║░░██╗██║░░██║██║░░██║██╔══╝░░░██╔██╗░██╔══██╗██║░░██║░░░██║░░░██╔══╝░░
╚█████╔╝╚█████╔╝██████╔╝███████╗██╔╝╚██╗██████╦╝╚█████╔╝░░░██║░░░███████╗
░╚════╝░░╚════╝░╚═════╝░╚══════╝╚═╝░░╚═╝╚═════╝░╚════╝░░░░╚═╝░░░╚══════╝
"""


class Bot(Client):
    def __init__(self):
        kwargs = dict(
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN,
        )
        if SESSION_STRING:
            kwargs["session_string"] = SESSION_STRING
            kwargs["name"] = ":memory:"
        else:
            kwargs["name"] = "Bot"
        super().__init__(**kwargs)
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()
        usr_bot_me  = await self.get_me()
        self.uptime = datetime.now()

        # ── Force Sub channel: resolve peer + cache invite link ────────────
        from plugins.force_sub import _resolve_peer, get_invite_link
        await _resolve_peer(self, FORCE_SUB_CHANNEL)
        link = await get_invite_link(self)
        if link:
            self.invitelink = link
            self.LOGGER(__name__).info("✅ Force Sub invite link cached.")

        # ── DB channel check ───────────────────────────────────────────────
        from database.database import get_setting, set_setting
        active_ch = int(await get_setting('db_channel_id') or CHANNEL_ID)

        # Resolve DB channel peer
        from plugins.force_sub import _resolve_peer as _rp
        await _rp(self, active_ch)

        try:
            test = await self.send_message(chat_id=active_ch, text="✅ Bot started!")
            self.db_channel = test.chat
            await test.delete()
            self.LOGGER(__name__).info(f"✅ DB Channel connected: {active_ch}")
        except Exception as e:
            self.LOGGER(__name__).warning(str(e))
            self.LOGGER(__name__).warning(
                f"Make Sure bot is Admin in DB Channel. CHANNEL_ID: {active_ch}"
            )
            self.LOGGER(__name__).info("\nBot Stopped.")
            sys.exit()

        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username

        # ── Start premium expiry reminder scheduler ────────────────────────
        from config import SURVIVAL_MODE
        if not SURVIVAL_MODE:
            from plugins.reminder import start_reminder_scheduler
            await start_reminder_scheduler(self)
        else:
            self.LOGGER(__name__).info("⚡ SURVIVAL MODE — reminders disabled.")

        self.LOGGER(__name__).info(
            f"✅ Bot @{self.username} is running!\n\n"
            "Active Features:\n"
            "  💎 Premium Subscription System\n"
            "  ⏩ Premium: Skip Force Subscribe\n"
            "  🔒 Premium: Auto-delete Bypass\n"
            "  ⏰ Premium: Expiry Reminders (3d + 1d)\n"
            "  🚫 User Ban/Unban System\n"
            "  📊 File Statistics Dashboard\n"
            "  📋 Join Request Management\n"
            "  📡 Improved Broadcast (with progress)\n"
        )
        print(ascii_art)
        print("Welcome to File Sharing Bot — Enhanced Edition")

        # ── Web server ─────────────────────────────────────────────────────
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")
