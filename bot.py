#(©)CodeXBotz - Enhanced by Claude

from aiohttp import web
from plugins import web_server

import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime

from config import API_HASH, APP_ID, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, FORCE_SUB_CHANNEL, CHANNEL_ID, PORT

ascii_art = """
░█████╗░░█████╗░██████╗░███████╗██╗░░██╗██████╗░░█████╗░████████╗███████╗
██╔══██╗██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗╚══██╔══╝╚════██║
██║░░╚═╝██║░░██║██║░░██║█████╗░░░╚███╔╝░██████╦╝██║░░██║░░░██║░░░░░███╔═╝
██║░░██╗██║░░██║██║░░██║██╔══╝░░░██╔██╗░██╔══██╗██║░░██║░░░██║░░░██╔══╝░░
╚█████╔╝╚█████╔╝██████╔╝███████╗██╔╝╚██╗██████╦╝╚█████╔╝░░░██║░░░███████╗
░╚════╝░░╚════╝░╚═════╝░╚══════╝╚═╝░░╚═╝╚═════╝░╚════╝░░░░╚═╝░░░╚══════╝
"""


async def _inject_peer(client: Client, channel_id: int, access_hash: int):
    """
    Manually inject a channel peer into Pyrogram's in-memory storage.
    Pyromod-compatible — does not use the 'storage' constructor kwarg.
    """
    try:
        bare_id = int(str(channel_id).replace('-100', ''))
        await client.storage.update_peers([
            (bare_id, access_hash, 'channel', None, None)
        ])
        LOGGER(__name__).info("✅ Peer injected from MongoDB cache.")
    except Exception as e:
        LOGGER(__name__).warning(f"Peer injection failed: {e}")


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN,
        )
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
                    await self.export_chat_invoke_link(FORCE_SUB_CHANNEL)
                    link = (await self.get_chat(FORCE_SUB_CHANNEL)).invite_link
                self.invitelink = link
            except Exception as a:
                self.LOGGER(__name__).warning(a)
                self.LOGGER(__name__).warning(
                    f"Can't export invite link from Force Sub Channel! Value: {FORCE_SUB_CHANNEL}"
                )
                self.LOGGER(__name__).info("\nBot Stopped.")
                sys.exit()

        # ── DB channel check ───────────────────────────────────────────────
        from database.database import get_setting, set_setting
        active_ch = await get_setting('db_channel_id') or CHANNEL_ID
        active_ch = int(active_ch)

        # Step 1: Try to get access hash via get_chat() first (no peer needed)
        saved_hash = await get_setting('channel_access_hash')
        if saved_hash:
            await _inject_peer(self, active_ch, int(saved_hash))
            self.LOGGER(__name__).info("✅ Peer injected from MongoDB cache.")

        # Step 2: Try get_chat to resolve peer and save fresh hash
        try:
            chat = await self.get_chat(active_ch)
            # Save access hash to MongoDB for future restarts
            if hasattr(chat, 'access_hash') and chat.access_hash:
                await set_setting('channel_access_hash', chat.access_hash)
                if not saved_hash:
                    # First time — inject now so send_message works below
                    await _inject_peer(self, active_ch, chat.access_hash)
            self.LOGGER(__name__).info(f"✅ DB Channel resolved: {active_ch}")
        except Exception as e:
            self.LOGGER(__name__).warning(f"get_chat failed: {e}")

        # Step 3: Try to contact the channel
        try:
            test = await self.send_message(chat_id=active_ch, text="✅ Bot started!")
            self.db_channel = test.chat
            await set_setting('channel_access_hash', test.chat.access_hash)
            await test.delete()
            self.LOGGER(__name__).info(f"✅ DB Channel connected: {active_ch}")
        except Exception as e:
            self.LOGGER(__name__).warning(str(e))
            self.LOGGER(__name__).warning(
                f"Could not send to DB Channel. Continuing anyway. CHANNEL_ID: {active_ch}"
            )
            self.db_channel = type('obj', (object,), {'id': active_ch})()

        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username

        # ── Start premium expiry reminder scheduler (skip in survival mode) ──
        from config import SURVIVAL_MODE
        if not SURVIVAL_MODE:
            from plugins.reminder import start_reminder_scheduler
            await start_reminder_scheduler(self)
        else:
            self.LOGGER(__name__).info("⚡ SURVIVAL MODE — reminders, support, captcha disabled.")

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
