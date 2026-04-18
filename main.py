"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 ULTRA ADVANCED FILESTORE BOT v4.1 — PRODUCTION GRADE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ RENDER READY      — aiohttp health-check on $PORT
✅ BROADCAST FIXED   — pre-stored in DB_CHANNEL, copy per-bot
✅ REBUILD FIXED     — Userbot (SESSION_STRING) scans channel history
                       Bot alone CANNOT use get_chat_history (API limit)
✅ CHANNEL DELIVERY  — works even after full local DB wipe
✅ THUMBNAIL FIXED   — BytesIO in_memory download → thumb param
✅ CAPTION EDITOR    — FSM, -clear support, persisted to channel
✅ WELCOME EDITOR    — /setwelcome interactive 2-step FSM
✅ JOIN REQUEST      — pending join = bot access granted
✅ FORCE SUB MULTI   — up to 3 channels, cascade to clones
✅ CLONE SYSTEM      — multi-level bot cloning
✅ REFERRAL+PREMIUM  — points system
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO SETUP SESSION_STRING:
  1. Run generate_session.py on your local machine
  2. Set SESSION_STRING as env var on Render
  3. The userbot account must be admin/member of DB_CHANNEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import json
import asyncio
import hashlib
import logging
import random
import shutil
import time
import aiohttp
from aiohttp import web
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, BotCommand,
    InlineQueryResultArticle, InputTextMessageContent
)
from pyrogram.errors import (
    FloodWait, UserNotParticipant, MessageNotModified,
    SessionPasswordNeeded, PhoneCodeInvalid
)
from pyrogram.enums import ChatMemberStatus

# ═══════════════════════════════════════════════════════════════
# 🔧 CONFIGURATION  (env vars override hardcoded defaults)
# ═══════════════════════════════════════════════════════════════

API_ID          = int(os.environ.get("API_ID",          "23790796"))
API_HASH        = os.environ.get("API_HASH",             "626eb31c9057007df4c2851b3074f27f")
MAIN_BOT_TOKEN  = os.environ.get("MAIN_BOT_TOKEN",      "8607033631:AAEEHymSzeLeP8wpH1TR4vnZSyai3kI1DTE")
MAIN_ADMIN      = int(os.environ.get("MAIN_ADMIN",      "8756786934"))
DB_CHANNEL      = int(os.environ.get("DB_CHANNEL",      "-1003982754680"))
PORT            = int(os.environ.get("PORT",             "8080"))

# SESSION_STRING: Required for /rebuild (userbot scans channel history)
# Generate with: python generate_session.py
SESSION_STRING  = os.environ.get("SESSION_STRING", "")

FILE_CACHE_DURATION      = 60 * 60
MAX_FORCE_SUB_CHANNELS   = 3
PENDING_REQUEST_TTL_DAYS = 30
METADATA_TAG             = "#FS_META"   # prefix in DB_CHANNEL text messages
MAX_BROADCAST_RATE       = 0.05         # seconds between sends (flood prevention)

# ─── Database paths ─────────────────────────────────────────────
DB_FOLDER       = "database"
FILES_DB        = f"{DB_FOLDER}/files.json"
BATCH_DB        = f"{DB_FOLDER}/batches.json"
BOTS_DB         = f"{DB_FOLDER}/bots.json"
USERS_DB        = f"{DB_FOLDER}/users.json"
ADMINS_DB       = f"{DB_FOLDER}/admins.json"
FILE_CACHE_DB   = f"{DB_FOLDER}/file_cache.json"
CONFIG_DB       = f"{DB_FOLDER}/config.json"
PENDING_REQ_DB  = f"{DB_FOLDER}/pending_requests.json"

BOT_COMMANDS = [
    BotCommand("start",         "🚀 Start the bot"),
    BotCommand("admin",         "⚡ Admin Panel"),
    BotCommand("supreme",       "👑 Supreme Panel"),
    BotCommand("clone",         "🤖 Clone your bot"),
    BotCommand("batch",         "📦 Batch mode"),
    BotCommand("done",          "✅ Finish batch"),
    BotCommand("cancel",        "❌ Cancel"),
    BotCommand("setfs",         "⚙️ Force subscribe"),
    BotCommand("mybots",        "🤖 Your cloned bots"),
    BotCommand("stats",         "📊 Statistics"),
    BotCommand("help",          "ℹ️ Help"),
    BotCommand("broadcast",     "📢 Broadcast"),
    BotCommand("ban",           "🚫 Ban user"),
    BotCommand("unban",         "✅ Unban user"),
    BotCommand("botinfo",       "ℹ️ Bot info"),
    BotCommand("settimer",      "⏱ Auto-delete timer"),
    BotCommand("search",        "🔍 Search files"),
    BotCommand("points",        "💰 Points"),
    BotCommand("refer",         "🔗 Referral"),
    BotCommand("premium",       "🌟 Premium"),
    BotCommand("shortener",     "🔗 URL Shortener"),
    BotCommand("buy_premium",   "🎁 Buy Premium"),
    BotCommand("setlog",        "📝 Log Channel"),
    BotCommand("rebuild",       "🔄 Rebuild DB from channel"),
    BotCommand("restart",       "♻️ Restart (Supreme)"),
    BotCommand("ping",          "🏓 Ping"),
    BotCommand("listfiles",     "📋 List files"),
    BotCommand("editfile",      "✏️ Edit file"),
    BotCommand("delfile",       "🗑 Delete file"),
    BotCommand("addpoints",     "💰 Add points (Admin)"),
    BotCommand("setwelcome",    "👋 Set welcome message"),
]

# ═══════════════════════════════════════════════════════════════
# 📝 LOGGING
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("FileStore")

# ═══════════════════════════════════════════════════════════════
# 💾 DATABASE — Atomic JSON with in-memory cache
# ═══════════════════════════════════════════════════════════════

os.makedirs(DB_FOLDER, exist_ok=True)
_DB_CACHE:  dict = {}
_GLOBAL_CFG: dict = {}

def load_db(path: str) -> dict:
    if path in _DB_CACHE:
        return _DB_CACHE[path]
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({}, f)
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        data = {}
    _DB_CACHE[path] = data
    return data

def save_db(path: str, data: dict) -> None:
    _DB_CACHE[path] = data
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def invalidate_cache(path: str) -> None:
    _DB_CACHE.pop(path, None)

def get_global_config() -> dict:
    global _GLOBAL_CFG
    if not _GLOBAL_CFG:
        _GLOBAL_CFG = load_db(CONFIG_DB)
    return _GLOBAL_CFG

def update_global_config(key: str, value) -> None:
    global _GLOBAL_CFG
    cfg = load_db(CONFIG_DB)
    cfg[key] = value
    save_db(CONFIG_DB, cfg)
    _GLOBAL_CFG = cfg

# ─── PENDING JOIN REQUESTS ──────────────────────────────────────

_PENDING: dict = {}   # {channel_id: {user_id: iso_ts}}

def _load_pending():
    global _PENDING
    raw = load_db(PENDING_REQ_DB)
    now = datetime.now()
    result = {}
    for cid, users in raw.items():
        if not isinstance(users, dict):
            continue
        clean = {}
        for uid, ts in users.items():
            try:
                if (now - datetime.fromisoformat(ts)).days <= PENDING_REQUEST_TTL_DAYS:
                    clean[int(uid)] = ts
            except Exception:
                pass
        if clean:
            result[int(cid)] = clean
    _PENDING = result

def _save_pending():
    data = {str(c): {str(u): ts for u, ts in users.items()} for c, users in _PENDING.items()}
    save_db(PENDING_REQ_DB, data)

def mark_join_request(channel_id: int, user_id: int):
    _PENDING.setdefault(channel_id, {})[user_id] = datetime.now().isoformat()
    _save_pending()

def clear_join_request(channel_id: int, user_id: int):
    _PENDING.get(channel_id, {}).pop(user_id, None)
    _save_pending()

def has_pending_request(channel_id: int, user_id: int) -> bool:
    ts_str = _PENDING.get(channel_id, {}).get(user_id)
    if not ts_str:
        return False
    try:
        return (datetime.now() - datetime.fromisoformat(ts_str)).days <= PENDING_REQUEST_TTL_DAYS
    except Exception:
        return False

# ─── USER FUNCTIONS ─────────────────────────────────────────────

def add_user(user_id, bot_id, username=None, name=None, referred_by=None):
    users = load_db(USERS_DB)
    key   = f"{bot_id}_{user_id}"
    is_new = key not in users
    if is_new:
        users[key] = {
            "user_id": user_id, "bot_id": bot_id,
            "username": username, "name": name,
            "join_date": str(datetime.now()),
            "is_banned": False, "files_uploaded": 0,
            "batches_created": 0, "bots_cloned": 0,
            "referred_by": referred_by, "referrals": 0,
            "points": 0, "is_premium": False
        }
        save_db(USERS_DB, users)
        if referred_by and referred_by != user_id:
            rk = f"{bot_id}_{referred_by}"
            if rk in users:
                users[rk]["referrals"] = users[rk].get("referrals", 0) + 1
                users[rk]["points"]    = users[rk].get("points", 0) + 10
                save_db(USERS_DB, users)
    return users[key], is_new

def get_user(user_id, bot_id):
    return load_db(USERS_DB).get(f"{bot_id}_{user_id}")

def update_user_stats(user_id, bot_id, field, delta=1):
    users = load_db(USERS_DB)
    k = f"{bot_id}_{user_id}"
    if k in users:
        users[k][field] = users[k].get(field, 0) + delta
        save_db(USERS_DB, users)

def is_user_banned(user_id, bot_id) -> bool:
    if user_id in get_global_config().get("global_bans", []):
        return True
    u = get_user(user_id, bot_id)
    return bool(u and u.get("is_banned"))

def ban_user(user_id, bot_id) -> bool:
    users = load_db(USERS_DB)
    k = f"{bot_id}_{user_id}"
    if k in users:
        users[k]["is_banned"] = True
        save_db(USERS_DB, users)
        return True
    return False

def unban_user(user_id, bot_id) -> bool:
    users = load_db(USERS_DB)
    k = f"{bot_id}_{user_id}"
    if k in users:
        users[k]["is_banned"] = False
        save_db(USERS_DB, users)
        return True
    return False

def get_all_users(bot_id=None):
    users = load_db(USERS_DB)
    if bot_id:
        return [u for u in users.values() if u["bot_id"] == bot_id and not u.get("is_banned")]
    return [u for u in users.values() if not u.get("is_banned")]

def is_admin(user_id) -> bool:
    return user_id == MAIN_ADMIN or str(user_id) in load_db(ADMINS_DB)

# ─── BOT INFO ───────────────────────────────────────────────────

def save_bot_info(token, bot_id, bot_username, owner_id, owner_name, parent_bot_id=None):
    bots = load_db(BOTS_DB)
    bots[str(bot_id)] = {
        "token": token, "bot_id": bot_id,
        "bot_username": bot_username, "owner_id": owner_id,
        "owner_name": owner_name, "parent_bot_id": parent_bot_id,
        "created_on": str(datetime.now()), "is_active": True,
        "custom_welcome": None, "welcome_image": None,
        "auto_delete_time": 600, "auto_approve": False,
        "force_subs": [],
        "shortener_api": None, "shortener_url": None, "is_shortener_enabled": False,
        "log_channel": None
    }
    save_db(BOTS_DB, bots)
    if parent_bot_id:
        update_user_stats(owner_id, parent_bot_id, "bots_cloned")

def get_bot_info(bot_id):
    return load_db(BOTS_DB).get(str(bot_id))

def update_bot_info(bot_id, field, value) -> bool:
    bots = load_db(BOTS_DB)
    if str(bot_id) in bots:
        bots[str(bot_id)][field] = value
        save_db(BOTS_DB, bots)
        return True
    return False

def get_all_bots():
    return load_db(BOTS_DB)

def get_child_bots(parent_bot_id):
    return [b for b in load_db(BOTS_DB).values()
            if isinstance(b, dict) and b.get("parent_bot_id") == parent_bot_id]

def get_all_descendant_bots(parent_bot_id):
    result = []
    def recurse(bid):
        for child in get_child_bots(bid):
            result.append(child)
            recurse(child["bot_id"])
    recurse(parent_bot_id)
    return result

def cascade_force_subs(parent_bot_id, force_subs) -> int:
    bots = load_db(BOTS_DB)
    count = 0
    for bot in get_all_descendant_bots(parent_bot_id):
        k = str(bot["bot_id"])
        if k in bots:
            bots[k]["force_subs"] = force_subs
            count += 1
    if count:
        save_db(BOTS_DB, bots)
    return count

# ─── FILE CACHE ─────────────────────────────────────────────────

def add_to_cache(file_id, message_id, chat_id, bot_id, caption=None):
    cache = load_db(FILE_CACHE_DB)
    cache[file_id] = {
        "message_id": message_id, "chat_id": chat_id,
        "bot_id": bot_id, "caption": caption,
        "expires_at": (datetime.now() + timedelta(seconds=FILE_CACHE_DURATION)).isoformat()
    }
    save_db(FILE_CACHE_DB, cache)

def get_from_cache(file_id):
    cache = load_db(FILE_CACHE_DB)
    entry = cache.get(file_id)
    if not entry:
        return None
    try:
        if datetime.now() > datetime.fromisoformat(entry["expires_at"]):
            del cache[file_id]
            save_db(FILE_CACHE_DB, cache)
            return None
    except Exception:
        return None
    return entry

def clean_expired_cache() -> int:
    cache = load_db(FILE_CACHE_DB)
    expired = [k for k, v in cache.items()
               if datetime.now() > datetime.fromisoformat(v.get("expires_at", "2000-01-01"))]
    for k in expired:
        del cache[k]
    if expired:
        save_db(FILE_CACHE_DB, cache)
    return len(expired)

# ─── UTILITIES ──────────────────────────────────────────────────

def fmt_size(size) -> str:
    if not size:
        return "N/A"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

def unique_id() -> str:
    return hashlib.md5(str(time.time()).encode()).hexdigest()[:12]

def file_icon(name: str) -> str:
    if not name:
        return "📁"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return {
        "pdf": "📄", "doc": "📝", "docx": "📝", "txt": "📃",
        "xlsx": "📊", "pptx": "📑", "csv": "📊",
        "mp4": "🎬", "mkv": "🎬", "avi": "🎬", "mov": "🎬", "webm": "🎬",
        "mp3": "🎵", "flac": "🎵", "wav": "🎵", "aac": "🎵", "m4a": "🎵",
        "jpg": "🖼", "jpeg": "🖼", "png": "🖼", "gif": "🖼", "webp": "🖼",
        "zip": "🗜", "rar": "🗜", "7z": "🗜", "tar": "🗜", "gz": "🗜",
        "apk": "📱", "exe": "💻", "py": "🐍", "js": "🌐", "html": "🌐",
    }.get(ext, "📁")

async def get_short_link(bot_info, link: str) -> str:
    if not (bot_info and bot_info.get("is_shortener_enabled")
            and bot_info.get("shortener_api") and bot_info.get("shortener_url")):
        return link
    url = f"https://{bot_info['shortener_url']}/api?api={bot_info['shortener_api']}&url={link}"
    try:
        async with _HTTP.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
            data = await r.json()
            if data.get("status") == "success":
                return data.get("shortenedUrl", link)
    except Exception as e:
        logger.warning(f"Shortener: {e}")
    return link

def main_bot_username() -> str:
    for d in ACTIVE_CLIENTS.values():
        if d.get("is_main"):
            return d.get("username", "Admin")
    return "Admin"

async def backup_db():
    client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None)
    if not client:
        return
    try:
        for f in os.listdir(DB_FOLDER):
            if f.endswith(".json"):
                await client.send_document(
                    DB_CHANNEL,
                    document=f"{DB_FOLDER}/{f}",
                    caption=f"📂 **DB Backup** | `{f}` | {datetime.now():%Y-%m-%d %H:%M}"
                )
    except Exception as e:
        logger.error(f"Backup failed: {e}")

# ═══════════════════════════════════════════════════════════════
# 📤 DELIVER FILE — Centralized, all paths with thumbnail fix
# ═══════════════════════════════════════════════════════════════

async def deliver_file(client, chat_id: int, file_data: dict):
    """
    Priority:
     1. Custom thumbnail → download BytesIO → send_document/video/audio
     2. DB Channel copy_message (works even after local DB wipe)
     3. In-memory file cache copy
     4. send_cached_media (last resort)
    """
    caption    = file_data.get("caption") or None
    thumb_fid  = file_data.get("custom_thumbnail")
    media_type = file_data.get("media_type", "document")
    file_id    = file_data["file_id"]
    db_msg_id  = file_data.get("db_msg_id")

    # ── 1. Custom Thumbnail (BytesIO fix) ────────────────────────
    if thumb_fid and media_type in ("document", "video", "audio"):
        try:
            # Must download to BytesIO — passing file_id as thumb doesn't work
            thumb_io = await client.download_media(thumb_fid, in_memory=True)
            thumb_io.seek(0)
            if media_type == "document":
                return await client.send_document(
                    chat_id, document=file_id, thumb=thumb_io, caption=caption
                )
            elif media_type == "video":
                return await client.send_video(
                    chat_id, video=file_id, thumb=thumb_io, caption=caption
                )
            elif media_type == "audio":
                return await client.send_audio(
                    chat_id, audio=file_id, thumb=thumb_io, caption=caption
                )
        except Exception as e:
            logger.warning(f"Thumb delivery failed: {e} — falling back")

    # ── 2. DB Channel copy (survives local DB wipe) ──────────────
    if db_msg_id:
        try:
            return await client.copy_message(
                chat_id=chat_id,
                from_chat_id=DB_CHANNEL,
                message_id=db_msg_id,
                caption=caption
            )
        except Exception as e:
            logger.warning(f"DB copy failed: {e}")

    # ── 3. In-memory cache ───────────────────────────────────────
    cached = get_from_cache(file_id)
    if cached and cached["bot_id"] in ACTIVE_CLIENTS:
        try:
            cached_app = ACTIVE_CLIENTS[cached["bot_id"]]["app"]
            return await cached_app.copy_message(
                chat_id, cached["chat_id"], cached["message_id"], caption=caption
            )
        except Exception as e:
            logger.warning(f"Cache delivery failed: {e}")

    # ── 4. send_cached_media (last resort) ───────────────────────
    return await client.send_cached_media(
        chat_id=chat_id,
        file_id=file_id,
        caption=caption or f"📁 {file_data.get('file_name', 'File')}"
    )

# ═══════════════════════════════════════════════════════════════
# 💾 METADATA — Save to DB_CHANNEL for recovery
# ═══════════════════════════════════════════════════════════════

async def save_metadata_to_channel(client, meta: dict) -> bool:
    """
    Save file/batch metadata as a text message in DB_CHANNEL.
    Format: #FS_META\n{json}
    Used by /rebuild to reconstruct the database.
    """
    try:
        txt = f"{METADATA_TAG}\n{json.dumps(meta, ensure_ascii=False)}"
        await client.send_message(DB_CHANNEL, txt)
        return True
    except Exception as e:
        logger.error(f"Metadata save failed: {e}")
        return False

# ═══════════════════════════════════════════════════════════════
# 🔄 DB RECOVERY — Userbot scans channel history
# ═══════════════════════════════════════════════════════════════
#
# WHY USERBOT:
#   Telegram bots cannot call messages.GetHistory (get_chat_history).
#   This is a hard API restriction. Only user accounts can do it.
#   We use a session string (generated once) to create a user client
#   that is used ONLY for scanning DB_CHANNEL during /rebuild.
#
# HOW TO GET SESSION_STRING:
#   Run: python generate_session.py
#   Set SESSION_STRING as environment variable.
# ════════════════════════════════════════════════════════════════

async def rebuild_db_with_userbot(status_msg=None) -> dict:
    """
    Use userbot (session string) to scan DB_CHANNEL history.
    Finds all #FS_META messages and rebuilds files.json + batches.json.
    """
    stats   = {"files": 0, "batches": 0, "skipped": 0, "errors": 0}
    files   = {}
    batches = {}

    async def upd(text):
        if status_msg:
            try:
                await status_msg.edit(text)
            except Exception:
                pass

    if not SESSION_STRING:
        await upd(
            "❌ **SESSION_STRING not configured!**\n\n"
            "Bots cannot read channel history (Telegram restriction).\n"
            "You need a user session for `/rebuild`.\n\n"
            "**Steps:**\n"
            "1. Run `python generate_session.py` on your local machine\n"
            "2. Set `SESSION_STRING` as environment variable on Render\n"
            "3. Restart the bot and try `/rebuild` again"
        )
        raise ValueError("SESSION_STRING not set")

    await upd(
        "🔄 **Starting DB Rebuild...**\n\n"
        "Connecting userbot to scan DB Channel history..."
    )

    async with Client(
        "userbot_rebuild",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION_STRING,
        in_memory=True
    ) as userbot:

        await upd("✅ Userbot connected! Scanning messages...")

        msg_count = 0
        async for msg in userbot.get_chat_history(DB_CHANNEL):
            msg_count += 1

            # Progress update every 200 messages
            if msg_count % 200 == 0:
                await upd(
                    f"🔄 **Rebuilding DB...**\n\n"
                    f"📨 Scanned: `{msg_count}` messages\n"
                    f"📁 Files: `{stats['files']}`\n"
                    f"📦 Batches: `{stats['batches']}`\n"
                    f"❌ Errors: `{stats['errors']}`"
                )

            try:
                text = msg.text or msg.caption
                if not text or not str(text).startswith(METADATA_TAG):
                    continue

                raw  = str(text)[len(METADATA_TAG):].strip()
                meta = json.loads(raw)

                if "unique_id" not in meta:
                    stats["skipped"] += 1
                    continue

                if meta.get("type") == "batch":
                    batches[meta["unique_id"]] = {
                        "files":      meta.get("files", []),
                        "created_by": meta.get("created_by"),
                        "bot_id":     meta.get("bot_id"),
                        "date":       meta.get("date", str(datetime.now()))
                    }
                    stats["batches"] += 1
                else:
                    uid = meta["unique_id"]
                    # Always take the latest version (newer #FS_META overwrites older)
                    files[uid] = {
                        "file_id":          meta["file_id"],
                        "file_name":        meta.get("file_name", "Unknown"),
                        "file_size":        meta.get("file_size", 0),
                        "caption":          meta.get("caption"),
                        "user_id":          meta.get("user_id"),
                        "bot_id":           meta.get("bot_id"),
                        "upload_date":      meta.get("upload_date", str(datetime.now())),
                        "db_msg_id":        meta.get("db_msg_id"),
                        "access_count":     meta.get("access_count", 0),
                        "media_type":       meta.get("media_type", "document"),
                        "custom_thumbnail": meta.get("custom_thumbnail"),
                    }
                    stats["files"] += 1

            except json.JSONDecodeError:
                stats["errors"] += 1
            except Exception as e:
                stats["errors"] += 1
                logger.debug(f"Rebuild parse error: {e}")

    # Write rebuilt databases
    save_db(FILES_DB, files)
    save_db(BATCH_DB, batches)
    invalidate_cache(FILES_DB)
    invalidate_cache(BATCH_DB)

    return stats

# ═══════════════════════════════════════════════════════════════
# 📢 BROADCAST — Pre-store in DB_CHANNEL, copy per-bot
# ═══════════════════════════════════════════════════════════════

async def _store_broadcast(client, original_msg) -> int | None:
    """Forward the broadcast message to DB_CHANNEL. Returns message_id."""
    try:
        stored = await original_msg.forward(DB_CHANNEL)
        return stored.id
    except Exception as e:
        logger.error(f"Broadcast store failed: {e}")
        return None

async def do_broadcast(bot_ids: list, bc_msg_id: int, status_msg=None) -> tuple:
    """
    Copy broadcast from DB_CHANNEL to all users of all bots.
    Each bot copies independently from the same stored message.
    """
    total_ok = total_fail = 0
    t0 = datetime.now()

    for b_idx, bot_id in enumerate(bot_ids, 1):
        if bot_id not in ACTIVE_CLIENTS:
            continue
        app   = ACTIVE_CLIENTS[bot_id]["app"]
        uname = ACTIVE_CLIENTS[bot_id]["username"]
        users = get_all_users(bot_id)

        for u_idx, user in enumerate(users, 1):
            uid = user["user_id"]
            try:
                await app.copy_message(
                    chat_id=uid,
                    from_chat_id=DB_CHANNEL,
                    message_id=bc_msg_id
                )
                total_ok += 1
            except FloodWait as e:
                await asyncio.sleep(e.value + 2)
                try:
                    await app.copy_message(uid, DB_CHANNEL, bc_msg_id)
                    total_ok += 1
                except Exception:
                    total_fail += 1
            except Exception:
                total_fail += 1

            done = total_ok + total_fail
            if status_msg and done % 30 == 0:
                try:
                    elapsed  = (datetime.now() - t0).seconds
                    all_cnt  = sum(len(get_all_users(bid)) for bid in bot_ids)
                    pct      = int((done / max(all_cnt, 1)) * 100)
                    bar      = "█" * (pct // 10) + "░" * (10 - pct // 10)
                    await status_msg.edit(
                        f"📢 **Broadcast**\n\n"
                        f"`[{bar}]` {pct}%\n"
                        f"🤖 Bot {b_idx}/{len(bot_ids)}: @{uname}\n"
                        f"✅ `{total_ok}` | ❌ `{total_fail}` | ⏱ `{elapsed}s`"
                    )
                except Exception:
                    pass
            await asyncio.sleep(MAX_BROADCAST_RATE)

    return total_ok, total_fail

# ═══════════════════════════════════════════════════════════════
# 🌐 RENDER HEALTH-CHECK SERVER
# ═══════════════════════════════════════════════════════════════

async def health_handler(request):
    uptime = str(datetime.now() - START_TIME).split(".")[0]
    return web.json_response({
        "status":      "ok",
        "uptime":      uptime,
        "bots_online": len(ACTIVE_CLIENTS),
        "ts":          datetime.now().isoformat()
    })

async def start_web_server():
    webapp = web.Application()
    webapp.router.add_get("/",       health_handler)
    webapp.router.add_get("/health", health_handler)
    webapp.router.add_get("/ping",   health_handler)
    runner = web.AppRunner(webapp)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f"🌐 Health-check server on port {PORT}")

# ═══════════════════════════════════════════════════════════════
# 🤖 BOT MANAGEMENT
# ═══════════════════════════════════════════════════════════════

START_TIME    = datetime.now()
ACTIVE_CLIENTS: dict = {}
TEMP_BATCH:    dict  = {}
TEMP_BROADCAST:dict  = {}
TEMP_EDIT:     dict  = {}
TEMP_WELCOME:  dict  = {}
USER_FLOOD:    dict  = {}
_HTTP: aiohttp.ClientSession = None

async def get_http() -> aiohttp.ClientSession:
    global _HTTP
    if _HTTP is None or _HTTP.closed:
        _HTTP = aiohttp.ClientSession()
    return _HTTP

async def setup_commands(app):
    try:
        await app.set_bot_commands(BOT_COMMANDS)
    except Exception as e:
        logger.warning(f"Commands setup: {e}")

async def check_force_sub(client, user_id: int):
    bi = get_bot_info(client.me.id)
    if not bi:
        return True, []
    force_subs = bi.get("force_subs", [])
    if not force_subs:
        return True, []

    must_join = []
    for fs in force_subs:
        ch_id = fs["channel_id"] if isinstance(fs, dict) else fs
        try:
            m = await client.get_chat_member(ch_id, user_id)
            if m.status in (ChatMemberStatus.BANNED, ChatMemberStatus.LEFT):
                must_join.append(fs)
        except UserNotParticipant:
            if has_pending_request(ch_id, user_id):
                continue
            must_join.append(fs)
        except Exception:
            continue

    if not must_join:
        return True, []

    links = []
    for fs in must_join:
        ch_id = fs["channel_id"] if isinstance(fs, dict) else fs
        inv   = fs.get("invite_link") if isinstance(fs, dict) else None
        try:
            chat = await client.get_chat(ch_id)
            if not inv:
                inv = chat.invite_link or (f"https://t.me/{chat.username}" if chat.username else None)
            if inv:
                links.append({"title": chat.title, "link": inv})
        except Exception:
            continue
    return False, links

async def start_bot(token: str, parent_bot_id=None):
    try:
        app = Client(
            f"bot_{token.split(':')[0]}",
            api_id=API_ID, api_hash=API_HASH,
            bot_token=token, in_memory=True
        )
        await app.start()
        me = await app.get_me()
        await setup_commands(app)
        is_main = (token == MAIN_BOT_TOKEN)
        ACTIVE_CLIENTS[me.id] = {
            "app": app, "username": me.username,
            "is_main": is_main, "token": token,
            "parent_bot_id": parent_bot_id,
            "started_at": datetime.now()
        }
        register_handlers(app)
        logger.info(f"✅ {'[MAIN]' if is_main else '[CLONE]'} @{me.username}")
        return app
    except Exception as e:
        logger.error(f"Bot start failed [{token[:12]}...]: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# 🎨 KEYBOARDS
# ═══════════════════════════════════════════════════════════════

def kb_start(bot_id, user_id):
    bi       = get_bot_info(bot_id)
    is_owner = bi and bi.get("owner_id") == user_id
    rows     = []
    if user_id == MAIN_ADMIN:
        rows.append([InlineKeyboardButton("👑 SUPREME PANEL", callback_data="supreme_panel")])
    if is_admin(user_id) or is_owner:
        rows.append([InlineKeyboardButton("⚡ ADMIN PANEL", callback_data="admin_panel")])
    rows += [
        [InlineKeyboardButton("📦 BATCH",      callback_data="start_batch"),
         InlineKeyboardButton("🤖 CLONE",      callback_data="clone_menu")],
        [InlineKeyboardButton("📊 DASHBOARD",  callback_data="user_dashboard"),
         InlineKeyboardButton("🎁 REFERRAL",   callback_data="referral_menu")],
        [InlineKeyboardButton("🎯 MY BOTS",    callback_data="my_bots_menu"),
         InlineKeyboardButton("💎 PREMIUM",    callback_data="premium_menu")],
        [InlineKeyboardButton("🔍 SEARCH",     callback_data="cb_search"),
         InlineKeyboardButton("ℹ️ HELP",        callback_data="help_menu")],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 BROADCAST",    callback_data="broadcast_menu"),
         InlineKeyboardButton("📊 STATS",         callback_data="admin_stats")],
        [InlineKeyboardButton("👥 USERS",          callback_data="manage_users"),
         InlineKeyboardButton("🤖 CLONES",         callback_data="my_bots_admin")],
        [InlineKeyboardButton("⚙️ SETTINGS",       callback_data="bot_settings_admin"),
         InlineKeyboardButton("🔒 FORCE SUB",      callback_data="forcesub_admin")],
        [InlineKeyboardButton("🔗 SHORTENER",      callback_data="shortener_admin"),
         InlineKeyboardButton("⏱ TIMER",           callback_data="edit_timer")],
        [InlineKeyboardButton("👋 WELCOME MSG",    callback_data="edit_welcome_msg"),
         InlineKeyboardButton("✅ AUTO APPROVE",   callback_data="toggle_auto_approve")],
        [InlineKeyboardButton("🔙 HOME",            callback_data="back_to_start")],
    ])

def kb_supreme():
    maint = get_global_config().get("maintenance", False)
    sess  = "✅" if SESSION_STRING else "❌ Not Set"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 GLOBAL BC",      callback_data="global_broadcast"),
         InlineKeyboardButton("🖥 SYS STATS",      callback_data="system_stats")],
        [InlineKeyboardButton("🤖 ALL BOTS",        callback_data="all_bots_list"),
         InlineKeyboardButton("👑 ADMINS",           callback_data="manage_admins")],
        [InlineKeyboardButton(
            f"🛠 MAINTENANCE: {'ON ⚠️' if maint else 'OFF ✅'}",
            callback_data="toggle_maintenance"),
         InlineKeyboardButton("📢 GLOBAL MSG",      callback_data="global_msg_set")],
        [InlineKeyboardButton("💾 BACKUP DB",        callback_data="manual_backup"),
         InlineKeyboardButton("🧹 CLEAN CACHE",     callback_data="manual_clean_cache")],
        [InlineKeyboardButton(
            f"🔄 REBUILD DB (Session: {sess})",
            callback_data="confirm_rebuild")],
        [InlineKeyboardButton("♻️ RESTART",          callback_data="restart_all_bots"),
         InlineKeyboardButton("🔙 HOME",             callback_data="back_to_start")],
    ])

def kb_file_edit(uid: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Caption",    callback_data=f"edit_caption_{uid}"),
         InlineKeyboardButton("🖼 Thumbnail",  callback_data=f"edit_thumb_{uid}")],
        [InlineKeyboardButton("🗑 Delete",      callback_data=f"del_file_{uid}"),
         InlineKeyboardButton("📤 Get File",   callback_data=f"get_file_{uid}")],
        [InlineKeyboardButton("🔙 Back",        callback_data="my_files_back")],
    ])

# ═══════════════════════════════════════════════════════════════
# 📝 HANDLERS
# ═══════════════════════════════════════════════════════════════

def register_handlers(app: Client):

    # ── FLOOD CONTROL (group 0) ──────────────────────────────────
    @app.on_message(filters.private, group=0)
    async def flood_ctrl(client, message):
        uid = message.from_user.id
        now = time.time()
        USER_FLOOD[uid] = [t for t in USER_FLOOD.get(uid, []) if now - t < 5]
        USER_FLOOD[uid].append(now)
        if len(USER_FLOOD[uid]) > 5:
            await message.reply("⚠️ **Anti-Flood!** Please slow down.")
            message.stop_propagation()

    # ── JOIN REQUEST ─────────────────────────────────────────────
    @app.on_chat_join_request()
    async def on_join_request(client, req):
        bi  = get_bot_info(client.me.id)
        uid = req.from_user.id
        ch  = req.chat.id
        if bi and bi.get("auto_approve"):
            try:
                await client.approve_chat_join_request(ch, uid)
                clear_join_request(ch, uid)
            except Exception as e:
                logger.warning(f"Auto-approve: {e}")
        else:
            mark_join_request(ch, uid)

    # ── /ping ─────────────────────────────────────────────────────
    @app.on_message(filters.command("ping") & filters.private, group=1)
    async def ping_cmd(client, message):
        t0   = time.time()
        sent = await message.reply("🏓 Pong...")
        ms   = round((time.time() - t0) * 1000, 2)
        sess = "✅ Set" if SESSION_STRING else "❌ Not Set"
        await sent.edit(
            f"🏓 **Pong!**\n\n"
            f"⚡ `{ms}ms`\n"
            f"⏳ Uptime: `{str(datetime.now() - START_TIME).split('.')[0]}`\n"
            f"🤖 Bots: `{len(ACTIVE_CLIENTS)}`\n"
            f"🔑 Session: {sess}"
        )

    # ── /restart ─────────────────────────────────────────────────
    @app.on_message(filters.command("restart") & filters.private, group=1)
    async def restart_cmd(client, message):
        if message.from_user.id != MAIN_ADMIN:
            return
        await message.reply("♻️ Restarting...")
        os.execl(sys.executable, sys.executable, *sys.argv)

    # ── /rebuild ─────────────────────────────────────────────────
    @app.on_message(filters.command("rebuild") & filters.private, group=1)
    async def rebuild_cmd(client, message):
        uid = message.from_user.id
        if not is_admin(uid):
            return await message.reply("❌ Admin only!")

        if not SESSION_STRING:
            return await message.reply(
                "❌ **SESSION_STRING not configured!**\n\n"
                "Bots cannot access channel history (Telegram API restriction).\n"
                "A user account session is required.\n\n"
                "**Setup Steps:**\n"
                "1️⃣ Run `python generate_session.py` on your local machine\n"
                "2️⃣ Set `SESSION_STRING` as environment variable\n"
                "3️⃣ Restart bot → `/rebuild` will work\n\n"
                "**Alternative:** If DB Channel still exists, files are\n"
                "delivered via `db_msg_id` even without local JSON."
            )

        sm = await message.reply(
            "🔄 **Starting DB Rebuild...**\n\n"
            "Connecting userbot to scan DB Channel...\n"
            "This may take a few minutes."
        )
        try:
            stats = await rebuild_db_with_userbot(status_msg=sm)
            await sm.edit(
                f"✅ **DB Rebuild Complete!**\n\n"
                f"📁 Files Restored: `{stats['files']}`\n"
                f"📦 Batches Restored: `{stats['batches']}`\n"
                f"⏭ Skipped: `{stats['skipped']}`\n"
                f"❌ Parse Errors: `{stats['errors']}`\n\n"
                f"Database is now synced with DB Channel! ✨"
            )
        except ValueError:
            pass  # Already edited with instructions
        except Exception as e:
            await sm.edit(f"❌ Rebuild failed!\n\n`{e}`")

    # ── /start ────────────────────────────────────────────────────
    @app.on_message(filters.command("start") & filters.private, group=1)
    async def start_handler(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        cfg    = get_global_config()

        if cfg.get("maintenance") and uid != MAIN_ADMIN:
            return await message.reply("🚧 **Maintenance Mode** — Bot is temporarily down.")

        if is_user_banned(uid, bot_id):
            return await message.reply("🚫 You are banned from this bot!")

        deep   = message.command[1] if len(message.command) > 1 else ""
        ref_by = None
        if deep.startswith("ref_"):
            try:
                r = int(deep[4:])
                if r != uid:
                    ref_by = r
            except ValueError:
                pass

        user_data, is_new = add_user(uid, bot_id, message.from_user.username,
                                      message.from_user.first_name, ref_by)

        is_ok, links = await check_force_sub(client, uid)
        if not is_ok:
            btns = [[InlineKeyboardButton(f"📢 Join {i['title']}", url=i["link"])] for i in links]
            btns.append([InlineKeyboardButton(
                "🔄 I Joined / Sent Request — Try Again",
                url=f"https://t.me/{client.me.username}?start={deep}"
            )])
            return await message.reply(
                "⚠️ **Membership Required!**\n\n"
                "Join the channels below to use this bot.\n"
                "_Already sent a join request? Press Try Again._",
                reply_markup=InlineKeyboardMarkup(btns)
            )

        bi         = get_bot_info(bot_id)
        auto_del   = bi.get("auto_delete_time", 600) if bi else 600
        is_premium = user_data.get("is_premium", False)

        # ── Deep link: single file ────────────────────────────────
        if deep.startswith("f_"):
            fuid  = deep[2:]
            files = load_db(FILES_DB)
            fdata = files.get(fuid)

            if not fdata:
                btns = None
                if is_admin(uid):
                    btns = InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Rebuild DB", callback_data="confirm_rebuild")
                    ]])
                return await message.reply(
                    "❌ **File Not Found in Database!**\n\n"
                    "The file data is missing locally.\n\n"
                    "_If the DB Channel still has this file's message,\n"
                    "use `/rebuild` to restore all files from the channel._",
                    reply_markup=btns
                )

            files[fuid]["access_count"] = files[fuid].get("access_count", 0) + 1
            save_db(FILES_DB, files)

            try:
                sent = await deliver_file(client, message.chat.id, fdata)
            except Exception as e:
                return await message.reply(
                    f"❌ **File unavailable!**\n\n"
                    f"The file may have been deleted from the DB Channel.\n`{e}`"
                )

            if sent and not is_premium:
                asyncio.create_task(_auto_delete(sent, auto_del))
                await message.reply(
                    f"⏳ **Auto-Delete:** File deletes in `{auto_del // 60}` min(s). Save it! 💾"
                )
            elif sent and is_premium:
                await message.reply("🌟 **Premium:** No auto-delete for you!")
            return

        # ── Deep link: batch ──────────────────────────────────────
        elif deep.startswith("b_"):
            bid_key  = deep[2:]
            batches  = load_db(BATCH_DB)
            bdata    = batches.get(bid_key)
            if not bdata:
                return await message.reply("❌ Batch not found or expired.")
            files  = load_db(FILES_DB)
            total  = len(bdata["files"])
            sm     = await message.reply(f"📦 Sending batch ({total} files)...")
            sent_c = 0
            for fuid in bdata["files"]:
                fd = files.get(fuid)
                if not fd:
                    continue
                try:
                    await deliver_file(client, message.chat.id, fd)
                    sent_c += 1
                except Exception:
                    pass
                await asyncio.sleep(0.5)
            await sm.delete()
            await message.reply(f"✅ Delivered **{sent_c}/{total}** files!")
            return

        # ── Standard welcome ──────────────────────────────────────
        global_msg   = cfg.get("global_msg", "")
        welcome_text = bi.get("custom_welcome") if bi else None
        welcome_img  = bi.get("welcome_image")  if bi else None

        if global_msg:
            await message.reply(f"📢 **System Notice**\n\n{global_msg}")

        if not welcome_text:
            welcome_text = (
                f"✨ **{'Welcome' if is_new else 'Welcome Back'}, {message.from_user.first_name}!**\n\n"
                f"🛠 **Advanced FileStore Bot v4.1**\n\n"
                f" ├ 📂 Unlimited Cloud Storage\n"
                f" ├ 📦 Batch Mode (many files → 1 link)\n"
                f" ├ ✏️ Caption & Thumbnail Editor\n"
                f" ├ 🤖 Bot Cloning System\n"
                f" ├ 🔐 Auto-Destruct Files\n"
                f" └ ⚡ Instant Fast Delivery"
            )

        kbd = kb_start(bot_id, uid)
        if welcome_img:
            try:
                await message.reply_photo(welcome_img, caption=welcome_text, reply_markup=kbd)
                return
            except Exception:
                pass
        await message.reply(welcome_text, reply_markup=kbd)

    # ── /admin ───────────────────────────────────────────────────
    @app.on_message(filters.command("admin") & filters.private, group=1)
    async def admin_cmd(client, message):
        uid = message.from_user.id
        bi  = get_bot_info(client.me.id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
            return
        await message.reply("⚡ **Admin Panel**", reply_markup=kb_admin())

    # ── /supreme ──────────────────────────────────────────────────
    @app.on_message(filters.command("supreme") & filters.private, group=1)
    async def supreme_cmd(client, message):
        if message.from_user.id != MAIN_ADMIN:
            return
        sess = "✅ Configured" if SESSION_STRING else "❌ Not Set (Rebuild won't work)"
        await message.reply(
            f"👑 **Supreme Panel**\n\n"
            f"🤖 Bots: `{len(ACTIVE_CLIENTS)}` | 👥 Users: `{len(load_db(USERS_DB))}`\n"
            f"📁 Files: `{len(load_db(FILES_DB))}` | 🔑 Session: {sess}",
            reply_markup=kb_supreme()
        )

    # ── /stats ────────────────────────────────────────────────────
    @app.on_message(filters.command("stats") & filters.private, group=1)
    async def stats_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        if uid == MAIN_ADMIN:
            await message.reply(
                "🌐 **Global Analytics**\n━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bots: `{len(get_all_bots())}` | 🟢 Online: `{len(ACTIVE_CLIENTS)}`\n"
                f"👥 Users: `{len(load_db(USERS_DB))}`\n"
                f"📁 Files: `{len(load_db(FILES_DB))}`\n"
                f"⏳ Uptime: `{str(datetime.now() - START_TIME).split('.')[0]}`"
            )
        else:
            ud   = get_user(uid, bot_id)
            ubts = [b for b in get_all_bots().values() if isinstance(b, dict) and b.get("owner_id") == uid]
            await message.reply(
                "📊 **Your Dashboard**\n━━━━━━━━━━━━━━━━━━━━\n"
                f"📤 Uploaded: `{ud.get('files_uploaded',0) if ud else 0}`\n"
                f"📦 Batches: `{ud.get('batches_created',0) if ud else 0}`\n"
                f"🤖 Bots: `{len(ubts)}` | 💰 Points: `{ud.get('points',0) if ud else 0}`\n"
                f"💎 Premium: `{'Yes ✅' if ud and ud.get('is_premium') else 'No'}`"
            )

    # ── /setwelcome — Interactive Welcome Editor ──────────────────
    @app.on_message(filters.command("setwelcome") & filters.private, group=1)
    async def setwelcome_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        if not bi or (bi.get("owner_id") != uid and uid != MAIN_ADMIN):
            return await message.reply("❌ Only bot owner!")
        TEMP_WELCOME[uid] = {"bot_id": bot_id, "step": "text"}
        curr_t = bi.get("custom_welcome") or "_(default)_"
        curr_i = "✅ Set" if bi.get("welcome_image") else "❌ None"
        await message.reply(
            f"👋 **Welcome Message Editor**\n\n"
            f"Current text: {curr_t[:80]}\n"
            f"Current image: {curr_i}\n\n"
            f"**Step 1/2:** Send the **new welcome text**\n"
            f"`-skip` = keep current | `-clear` = use default\n"
            f"/cancel to abort.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_welcome")]
            ])
        )

    # ── /broadcast ────────────────────────────────────────────────
    @app.on_message(filters.command("broadcast") & filters.private, group=1)
    async def broadcast_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)

        can_bc = target_bots = None
        if uid == MAIN_ADMIN:
            can_bc, target_bots = True, list(ACTIVE_CLIENTS.keys())
        elif bi and bi.get("owner_id") == uid:
            can_bc = True
            target_bots = [bot_id] + [
                d["bot_id"] for d in get_all_descendant_bots(bot_id)
                if d["bot_id"] in ACTIVE_CLIENTS
            ]
        if not can_bc:
            return await message.reply("❌ No permission!")

        if not message.reply_to_message:
            total = sum(len(get_all_users(bid)) for bid in target_bots)
            return await message.reply(
                f"📢 **Broadcast**\n\n"
                f"🤖 Bots: `{len(target_bots)}` | 👥 Users: `{total}`\n\n"
                f"**Reply to any message** with `/broadcast` to send it."
            )

        sm = await message.reply("⏳ Storing broadcast message in DB Channel...")
        bc_msg_id = await _store_broadcast(client, message.reply_to_message)

        if not bc_msg_id:
            return await sm.edit(
                "❌ Failed to store in DB Channel!\n"
                "Make sure I am **admin** in the DB Channel."
            )

        TEMP_BROADCAST[uid] = {"bc_msg_id": bc_msg_id, "bot_ids": target_bots}
        total = sum(len(get_all_users(bid)) for bid in target_bots)
        await sm.edit(
            f"⚠️ **Confirm Broadcast?**\n\n"
            f"🤖 Bots: `{len(target_bots)}`\n"
            f"👥 Users: `{total}`\n\n"
            f"This will send to **ALL** users.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Send!", callback_data="confirm_broadcast"),
                 InlineKeyboardButton("❌ Cancel",     callback_data="cancel_broadcast")]
            ])
        )

    # ── /batch /done /cancel ──────────────────────────────────────
    @app.on_message(filters.command("batch") & filters.private, group=1)
    async def batch_start(client, message):
        uid = message.from_user.id
        if is_user_banned(uid, client.me.id):
            return await message.reply("🚫 Banned!")
        TEMP_BATCH[uid] = []
        await message.reply("📦 **Batch Mode ON!**\n\nSend files now.\n`/done` to finish | `/cancel` to abort.")

    @app.on_message(filters.command("done") & filters.private, group=1)
    async def batch_done(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        if uid not in TEMP_BATCH or not TEMP_BATCH[uid]:
            return await message.reply("❌ No files in batch! Use `/batch` first.")
        fids    = TEMP_BATCH.pop(uid)
        bid     = unique_id()
        batches = load_db(BATCH_DB)
        batches[bid] = {"files": fids, "created_by": uid, "bot_id": bot_id, "date": str(datetime.now())}
        save_db(BATCH_DB, batches)
        update_user_stats(uid, bot_id, "batches_created")
        # Save batch metadata to channel for recovery
        main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
        asyncio.create_task(save_metadata_to_channel(main_client, {
            "type": "batch", "unique_id": bid, "files": fids,
            "created_by": uid, "bot_id": bot_id, "date": str(datetime.now())
        }))
        link  = f"https://t.me/{client.me.username}?start=b_{bid}"
        short = await get_short_link(bi, link)
        await message.reply(
            f"✅ **Batch Created!**\n\n📦 `{len(fids)}` files\n\n🔗 `{short}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Share Batch", url=f"https://t.me/share/url?url={short}")]
            ])
        )

    @app.on_message(filters.command("cancel") & filters.private, group=1)
    async def cancel_cmd(client, message):
        uid = message.from_user.id
        b = TEMP_BATCH.pop(uid, None)
        e = TEMP_EDIT.pop(uid, None)
        w = TEMP_WELCOME.pop(uid, None)
        if any(x is not None for x in [b, e, w]):
            await message.reply("❌ Cancelled!")
        else:
            await message.reply("Nothing to cancel.")

    # ── /editfile ─────────────────────────────────────────────────
    @app.on_message(filters.command("editfile") & filters.private, group=1)
    async def editfile_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        if len(message.command) < 2:
            return await message.reply("Usage: `/editfile FILE_ID`\nFind IDs in `/listfiles`")
        fuid  = message.command[1]
        files = load_db(FILES_DB)
        fd    = files.get(fuid)
        if not fd:
            return await message.reply("❌ File not found!")
        bi  = get_bot_info(bot_id)
        can = uid == MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id") == uid) or fd.get("user_id") == uid
        if not can:
            return await message.reply("❌ Not your file!")
        icon  = file_icon(fd.get("file_name",""))
        cap   = fd.get("caption") or "_(none)_"
        thumb = "✅ Set" if fd.get("custom_thumbnail") else "❌ None"
        await message.reply(
            f"✏️ **File Editor**\n\n"
            f"{icon} **{fd.get('file_name','?')}**\n"
            f"🆔 `{fuid}` | 📊 {fmt_size(fd.get('file_size',0))}\n"
            f"🎭 Type: `{fd.get('media_type','document')}`\n"
            f"💬 Caption: {cap}\n🖼 Thumbnail: {thumb}\n"
            f"👁 Views: `{fd.get('access_count',0)}`",
            reply_markup=kb_file_edit(fuid)
        )

    # ── /delfile ──────────────────────────────────────────────────
    @app.on_message(filters.command("delfile") & filters.private, group=1)
    async def delfile_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        if len(message.command) < 2:
            return await message.reply("Usage: `/delfile FILE_ID`")
        fuid  = message.command[1]
        files = load_db(FILES_DB)
        fd    = files.get(fuid)
        if not fd:
            return await message.reply("❌ File not found!")
        bi  = get_bot_info(bot_id)
        can = uid == MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id") == uid) or fd.get("user_id") == uid
        if not can:
            return await message.reply("❌ Not your file!")
        del files[fuid]
        save_db(FILES_DB, files)
        await message.reply(f"🗑 **Deleted:** `{fd.get('file_name','?')}`")

    # ── /listfiles ────────────────────────────────────────────────
    @app.on_message(filters.command("listfiles") & filters.private, group=1)
    async def listfiles_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        files  = load_db(FILES_DB)
        bi     = get_bot_info(bot_id)
        is_sup = uid == MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id") == uid)
        all_f  = [(k, f) for k, f in files.items()
                  if f.get("bot_id") == bot_id and (is_sup or f.get("user_id") == uid)]
        if not all_f:
            return await message.reply("📭 No files found!")
        recent = sorted(all_f, key=lambda x: x[1].get("upload_date",""), reverse=True)[:10]
        lbl    = "All Files" if is_sup else "Your Files"
        text   = f"📋 **{lbl}** ({len(all_f)} total)\n\n"
        btns   = []
        for k, f in recent:
            icon  = file_icon(f.get("file_name",""))
            name  = (f.get("file_name") or "?")[:35]
            thumb = "🖼" if f.get("custom_thumbnail") else ""
            cap   = "💬" if f.get("caption") else ""
            text += f"{icon} **{name}** {thumb}{cap}\n   📊 {fmt_size(f.get('file_size',0))} | 👁 {f.get('access_count',0)} | `{k}`\n\n"
            btns.append([
                InlineKeyboardButton(f"{icon} {name[:20]}", url=f"https://t.me/{client.me.username}?start=f_{k}"),
                InlineKeyboardButton("✏️", callback_data=f"edit_file_{k}")
            ])
        await message.reply(text, reply_markup=InlineKeyboardMarkup(btns) if btns else None)

    # ── Misc admin commands ───────────────────────────────────────
    @app.on_message(filters.command("addpoints") & filters.private, group=1)
    async def addpoints_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        if not (uid == MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id") == uid)):
            return
        if len(message.command) < 3:
            return await message.reply("Usage: `/addpoints USER_ID AMOUNT`")
        try:
            target = int(message.command[1])
            amount = int(message.command[2])
        except ValueError:
            return await message.reply("❌ Invalid values!")
        update_user_stats(target, bot_id, "points", amount)
        await message.reply(f"✅ Added `{amount}` points to `{target}`!")

    @app.on_message(filters.command("mybots") & filters.private, group=1)
    async def mybots_cmd(client, message):
        uid  = message.from_user.id
        ubts = [b for b in get_all_bots().values() if isinstance(b, dict) and b.get("owner_id") == uid]
        if not ubts:
            return await message.reply("🤖 No bots yet! `/clone TOKEN`")
        text = f"🤖 **Your Bots ({len(ubts)})**\n\n"
        for i, b in enumerate(ubts[:10], 1):
            st = "🟢" if b["bot_id"] in ACTIVE_CLIENTS else "🔴"
            text += f"{i}. {st} @{b['bot_username']}\n"
        await message.reply(text)

    @app.on_message(
        filters.command(["ban","unban","info","setpremium","gban","ungban"]) & filters.private,
        group=1
    )
    async def admin_utils(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        if not (uid == MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id") == uid)):
            return
        if len(message.command) < 2:
            return await message.reply(f"Usage: `/{message.command[0]} USER_ID`")
        try:
            target = int(message.command[1])
        except ValueError:
            return await message.reply("❌ Invalid User ID!")
        cmd = message.command[0]
        if cmd == "ban":
            await message.reply("🚫 Banned!" if ban_user(target, bot_id) else "❌ Not found.")
        elif cmd == "unban":
            await message.reply("✅ Unbanned!" if unban_user(target, bot_id) else "❌ Not found.")
        elif cmd == "setpremium":
            users = load_db(USERS_DB)
            k = f"{bot_id}_{target}"
            if k in users:
                users[k]["is_premium"] = True
                save_db(USERS_DB, users)
                await message.reply(f"💎 `{target}` is now Premium!")
            else:
                await message.reply("❌ Not found.")
        elif cmd == "gban":
            if uid != MAIN_ADMIN: return
            cfg = get_global_config(); gb = cfg.get("global_bans", [])
            if target not in gb:
                gb.append(target); update_global_config("global_bans", gb)
                await message.reply(f"🌍 Globally banned `{target}`!")
        elif cmd == "ungban":
            if uid != MAIN_ADMIN: return
            cfg = get_global_config(); gb = cfg.get("global_bans", [])
            if target in gb:
                gb.remove(target); update_global_config("global_bans", gb)
                await message.reply(f"✅ Globally unbanned `{target}`!")
        elif cmd == "info":
            u = get_user(target, bot_id)
            if not u:
                return await message.reply("❌ Not found.")
            await message.reply(
                f"👤 **User Info**\n🆔 `{u['user_id']}`\n"
                f"🏷 {u.get('name','?')} | @{u.get('username') or 'None'}\n"
                f"🚫 Banned: {u.get('is_banned',False)} | 💎 Premium: {u.get('is_premium',False)}\n"
                f"💰 Points: `{u.get('points',0)}`\n"
                f"📤 Uploaded: `{u.get('files_uploaded',0)}` | Referrals: `{u.get('referrals',0)}`"
            )

    @app.on_message(filters.command("settimer") & filters.private, group=1)
    async def settimer_cmd(client, message):
        uid    = message.from_user.id; bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        if not bi or (bi.get("owner_id") != uid and uid != MAIN_ADMIN):
            return await message.reply("❌ Access Denied!")
        if len(message.command) < 2:
            curr = bi.get("auto_delete_time", 600)
            return await message.reply(f"⏱ Current: `{curr}s` ({curr//60}min)\n`/settimer SECONDS`")
        try:
            secs = int(message.command[1])
            if secs < 60: return await message.reply("❌ Min 60s!")
            update_bot_info(bot_id, "auto_delete_time", secs)
            await message.reply(f"✅ Set to `{secs}s` ({secs//60}min).")
        except ValueError:
            await message.reply("❌ Invalid number!")

    @app.on_message(filters.command("setlog") & filters.private, group=1)
    async def setlog_cmd(client, message):
        uid    = message.from_user.id; bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        if not bi or (bi.get("owner_id") != uid and uid != MAIN_ADMIN):
            return await message.reply("❌ Access Denied!")
        if len(message.command) < 2:
            return await message.reply(f"📝 Log: `{bi.get('log_channel') or 'None'}`\n`/setlog CHANNEL_ID` or off")
        if message.command[1].lower() == "off":
            update_bot_info(bot_id, "log_channel", None)
            return await message.reply("✅ Log disabled!")
        try:
            update_bot_info(bot_id, "log_channel", int(message.command[1]))
            await message.reply(f"✅ Log channel set!")
        except ValueError:
            await message.reply("❌ Invalid ID!")

    @app.on_message(filters.command("shortener") & filters.private, group=1)
    async def shortener_cmd(client, message):
        uid    = message.from_user.id; bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        if not bi or (bi.get("owner_id") != uid and uid != MAIN_ADMIN):
            return await message.reply("❌ Access Denied!")
        if len(message.command) < 2:
            st = "✅ ON" if bi.get("is_shortener_enabled") else "❌ OFF"
            return await message.reply(f"🔗 Shortener {st}\nURL: `{bi.get('shortener_url') or 'Not set'}`\nCmds: `on`, `off`, `set URL APIKEY`")
        cmd = message.command[1].lower()
        if cmd == "on":
            if not bi.get("shortener_url"): return await message.reply("❌ Set URL first!")
            update_bot_info(bot_id, "is_shortener_enabled", True); await message.reply("✅ Enabled!")
        elif cmd == "off":
            update_bot_info(bot_id, "is_shortener_enabled", False); await message.reply("✅ Disabled!")
        elif cmd == "set":
            if len(message.command) < 4: return await message.reply("Usage: `/shortener set URL APIKEY`")
            update_bot_info(bot_id, "shortener_url", message.command[2])
            update_bot_info(bot_id, "shortener_api", message.command[3])
            await message.reply(f"✅ Configured: `{message.command[2]}`")

    @app.on_message(filters.command("clone") & filters.private, group=1)
    async def clone_cmd(client, message):
        uid    = message.from_user.id; bot_id = client.me.id
        if is_user_banned(uid, bot_id): return await message.reply("🚫 Banned!")
        if len(message.command) < 2:
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            return await message.reply(
                f"🤖 **Clone** — Your bots: `{len(ubts)}`\n\n1. @BotFather → /newbot\n2. `/clone TOKEN`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🤖 BotFather", url="https://t.me/BotFather")]])
            )
        token = message.command[1]
        for b in get_all_bots().values():
            if isinstance(b, dict) and b.get("token") == token:
                return await message.reply("❌ Token already registered!")
        sm = await message.reply("🔄 Cloning...")
        try:
            na = await start_bot(token, parent_bot_id=bot_id)
            if na:
                me = await na.get_me()
                save_bot_info(token, me.id, me.username, uid, message.from_user.first_name, bot_id)
                await sm.edit(f"✅ **Cloned!**\n🤖 @{me.username} | `{me.id}`",
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Open", url=f"https://t.me/{me.username}")]]))
            else:
                await sm.edit("❌ Failed! Invalid token?")
        except Exception as e:
            await sm.edit(f"❌ Error: `{e}`")

    @app.on_message(filters.command("setfs") & filters.private, group=1)
    async def setfs_cmd(client, message):
        uid    = message.from_user.id; bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        if not bi or (bi.get("owner_id") != uid and uid != MAIN_ADMIN):
            return await message.reply("❌ Only bot owner!")
        fs = bi.get("force_subs", [])
        if len(message.command) < 2:
            text = f"⚙️ **Force Subscribe** ({len(fs)}/{MAX_FORCE_SUB_CHANNELS})\n\n"
            for i, f in enumerate(fs,1):
                cid = f["channel_id"] if isinstance(f,dict) else f
                text += f"{i}. `{cid}`\n"
            if not fs: text += "None.\n"
            text += "\nCmds: `add -100xxx [link]`, `del -100xxx`, `clear`"
            return await message.reply(text)
        cmd = message.command[1].lower()
        if cmd in ("clear","off"):
            update_bot_info(bot_id,"force_subs",[]); n = cascade_force_subs(bot_id,[])
            return await message.reply(f"✅ Cleared! ({n} clones updated)")
        if cmd == "add":
            if len(fs) >= MAX_FORCE_SUB_CHANNELS: return await message.reply(f"❌ Max {MAX_FORCE_SUB_CHANNELS}!")
            if len(message.command) < 3: return await message.reply("Usage: `/setfs add -100xxx [link]`")
            try: cid = int(message.command[2])
            except ValueError: return await message.reply("❌ Invalid ID!")
            lnk = message.command[3] if len(message.command)>3 else None
            try: await client.get_chat_member(cid, client.me.id)
            except Exception: return await message.reply("❌ I'm not admin in that channel!")
            fs.append({"channel_id":cid,"invite_link":lnk})
            update_bot_info(bot_id,"force_subs",fs); n = cascade_force_subs(bot_id,fs)
            return await message.reply(f"✅ Added! ({n} clones updated)")
        if cmd == "del":
            if len(message.command)<3: return await message.reply("Usage: `/setfs del -100xxx`")
            try: cid = int(message.command[2])
            except ValueError: return await message.reply("❌ Invalid ID!")
            new_fs = [f for f in fs if (f["channel_id"] if isinstance(f,dict) else f) != cid]
            if len(new_fs)==len(fs): return await message.reply("❌ Not in list!")
            update_bot_info(bot_id,"force_subs",new_fs); n = cascade_force_subs(bot_id,new_fs)
            return await message.reply(f"✅ Removed! ({n} clones updated)")

    @app.on_message(filters.command(["refer","points","premium","buy_premium","botinfo","help","setglobal","addadmin","deladmin","search"]) & filters.private, group=1)
    async def misc_commands(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        cmd    = message.command[0]

        if cmd == "refer":
            ud   = get_user(uid, bot_id)
            link = f"https://t.me/{client.me.username}?start=ref_{uid}"
            await message.reply(
                f"🔗 **Referral**\n💰 Points: `{ud.get('points',0) if ud else 0}` | 👥 Referrals: `{ud.get('referrals',0) if ud else 0}`\n\n"
                f"Earn 10pts per referral! 500pts = Premium 🌟\n\n`{link}`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={link}")]]))

        elif cmd == "points":
            ud = get_user(uid, bot_id)
            await message.reply(f"💰 **Points: `{ud.get('points',0) if ud else 0}`**\n500pts = Premium. `/refer` to earn.")

        elif cmd == "premium":
            ud = get_user(uid, bot_id)
            is_p = ud.get("is_premium",False) if ud else False
            await message.reply(f"🌟 **Premium** — {'✅ Active' if is_p else '❌ Inactive'}\n\nBenefits: No auto-delete | Priority delivery | Unlimited batch\nCost: 500pts → `/buy_premium`")

        elif cmd == "buy_premium":
            ud = get_user(uid, bot_id)
            if not ud: return await message.reply("❌ Please /start first.")
            if ud.get("is_premium"): return await message.reply("✅ Already Premium!")
            if ud.get("points",0)<500: return await message.reply(f"❌ Need `{500-ud.get('points',0)}` more pts. `/refer` to earn!")
            users = load_db(USERS_DB); k = f"{bot_id}_{uid}"
            users[k]["points"] -= 500; users[k]["is_premium"] = True
            save_db(USERS_DB, users)
            await message.reply("🎉 **You are now Premium!** Auto-delete disabled. Enjoy!")

        elif cmd == "botinfo":
            bi = get_bot_info(bot_id)
            if not bi: return await message.reply("ℹ️ Not in DB.")
            await message.reply(f"ℹ️ @{client.me.username}\n👤 Owner: {bi.get('owner_name','?')}\n🌳 Clones: `{len(get_child_bots(bot_id))}`\n📢 Force Sub: `{len(bi.get('force_subs',[]))}` ch\n⏱ Timer: `{bi.get('auto_delete_time',600)}s`\n✅ Auto-Approve: `{'ON' if bi.get('auto_approve') else 'OFF'}`")

        elif cmd == "help":
            sess = "✅ Set" if SESSION_STRING else "❌ Not Set (needed for /rebuild)"
            await message.reply(
                "🚀 **FileStore v4.1 — Help**\n\n"
                "**Files:** Send file → link\n"
                "**Batch:** `/batch` → files → `/done`\n"
                "**Edit:** `/editfile ID` → caption + thumbnail\n"
                "**Welcome:** `/setwelcome` → interactive editor\n"
                "**Clone:** `/clone TOKEN`\n"
                "**Force Sub:** pending join request = access ✅\n"
                f"**Rebuild:** `/rebuild` (Session: {sess})\n"
                "**Stats:** `/stats` | **Files:** `/listfiles`"
            )

        elif cmd == "setglobal":
            if uid != MAIN_ADMIN: return
            if len(message.command) < 2: return await message.reply("Usage: `/setglobal MSG` or `/setglobal off`")
            txt = message.text.split(None,1)[1]
            update_global_config("global_msg", "" if txt.lower()=="off" else txt)
            await message.reply("✅ Updated!")

        elif cmd == "addadmin":
            if uid != MAIN_ADMIN: return
            if len(message.command) < 2: return await message.reply("Usage: `/addadmin ID`")
            admins = load_db(ADMINS_DB); admins[message.command[1]] = str(datetime.now())
            save_db(ADMINS_DB, admins); await message.reply(f"✅ `{message.command[1]}` is now Admin.")

        elif cmd == "deladmin":
            if uid != MAIN_ADMIN: return
            if len(message.command) < 2: return await message.reply("Usage: `/deladmin ID`")
            admins = load_db(ADMINS_DB)
            if message.command[1] in admins:
                del admins[message.command[1]]; save_db(ADMINS_DB, admins)
                await message.reply(f"✅ Removed admin `{message.command[1]}`.")
            else:
                await message.reply("❌ Not an admin!")

        elif cmd == "search":
            if is_user_banned(uid, bot_id): return await message.reply("🚫 Banned!")
            if len(message.command) < 2: return await message.reply("🔍 Usage: `/search FILENAME`")
            q = message.text.split(None,1)[1].lower()
            files = load_db(FILES_DB)
            results = [(k,f) for k,f in files.items() if f.get("bot_id")==bot_id and q in f.get("file_name","").lower()][:10]
            if not results: return await message.reply(f"❌ No files for `{q}`")
            text = f"🔍 **Results ({len(results)})**\n\n"
            btns = []
            for k, f in results:
                icon = file_icon(f.get("file_name",""))
                name = f.get("file_name","?")
                link = f"https://t.me/{client.me.username}?start=f_{k}"
                text += f"{icon} `{name[:40]}`  📊 {fmt_size(f.get('file_size',0))}\n"
                btns.append([InlineKeyboardButton(f"{icon} {name[:30]}", url=link)])
            await message.reply(text, reply_markup=InlineKeyboardMarkup(btns))

    # ── INLINE SEARCH ─────────────────────────────────────────────
    @app.on_inline_query()
    async def inline_search(client, query):
        q = query.query.strip().lower()
        if not q: return await query.answer([], cache_time=1)
        bot_id = client.me.id
        files  = load_db(FILES_DB)
        results = []
        for k, f in files.items():
            if f.get("bot_id") == bot_id and q in f.get("file_name","").lower():
                icon = file_icon(f.get("file_name",""))
                link = f"https://t.me/{client.me.username}?start=f_{k}"
                results.append(InlineQueryResultArticle(
                    title=f"{icon} {f.get('file_name','?')}",
                    description=f"📊 {fmt_size(f.get('file_size',0))} | 👁 {f.get('access_count',0)}",
                    input_message_content=InputTextMessageContent(
                        f"{icon} **{f.get('file_name')}**\n📊 `{fmt_size(f.get('file_size',0))}`\n🔗 {link}"
                    ),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Get File", url=link)]])
                ))
                if len(results) >= 20: break
        await query.answer(results, cache_time=1)

    # ── FILE HANDLER ─────────────────────────────────────────────
    @app.on_message(
        (filters.document | filters.video | filters.audio | filters.photo) & filters.private,
        group=1
    )
    async def file_handler(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        if is_user_banned(uid, bot_id): return await message.reply("🚫 Banned!")
        # Let FSM handlers take photo/document if in edit/welcome mode
        if uid in TEMP_EDIT and TEMP_EDIT[uid].get("mode")=="thumbnail" and message.photo:
            return
        if uid in TEMP_WELCOME and TEMP_WELCOME[uid].get("step")=="image" and message.photo:
            return

        try:
            db_msg = await message.forward(DB_CHANNEL)
        except Exception as e:
            return await message.reply(f"❌ DB Channel error!\n`{e}`\n\nMake sure I'm admin in DB Channel.")

        original_caption = message.caption

        if db_msg.photo:
            file_id = db_msg.photo.file_id; file_name = f"photo_{db_msg.photo.file_unique_id}.jpg"
            file_size = db_msg.photo.file_size or 0; media_type = "photo"
        elif db_msg.video:
            file_id = db_msg.video.file_id; file_name = db_msg.video.file_name or f"video_{db_msg.video.file_unique_id}.mp4"
            file_size = db_msg.video.file_size or 0; media_type = "video"
        elif db_msg.audio:
            file_id = db_msg.audio.file_id; file_name = db_msg.audio.file_name or f"audio_{db_msg.audio.file_unique_id}.mp3"
            file_size = db_msg.audio.file_size or 0; media_type = "audio"
        elif db_msg.document:
            file_id = db_msg.document.file_id; file_name = db_msg.document.file_name or f"file_{db_msg.document.file_unique_id}"
            file_size = db_msg.document.file_size or 0; media_type = "document"
        else:
            return

        fuid  = unique_id()
        files = load_db(FILES_DB)
        fdata = {
            "file_id": file_id, "file_name": file_name, "file_size": file_size,
            "caption": original_caption, "user_id": uid, "bot_id": bot_id,
            "upload_date": str(datetime.now()), "db_msg_id": db_msg.id,
            "access_count": 0, "media_type": media_type, "custom_thumbnail": None
        }
        files[fuid] = fdata
        save_db(FILES_DB, files)
        add_to_cache(file_id, db_msg.id, DB_CHANNEL, bot_id, original_caption)
        update_user_stats(uid, bot_id, "files_uploaded")

        # Save metadata to channel for future /rebuild
        main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
        asyncio.create_task(save_metadata_to_channel(main_client, {**fdata, "unique_id": fuid}))

        bi = get_bot_info(bot_id)
        if bi and bi.get("log_channel"):
            try:
                await client.copy_message(bi["log_channel"], message.chat.id, message.id,
                    caption=f"📤 **Upload**\n{file_icon(file_name)} `{file_name}`\n📊 {fmt_size(file_size)}\n👤 `{uid}`\n🆔 `{fuid}`")
            except Exception:
                pass

        if uid in TEMP_BATCH:
            TEMP_BATCH[uid].append(fuid)
            await message.reply(f"✅ **Added to Batch!**\n{file_icon(file_name)} `{file_name}`\n📦 Total: `{len(TEMP_BATCH[uid])}`", quote=True)
        else:
            link  = f"https://t.me/{client.me.username}?start=f_{fuid}"
            short = await get_short_link(bi, link)
            await message.reply(
                f"✅ **File Saved!**\n\n{file_icon(file_name)} `{file_name}`\n📊 {fmt_size(file_size)}\n🆔 `{fuid}`\n\n🔗 `{short}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={short}"),
                     InlineKeyboardButton("✏️ Edit", callback_data=f"edit_file_{fuid}")]
                ])
            )

    # ── FSM RESPONDER (group 2) ───────────────────────────────────
    _CMD_LIST = [
        "start","admin","supreme","clone","batch","done","cancel","setfs","mybots","stats",
        "help","broadcast","ban","unban","info","setpremium","gban","ungban","botinfo",
        "settimer","search","points","refer","premium","shortener","buy_premium","setlog",
        "rebuild","restart","ping","listfiles","editfile","delfile","addpoints","setwelcome",
        "setglobal","addadmin","deladmin",
    ]

    @app.on_message(filters.private & ~filters.command(_CMD_LIST), group=2)
    async def fsm_responder(client, message):
        uid = message.from_user.id

        # ── Welcome FSM ───────────────────────────────────────────
        if uid in TEMP_WELCOME:
            sess   = TEMP_WELCOME[uid]
            bot_id = sess["bot_id"]
            step   = sess.get("step")

            if step == "text":
                if not message.text:
                    return await message.reply("❌ Send text or `-skip`.")
                txt = message.text.strip()
                if txt == "-skip":
                    pass  # keep current
                elif txt == "-clear":
                    update_bot_info(bot_id, "custom_welcome", None)
                else:
                    update_bot_info(bot_id, "custom_welcome", txt)
                sess["step"] = "image"
                await message.reply(
                    f"✅ {'Text updated!' if txt not in ('-skip','-clear') else 'Text unchanged!' if txt=='-skip' else 'Text reset!'}\n\n"
                    f"🖼 **Step 2/2:** Send a **photo** for welcome image.\n"
                    f"`-skip` = keep current | `-clear` = remove image",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_welcome")]])
                )

            elif step == "image":
                if message.photo:
                    update_bot_info(bot_id, "welcome_image", message.photo.file_id)
                    del TEMP_WELCOME[uid]
                    bi = get_bot_info(bot_id)
                    await message.reply(
                        "✅ **Welcome fully updated!**\n\n"
                        f"Text: {'Custom ✅' if bi.get('custom_welcome') else 'Default'}\n"
                        f"Image: Set ✅",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("👀 Preview", callback_data="preview_welcome")],
                            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
                        ])
                    )
                elif message.text:
                    txt = message.text.strip()
                    if txt == "-skip":
                        del TEMP_WELCOME[uid]
                        await message.reply("✅ **Welcome updated!** Image unchanged.",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]))
                    elif txt == "-clear":
                        update_bot_info(bot_id, "welcome_image", None)
                        del TEMP_WELCOME[uid]
                        await message.reply("✅ **Welcome updated!** Image removed.",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]))
                    else:
                        await message.reply("❌ Send a **photo**, `-skip`, or `-clear`.")
                else:
                    await message.reply("❌ Send a **photo**, `-skip`, or `-clear`.")
            return

        # ── Caption/Thumbnail Edit FSM ────────────────────────────
        if uid in TEMP_EDIT:
            sess  = TEMP_EDIT[uid]
            mode  = sess["mode"]
            fuid  = sess["uid"]
            files = load_db(FILES_DB)
            if fuid not in files:
                del TEMP_EDIT[uid]
                return await message.reply("❌ File no longer exists.")

            if mode == "caption":
                if not message.text:
                    return await message.reply("❌ Send **text** for caption.")
                txt = message.text.strip()
                files[fuid]["caption"] = None if txt == "-clear" else txt
                save_db(FILES_DB, files)
                # Update metadata in channel
                main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
                asyncio.create_task(save_metadata_to_channel(main_client, {**files[fuid], "unique_id": fuid}))
                del TEMP_EDIT[uid]
                await message.reply(
                    f"✅ **Caption {'removed' if txt=='-clear' else 'updated'}!**\n\n"
                    f"New: `{txt if txt!='-clear' else '(none)'}`",
                    reply_markup=kb_file_edit(fuid)
                )

            elif mode == "thumbnail":
                if not message.photo:
                    return await message.reply("❌ Send a **photo** as thumbnail.")
                files[fuid]["custom_thumbnail"] = message.photo.file_id
                save_db(FILES_DB, files)
                main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
                asyncio.create_task(save_metadata_to_channel(main_client, {**files[fuid], "unique_id": fuid}))
                del TEMP_EDIT[uid]
                await message.reply("✅ **Thumbnail updated!**", reply_markup=kb_file_edit(fuid))

    # ── CALLBACK HANDLER ──────────────────────────────────────────
    @app.on_callback_query(group=1)
    async def cb_handler(client, cb):
        uid    = cb.from_user.id
        data   = cb.data
        bot_id = client.me.id
        if is_user_banned(uid, bot_id):
            return await cb.answer("🚫 Banned!", show_alert=True)

        # ─── File edit callbacks ─────────────────────────────────
        if data.startswith("edit_file_"):
            fuid = data[10:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("❌ Not found!", show_alert=True)
            bi  = get_bot_info(bot_id)
            can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or fd.get("user_id")==uid
            if not can: return await cb.answer("❌ Not your file!", show_alert=True)
            icon = file_icon(fd.get("file_name","")); cap = fd.get("caption") or "_(none)_"; thumb = "✅" if fd.get("custom_thumbnail") else "❌"
            await cb.message.edit(
                f"✏️ **File Editor**\n\n{icon} **{fd.get('file_name','?')}**\n🆔 `{fuid}` | 📊 {fmt_size(fd.get('file_size',0))}\n"
                f"🎭 `{fd.get('media_type','?')}` | 💬 {cap} | 🖼 {thumb}\n👁 `{fd.get('access_count',0)}`",
                reply_markup=kb_file_edit(fuid)
            )
            await cb.answer()

        elif data.startswith("edit_caption_"):
            fuid = data[13:]; files = load_db(FILES_DB)
            if fuid not in files: return await cb.answer("❌ Not found!", show_alert=True)
            TEMP_EDIT[uid] = {"mode":"caption","uid":fuid}
            await cb.message.edit(
                f"✏️ **Edit Caption**\n\nFile: `{files[fuid].get('file_name','?')}`\n\nSend new caption text.\n`-clear` to remove. /cancel to abort.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]])
            )
            await cb.answer("Send caption text")

        elif data.startswith("edit_thumb_"):
            fuid = data[11:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("❌ Not found!", show_alert=True)
            if fd.get("media_type") == "photo":
                return await cb.answer("❌ Photos can't have custom thumbnails!", show_alert=True)
            TEMP_EDIT[uid] = {"mode":"thumbnail","uid":fuid}
            await cb.message.edit(
                f"🖼 **Edit Thumbnail**\n\nFile: `{fd.get('file_name','?')}`\n\nSend a **photo** as thumbnail.\n/cancel to abort.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🗑 Remove Thumb", callback_data=f"remove_thumb_{fuid}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]
                ])
            )
            await cb.answer("Send a photo")

        elif data.startswith("remove_thumb_"):
            fuid = data[13:]; files = load_db(FILES_DB)
            if fuid in files:
                files[fuid]["custom_thumbnail"] = None; save_db(FILES_DB, files)
                TEMP_EDIT.pop(uid, None)
                # Update metadata
                main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
                asyncio.create_task(save_metadata_to_channel(main_client, {**files[fuid], "unique_id": fuid}))
                await cb.answer("✅ Thumbnail removed!", show_alert=True)
                await cb.message.edit("✅ Thumbnail removed!", reply_markup=kb_file_edit(fuid))

        elif data.startswith("del_file_"):
            fuid = data[9:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("Already deleted!", show_alert=True)
            bi = get_bot_info(bot_id)
            can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or fd.get("user_id")==uid
            if not can: return await cb.answer("❌ Not your file!", show_alert=True)
            del files[fuid]; save_db(FILES_DB, files)
            await cb.answer("🗑 Deleted!", show_alert=True)
            await cb.message.edit(f"🗑 **Deleted:** `{fd.get('file_name','?')}`")

        elif data.startswith("get_file_"):
            fuid = data[9:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("❌ Not found!", show_alert=True)
            await cb.answer("📤 Sending...")
            try:
                sent = await deliver_file(client, cb.message.chat.id, fd)
                bi = get_bot_info(bot_id); ud = get_user(uid, bot_id)
                if sent and not (ud and ud.get("is_premium")):
                    auto_del = bi.get("auto_delete_time",600) if bi else 600
                    asyncio.create_task(_auto_delete(sent, auto_del))
            except Exception as e:
                await cb.message.reply(f"❌ `{e}`")

        elif data == "cancel_edit":
            TEMP_EDIT.pop(uid, None)
            await cb.message.edit("❌ Edit cancelled.")
            await cb.answer()

        elif data == "cancel_welcome":
            TEMP_WELCOME.pop(uid, None)
            await cb.message.edit("❌ Welcome editor cancelled.")
            await cb.answer()

        elif data == "my_files_back":
            await cb.message.edit("📋 Use `/listfiles` to browse your files.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Home", callback_data="back_to_start")]]))
            await cb.answer()

        # ─── Welcome callbacks ───────────────────────────────────
        elif data == "edit_welcome_msg":
            bi = get_bot_info(bot_id)
            if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN):
                return await cb.answer("❌ Only owner!", show_alert=True)
            TEMP_WELCOME[uid] = {"bot_id":bot_id,"step":"text"}
            curr_t = bi.get("custom_welcome") or "_(default)_"
            curr_i = "✅ Set" if bi.get("welcome_image") else "❌ None"
            await cb.message.edit(
                f"👋 **Welcome Editor**\n\nCurrent text: {curr_t[:80]}\nCurrent image: {curr_i}\n\n"
                f"**Step 1/2:** Send new welcome text.\n`-skip` = keep | `-clear` = default",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_welcome")]])
            )
            await cb.answer()

        elif data == "preview_welcome":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer()
            text = bi.get("custom_welcome") or "_(Default welcome)_"
            img  = bi.get("welcome_image")
            await cb.answer()
            if img:
                try:
                    await client.send_photo(cb.message.chat.id, img, caption=f"**Preview:**\n\n{text}"); return
                except Exception:
                    pass
            await cb.message.reply(f"**Preview:**\n\n{text}")

        # ─── Rebuild ─────────────────────────────────────────────
        elif data == "confirm_rebuild":
            if not is_admin(uid): return await cb.answer("❌ Admin only!", show_alert=True)
            if not SESSION_STRING:
                return await cb.answer("❌ SESSION_STRING not set! Check /help", show_alert=True)
            await cb.answer("🔄 Starting rebuild...", show_alert=True)
            sm = await cb.message.edit("🔄 **Rebuilding DB from DB Channel...**")
            try:
                stats = await rebuild_db_with_userbot(status_msg=sm)
                await sm.edit(f"✅ **Rebuild Complete!**\n\n📁 Files: `{stats['files']}`\n📦 Batches: `{stats['batches']}`\n❌ Errors: `{stats['errors']}`")
            except ValueError:
                pass
            except Exception as e:
                await sm.edit(f"❌ Rebuild failed!\n`{e}`")

        # ─── Batch ───────────────────────────────────────────────
        elif data == "start_batch":
            TEMP_BATCH[uid] = []
            await cb.message.edit("📦 **Batch Mode**\n\nSend files. `/done` to finish.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_batch")]]))
            await cb.answer("Batch started!")

        elif data == "cancel_batch":
            TEMP_BATCH.pop(uid, None)
            await cb.message.edit("❌ Batch cancelled!")
            await cb.answer()

        # ─── Broadcast ───────────────────────────────────────────
        elif data == "confirm_broadcast":
            bd = TEMP_BROADCAST.get(uid)
            if not bd: return await cb.answer("❌ Expired!", show_alert=True)
            sm = await cb.message.edit("📢 **Broadcasting...**")
            s, f = await do_broadcast(bd["bot_ids"], bd["bc_msg_id"], status_msg=sm)
            TEMP_BROADCAST.pop(uid, None)
            await sm.edit(f"✅ **Broadcast Done!**\n\n✅ `{s}` | ❌ `{f}` | 🤖 `{len(bd['bot_ids'])}` bots")

        elif data == "cancel_broadcast":
            TEMP_BROADCAST.pop(uid, None)
            await cb.message.edit("❌ Cancelled!")
            await cb.answer()

        # ─── Navigation ──────────────────────────────────────────
        elif data == "clone_menu":
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            await cb.message.edit(
                f"🤖 **Clone** — Your bots: `{len(ubts)}`\n\n1. @BotFather → /newbot\n2. `/clone TOKEN`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🤖 BotFather", url="https://t.me/BotFather")],[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
            )
            await cb.answer()

        elif data == "user_dashboard":
            ud = get_user(uid, bot_id)
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            await cb.message.edit(
                f"📊 **Dashboard**\n\n📤 `{ud.get('files_uploaded',0) if ud else 0}` | 📦 `{ud.get('batches_created',0) if ud else 0}` | 🤖 `{len(ubts)}`\n💰 `{ud.get('points',0) if ud else 0}` pts | 💎 {'Premium ✅' if ud and ud.get('is_premium') else 'Free'}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
            )
            await cb.answer()

        elif data == "my_bots_menu":
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            text = f"🤖 **Your Bots ({len(ubts)})**\n\n"
            for i, b in enumerate(ubts[:10],1): text += f"{i}. {'🟢' if b['bot_id'] in ACTIVE_CLIENTS else '🔴'} @{b['bot_username']}\n"
            if not ubts: text += "None yet!"
            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Clone", callback_data="clone_menu")],[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]))
            await cb.answer()

        elif data in ("bot_settings","cb_search","help_menu","referral_menu","premium_menu"):
            texts = {
                "bot_settings": lambda: (lambda bi: f"⚙️ **Settings**\n⏱ `{bi.get('auto_delete_time',600)}s` | 📢 `{len(bi.get('force_subs',[]))}` ch\n🔗 `{'ON' if bi.get('is_shortener_enabled') else 'OFF'}`" if bi else "Not found")(get_bot_info(bot_id)),
                "cb_search":    lambda: "🔍 **Search**\n\nUse: `/search FILENAME`\nOr inline: `@BotUsername query`",
                "help_menu":    lambda: "ℹ️ **Help**\n\nSend file → link | `/batch` → multi link\n`/editfile ID` → edit | `/setwelcome` → welcome\n`/clone TOKEN` → your bot | `/rebuild` → restore DB",
                "referral_menu": lambda: f"🎁 **Referral**\n\n👥 `{(get_user(uid,bot_id) or {}).get('referrals',0)}` | 💰 `{(get_user(uid,bot_id) or {}).get('points',0)}` pts\n\n`https://t.me/{client.me.username}?start=ref_{uid}`",
                "premium_menu": lambda: f"💎 **Premium** — {'💎 Active' if (get_user(uid,bot_id) or {}).get('is_premium') else '🆓 Free'}\n\nBenefits: No auto-delete | Unlimited batch\nCost: 500 pts → `/buy_premium`",
            }
            await cb.message.edit(texts[data](), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]))
            await cb.answer()

        elif data == "admin_panel":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id")==uid)):
                return await cb.answer("❌ No access!", show_alert=True)
            await cb.message.edit("⚡ **Admin Panel**", reply_markup=kb_admin())
            await cb.answer()

        elif data == "broadcast_menu":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or uid==MAIN_ADMIN or (bi and bi.get("owner_id")==uid)):
                return await cb.answer("❌ No access!", show_alert=True)
            await cb.message.edit(f"📢 **Broadcast**\n\n👥 `{len(get_all_users(bot_id))}`\n\nReply to a message with `/broadcast`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
            await cb.answer()

        elif data == "admin_stats":
            bot_files = [f for f in load_db(FILES_DB).values() if f.get("bot_id")==bot_id]
            await cb.message.edit(
                f"📊 **Bot Stats**\n\n👥 `{len(get_all_users(bot_id))}` | 📁 `{len(bot_files)}` | 👁 `{sum(f.get('access_count',0) for f in bot_files)}`\n🖼 Custom thumbs: `{sum(1 for f in bot_files if f.get('custom_thumbnail'))}`\n⏳ `{str(datetime.now()-START_TIME).split('.')[0]}`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
            await cb.answer()

        elif data == "manage_users":
            all_u = load_db(USERS_DB)
            banned = sum(1 for u in all_u.values() if u.get("bot_id")==bot_id and u.get("is_banned"))
            await cb.message.edit(f"👥 **Users**\n\n🟢 Active: `{len(get_all_users(bot_id))}` | 🚫 Banned: `{banned}`\n\n`/ban ID` `/unban ID` `/info ID` `/setpremium ID`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
            await cb.answer()

        elif data == "my_bots_admin":
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            text = f"🤖 **Your Bots ({len(ubts)})**\n\n"
            for i, b in enumerate(ubts[:15],1): text += f"{i}. {'🟢' if b['bot_id'] in ACTIVE_CLIENTS else '🔴'} @{b['bot_username']}\n"
            if not ubts: text += "None!"
            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Clone", callback_data="clone_menu")],[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
            await cb.answer()

        elif data == "bot_settings_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            t = bi.get("auto_delete_time",600)
            await cb.message.edit(
                f"⚙️ **Bot Settings**\n\n👋 Welcome: {'Custom ✅' if bi.get('custom_welcome') else 'Default'}\n🖼 Image: {'Set ✅' if bi.get('welcome_image') else 'None'}\n⏱ Timer: `{t}s` ({t//60}min)\n✅ Auto-Approve: `{'ON' if bi.get('auto_approve') else 'OFF'}`\n📝 Log: `{bi.get('log_channel') or 'None'}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👋 Edit Welcome", callback_data="edit_welcome_msg")],
                    [InlineKeyboardButton("⏱ Timer", callback_data="edit_timer"), InlineKeyboardButton("📝 Log", callback_data="set_log_info")],
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
                ]))
            await cb.answer()

        elif data == "edit_timer":
            bi = get_bot_info(bot_id); curr = bi.get("auto_delete_time",600) if bi else 600
            await cb.message.edit(f"⏱ Current: `{curr}s` ({curr//60}min)\n\n`/settimer SECONDS` (min 60)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
            await cb.answer()

        elif data == "set_log_info":
            await cb.message.edit("📝 `/setlog CHANNEL_ID` or `/setlog off`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="bot_settings_admin")]]))
            await cb.answer()

        elif data == "forcesub_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            fs = bi.get("force_subs",[])
            text = f"🔒 **Force Subscribe** ({len(fs)}/{MAX_FORCE_SUB_CHANNELS})\n\n"
            for i,f in enumerate(fs,1):
                cid = f["channel_id"] if isinstance(f,dict) else f
                text += f"{i}. `{cid}`\n"
            if not fs: text += "None.\n"
            text += "\n🆕 Pending join requests also grant access!\nManage via `/setfs`."
            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
            await cb.answer()

        elif data == "toggle_auto_approve":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            curr = bi.get("auto_approve",False); update_bot_info(bot_id,"auto_approve",not curr)
            await cb.answer(f"Auto-Approve: {'ON ✅' if not curr else 'OFF ❌'}", show_alert=True)
            await cb.message.edit("⚡ **Admin Panel**", reply_markup=kb_admin())

        elif data == "shortener_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            st = "✅ ON" if bi.get("is_shortener_enabled") else "❌ OFF"
            await cb.message.edit(f"🔗 **Shortener** {st}\nURL: `{bi.get('shortener_url') or 'Not set'}`\n`/shortener` to manage.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
            await cb.answer()

        elif data == "supreme_panel":
            if uid != MAIN_ADMIN: return await cb.answer("❌ Supreme only!", show_alert=True)
            sess = "✅ Set" if SESSION_STRING else "❌ Not Set"
            await cb.message.edit(f"👑 **Supreme Panel**\n🔑 Session: {sess}", reply_markup=kb_supreme())
            await cb.answer()

        elif data == "global_broadcast":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            await cb.message.edit(f"🌍 **Global Broadcast**\n\n👥 `{len(get_all_users())}` | 🤖 `{len(ACTIVE_CLIENTS)}`\n\nReply to a message with `/broadcast`.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="supreme_panel")]]))
            await cb.answer()

        elif data == "system_stats":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            t, u, f = shutil.disk_usage("/")
            pend = sum(len(v) for v in _PENDING.values())
            sess = "✅ Set" if SESSION_STRING else "❌ Not Set (needed for /rebuild)"
            await cb.message.edit(
                f"🖥 **System Stats**\n━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 `{len(get_all_bots())}` bots | 🟢 `{len(ACTIVE_CLIENTS)}` online\n"
                f"👥 `{len(load_db(USERS_DB))}` users | 📁 `{len(load_db(FILES_DB))}` files\n"
                f"⏳ Pending joins: `{pend}` | 🔑 Session: {sess}\n"
                f"💾 Disk: `{u//(2**30)}GB/{t//(2**30)}GB` (Free: `{f//(2**30)}GB`)\n"
                f"⏱ Uptime: `{str(datetime.now()-START_TIME).split('.')[0]}`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="system_stats")],[InlineKeyboardButton("🔙 Back", callback_data="supreme_panel")]]))
            await cb.answer()

        elif data == "all_bots_list":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            ab = get_all_bots(); text = f"🤖 **All Bots ({len(ab)})**\n\n"
            for i, (k, b) in enumerate(list(ab.items())[:20],1):
                if isinstance(b,dict):
                    text += f"{i}. {'🟢' if int(k) in ACTIVE_CLIENTS else '🔴'} @{b['bot_username']} — {b.get('owner_name','?')}\n"
            if len(ab)>20: text += f"\n...+{len(ab)-20} more"
            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="supreme_panel")]]))
            await cb.answer()

        elif data == "manage_admins":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            admins = load_db(ADMINS_DB)
            text = f"👑 **Admins**\n\n🌟 Main: `{MAIN_ADMIN}`\n\nSecondary ({len(admins)}):\n"
            for aid in admins: text += f"• `{aid}`\n"
            text += "\n`/addadmin ID` `/deladmin ID`"
            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="supreme_panel")]]))
            await cb.answer()

        elif data == "toggle_maintenance":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            curr = get_global_config().get("maintenance",False); update_global_config("maintenance",not curr)
            await cb.answer(f"Maintenance: {'ON ⚠️' if not curr else 'OFF ✅'}", show_alert=True)
            await cb.message.edit("👑 **Supreme Panel**", reply_markup=kb_supreme())

        elif data == "global_msg_set":
            if uid != MAIN_ADMIN: return await cb.answer()
            await cb.message.edit("📢 `/setglobal MESSAGE` or `/setglobal off`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="supreme_panel")]]))
            await cb.answer()

        elif data == "manual_backup":
            if uid != MAIN_ADMIN: return await cb.answer()
            await cb.answer("⏳ Backing up...", show_alert=True)
            asyncio.create_task(backup_db())

        elif data == "manual_clean_cache":
            if uid != MAIN_ADMIN: return await cb.answer()
            count = clean_expired_cache()
            await cb.answer(f"🧹 Cleaned {count} entries!", show_alert=True)

        elif data == "restart_all_bots":
            if uid != MAIN_ADMIN: return await cb.answer()
            await cb.answer("♻️ Restarting...", show_alert=True)
            os.execl(sys.executable, sys.executable, *sys.argv)

        elif data == "back_to_start":
            bi = get_bot_info(bot_id)
            text = (bi.get("custom_welcome") if bi else None) or f"✨ **Welcome Back!**\n🤖 @{client.me.username}"
            img  = bi.get("welcome_image") if bi else None
            kbd  = kb_start(bot_id, uid)
            try:
                if img:
                    await cb.message.delete()
                    await client.send_photo(cb.message.chat.id, img, caption=text, reply_markup=kbd)
                else:
                    await cb.message.edit(text, reply_markup=kbd)
            except Exception:
                await cb.message.edit(f"👋 **Welcome Back!**\n🤖 @{client.me.username}", reply_markup=kbd)
            await cb.answer()

        else:
            await cb.answer()


# ═══════════════════════════════════════════════════════════════
# 🔧 HELPERS
# ═══════════════════════════════════════════════════════════════

async def _auto_delete(msg, delay: int):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# ⏰ BACKGROUND TASKS
# ═══════════════════════════════════════════════════════════════

async def background_tasks():
    while True:
        await asyncio.sleep(600)
        try:
            USER_FLOOD.clear()
            n = clean_expired_cache()
            if n: logger.info(f"🗑 Cleaned {n} cache entries")
            await backup_db()
            # Clean stale pending requests
            now = datetime.now()
            for cid in list(_PENDING):
                for uid in list(_PENDING.get(cid,{})):
                    try:
                        if (now - datetime.fromisoformat(_PENDING[cid][uid])).days > PENDING_REQUEST_TTL_DAYS:
                            del _PENDING[cid][uid]
                    except Exception:
                        _PENDING[cid].pop(uid, None)
                if not _PENDING.get(cid): _PENDING.pop(cid, None)
        except Exception as e:
            logger.error(f"Background task error: {e}")

# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  🚀 ULTRA FILESTORE BOT v4.1 — PRODUCTION GRADE          ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    if DB_CHANNEL == -1000000000000:
        logger.error("❌ DB_CHANNEL not configured!"); return

    _load_pending()
    logger.info(f"📋 Loaded pending requests for {len(_PENDING)} channels")
    logger.info(f"🔑 SESSION_STRING: {'✅ Set' if SESSION_STRING else '❌ Not set (rebuild unavailable)'}")

    await start_web_server()

    logger.info("🔥 Starting Main Bot...")
    if not await start_bot(MAIN_BOT_TOKEN):
        logger.error("❌ Main bot failed!"); return

    all_bots = get_all_bots()
    if all_bots:
        tasks = [
            start_bot(b["token"], parent_bot_id=b.get("parent_bot_id"))
            for b in all_bots.values()
            if isinstance(b,dict) and b.get("token") and b["token"] != MAIN_BOT_TOKEN
        ]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            ok = sum(1 for r in results if r and not isinstance(r, Exception))
            logger.info(f"✅ {ok}/{len(tasks)} clone bots started")

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║        ✅ ALL SYSTEMS OPERATIONAL v4.1 ✅                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"👑 Admin   : {MAIN_ADMIN}")
    print(f"🤖 Bots    : {len(ACTIVE_CLIENTS)}")
    print(f"🌐 Port    : {PORT}")
    print(f"🔑 Session : {'✅ Set' if SESSION_STRING else '❌ Not Set'}")
    print(f"📅 Started : {START_TIME:%Y-%m-%d %H:%M:%S}")
    print()

    asyncio.create_task(background_tasks())
    await idle()

    logger.info("🛑 Shutting down...")
    global _HTTP
    if _HTTP and not _HTTP.closed:
        await _HTTP.close()
    for cd in ACTIVE_CLIENTS.values():
        try: await cd["app"].stop()
        except Exception: pass
    logger.info("✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped.")
    except Exception as e:
        logger.error(f"❌ Fatal: {e}"); raise
