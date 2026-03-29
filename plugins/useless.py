#(©)CodeXBotz - Enhanced by Claude

from bot import Bot
from pyrogram.types import Message
from pyrogram import filters
from config import ADMINS, BOT_STATS_TEXT, USER_REPLY_TEXT
from datetime import datetime
from helper_func import get_readable_time

ALL_COMMANDS = [
    'start','users','broadcast','batch','genlink','stats',
    'ban','unban','banned','filestats','requests','approverequest','approveall',
    'addpremium','removepremium','listpremium','allrequests','fulfill','decline',
    'chatto','endchat','activechats','support','closechat','mystatus','request',
    'addadmin','removeadmin','listadmins','togglepremium','setdailylimit',
    'adminhelp','premium','addfile','getfiles','listfiles','deletefile',
    'filestore','cancel','linkstats','clearjoinrequests','settings','announce',
    'setpayment','setqr','help','profile','approverequest','approveall'
]

@Bot.on_message(filters.command('stats') & filters.user(ADMINS))
async def stats(bot: Bot, message: Message):
    now   = datetime.now()
    delta = now - bot.uptime
    time  = get_readable_time(delta.seconds)
    await message.reply(BOT_STATS_TEXT.format(uptime=time))


@Bot.on_message(filters.private & filters.incoming & ~filters.command(ALL_COMMANDS))
async def useless(_, message: Message):
    # Let support_chat.py relay handler process it first
    # This only fires if none of the relay conditions matched
    pass
