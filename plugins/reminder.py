#(©)CodeXBotz - Enhanced by Claude
# Premium Expiry Reminder Scheduler

import asyncio
import logging
from datetime import datetime
from pyrogram.errors import FloodWait

from database.database import list_premium_users, remove_premium

logger = logging.getLogger(__name__)

# Days before expiry to send reminders
REMINDER_DAYS = [3, 1]


async def send_expiry_reminders(client):
    """
    Background task — runs every 12 hours.
    • Sends reminders at 3 days and 1 day before expiry.
    • Auto-removes and notifies users whose premium has expired.
    """
    while True:
        try:
            now   = datetime.utcnow()
            users = await list_premium_users()

            for user in users:
                expiry    = user['expiry']
                user_id   = user['_id']
                days_left = (expiry - now).days

                # ── Expired ────────────────────────────────────────────────
                if expiry < now:
                    await remove_premium(user_id)
                    try:
                        await client.send_message(
                            chat_id=user_id,
                            text=(
                                "⚠️ <b>Premium Expired</b>\n\n"
                                "Your premium subscription has expired and you've been "
                                "moved back to the free tier.\n\n"
                                "Contact the admin to renew! 💎"
                            )
                        )
                    except Exception:
                        pass
                    continue

                # ── Reminder ───────────────────────────────────────────────
                if days_left in REMINDER_DAYS:
                    try:
                        await client.send_message(
                            chat_id=user_id,
                            text=(
                                f"⏰ <b>Premium Expiry Reminder</b>\n\n"
                                f"Your subscription expires in "
                                f"<b>{days_left} day{'s' if days_left > 1 else ''}</b> "
                                f"(<code>{expiry.strftime('%Y-%m-%d')}</code>).\n\n"
                                f"Renew now to keep your premium perks! 💎"
                            )
                        )
                        logger.info(f"Sent expiry reminder → user {user_id} ({days_left}d left)")
                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                    except Exception as e:
                        logger.warning(f"Reminder failed for {user_id}: {e}")

        except Exception as e:
            logger.warning(f"Reminder scheduler error: {e}")

        # Run every 12 hours
        await asyncio.sleep(12 * 60 * 60)


async def start_reminder_scheduler(client):
    """Launch the background reminder task. Call from bot.py after start()."""
    asyncio.create_task(send_expiry_reminders(client))
    logger.info("✅ Premium expiry reminder scheduler started (checks every 12h).")
