#(©)CodeXBotz - Enhanced by Claude

from aiohttp import web
from plugins import web_server

import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime

from config import API_HASH, APP_ID, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, FORCE_SUB_CHANNEL, CHANNEL_ID, PORT, DB_URI, DB_NAME

ascii_art = """
░█████╗░░█████╗░██████╗░███████╗██╗░░██╗██████╗░░█████╗░████████╗███████╗
██╔══██╗██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗╚══██╔══╝╚════██║
██║░░╚═╝██║░░██║██║░░██║█████╗░░░╚███╔╝░██████╦╝██║░░██║░░░██║░░░░░███╔═╝
██║░░██╗██║░░██║██║░░██║██╔══╝░░░██╔██╗░██╔══██╗██║░░██║░░░██║░░░██╔══╝░░
╚█████╔╝╚█████╔╝██████╔╝███████╗██╔╝╚██╗██████╦╝╚█████╔╝░░░██║░░░███████╗
░╚════╝░░╚════╝░╚═════╝░╚══════╝╚═╝░░╚═╝╚═════╝░╚════╝░░░░╚═╝░░░╚══════╝
"""

# ── MongoDB Session Storage ────────────────────────────────────────────────────
# Stores Pyrogram session (including peer/access hash cache) in MongoDB so it
# survives Railway/Koyeb redeploys — fixes "Peer id invalid" on every restart.
try:
    from pymongo import MongoClient as _MongoClient
    from pyrogram.storage import MemoryStorage
    import pickle, struct

    class MongoStorage(MemoryStorage):
        """
        Thin MongoDB-backed session storage for Pyrogram.
        Loads session from MongoDB on init, saves back on every update.
        """
        COLLECTION = "pyrogram_session"

        def __init__(self, name: str, mongo_uri: str, db_name: str):
            super().__init__(name)
            self._col = _MongoClient(mongo_uri)[db_name][self.COLLECTION]

        async def open(self):
            await super().open()
            doc = self._col.find_one({"_id": "session"})
            if doc and doc.get("data"):
                try:
                    # Restore all stored peers into memory
                    peers = pickle.loads(doc["data"])
                    if isinstance(peers, list) and peers:
                        await self.update_peers(peers)
                        LOGGER(__name__).info(
                            f"✅ Session restored from MongoDB ({len(peers)} peers)."
                        )
                except Exception as e:
                    LOGGER(__name__).warning(f"Could not restore session from MongoDB: {e}")

        async def update_peers(self, peers):
            await super().update_peers(peers)
            # Persist updated peers back to MongoDB immediately
            try:
                all_peers = list((await self.peers_by_id()).values()) if hasattr(self, 'peers_by_id') else peers
                self._col.update_one(
                    {"_id": "session"},
                    {"$set": {"data": pickle.dumps(peers)}},
                    upsert=True
                )
            except Exception as e:
                LOGGER(__name__).warning(f"Could not save session to MongoDB: {e}")

    _USE_MONGO_SESSION = True
except Exception as _e:
    LOGGER(__name__).warning(f"MongoStorage unavailable, using file session: {_e}")
    _USE_MONGO_SESSION = False


class Bot(Client):
    def __init__(self):
        kwargs = dict(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN,
        )
        if _USE_MONGO_SESSION:
            kwargs["storage"] = MongoStorage("Bot", DB_URI, DB_NAME)
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
                    f"Can't export invite link from Force Sub Channel! Value: {FORCE_SUB_CHANNEL}"
                )
                self.LOGGER(__name__).info("\nBot Stopped.")
                sys.exit()

        # ── DB channel check ───────────────────────────────────────────────
        # Try to resolve peer from stored access hash in MongoDB
        from database.database import get_setting, set_setting
        active_ch = await get_setting('db_channel_id') or CHANNEL_ID
        active_ch = int(active_ch)

        # Try to restore peer from saved access hash
        saved_hash = await get_setting('channel_access_hash')
        if saved_hash:
            try:
                from pyrogram.raw import types as raw_types
                from pyrogram.errors import PeerIdInvalid
                peer = raw_types.InputChannel(
                    channel_id=int(str(active_ch).replace('-100', '')),
                    access_hash=int(saved_hash)
                )
                await self.storage.update_peers([(
                    int(str(active_ch).replace('-100', '')),
                    int(saved_hash),
                    'channel', None, None
                )])
                self.LOGGER(__name__).info("✅ Peer restored from MongoDB cache.")
            except Exception as e:
                self.LOGGER(__name__).warning(f"Could not restore peer: {e}")

        try:
            test = await self.send_message(chat_id=active_ch, text="✅ Bot started!")
            self.db_channel = test.chat
            # Save access hash for future restores
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

        # ── Start premium expiry reminder scheduler ────────────────────────
        from plugins.reminder import start_reminder_scheduler
        await start_reminder_scheduler(self)

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
