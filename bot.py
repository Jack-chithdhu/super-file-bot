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
        # Use session string if available — persists across redeploys on Railway/Koyeb
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

        # ── Force Sub channel check ────────────────────────────────────────
        if FORCE_SUB_CHANNEL:
            try:
                link = (await self.get_chat(FORCE_SUB_CHANNEL)).invite_link
                if not link:
                    await self.export_chat_invite_link(FORCE_SUB_CHANNEL)
                    link = (await self.get_chat(FORCE_SUB_CHANNEL)).invite_link
                self.invitelink = link
            except Exception as a:
                self.LOGGER(__name__).warning(a)
                self.LOGGER(__name__).warning(
                    f"Please Double check the FORCE_SUB_CHANNEL value, Current Value: {FORCE_SUB_CHANNEL}"
                )
                self.LOGGER(__name__).info("\nBot Stopped.")
                sys.exit()

        # ── DB channel check ───────────────────────────────────────────────
        from database.database import get_setting, set_setting
        active_ch = await get_setting('db_channel_id') or CHANNEL_ID
        active_ch = int(active_ch)

        try:
            test = await self.send_message(chat_id=active_ch, text="✅ Bot started!")
            self.db_channel = test.chat
            await test.delete()
            self.LOGGER(__name__).info(f"✅ DB Channel connected: {active_ch}")
        except Exception as e:
            self.LOGGER(__name__).warning(str(e))
            # Try to resolve peer by joining/getting the channel directly
            try:
                from pyrogram.raw.functions.messages import GetDialogs
                from pyrogram.raw.types import InputPeerEmpty
                # Fetch dialogs to populate peer cache
                await self.invoke(GetDialogs(
                    offset_date=0, offset_id=0,
                    offset_peer=InputPeerEmpty(),
                    limit=100, hash=0
                ))
                # Retry sending message
                test = await self.send_message(chat_id=active_ch, text="✅ Bot started!")
                self.db_channel = test.chat
                await test.delete()
                self.LOGGER(__name__).info(f"✅ DB Channel connected after peer refresh: {active_ch}")
            except Exception as e2:
                self.LOGGER(__name__).warning(f"Could not connect to DB Channel: {e2}")
                self.LOGGER(__name__).warning(
                    f"Bot will continue but file delivery may not work. CHANNEL_ID: {active_ch}"
                )
                self.db_channel = type('obj', (object,), {'id': active_ch})()

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
