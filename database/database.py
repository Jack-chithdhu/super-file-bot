#(©)CodeXBotz - Enhanced by Claude

import pymongo
from datetime import datetime
from config import DB_URI, DB_NAME

# ── Connection with retry ──────────────────────────────────────────────────────
def _connect():
    import time
    for attempt in range(1, 4):
        try:
            client = pymongo.MongoClient(DB_URI, serverSelectionTimeoutMS=5000)
            client.server_info()
            return client
        except Exception as e:
            if attempt == 3:
                raise RuntimeError(f"MongoDB connection failed after 3 attempts: {e}")
            time.sleep(2 ** attempt)

dbclient         = _connect()
database         = dbclient[DB_NAME]

user_data        = database['users']
premium_data     = database['premium_users']
banned_data      = database['banned_users']
file_stats_data  = database['file_stats']
join_req_data    = database['join_requests']
movie_req_data   = database['movie_requests']
admin_data       = database['bot_admins']
settings_data    = database['bot_settings']
chat_data        = database['support_chats']

# ── Indexes ───────────────────────────────────────────────────────────────────
user_data.create_index("_id")
premium_data.create_index("_id")
banned_data.create_index("_id")
file_stats_data.create_index("file_id")
movie_req_data.create_index("user_id")
movie_req_data.create_index("request_id")
admin_data.create_index("_id")
chat_data.create_index("user_id")

# ════════════════════════ USERS ═══════════════════════════════════════════════

async def present_user(user_id: int) -> bool:
    return bool(user_data.find_one({'_id': user_id}))

async def add_user(user_id: int):
    if not await present_user(user_id):
        user_data.insert_one({
            '_id': user_id,
            'joined': datetime.utcnow(),
            'downloads': 0,
            'daily_downloads': 0,
            'last_download_date': None
        })

async def full_userbase() -> list:
    return [doc['_id'] for doc in user_data.find()]

async def del_user(user_id: int):
    user_data.delete_one({'_id': user_id})

async def get_user_count() -> int:
    return user_data.count_documents({})

async def increment_user_downloads(user_id: int):
    today = datetime.utcnow().date().isoformat()
    doc   = user_data.find_one({'_id': user_id})
    if doc and doc.get('last_download_date') == today:
        user_data.update_one({'_id': user_id}, {'$inc': {'downloads': 1, 'daily_downloads': 1}})
    else:
        user_data.update_one(
            {'_id': user_id},
            {'$inc': {'downloads': 1}, '$set': {'daily_downloads': 1, 'last_download_date': today}},
            upsert=True
        )

async def get_daily_downloads(user_id: int) -> int:
    today = datetime.utcnow().date().isoformat()
    doc   = user_data.find_one({'_id': user_id})
    if not doc:
        return 0
    if doc.get('last_download_date') != today:
        return 0
    return doc.get('daily_downloads', 0)

# ════════════════════════ PREMIUM ═════════════════════════════════════════════

async def add_premium(user_id: int, expiry: datetime):
    premium_data.update_one(
        {'_id': user_id},
        {'$set': {'expiry': expiry, 'granted': datetime.utcnow()}},
        upsert=True
    )

async def remove_premium(user_id: int):
    premium_data.delete_one({'_id': user_id})

async def is_premium(user_id: int) -> bool:
    doc = premium_data.find_one({'_id': user_id})
    if not doc:
        return False
    if doc['expiry'] < datetime.utcnow():
        remove_premium(user_id)
        return False
    return True

async def get_premium_info(user_id: int):
    doc = premium_data.find_one({'_id': user_id})
    if doc and doc['expiry'] >= datetime.utcnow():
        return doc
    return None

async def list_premium_users() -> list:
    now = datetime.utcnow()
    return [doc for doc in premium_data.find({'expiry': {'$gte': now}})]

# ════════════════════════ BOT SETTINGS ════════════════════════════════════════

import asyncio

def _get_settings() -> dict:
    doc = settings_data.find_one({'_id': 'global'})
    if not doc:
        default = {
            '_id': 'global',
            'premium_mode': True,       # True = premium enforced, False = all free
            'free_daily_limit': 20,     # downloads per day for free users
            'free_auto_delete': True,   # auto-delete for free users
            'request_channel': None,    # channel id for movie requests
        }
        settings_data.insert_one(default)
        return default
    return doc

async def get_setting(key: str):
    loop = asyncio.get_event_loop()
    doc = await loop.run_in_executor(None, _get_settings)
    return doc.get(key)

async def set_setting(key: str, value):
    def _set():
        settings_data.update_one(
            {'_id': 'global'},
            {'$set': {key: value}},
            upsert=True
        )
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _set)

# ════════════════════════ BOT ADMINS ══════════════════════════════════════════

async def add_bot_admin(user_id: int, added_by: int):
    admin_data.update_one(
        {'_id': user_id},
        {'$set': {'added_by': added_by, 'added_at': datetime.utcnow()}},
        upsert=True
    )

async def remove_bot_admin(user_id: int):
    admin_data.delete_one({'_id': user_id})

async def get_bot_admins() -> list:
    return [doc['_id'] for doc in admin_data.find()]

async def is_bot_admin(user_id: int) -> bool:
    return bool(admin_data.find_one({'_id': user_id}))

# ════════════════════════ BANS ════════════════════════════════════════════════

async def ban_user(user_id: int, reason: str = "No reason provided"):
    banned_data.update_one(
        {'_id': user_id},
        {'$set': {'reason': reason, 'banned_at': datetime.utcnow()}},
        upsert=True
    )

async def unban_user(user_id: int):
    banned_data.delete_one({'_id': user_id})

async def is_banned(user_id: int) -> bool:
    return bool(banned_data.find_one({'_id': user_id}))

async def get_ban_info(user_id: int):
    return banned_data.find_one({'_id': user_id})

async def list_banned_users() -> list:
    return list(banned_data.find())

# ════════════════════════ FILE STATS ══════════════════════════════════════════

async def record_file_access(file_id: str, user_id: int):
    file_stats_data.update_one(
        {'file_id': file_id},
        {
            '$inc': {'access_count': 1},
            '$set': {'last_accessed': datetime.utcnow()},
            '$setOnInsert': {'created': datetime.utcnow()}
        },
        upsert=True
    )
    await increment_user_downloads(user_id)

async def get_top_files(limit: int = 10) -> list:
    return list(file_stats_data.find().sort('access_count', -1).limit(limit))

async def get_total_file_accesses() -> int:
    result = list(file_stats_data.aggregate([{'$group': {'_id': None, 'total': {'$sum': '$access_count'}}}]))
    return result[0]['total'] if result else 0

async def get_unique_files_count() -> int:
    return file_stats_data.count_documents({})

# ════════════════════════ MOVIE / ANIME REQUESTS ══════════════════════════════

import random, string

def _gen_req_id() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

async def create_movie_request(user_id: int, title: str, req_type: str, note: str = "") -> str:
    req_id = _gen_req_id()
    movie_req_data.insert_one({
        'request_id': req_id,
        'user_id':    user_id,
        'title':      title,
        'type':       req_type,   # 'movie' or 'anime'
        'note':       note,
        'status':     'pending',  # pending / fulfilled / declined
        'created_at': datetime.utcnow(),
        'response':   None,
        'responded_at': None,
    })
    return req_id

async def get_user_active_request(user_id: int):
    return movie_req_data.find_one({'user_id': user_id, 'status': 'pending'})

async def get_request_by_id(req_id: str):
    return movie_req_data.find_one({'request_id': req_id})

async def fulfill_request(req_id: str, admin_note: str = ""):
    movie_req_data.update_one(
        {'request_id': req_id},
        {'$set': {'status': 'fulfilled', 'response': admin_note, 'responded_at': datetime.utcnow()}}
    )

async def decline_request(req_id: str, reason: str):
    movie_req_data.update_one(
        {'request_id': req_id},
        {'$set': {'status': 'declined', 'response': reason, 'responded_at': datetime.utcnow()}}
    )

async def get_all_requests(status: str = None, limit: int = 20) -> list:
    query = {'status': status} if status else {}
    return list(movie_req_data.find(query).sort('created_at', -1).limit(limit))

async def get_user_requests(user_id: int, limit: int = 5) -> list:
    return list(movie_req_data.find({'user_id': user_id}).sort('created_at', -1).limit(limit))

# ════════════════════════ SUPPORT CHAT ════════════════════════════════════════

async def open_chat_session(user_id: int):
    chat_data.update_one(
        {'user_id': user_id},
        {'$set': {'active': True, 'opened_at': datetime.utcnow()}},
        upsert=True
    )

async def close_chat_session(user_id: int):
    chat_data.update_one(
        {'user_id': user_id},
        {'$set': {'active': False, 'closed_at': datetime.utcnow()}}
    )

async def get_chat_session(user_id: int):
    return chat_data.find_one({'user_id': user_id, 'active': True})

async def get_all_active_chats() -> list:
    return list(chat_data.find({'active': True}))

async def get_session_by_user(user_id: int):
    return chat_data.find_one({'user_id': user_id})

# ════════════════════════ JOIN REQUESTS ═══════════════════════════════════════

async def add_join_request(user_id: int):
    join_req_data.update_one(
        {'user_id': user_id},
        {'$set': {'requested_at': datetime.utcnow(), 'status': 'pending'}},
        upsert=True
    )

async def approve_join_request(user_id: int):
    join_req_data.update_one(
        {'user_id': user_id},
        {'$set': {'status': 'approved', 'approved_at': datetime.utcnow()}}
    )

async def get_pending_requests(limit: int = 50) -> list:
    return list(join_req_data.find({'status': 'pending'}).limit(limit))

async def get_request_count() -> dict:
    return {
        'pending':  join_req_data.count_documents({'status': 'pending'}),
        'approved': join_req_data.count_documents({'status': 'approved'}),
        'total':    join_req_data.count_documents({})
    }


# ════════════════════════ CAPTCHA PASSED ══════════════════════════════════════

captcha_passed_data = database['captcha_passed']
captcha_passed_data.create_index("expires_at", expireAfterSeconds=0)  # MongoDB TTL index

async def mark_captcha_passed(user_id: int):
    """Mark user as having just passed captcha (expires in 60s)."""
    from datetime import timedelta
    def _mark():
        captcha_passed_data.update_one(
            {'_id': user_id},
            {'$set': {'expires_at': datetime.utcnow() + timedelta(seconds=60)}},
            upsert=True
        )
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _mark)

async def check_captcha_passed(user_id: int) -> bool:
    """Returns True if user recently passed captcha (within 60s)."""
    def _check():
        doc = captcha_passed_data.find_one({'_id': user_id})
        if not doc:
            return False
        return doc['expires_at'] > datetime.utcnow()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _check)

async def clear_captcha_passed(user_id: int):
    def _clear():
        captcha_passed_data.delete_one({'_id': user_id})
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _clear)

async def reset_all_captcha_passed():
    """Admin reset — clears captcha_just_passed state for all users."""
    def _reset():
        captcha_passed_data.delete_many({})
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _reset)

# ════════════════════════ PAYMENT SETTINGS ════════════════════════════════════

pending_deletes_data = database['pending_deletes']
pending_deletes_data.create_index("scheduled_at")

async def save_pending_delete(user_id: int, message_ids: list, delete_at: float):
    """Persist a scheduled auto-delete so it survives bot restarts."""
    def _save():
        pending_deletes_data.insert_one({
            'user_id':    user_id,
            'message_ids': message_ids,
            'delete_at':  delete_at,
        })
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _save)

async def get_due_pending_deletes() -> list:
    """Return all pending deletes that are due now."""
    import time
    def _get():
        return list(pending_deletes_data.find({'delete_at': {'$lte': time.time()}}))
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)

async def remove_pending_delete(doc_id):
    def _remove():
        pending_deletes_data.delete_one({'_id': doc_id})
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _remove)

async def get_all_pending_deletes() -> list:
    def _get():
        return list(pending_deletes_data.find())
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get)


async def set_payment_info(info: dict):
    """Save payment details set by owner."""
    settings_data.update_one(
        {'_id': 'global'},
        {'$set': {'payment_info': info}},
        upsert=True
    )

async def get_payment_info() -> dict:
    """Get payment details."""
    doc = settings_data.find_one({'_id': 'global'})
    return doc.get('payment_info', {}) if doc else {}

# ════════════════════════ PREMIUM REQUESTS ════════════════════════════════════

premium_req_data = database['premium_requests']
premium_req_data.create_index("user_id")

async def create_premium_request(user_id: int, username: str, first_name: str) -> str:
    import random, string
    req_id = 'PR' + ''.join(random.choices(string.digits, k=6))
    premium_req_data.update_one(
        {'user_id': user_id},
        {'$set': {
            'req_id':     req_id,
            'username':   username,
            'first_name': first_name,
            'status':     'pending',
            'created_at': datetime.utcnow(),
        }},
        upsert=True
    )
    return req_id

async def get_premium_request(user_id: int):
    return premium_req_data.find_one({'user_id': user_id, 'status': 'pending'})

async def close_premium_request(user_id: int):
    premium_req_data.update_one(
        {'user_id': user_id},
        {'$set': {'status': 'closed', 'closed_at': datetime.utcnow()}}
    )

# ════════════════════════ PAYMENT QR ══════════════════════════════════════════

async def set_payment_qr(file_id: str):
    settings_data.update_one(
        {'_id': 'global'},
        {'$set': {'payment_qr': file_id}},
        upsert=True
    )

async def get_payment_qr() -> str:
    doc = settings_data.find_one({'_id': 'global'})
    return doc.get('payment_qr', None) if doc else None

async def clear_payment_qr():
    settings_data.update_one(
        {'_id': 'global'},
        {'$unset': {'payment_qr': ''}}
    )

# ════════════════════════ REQUEST SETTINGS ════════════════════════════════════

async def get_request_settings() -> dict:
    doc = settings_data.find_one({'_id': 'global'})
    defaults = {
        'requests_enabled':    True,
        'request_channel':     None,
        'request_custom_msg':  None,
        'auto_decline_days':   0,       # 0 = disabled
        'allowed_req_types':   ['movie', 'anime', 'series'],
    }
    if not doc:
        return defaults
    for k, v in defaults.items():
        if k not in doc:
            doc[k] = v
    return doc

async def get_old_pending_requests(days: int) -> list:
    """Get pending requests older than X days."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    return list(movie_req_data.find({
        'status': 'pending',
        'created_at': {'$lt': cutoff}
    }))

async def clear_all_chat_sessions():
    """Force close all active chat sessions."""
    chat_data.update_many(
        {'active': True},
        {'$set': {'active': False, 'closed_at': datetime.utcnow()}}
    )
