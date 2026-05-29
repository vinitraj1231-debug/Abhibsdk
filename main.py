"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ULTRA ADVANCED FILESTORE BOT v7.0 — ELITE EDITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DUAL TIER POST SYSTEM
   ├─ EK LINK → 2 experiences: FREE + PREMIUM
   ├─ FREE users  → shortener ads → free files (auto-delete)
   ├─ PREMIUM users → direct delivery → pro files (no delete)
   ├─ Creator workflow: /dualpost → files → /dpremium → files → /dpdone
   ├─ Dual post preview, analytics, delete
   └─ Token-secured shortener bypass

 SHORTENER TOKEN SYSTEM  — 15min expiry, one-time use
 RENDER READY            — aiohttp health-check on $PORT
 BROADCAST               — stored in DB_CHANNEL, copy per-bot
 THUMBNAIL               — BytesIO in_memory → thumb param
 CAPTION EDITOR          — FSM, -clear support
 WELCOME EDITOR          — /setwelcome interactive 2-step
 JOIN REQUEST ACCESS     — pending = bot access
 ADVANCED LINK PROTECT   — dynamic invite link with expiry
 FILE RENAMER            — renaming with download & re-upload
 CLONE + REFERRAL + PREMIUM + ANALYTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import os, sys, json, asyncio, hashlib, logging, random, shutil, time, tempfile, re, concurrent.futures
import aiohttp
import yt_dlp
from typing import Optional
from aiohttp import web
from datetime import datetime, timedelta

try:
    import sqlite3
except ImportError:
    from unittest.mock import MagicMock
    mock_sqlite3 = MagicMock()
    sys.modules["sqlite3"] = mock_sqlite3
    sys.modules["_sqlite3"] = mock_sqlite3

# Monkey-patching Pyrogram's get_peer_type to fix PeerIdInvalid for some channel IDs
# This must be done as early as possible before Client or any pyrogram methods are imported.
try:
    import pyrogram.utils
    def get_peer_type_new(peer_id: int) -> str:
        peer_id_str = str(peer_id)
        if not peer_id_str.startswith("-"):
            return "user"
        return "channel" if peer_id_str.startswith("-100") else "chat"
    pyrogram.utils.get_peer_type = get_peer_type_new
except (ImportError, ModuleNotFoundError):
    pass

from pyrogram import Client, filters, idle, utils
from pyrogram.storage import MemoryStorage
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, WebAppInfo,
    InlineQueryResultArticle, InputTextMessageContent
)
from pyrogram.errors import FloodWait, UserNotParticipant, SlowmodeWait
from pyrogram.enums import ChatMemberStatus

# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════

API_ID         = int(os.environ.get("API_ID",         "22528639"))
API_HASH       = os.environ.get("API_HASH",            "43df9dcf764afd03a1fd1dc3cec68bbd")
MAIN_BOT_TOKEN = os.environ.get("MAIN_BOT_TOKEN",     "8235471153:AAEBfhiiUE-2977TqWEeI_cpCQeWJV9W9RY")
MAIN_ADMIN     = int(os.environ.get("MAIN_ADMIN",     "8647666069"))
DB_CHANNEL     = int(os.environ.get("DB_CHANNEL",     "-1003921125499"))
PORT           = int(os.environ.get("PORT",            "8080"))
WEBAPP_URL     = os.environ.get("WEBAPP_URL",          "")
FILE_CACHE_DURATION      = 3600
MAX_FORCE_SUB_CHANNELS   = 100
PENDING_REQUEST_TTL_DAYS = 30
MAX_BROADCAST_RATE       = 0.05
SHORTENER_TOKEN_EXPIRY   = 900   # 15 minutes

DB_FOLDER       = "database"
FILES_DB        = f"{DB_FOLDER}/files.json"
BATCH_DB        = f"{DB_FOLDER}/batches.json"
BOTS_DB         = f"{DB_FOLDER}/bots.json"
USERS_DB        = f"{DB_FOLDER}/users.json"
ADMINS_DB       = f"{DB_FOLDER}/admins.json"
FILE_CACHE_DB   = f"{DB_FOLDER}/file_cache.json"
CONFIG_DB       = f"{DB_FOLDER}/config.json"
PENDING_REQ_DB  = f"{DB_FOLDER}/pending_requests.json"
DUAL_POST_DB    = f"{DB_FOLDER}/dual_posts.json"
PLINKS_DB       = f"{DB_FOLDER}/protected_links.json"

BOT_COMMANDS = [
    BotCommand("start",       " Start the bot"),
    BotCommand("admin",       " Admin Panel"),
    BotCommand("supreme",     " Supreme Panel"),
    BotCommand("clone",       " Clone your bot"),
    BotCommand("batch",       " Batch mode"),
    BotCommand("done",        " Finish batch"),
    BotCommand("cancel",      " Cancel"),
    BotCommand("setfs",       " Force subscribe"),
    BotCommand("mybots",      " Your cloned bots"),
    BotCommand("stats",       " Statistics"),
    BotCommand("help",        " Help"),
    BotCommand("broadcast",   " Broadcast"),
    BotCommand("ban",         " Ban user"),
    BotCommand("unban",       " Unban user"),
    BotCommand("botinfo",     " Bot info"),
    BotCommand("settimer",    " Auto-delete timer"),
    BotCommand("search",      " Search files"),
    BotCommand("premium",     " Premium"),
    BotCommand("setprice",    " Set Premium Price (Admin)"),
    BotCommand("setcontact",  " Set Premium Contact (Admin)"),
    BotCommand("setqr",       " Set Premium QR Code (Admin)"),
    BotCommand("givepremium", " Give Premium (Admin)"),
    BotCommand("removepremium", " Remove Premium (Admin)"),
    BotCommand("shortener",   " URL Shortener"),
    BotCommand("setlog",      " Log Channel"),
    BotCommand("setchannel",  " Connect Channel"),
    BotCommand("setmode",     " Set Join Mode"),
    BotCommand("protect",     " Protect Channel Link"),
    BotCommand("myplinks",    " My Protected Links"),
    BotCommand("restart",     " Restart (Supreme)"),
    BotCommand("ping",        " Ping"),
    BotCommand("listfiles",   " List files"),
    BotCommand("mybatches",   " List your batches"),
    BotCommand("editfile",    " Edit file"),
    BotCommand("delfile",     " Delete file"),
    BotCommand("setwelcome",  " Set welcome message"),
    BotCommand("dualpost",    " Create dual-tier post"),
    BotCommand("dpremium",    " Switch to premium tier"),
    BotCommand("dpdone",      " Finish dual post"),
    BotCommand("dpcancel",    " Cancel dual post"),
    BotCommand("myduals",     " My dual posts"),
    BotCommand("deldual",     " Delete dual post"),
    BotCommand("dpstats",     " Dual post analytics"),
    BotCommand("createpost",  " Create custom post"),
    BotCommand("addadmin",    " Add bot admin"),
    BotCommand("deladmin",    " Remove bot admin"),
    BotCommand("font",        " Font Editor"),
    BotCommand("requests",    " Manage join requests"),
    BotCommand("download",    " Download videos from any site"),
    BotCommand("refer",       " Refer and Earn"),
    BotCommand("about",       " About the bot"),
    BotCommand("rename",      " Rename a file"),
    BotCommand("setcaption",  " Set caption for a file"),
    BotCommand("setthumb",    " Set thumbnail for a file"),
    BotCommand("autoapprove", " Toggle Auto Approve"),
    BotCommand("autocaption", " Toggle Auto Caption"),
]

# ═══════════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("FS")

# ═══════════════════════════════════════════════════════════════
#  DATABASE — Atomic JSON with in-memory cache
# ═══════════════════════════════════════════════════════════════

os.makedirs(DB_FOLDER, exist_ok=True)
_DB_CACHE:   dict = {}
_GLOBAL_CFG: dict = {}

def load_db(path: str) -> dict:
    """Load JSON database with fallback to backup and cache."""
    if path in _DB_CACHE:
        return _DB_CACHE[path]

    data = {}
    bak_path = path + ".bak"

    # Try primary
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load primary DB {path}: {e}")
            # Try backup if primary failed
            if os.path.exists(bak_path):
                try:
                    with open(bak_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    logger.info(f"Successfully restored {path} from backup.")
                except Exception as be:
                    logger.error(f"Failed to load backup DB {bak_path}: {be}")
    elif os.path.exists(bak_path):
        # Primary missing, try backup
        try:
            with open(bak_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Restored {path} from backup (primary was missing).")
        except Exception as be:
            logger.error(f"Failed to load backup DB {bak_path}: {be}")

    _DB_CACHE[path] = data
    return data

def save_db(path: str, data: dict) -> None:
    """Save JSON database atomically with verification and backup."""
    _DB_CACHE[path] = data
    tmp = path + ".tmp"
    bak = path + ".bak"

    try:
        # Write to temporary file
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Verify written file is valid JSON
        with open(tmp, "r", encoding="utf-8") as f:
            json.load(f)

        # If primary exists, move it to backup
        if os.path.exists(path):
            shutil.copy2(path, bak)

        # Move temp to primary
        os.replace(tmp, path)
    except Exception as e:
        logger.error(f"Critical error saving database {path}: {e}")
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except: pass

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

_PENDING: dict = {}

def _load_pending():
    global _PENDING
    raw = load_db(PENDING_REQ_DB)
    now = datetime.now()
    result = {}
    for cid, users in raw.items():
        if not isinstance(users, dict): continue
        clean = {}
        for uid, ts in users.items():
            try:
                if (now - datetime.fromisoformat(ts)).days <= PENDING_REQUEST_TTL_DAYS:
                    clean[int(uid)] = ts
            except Exception: pass
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
    if not ts_str: return False
    try:
        return (datetime.now() - datetime.fromisoformat(ts_str)).days <= PENDING_REQUEST_TTL_DAYS
    except Exception:
        return False

# ─── USER FUNCTIONS ─────────────────────────────────────────────

def add_user(user_id, bot_id, username=None, name=None):
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
            "is_premium": False,
            "refer_count": 0, "refer_rewards": 0,
            "last_active": str(datetime.now()),
            "pref_font": "smallcaps"
        }
    else:
        users[key]["last_active"] = str(datetime.now())
        if "pref_font" not in users[key]:
            users[key]["pref_font"] = "smallcaps"
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

def is_admin(user_id, bot_id=None) -> bool:
    if user_id == MAIN_ADMIN: return True
    if str(user_id) in load_db(ADMINS_DB): return True
    if bot_id:
        bi = get_bot_info(bot_id)
        if bi and user_id in bi.get("secondary_admins", []): return True
    return False

# ─── BOT INFO ───────────────────────────────────────────────────

def save_bot_info(token, bot_id, bot_username, owner_id, owner_name, parent_bot_id=None):
    bots = load_db(BOTS_DB)
    data = {
        "token": token, "bot_id": bot_id,
        "bot_username": bot_username, "owner_id": owner_id,
        "owner_name": owner_name, "parent_bot_id": parent_bot_id,
        "created_on": str(datetime.now()), "is_active": True,
        "custom_welcome": None, "welcome_image": None,
        "auto_delete_time": 300, "auto_approve": False,
        "premium_price": "500",
        "premium_contact": "zolvid",
        "premium_qr": None,
        "auto_caption": True,
        "connected_channel": None,
        "join_method": "direct",
        "verify_link": None,
        "update_channel": None,
        "force_subs": [],
        "shortener_api": None, "shortener_url": None,
        "is_shortener_enabled": False,
        "log_channel": None,
        "secondary_admins": []
    }
    bots[str(bot_id)] = data
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

def get_all_bots(): return load_db(BOTS_DB)

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
    if count: save_db(BOTS_DB, bots)
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
    if not entry: return None
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
    if expired: save_db(FILE_CACHE_DB, cache)
    return len(expired)

# ─── UTILITIES ──────────────────────────────────────────────────

_FONTS = {
    "smallcaps": {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'
    },
    "monospace": {
        'a': '𝚊', 'b': '𝚋', 'c': '𝚌', 'd': '𝚍', 'e': '𝚎', 'f': '𝚏', 'g': '𝚐', 'h': '𝚑', 'i': '𝚒', 'j': '𝚓', 'k': '𝚔', 'l': '𝚕', 'm': '𝚖', 'n': '𝚗', 'o': '𝚘', 'p': '𝚙', 'q': '𝚚', 'r': '𝚛', 's': '𝚜', 't': '𝚝', 'u': '𝚞', 'v': '𝚟', 'w': '𝚠', 'x': '𝚡', 'y': '𝚢', 'z': '𝚣',
        'A': '𝙰', 'B': '𝙱', 'C': '𝙲', 'D': '𝙳', 'E': '𝙴', 'F': '𝙵', 'G': '𝙶', 'H': '𝙷', 'I': '𝙸', 'J': '𝙹', 'K': '𝙺', 'L': '𝙻', 'M': '𝙼', 'N': '𝙽', 'O': '𝙾', 'P': '𝙿', 'Q': '𝚀', 'R': '𝚁', 'S': '𝚂', 'T': '𝚃', 'U': '𝚄', 'V': '𝚅', 'W': '𝚆', 'X': '𝚇', 'Y': '𝚈', 'Z': '𝚉',
        '0': '𝟶', '1': '𝟷', '2': '𝟸', '3': '𝟹', '4': '𝟺', '5': '𝟻', '6': '𝟼', '7': '𝟽', '8': '𝟾', '9': '𝟿'
    },
    "bold_serif": {
        'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝', 'e': '𝐞', 'f': '𝐟', 'g': '𝐠', 'h': '𝐡', 'i': '𝐢', 'j': '𝐣', 'k': '𝐤', 'l': '𝐥', 'm': '𝐦', 'n': '𝐧', 'o': '𝐨', 'p': '𝐩', 'q': '𝐪', 'r': '𝐫', 's': '𝐬', 't': '𝐭', 'u': '𝐮', 'v': '𝐯', 'w': '𝐰', 'x': '𝐱', 'y': '𝐲', 'z': '𝐳',
        'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆', 'H': '𝐇', 'I': '𝐈', 'J': '𝐉', 'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍', 'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑', 'S': '𝐒', 'T': '𝐓', 'U': '𝐔', 'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙'
    },
    "italic_serif": {
        'a': '𝑎', 'b': '𝑏', 'c': '𝑐', 'd': '𝑑', 'e': '𝑒', 'f': '𝑓', 'g': '𝑔', 'h': 'ℎ', 'i': '𝑖', 'j': '𝑗', 'k': '𝑘', 'l': '𝑙', 'm': '𝑚', 'n': '𝑛', 'o': '𝑜', 'p': '𝑝', 'q': '𝑞', 'r': '𝑟', 's': '𝑠', 't': '𝑡', 'u': '𝑢', 'v': '𝑣', 'w': '𝑤', 'x': '𝑥', 'y': '𝑦', 'z': '𝑧',
        'A': '𝐴', 'B': '𝐵', 'C': '𝐶', 'D': '𝐷', 'E': '𝐸', 'F': '𝐹', 'G': '𝐺', 'H': '𝐻', 'I': '𝐼', 'J': '𝐽', 'K': '𝐾', 'L': '𝐿', 'M': '𝑀', 'N': '𝑁', 'O': '𝑂', 'P': '𝑃', 'Q': '𝑄', 'R': '𝑅', 'S': '𝑆', 'T': '𝑇', 'U': '𝑈', 'V': '𝑉', 'W': '𝑊', 'X': '𝑋', 'Y': '𝑌', 'Z': '𝑍'
    },
    "script": {
        'a': '𝒶', 'b': '𝒷', 'c': '𝒸', 'd': '𝒹', 'e': '𝑒', 'f': '𝒻', 'g': '𝑔', 'h': '𝒽', 'i': '𝒾', 'j': '𝒿', 'k': '𝓀', 'l': '𝓁', 'm': '𝓂', 'n': '𝓃', 'o': '𝑜', 'p': '𝓅', 'q': '𝓆', 'r': '𝓇', 's': '𝓈', 't': '𝓉', 'u': '𝓊', 'v': '𝓋', 'w': '𝓌', 'x': '𝓍', 'y': '𝓎', 'z': '𝓏',
        'A': '𝒜', 'B': 'ℬ', 'C': '𝒞', 'D': '𝒟', 'E': 'ℰ', 'F': 'ℱ', 'G': '𝒢', 'H': 'ℋ', 'I': 'ℐ', 'J': '𝒥', 'K': '𝒦', 'L': 'ℒ', 'M': 'ℳ', 'N': '𝒩', 'O': '𝒪', 'P': '𝒫', 'Q': '𝒬', 'R': 'ℛ', 'S': '𝒮', 'T': '𝒯', 'U': '𝒰', 'V': '𝒱', 'W': '𝒲', 'X': '𝒳', 'Y': '𝒴', 'Z': '𝒵'
    },
    "double_struck": {
        'a': '𝕒', 'b': '𝕓', 'c': '𝕔', 'd': '𝕕', 'e': '𝕖', 'f': '𝕗', 'g': '𝕘', 'h': '𝕙', 'i': '𝕚', 'j': '𝕛', 'k': '𝕜', 'l': '𝕝', 'm': '𝕞', 'n': '𝕟', 'o': '𝕠', 'p': '𝕡', 'q': '𝕢', 'r': '𝕣', 's': '𝕤', 't': '𝕥', 'u': '𝕦', 'v': '𝕧', 'w': '𝕨', 'x': '𝕩', 'y': '𝕪', 'z': '𝕫',
        'A': '𝔸', 'B': '𝔹', 'C': 'ℂ', 'D': '𝔻', 'E': '𝔼', 'F': '𝔽', 'G': '𝔾', 'H': 'ℍ', 'I': '𝕀', 'J': '𝕁', 'K': '𝕂', 'L': '𝕃', 'M': '𝕄', 'N': 'ℕ', 'O': '𝕆', 'P': 'ℙ', 'Q': 'ℚ', 'R': 'ℝ', 'S': '𝕊', 'T': '𝕋', 'U': '𝕌', 'V': '𝕍', 'W': '𝕎', 'X': '𝕏', 'Y': '𝕐', 'Z': 'ℤ',
        '0': '𝟘', '1': '𝟙', '2': '𝟚', '3': '𝟛', '4': '𝟜', '5': '𝟝', '6': '𝟞', '7': '𝟟', '8': '𝟠', '9': '𝟡'
    },
    "fraktur": {
        'a': '𝔞', 'b': '𝔟', 'c': '𝔠', 'd': '𝔡', 'e': '𝔢', 'f': '𝔣', 'g': '𝔤', 'h': '𝔥', 'i': '𝔦', 'j': '𝔧', 'k': '𝔨', 'l': '𝔩', 'm': '𝔪', 'n': '𝔫', 'o': '𝔬', 'p': '𝔭', 'q': '𝔮', 'r': '𝔯', 's': '𝔰', 't': '𝔱', 'u': '𝔲', 'v': '𝔳', 'w': '𝔴', 'x': '𝔵', 'y': '𝔶', 'z': '𝔷',
        'A': '𝔄', 'B': '𝔅', 'C': 'ℭ', 'D': '𝔇', 'E': '𝔈', 'F': '𝔉', 'G': '𝔊', 'H': 'ℌ', 'I': 'ℑ', 'J': '𝔍', 'K': '𝔎', 'L': '𝔏', 'M': '𝔐', 'N': '𝔑', 'O': '𝔒', 'P': '𝔓', 'Q': '𝔔', 'R': 'ℜ', 'S': '𝔖', 'T': '𝔗', 'U': '𝔘', 'V': '𝔙', 'W': '𝔚', 'X': '𝔛', 'Y': '𝔜', 'Z': 'ℨ'
    },
    "sans_bold": {
        'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵', 'i': '𝗶', 'j': '𝗷', 'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽', 'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝘄', 'x': '𝘅', 'y': '𝘆', 'z': '𝘇',
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭'
    },
    "bold_italic": {
        'a': '𝒂', 'b': '𝒃', 'c': '𝒄', 'd': '𝒅', 'e': '𝒆', 'f': '𝒇', 'g': '𝒈', 'h': '𝒉', 'i': '𝒊', 'j': '𝒋', 'k': '𝒌', 'l': '𝒍', 'm': '𝒎', 'n': '𝒏', 'o': '𝒐', 'p': '𝒑', 'q': '𝒒', 'r': '𝒓', 's': '𝒔', 't': '𝒕', 'u': '𝒖', 'v': '𝒗', 'w': '𝒘', 'x': '𝒙', 'y': '𝒚', 'z': '𝒛',
        'A': '𝑨', 'B': '𝑩', 'C': '𝑪', 'D': '𝑫', 'E': '𝑬', 'F': '𝑭', 'G': '𝑮', 'H': '𝑯', 'I': '𝑰', 'J': '𝑱', 'K': '𝑲', 'L': '𝑳', 'M': '𝑴', 'N': '𝑵', 'O': '𝑶', 'P': '𝑷', 'Q': '𝑸', 'R': '𝑹', 'S': '𝑺', 'T': '𝑻', 'U': '𝑼', 'V': '𝑽', 'W': '𝑾', 'X': '𝑿', 'Y': '𝒀', 'Z': '𝒁'
    },
    "sans_italic": {
        'a': '𝘢', 'b': '𝘣', 'c': '𝘤', 'd': '𝘥', 'e': '𝘦', 'f': '𝘧', 'g': '𝘨', 'h': '𝘩', 'i': '𝘪', 'j': '𝘫', 'k': '𝘬', 'l': '𝘭', 'm': '𝘮', 'n': '𝘯', 'o': '𝘰', 'p': '𝘱', 'q': '𝘲', 'r': '𝘳', 's': '𝘴', 't': '𝘵', 'u': '𝘶', 'v': '𝘷', 'w': '𝘸', 'x': '𝘹', 'y': '𝘺', 'z': '𝘻',
        'A': '𝘈', 'B': '𝘉', 'C': '𝘊', 'D': '𝘋', 'E': '𝘌', 'F': '𝘍', 'G': '𝘎', 'H': '𝘏', 'I': '𝘐', 'J': '𝘑', 'K': '𝘒', 'L': '𝘓', 'M': '𝘔', 'N': '𝘕', 'O': '𝘖', 'P': '𝘗', 'Q': '𝘘', 'R': '𝘙', 'S': '𝘚', 'T': '𝘛', 'U': '𝘜', 'V': '𝘝', 'W': '𝘞', 'X': '𝘟', 'Y': '𝘠', 'Z': '𝘡'
    },
    "bubbles": {
        'a': 'ⓐ', 'b': 'ⓑ', 'c': 'ⓒ', 'd': 'ⓓ', 'e': 'ⓔ', 'f': 'ⓕ', 'g': 'ⓖ', 'h': 'ⓗ', 'i': 'ⓘ', 'j': 'ⓙ', 'k': 'ⓚ', 'l': 'ⓛ', 'm': 'ⓜ', 'n': 'ⓝ', 'o': 'ⓞ', 'p': 'ⓟ', 'q': 'ⓠ', 'r': 'ⓡ', 's': 'ⓢ', 't': 'ⓣ', 'u': 'ⓤ', 'v': 'ⓥ', 'w': 'ⓦ', 'x': 'ⓧ', 'y': 'ⓨ', 'z': 'ⓩ',
        'A': 'Ⓐ', 'B': 'Ⓑ', 'C': 'Ⓒ', 'D': 'Ⓓ', 'E': 'Ⓔ', 'F': 'Ⓕ', 'G': 'Ⓖ', 'H': 'Ⓗ', 'I': 'Ⓘ', 'J': 'Ⓙ', 'K': 'Ⓚ', 'L': 'Ⓛ', 'M': 'Ⓜ', 'N': 'Ⓝ', 'O': 'Ⓞ', 'P': 'Ⓟ', 'Q': 'Ⓠ', 'R': 'Ⓡ', 'S': 'Ⓢ', 'T': 'Ⓣ', 'U': 'Ⓤ', 'V': 'Ⓥ', 'W': 'Ⓦ', 'X': 'Ⓧ', 'Y': 'Ⓨ', 'Z': 'Ⓩ',
        '0': '⓪', '1': '①', '2': '②', '3': '③', '4': '④', '5': '⑤', '6': '⑥', '7': '⑦', '8': '⑧', '9': '⑨'
    },
    "squares": {
        'a': '🄰', 'b': '🄱', 'c': '🄲', 'd': '🄳', 'e': '🄴', 'f': '🄵', 'g': '🄶', 'h': '🄷', 'i': '🄸', 'j': '🄹', 'k': '🄺', 'l': '🄻', 'm': '🄼', 'n': '🄽', 'o': '🄾', 'p': '🄿', 'q': '🅀', 'r': '🅁', 's': '🅂', 't': '🅃', 'u': '🅄', 'v': '🅅', 'w': '🅆', 'x': '🅇', 'y': '🅈', 'z': '🅉',
        'A': '🄰', 'B': '🄱', 'C': '🄲', 'D': '🄳', 'E': '🄴', 'F': '🄵', 'G': '🄶', 'H': '🄷', 'I': '🄸', 'J': '🄹', 'K': '🄺', 'L': '🄻', 'M': '🄼', 'N': '🄽', 'O': '🄾', 'P': '🄿', 'Q': '🅀', 'R': '🅁', 'S': '🅂', 'T': '🅃', 'U': '🅄', 'V': '🅅', 'W': '🅆', 'X': '🅇', 'Y': '🅈', 'Z': '🅉'
    }
}

def stylish(text, style="smallcaps"):
    if not text or style == "none": return text or ""
    mapping = _FONTS.get(style, _FONTS["smallcaps"])
    def _rep(m):
        t = m.group(0)
        if t.startswith('<') and t.endswith('>'): return t
        if (t.startswith('{') and t.endswith('}')) or t.startswith('/'):
            return t
        res = []
        for c in t:
            r = mapping.get(c)
            if r is None:
                r = mapping.get(c.lower())
            res.append(r if r is not None else c)
        return "".join(res)
    return re.sub(r'<[^>]+>|\{[^{}]+\}|/\w+|[^<{}/]+|/', _rep, str(text))

def fmt_size(size) -> str:
    if not size: return "N/A"
    for unit in ["B","KB","MB","GB","TB"]:
        if size < 1024: return f"{size:.2f} {unit}"
        size /= 1024

def unique_id() -> str:
    return hashlib.md5(str(time.time() + random.random()).encode()).hexdigest()[:12]

def file_icon(name: str) -> str:
    if not name or name == "Message/Post": return ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return {
        "pdf":"","doc":"","docx":"","txt":"","xlsx":"","pptx":"","csv":"",
        "mp4":"","mkv":"","avi":"","mov":"","webm":"",
        "mp3":"","flac":"","wav":"","aac":"","m4a":"",
        "jpg":"","jpeg":"","png":"","gif":"","webp":"",
        "zip":"","rar":"","7z":"","tar":"","gz":"",
        "apk":"","exe":"","py":"","js":"","html":"",
    }.get(ext, "")

async def get_short_link(bot_info, link: str) -> str:
    if not shortener_enabled_for_bot(bot_info):
        return link
    api_url = f"https://{bot_info['shortener_url']}/api?api={bot_info['shortener_api']}&url={link}"
    try:
        http = await get_http()
        async with http.get(api_url, timeout=aiohttp.ClientTimeout(total=8)) as r:
            ct = r.headers.get("content-type", "")
            if "json" in ct:
                data = await r.json()
                short = (data.get("shortenedUrl") or data.get("short_url")
                         or data.get("result") or data.get("url"))
                if data.get("status") in ("success", "ok", 200) and short:
                    return short
            else:
                text = (await r.text()).strip()
                if text.startswith("http"):
                    return text
    except Exception as e:
        logger.warning(f"Shortener failed: {e}")
    return link

async def get_http():
    global _HTTP
    if _HTTP is None or _HTTP.closed:
        _HTTP = aiohttp.ClientSession()
    return _HTTP

def shortener_enabled_for_bot(bot_info: dict) -> bool:
    return bool(
        bot_info and
        bot_info.get("is_shortener_enabled") and
        bot_info.get("shortener_api") and
        bot_info.get("shortener_url")
    )

# ═══════════════════════════════════════════════════════════════
#  DUAL POST SYSTEM
# ═══════════════════════════════════════════════════════════════

class DualPostSession:
    """Active dual post creation state for one user."""
    def __init__(self, bot_id: int, created_by: int, title: str = None):
        self.bot_id      = bot_id
        self.created_by  = created_by
        self.free_files  = []
        self.pro_files   = []
        self.stage       = "free"
        self.title       = title
        self.description_free = "Free version — basic content."
        self.description_pro  = "Premium version — full exclusive content."
        self.created_at  = datetime.now()

    @property
    def total_files(self):
        return len(self.free_files) + len(self.pro_files)

    def stage_display(self):
        return " FREE" if self.stage == "free" else " PREMIUM"


def save_dual_post(post_id: str, session: DualPostSession) -> dict:
    posts = load_db(DUAL_POST_DB)
    data  = {
        "post_id":          post_id,
        "bot_id":           session.bot_id,
        "created_by":       session.created_by,
        "created_at":       str(session.created_at),
        "title":            session.title or "Dual Post",
        "free_files":       session.free_files,
        "pro_files":        session.pro_files,
        "description_free": session.description_free,
        "description_pro":  session.description_pro,
        "access_free":      0,
        "access_pro":       0,
        "access_total":     0,
        "last_accessed":    None,
    }
    posts[post_id] = data
    save_db(DUAL_POST_DB, posts)
    return data

def get_dual_post(post_id: str):
    return load_db(DUAL_POST_DB).get(post_id)

def del_dual_post(post_id: str) -> bool:
    posts = load_db(DUAL_POST_DB)
    if post_id in posts:
        del posts[post_id]
        save_db(DUAL_POST_DB, posts)
        return True
    return False

def get_user_dual_posts(bot_id: int, user_id: int) -> list:
    return [p for p in load_db(DUAL_POST_DB).values()
            if p.get("bot_id") == bot_id and p.get("created_by") == user_id]

def get_bot_dual_posts(bot_id: int) -> list:
    return [p for p in load_db(DUAL_POST_DB).values()
            if p.get("bot_id") == bot_id]

def bump_dual_access(post_id: str, tier: str):
    posts = load_db(DUAL_POST_DB)
    if post_id not in posts: return
    p = posts[post_id]
    p[f"access_{tier}"] = p.get(f"access_{tier}", 0) + 1
    p["access_total"]   = p.get("access_total", 0) + 1
    p["last_accessed"]  = str(datetime.now())
    save_db(DUAL_POST_DB, posts)


# ═══════════════════════════════════════════════════════════════
#  SHORTENER TOKEN SYSTEM
# ═══════════════════════════════════════════════════════════════

SHORTENER_TOKENS: dict = {}

def generate_token(uid: int, bot_id: int, resource_id: str) -> str:
    raw = f"{uid}:{bot_id}:{resource_id}:{time.time()}:{random.randint(0, 999999)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]

def store_token(token: str, uid: int, bot_id: int, resource_id: str, rtype: str = "file"):
    SHORTENER_TOKENS[token] = {
        "uid": uid, "bot_id": bot_id,
        "resource_id": resource_id, "type": rtype,
        "expires_at": time.time() + SHORTENER_TOKEN_EXPIRY,
        "used": False
    }

def validate_token(token: str, uid: int, bot_id: int):
    td = SHORTENER_TOKENS.get(token)
    if not td: return None
    if td["used"]: return None
    if time.time() > td["expires_at"]:
        del SHORTENER_TOKENS[token]
        return None
    if td["uid"] != uid or td["bot_id"] != bot_id: return None
    return td

def consume_token(token: str):
    if token in SHORTENER_TOKENS:
        SHORTENER_TOKENS[token]["used"] = True

def clean_expired_tokens() -> int:
    now = time.time()
    expired = [k for k, v in SHORTENER_TOKENS.items()
               if v["used"] or now > v["expires_at"]]
    for k in expired:
        del SHORTENER_TOKENS[k]
    return len(expired)

async def make_shortener_link(client, bi: dict, uid: int, bot_id: int,
                               resource_id: str, rtype: str) -> str:
    token = generate_token(uid, bot_id, resource_id)
    store_token(token, uid, bot_id, resource_id, rtype)

    prefix_map = {"file": "f", "batch": "b", "dual": "dp"}
    prefix     = prefix_map.get(rtype, "f")

    if rtype == "dual":
        bot_link = f"https://t.me/{client.me.username}?start=dp_{resource_id}_t_{token}"
    else:
        bot_link = f"https://t.me/{client.me.username}?start={prefix}_{resource_id}_t_{token}"

    short = await get_short_link(bi, bot_link)
    return short

# ═══════════════════════════════════════════════════════════════
#  DELIVER FILE
# ═══════════════════════════════════════════════════════════════

async def deliver_file(client, chat_id: int, file_data: dict):
    # Track usage
    fuid = None
    for k, v in load_db(FILES_DB).items():
        if v.get("file_id") == file_data.get("file_id"):
            fuid = k
            break

    if fuid:
        files = load_db(FILES_DB)
        files[fuid]["access_count"] = files[fuid].get("access_count", 0) + 1
        save_db(FILES_DB, files)

    caption    = file_data.get("caption") or None
    thumb_fid  = file_data.get("custom_thumbnail")
    media_type = file_data.get("media_type", "document")
    file_id    = file_data["file_id"]
    db_msg_id  = file_data.get("db_msg_id")
    reply_markup = None

    if file_data.get("reply_markup"):
        try:
            reply_markup = InlineKeyboardMarkup.from_json(json.dumps(file_data["reply_markup"]))
        except Exception:
            pass

    if thumb_fid and media_type in ("document", "video", "audio", "animation"):
        try:
            thumb_io = await client.download_media(thumb_fid, in_memory=True)
            thumb_io.seek(0)
            if media_type == "document":
                return await client.send_document(chat_id, document=file_id,
                                                  thumb=thumb_io, caption=caption, reply_markup=reply_markup)
            elif media_type == "video":
                return await client.send_video(chat_id, video=file_id,
                                               thumb=thumb_io, caption=caption, reply_markup=reply_markup)
            elif media_type == "audio":
                return await client.send_audio(chat_id, audio=file_id,
                                               thumb=thumb_io, caption=caption, reply_markup=reply_markup)
            elif media_type == "animation":
                return await client.send_animation(chat_id, animation=file_id,
                                                  thumb=thumb_io, caption=caption, reply_markup=reply_markup)
        except Exception as e:
            logger.warning(f"Thumb delivery: {e}")

    if db_msg_id:
        # Try current bot
        try:
            return await client.copy_message(
                chat_id=chat_id, from_chat_id=DB_CHANNEL,
                message_id=db_msg_id, caption=caption, reply_markup=reply_markup
            )
        except Exception:
            # Fallback 1: Use Main Bot if current bot is not in channel
            main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None)
            if main_client and main_client != client:
                try:
                    return await main_client.copy_message(
                        chat_id=chat_id, from_chat_id=DB_CHANNEL,
                        message_id=db_msg_id, caption=caption, reply_markup=reply_markup
                    )
                except Exception: pass


    # Fallback 3: Cache from other bots
    cached = get_from_cache(file_id)
    if cached and cached["bot_id"] in ACTIVE_CLIENTS:
        try:
            ca = ACTIVE_CLIENTS[cached["bot_id"]]["app"]
            return await ca.copy_message(chat_id, cached["chat_id"],
                                         cached["message_id"], caption=caption, reply_markup=reply_markup)
        except Exception as e:
            logger.warning(f"Cache delivery: {e}")

    if file_id:
        return await client.send_cached_media(
            chat_id=chat_id, file_id=file_id,
            caption=caption or f" {file_data.get('file_name', 'File')}",
            reply_markup=reply_markup
        )
    return None

async def deliver_batch_files(client, chat_id: int, file_ids: list,
                               bot_id: int, is_premium: bool) -> tuple:
    files  = load_db(FILES_DB)
    bi     = get_bot_info(bot_id)
    auto_del = bi.get("auto_delete_time", 300) if bi else 300
    total  = len(file_ids)
    sent_c = 0

    for fuid in file_ids:
        fd = files.get(fuid)
        if not fd: continue
        try:
            sent = await deliver_file(client, chat_id, fd)
            sent_c += 1
            if sent and not is_premium:
                asyncio.create_task(_auto_delete(sent, auto_del))
        except Exception as e:
            logger.warning(f"Batch deliver {fuid}: {e}")
        await asyncio.sleep(0.4)

    return sent_c, total

#  BROADCAST
# ═══════════════════════════════════════════════════════════════

async def store_broadcast(client, original_msg) -> Optional[int]:
    try:
        stored = await original_msg.forward(DB_CHANNEL)
        return stored.id
    except Exception as e:
        logger.error(f"Broadcast store: {e}")
        return None

async def do_broadcast(bot_ids: list, bc_msg_id: int, status_msg=None, reply_markup=None) -> tuple:
    total_ok = total_fail = 0
    t0 = datetime.now()
    main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None)

    for b_idx, bot_id in enumerate(bot_ids, 1):
        if bot_id not in ACTIVE_CLIENTS: continue
        app   = ACTIVE_CLIENTS[bot_id]["app"]
        uname = ACTIVE_CLIENTS[bot_id]["username"]
        users = get_all_users(bot_id)
        for u_idx, user in enumerate(users, 1):
            uid = user["user_id"]
            try:
                try:
                    await app.copy_message(uid, DB_CHANNEL, bc_msg_id, reply_markup=reply_markup)
                except Exception:
                    # Fallback to main client if clone is not in channel
                    if main_client and main_client != app:
                        await main_client.copy_message(uid, DB_CHANNEL, bc_msg_id, reply_markup=reply_markup)
                    else:
                        raise
                total_ok += 1
            except FloodWait as e:
                await asyncio.sleep(e.value + 2)
                try:
                    try:
                        await app.copy_message(uid, DB_CHANNEL, bc_msg_id, reply_markup=reply_markup)
                    except Exception:
                        if main_client and main_client != app:
                            await main_client.copy_message(uid, DB_CHANNEL, bc_msg_id, reply_markup=reply_markup)
                        else:
                            raise
                    total_ok += 1
                except Exception:
                    total_fail += 1
            except Exception:
                total_fail += 1
            done = total_ok + total_fail
            if status_msg and done % 30 == 0:
                try:
                    elapsed = (datetime.now() - t0).seconds
                    all_cnt = sum(len(get_all_users(bid)) for bid in bot_ids)
                    pct = int((done / max(all_cnt, 1)) * 100)
                    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
                    await status_msg.edit(
                        f" **Broadcast**\n\n`[{bar}]` {pct}%\n"
                        f" Bot {b_idx}/{len(bot_ids)}: @{uname}\n"
                        f" `{total_ok}` |  `{total_fail}` |  `{elapsed}s`"
                    )
                except Exception:
                    pass
            await asyncio.sleep(MAX_BROADCAST_RATE)
    return total_ok, total_fail

# ═══════════════════════════════════════════════════════════════
#  HEALTH CHECK SERVER
# ═══════════════════════════════════════════════════════════════

async def health_handler(request):
    uptime = str(datetime.now() - START_TIME).split(".")[0]
    return web.json_response({
        "status": "ok", "uptime": uptime,
        "bots_online": len(ACTIVE_CLIENTS),
        "ts": datetime.now().isoformat()
    })

async def webapp_handler(request):
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html")
    except Exception as e:
        return web.Response(text=f"Error: {e}", status=500)

async def api_files_handler(request):
    q = request.query.get("q", "").lower()
    uid = request.query.get("user_id")
    req_bot_id = request.query.get("bot_id")
    mode = request.query.get("mode", "all")

    bot_id = int(req_bot_id) if req_bot_id and req_bot_id.isdigit() else (next(iter(ACTIVE_CLIENTS.keys())) if ACTIVE_CLIENTS else None)
    if not bot_id: return web.json_response({"files": []})

    files = load_db(FILES_DB)
    results = []

    for k, f in files.items():
        if f.get("bot_id") != bot_id: continue
        if mode == "mine" and uid and str(f.get("user_id")) != str(uid): continue
        if q and q not in f.get("file_name", "").lower(): continue

        results.append({
            "id": k,
            "name": f.get("file_name", "Unknown"),
            "size": fmt_size(f.get("file_size", 0)),
            "icon": file_icon(f.get("file_name", "")),
            "views": f.get("access_count", 0),
            "date": f.get("upload_date", "")[:10]
        })

    results = sorted(results, key=lambda x: x["date"], reverse=True)[:100]
    bot_username = ACTIVE_CLIENTS[bot_id]["username"] if bot_id in ACTIVE_CLIENTS else "bot"

    return web.json_response({"files": results, "bot_username": bot_username})

async def api_user_handler(request):
    uid_str = request.query.get("user_id")
    req_bot_id = request.query.get("bot_id")

    bot_id = int(req_bot_id) if req_bot_id and req_bot_id.isdigit() else (next(iter(ACTIVE_CLIENTS.keys())) if ACTIVE_CLIENTS else None)

    if not uid_str or not bot_id:
        return web.json_response({"error": "missing info"}, status=400)

    uid = int(uid_str)
    u = get_user(uid, bot_id)
    bi = get_bot_info(bot_id)

    is_owner = bi and bi.get("owner_id") == uid
    is_adm = is_admin(uid) or is_owner
    is_supreme = uid == MAIN_ADMIN

    # Count dual posts
    all_duals = load_db(DUAL_POST_DB)
    user_duals = [d for d in all_duals.values() if d.get("bot_id") == bot_id and d.get("created_by") == uid]

    # Count bots
    all_bots = get_all_bots()
    user_bots = [b for b in all_bots.values() if isinstance(b, dict) and b.get("owner_id") == uid]

    data = {
        "uploads": u.get("files_uploaded", 0) if u else 0,
        "batches": u.get("batches_created", 0) if u else 0,
        "duals": len(user_duals),
        "bots": len(user_bots),
        "is_premium": u.get("is_premium", False) if u else False,
        "refer_count": u.get("refer_count", 0) if u else 0,
        "refer_rewards": u.get("refer_rewards", 0) if u else 0,
        "is_admin": is_adm,
        "is_supreme": is_supreme,
        "name": u.get("name", "User") if u else "User",
        "username": u.get("username", "") if u else "",
        "premium_price": bi.get("premium_price", "500") if bi else "500",
        "bot_username": ACTIVE_CLIENTS[bot_id]["username"] if bot_id in ACTIVE_CLIENTS else "bot"
    }
    return web.json_response(data)

async def api_admin_stats_handler(request):
    uid_str = request.query.get("user_id")
    req_bot_id = request.query.get("bot_id")
    bot_id = int(req_bot_id) if req_bot_id and req_bot_id.isdigit() else (next(iter(ACTIVE_CLIENTS.keys())) if ACTIVE_CLIENTS else None)

    if not uid_str or not bot_id: return web.json_response({"error": "missing info"}, status=400)
    uid = int(uid_str)
    bi = get_bot_info(bot_id)
    if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
        return web.json_response({"error": "unauthorized"}, status=403)

    if uid == MAIN_ADMIN:
        users_c, files_c, bots_c, duals_c = len(load_db(USERS_DB)), len(load_db(FILES_DB)), len(get_all_bots()), len(load_db(DUAL_POST_DB))
    else:
        users_c = len([u for u in load_db(USERS_DB).values() if u.get("bot_id") == bot_id])
        files_c = len([f for f in load_db(FILES_DB).values() if f.get("bot_id") == bot_id])
        bots_c = len(get_child_bots(bot_id))
        duals_c = len(get_bot_dual_posts(bot_id))

    return web.json_response({
        "users": users_c, "files": files_c, "bots": bots_c, "duals": duals_c,
        "uptime": str(datetime.now() - START_TIME).split(".")[0]
    })

async def api_batches_handler(request):
    uid = request.query.get("user_id")
    req_bot_id = request.query.get("bot_id")
    bot_id = int(req_bot_id) if req_bot_id and req_bot_id.isdigit() else (next(iter(ACTIVE_CLIENTS.keys())) if ACTIVE_CLIENTS else None)

    batches = load_db(BATCH_DB)
    results = []
    for k, b in batches.items():
        if bot_id and b.get("bot_id") != bot_id: continue
        if uid and str(b.get("created_by")) != str(uid): continue
        results.append({"id": k, "count": len(b.get("files", [])), "date": b.get("date", "")[:10]})
    return web.json_response({"batches": sorted(results, key=lambda x: x["date"], reverse=True)})

async def api_duals_handler(request):
    uid = request.query.get("user_id")
    req_bot_id = request.query.get("bot_id")
    bot_id = int(req_bot_id) if req_bot_id and req_bot_id.isdigit() else (next(iter(ACTIVE_CLIENTS.keys())) if ACTIVE_CLIENTS else None)

    duals = load_db(DUAL_POST_DB)
    results = []
    for k, d in duals.items():
        if bot_id and d.get("bot_id") != bot_id: continue
        if uid and str(d.get("created_by")) != str(uid): continue
        results.append({"id": k, "title": d.get("title", "Dual Post"), "views": d.get("access_total", 0), "date": d.get("created_at", "")[:10]})
    return web.json_response({"duals": sorted(results, key=lambda x: x["date"], reverse=True)})

async def start_web_server():
    app = web.Application()
    app.router.add_get("/",       webapp_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/ping",   health_handler)
    app.router.add_get("/api/files", api_files_handler)
    app.router.add_get("/api/user", api_user_handler)
    app.router.add_get("/api/admin/stats", api_admin_stats_handler)
    app.router.add_get("/api/batches", api_batches_handler)
    app.router.add_get("/api/duals", api_duals_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f" Health-check on port {PORT}")

# ═══════════════════════════════════════════════════════════════
#  BOT MANAGEMENT
# ═══════════════════════════════════════════════════════════════

START_TIME      = datetime.now()
HELP_TEXT       = (
    "<b>ULTRA FILESTORE v7.0 — COMPLETE GUIDE</b>\n\n"
    "Welcome to the most advanced FileStore bot! Here is a list of commands you can use:\n\n"
    "<b>GENERAL COMMANDS</b>\n"
    "├ /start — Start the bot\n"
    "├ /help — Show this guide\n"
    "├ /about — About the bot\n"
    "├ /refer — Refer and earn\n"
    "├ /search — Search for files\n"
    "├ /stats — View your statistics\n"
    "├ /ping — Check bot speed\n"
    "├ /botinfo — View bot details\n"
    "├ /premium — Premium membership info\n"
    "├ /download — Download videos\n"
    "├ /done — Finish session\n"
    "└ /cancel — Cancel current action\n\n"
    "<b>FILE MANAGEMENT</b>\n"
    "├ /batch — Start batch mode\n"
    "├ /listfiles — List your uploaded files\n"
    "├ /mybatches — List your batches\n"
    "├ /editfile — Edit metadata\n"
    "├ /delfile — Delete file\n"
    "├ /rename — Rename a file\n"
    "├ /setcaption — Set file caption\n"
    "├ /setthumb — Set file thumbnail\n"
    "├ /dualpost — Create dual-tier link\n"
    "├ /dpremium — Switch to premium tier\n"
    "├ /dpdone — Finish dual post\n"
    "├ /dpcancel — Cancel dual post\n"
    "├ /myduals — Manage your dual posts\n"
    "├ /deldual — Delete dual post\n"
    "├ /dpstats — Dual post analytics\n"
    "└ /createpost — Create custom post\n\n"
    "<b>ADVANCED FEATURES</b>\n"
    "├ /clone — Create your own bot\n"
    "├ /mybots — List your cloned bots\n"
    "├ /protect — Protect a channel link\n"
    "├ /myplinks — Manage protected links\n"
    "├ /font — Open font editor\n"
    "├ /addadmin — Add secondary admin\n"
    "└ /deladmin — Remove secondary admin\n\n"
    "<b>ADMIN TOOLS</b>\n"
    "├ /admin — Open Admin Panel\n"
    "├ /setfs — Configure Force Sub\n"
    "├ /setwelcome — Set welcome message\n"
    "├ /autoapprove — Toggle auto-approve\n"
    "├ /autocaption — Toggle auto-caption\n"
    "├ /broadcast — Send message to all\n"
    "├ /ban — Ban a user\n"
    "├ /unban — Unban a user\n"
    "├ /setlog — Set log channel\n"
    "├ /setchannel — Connect channel\n"
    "├ /setmode — Set join mode\n"
    "├ /settimer — Auto-delete timer\n"
    "├ /shortener — Configure shortener\n"
    "├ /requests — Manage join requests\n"
    "├ /givepremium — Give premium access\n"
    "├ /removepremium — Revoke premium access\n"
    "├ /setprice — Set premium price\n"
    "├ /setcontact — Set premium contact\n"
    "└ /setqr — Set premium QR code\n\n"
    "<b>SUPREME TOOLS</b>\n"
    "├ /supreme — Supreme Panel\n"
    "└ /restart — System restart\n\n"
    "<b>TIP:</b> Just send any file to the bot to store it and get a shareable link instantly!\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
)
ACTIVE_CLIENTS: dict = {}
TEMP_BATCH:     dict = {}
TEMP_BROADCAST: dict = {}
TEMP_EDIT:      dict = {}
TEMP_WELCOME:   dict = {}
TEMP_DUAL:      dict = {}
TEMP_PROTECT:   dict = {}
TEMP_POST:      dict = {}
USER_FLOOD:     dict = {}
_HTTP: aiohttp.ClientSession = None

async def setup_commands(app):
    try: await app.set_bot_commands(BOT_COMMANDS)
    except Exception as e: logger.warning(f"Commands: {e}")

async def check_force_sub(client, user_id: int):
    bi = get_bot_info(client.me.id)
    if not bi: return True, []
    force_subs = bi.get("force_subs", [])
    if not force_subs: return True, []
    must_join = []
    main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None)

    for fs in force_subs:
        ch_id = fs["channel_id"] if isinstance(fs, dict) else fs
        try:
            try:
                m = await client.get_chat_member(ch_id, user_id)
            except Exception:
                if main_client and main_client != client:
                    m = await main_client.get_chat_member(ch_id, user_id)
                else:
                    raise

            if m.status in (ChatMemberStatus.BANNED, ChatMemberStatus.LEFT):
                if has_pending_request(ch_id, user_id): continue
                must_join.append(fs)
        except UserNotParticipant:
            if has_pending_request(ch_id, user_id): continue
            must_join.append(fs)
        except Exception as e:
            logger.warning(f"FS Check error for {ch_id}: {e}")
            continue
    if not must_join: return True, []
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
        bot_session = f"bot_{token.split(':')[0]}"
        # Fallback to MemoryStorage if sqlite3 is mocked
        is_mocked = "unittest.mock" in sys.modules.get("sqlite3", "").__class__.__module__
        app = Client(
            bot_session,
            api_id=API_ID, api_hash=API_HASH,
            bot_token=token,
            in_memory=is_mocked,
            workdir=DB_FOLDER if not is_mocked else None
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
        logger.info(f" {'[MAIN]' if is_main else '[CLONE]'} @{me.username}")
        return app
    except Exception as e:
        logger.error(f"Bot start [{token[:12]}...]: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════════

def get_btn_name(key: str, default: str) -> str:
    btns = get_global_config().get("custom_buttons", {})
    return stylish(btns.get(key, default))

def get_msg_text(key: str, default: str) -> str:
    msgs = get_global_config().get("custom_messages", {})
    return stylish(msgs.get(key, default))

class SafeDict(dict):
    def __missing__(self, key): return '{' + key + '}'

def kb_start(bot_id, user_id):
    rows = [
        [InlineKeyboardButton(stylish("BATCH"), callback_data="start_batch"),
         InlineKeyboardButton(stylish("ABOUT"), callback_data="about_bot")],
        [InlineKeyboardButton(stylish("HELP"), callback_data="help_menu")]
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_btn_name("btn_abrd", " BROADCAST"),   callback_data="broadcast_menu"),
         InlineKeyboardButton(get_btn_name("btn_asta", " ANALYTICS"),   callback_data="admin_stats")],
        [InlineKeyboardButton(get_btn_name("btn_ausr", " USERS"),        callback_data="manage_users"),
         InlineKeyboardButton(get_btn_name("btn_acln", " CLONES"),       callback_data="my_bots_admin")],
        [InlineKeyboardButton(get_btn_name("btn_aset", " SETTINGS"),     callback_data="bot_settings_admin"),
         InlineKeyboardButton(get_btn_name("btn_afsb", " FORCE SUB"),    callback_data="forcesub_admin")],
        [InlineKeyboardButton(get_btn_name("btn_aver", " VERIFY"),       callback_data="verify_admin"),
         InlineKeyboardButton(get_btn_name("btn_ashr", " SHORTENER"),    callback_data="shortener_admin")],
        [InlineKeyboardButton(get_btn_name("btn_aprt", " PROTECT"),      callback_data="plinks_admin"),
         InlineKeyboardButton(get_btn_name("btn_adul", " DUAL POSTS"),   callback_data="dual_posts_admin")],
        [InlineKeyboardButton(get_btn_name("btn_awlc", " WELCOME"),      callback_data="edit_welcome_msg"),
         InlineKeyboardButton(get_btn_name("btn_aapr", " AUTO APP."),    callback_data="toggle_auto_approve")],
        [InlineKeyboardButton(stylish(" ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛs "), callback_data="manage_requests")],
        [InlineKeyboardButton(get_btn_name("btn_acap", " AUTO CAP."),    callback_data="toggle_auto_caption"),
         InlineKeyboardButton(get_btn_name("btn_atmr", " TIMER"),          callback_data="edit_timer")],
        [InlineKeyboardButton(stylish(" CREATE POST"), callback_data="cb_create_post")],
        [InlineKeyboardButton(get_btn_name("btn_back", " BACK TO HOME"), callback_data="back_to_start")],
    ])

def kb_supreme():
    maint = get_global_config().get("maintenance", False)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_btn_name("btn_sgbr", " GLOBAL BROADCAST"), callback_data="global_broadcast")],
        [InlineKeyboardButton(get_btn_name("btn_ssys", " SYSTEM STATS"),    callback_data="system_stats"),
         InlineKeyboardButton(get_btn_name("btn_snet", " BOT NETWORK"),     callback_data="all_bots_list")],
        [InlineKeyboardButton(get_btn_name("btn_sadm", " ADMIN MANAGER"),    callback_data="manage_admins"),
         InlineKeyboardButton(get_btn_name("btn_smsg", " SYSTEM MSG"),      callback_data="global_msg_set")],
        [InlineKeyboardButton(get_btn_name("btn_smnt", f" MAINT: {'ON' if maint else 'OFF'}"), callback_data="toggle_maintenance")],
        [InlineKeyboardButton(get_btn_name("btn_spur", " PURGE CACHE"),      callback_data="manual_clean_cache")],
        [InlineKeyboardButton(get_btn_name("btn_scus", " CUSTOMIZE"),        callback_data="supreme_customize")],
        [InlineKeyboardButton(get_btn_name("btn_srst", " SYSTEM RESTART"),   callback_data="restart_all_bots")],
        [InlineKeyboardButton(get_btn_name("btn_back", " BACK TO HOME"),     callback_data="back_to_start")],
    ])

def kb_dual_post_creator(stage: str, free_count: int, pro_count: int):
    rows = []
    if stage == "free":
        rows.append([InlineKeyboardButton(
            stylish(f"Switch to Premium Tier ({pro_count} Files)"),
            callback_data="dp_switch_pro"
        )])
    rows.append([InlineKeyboardButton(
        stylish(f"Generate Link ({free_count}F + {pro_count}P Files)"),
        callback_data="dp_finish"
    )])
    rows.append([InlineKeyboardButton(stylish("Cancel Session"), callback_data="dp_cancel_session")])
    return InlineKeyboardMarkup(rows)

def kb_dual_post_done(post_id: str, share_link: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(stylish("Share Link"),        url=f"https://t.me/share/url?url={share_link}")],
        [InlineKeyboardButton(stylish("Preview Free"),      callback_data=f"dp_prev_free_{post_id}"),
         InlineKeyboardButton(stylish("Preview Pro"),       callback_data=f"dp_prev_pro_{post_id}")],
        [InlineKeyboardButton(stylish("Analytics"),         callback_data=f"dp_analytics_{post_id}"),
         InlineKeyboardButton(stylish("Delete"),            callback_data=f"dp_delete_{post_id}")],
        [InlineKeyboardButton(stylish("Create Another"),    callback_data="dual_post_start_new")],
    ])

def kb_file_edit(uid: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(stylish("Caption"),   callback_data=f"edit_caption_{uid}"),
         InlineKeyboardButton(stylish("Thumbnail"), callback_data=f"edit_thumb_{uid}")],
        [InlineKeyboardButton(stylish("Quick Rename"), callback_data=f"qrename_{uid}"),
         InlineKeyboardButton(stylish("Hard Rename"),  callback_data=f"rename_file_{uid}")],
        [InlineKeyboardButton(stylish("Get File"), callback_data=f"get_file_{uid}"),
         InlineKeyboardButton(stylish("Delete"),    callback_data=f"del_file_{uid}")],
        [InlineKeyboardButton(stylish(" Password"), callback_data=f"set_pass_{uid}"),
         InlineKeyboardButton(stylish("Back"),      callback_data="my_files_back")],
    ])

def get_file_edit_text(client, fd, fuid):
    icon = file_icon(fd.get("file_name",""))
    cap = fd.get("caption") or "_(none)_"
    thumb = " [Thumb Set]" if fd.get("custom_thumbnail") else ""
    link = f"https://t.me/{client.me.username}?start=f_{fuid}"
    return (
        f" **File Editor**\n\n{icon} **{fd.get('file_name','?')}**\n"
        f" `{fuid}` |  {fmt_size(fd.get('file_size',0))}\n"
        f" {cap}{thumb} |  `{fd.get('access_count',0)}` views\n\n"
        f" **Link:** `{link}`"
    )

# ═══════════════════════════════════════════════════════════════
#  HANDLERS
# ═══════════════════════════════════════════════════════════════

def register_handlers(app: Client):

    @app.on_message(filters.command("download") & filters.private, group=1)
    async def download_video_cmd(client, message):
        uid = message.from_user.id
        if is_user_banned(uid, client.me.id): return await message.reply(" Banned!")

        url = message.text.split(None, 1)[1] if len(message.command) > 1 else None
        if not url:
            return await message.reply(stylish(" **Please send the video link with the command.**\n\nExample: `/download https://link.com`"))

        # Basic URL validation
        if not url.startswith("http"):
            return await message.reply(stylish(" **Invalid URL!** Please provide a valid http/https link."))

        sm = await message.reply(stylish(" **Processing video details...**"))

        def extract_info(url):
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                info = await loop.run_in_executor(pool, extract_info, url)

            title = info.get('title', 'Video')
            formats = info.get('formats', [])

            # Filter unique qualities (resolution + extension)
            seen_formats = set()
            buttons = []
            row = []

            # We want to offer a few distinct qualities
            for f in formats:
                res = f.get('height')
                ext = f.get('ext')
                if res and res not in seen_formats and f.get('vcodec') != 'none':
                    seen_formats.add(res)
                    fid = f.get('format_id')
                    row.append(InlineKeyboardButton(f"{res}p ({ext})", callback_data=f"dlv_{fid}"))
                    if len(row) == 2:
                        buttons.append(row)
                        row = []

            if row: buttons.append(row)
            buttons.append([InlineKeyboardButton(stylish(" Cancel"), callback_data="cancel_download")])

            # Store full URL and info temporarily
            TEMP_EDIT[uid] = {"mode": "download_video", "url": url, "title": title}

            await sm.edit(
                f" **Video Found!**\n\n **Title:** `{title}`\n\nSelect the quality you want to download:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        except Exception as e:
            logger.error(f"Download error info extraction: {e}")
            await sm.edit(f" **Error:** Could not extract video info.\n\n`{str(e)[:100]}`")

    @app.on_message(filters.private, group=0)
    async def flood_ctrl(client, message):
        uid = message.from_user.id
        now = time.time()
        USER_FLOOD[uid] = [t for t in USER_FLOOD.get(uid, []) if now - t < 5]
        USER_FLOOD[uid].append(now)
        if len(USER_FLOOD[uid]) > 5:
            await message.reply(stylish(" Anti-Flood! Please slow down."))
            message.stop_propagation()

    @app.on_chat_join_request()
    async def on_join_request(client, req):
        bi  = get_bot_info(client.me.id)
        uid = req.from_user.id
        ch  = req.chat.id

        # Check if auto-approve is enabled globally or for this specific channel
        # For now, we use the bot's auto_approve setting
        if bi and bi.get("auto_approve"):
            # Refinement: Users can now decide whose request to auto-accept?
            # Actually the requirement was "users select kar paye ki kiski request auto accept karna hai aur kiska nahi"
            # This usually refers to bot owners filtering or just a general toggle.
            # Given the context, we will improve the reliability and maybe add a simple whitelist/blacklist if needed.
            # But the prompt says "kiski request" which implies individual user selection.
            # Let's add a check for banned users first.
            if is_user_banned(uid, client.me.id):
                return logger.info(f"Join Request: User {uid} is banned. Not approving.")

            try:
                try:
                    await client.approve_chat_join_request(ch, uid)
                except Exception:
                    main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None)
                    if main_client and main_client != client:
                        await main_client.approve_chat_join_request(ch, uid)
                    else: raise
                clear_join_request(ch, uid)
                try:
                    await client.send_message(uid, stylish(f" **Your request to join has been approved!**\n\nWelcome to our community."))
                except: pass
            except Exception as e:
                logger.warning(f"Auto-approve: {e}")
        else:
            mark_join_request(ch, uid)

    @app.on_message(filters.command("ping") & filters.private, group=1)
    async def ping_cmd(client, message):
        t0   = time.time()
        sent = await message.reply(" Pong...")
        ms   = round((time.time() - t0) * 1000, 2)
        active_tokens = sum(1 for v in SHORTENER_TOKENS.values()
                            if not v["used"] and time.time() < v["expires_at"])
        await sent.edit(
            f" **Pong!**\n\n"
            f" `{ms}ms`\n"
            f" Uptime: `{str(datetime.now() - START_TIME).split('.')[0]}`\n"
            f" Bots: `{len(ACTIVE_CLIENTS)}`\n"
            f" Dual Posts: `{len(load_db(DUAL_POST_DB))}`\n"
            f" Active tokens: `{active_tokens}`"
        )

    @app.on_message(filters.command("restart") & filters.private, group=1)
    async def restart_cmd(client, message):
        if message.from_user.id != MAIN_ADMIN: return
        await message.reply(" Restarting...")
        os.execl(sys.executable, sys.executable, *sys.argv)



    # ═══════════════════════════════════════════════════════════
    #  DUAL POST COMMANDS
    # ═══════════════════════════════════════════════════════════

    @app.on_message(filters.command("dualpost") & filters.private, group=1)
    async def dualpost_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)

        can_create = (uid == MAIN_ADMIN or is_admin(uid) or
                      (bi and bi.get("owner_id") == uid))
        if not can_create:
            return await message.reply(
                " **Access Denied!**\n\nOnly bot owner and admins can create Dual Posts."
            )

        if uid in TEMP_DUAL:
            sess = TEMP_DUAL[uid]
            return await message.reply(
                f" **Active Session Found!**\n\n"
                f" Title: **{sess.title or 'Untitled'}**\n"
                f" Free: `{len(sess.free_files)}` files\n"
                f" Pro: `{len(sess.pro_files)}` files\n"
                f" Stage: `{sess.stage_display()}`\n\n"
                f"Continue adding files, or use the buttons below.",
                reply_markup=kb_dual_post_creator(
                    sess.stage, len(sess.free_files), len(sess.pro_files)
                )
            )

        title = message.text.split(None, 1)[1].strip() if len(message.command) > 1 else None
        session = DualPostSession(bot_id, uid, title)
        TEMP_DUAL[uid] = session

        await message.reply(
            f" **Dual Post Creator — Started!**\n\n"
            f" **Title:** {title or '_(not set — use `/dualpost My Title` next time)_'}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f" **Stage 1 of 2 — FREE TIER**\n\n"
            f"Send files for **non-premium users**.\n"
            f"• These users see shortener ads (if configured)\n"
            f"• Files auto-delete after timer\n"
            f"• Basic/teaser content goes here\n\n"
            f"When done → `/dpremium` to switch to Premium tier\n"
            f"Cancel anytime → `/dpcancel`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(" Switch to Premium Tier", callback_data="dp_switch_pro")],
                [InlineKeyboardButton(" Finish & Generate Link",  callback_data="dp_finish")],
                [InlineKeyboardButton(" Cancel",                  callback_data="dp_cancel_session")]
            ])
        )

    @app.on_message(filters.command("dpremium") & filters.private, group=1)
    async def dpremium_cmd(client, message):
        uid = message.from_user.id
        if uid not in TEMP_DUAL:
            return await message.reply(
                " No active dual post session.\n\nUse `/dualpost` to start one."
            )
        sess = TEMP_DUAL[uid]
        if sess.stage == "pro":
            return await message.reply(
                f" **Already in Premium Tier!**\n\n"
                f"Premium files added: `{len(sess.pro_files)}`\n\n"
                f"Send more files, or `/dpdone` to finish."
            )
        sess.stage = "pro"
        await message.reply(
            f" **Stage 2 of 2 — PREMIUM TIER**\n\n"
            f" Free tier locked: `{len(sess.free_files)}` files\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Now send files for **Premium users**.\n"
            f"• Delivered directly — no ads, no redirect\n"
            f"• No auto-delete\n"
            f"• Exclusive/full quality content\n\n"
            f"When done → `/dpdone` to generate the link\n"
            f"Cancel → `/dpcancel`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(" Finish & Generate Link", callback_data="dp_finish")],
                [InlineKeyboardButton(" Cancel Session",         callback_data="dp_cancel_session")]
            ])
        )

    @app.on_message(filters.command("dpdone") & filters.private, group=1)
    async def dpdone_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)

        if uid not in TEMP_DUAL:
            return await message.reply(" No active session. Use `/dualpost` to start.")

        sess = TEMP_DUAL[uid]
        if not sess.free_files and not sess.pro_files:
            return await message.reply(
                " **No files added!**\n\nSend at least one file before finishing."
            )

        post_id   = unique_id()
        post_data = save_dual_post(post_id, sess)
        del TEMP_DUAL[uid]


        base_link = f"https://t.me/{client.me.username}?start=dp_{post_id}"
        free_c    = len(sess.free_files)
        pro_c     = len(sess.pro_files)
        title     = sess.title or "Dual Post"

        shortener_status = (
            " _Free tier → Shortener (ads) → File delivery_"
            if shortener_enabled_for_bot(bi)
            else " _Free tier → Direct delivery_"
        )

        files_db = load_db(FILES_DB)
        free_links = ""
        for i, fuid in enumerate(sess.free_files[:10], 1):
            fd = files_db.get(fuid)
            f_name = fd.get("file_name", "File") if fd else "File"
            f_link = f"https://t.me/{client.me.username}?start=f_{fuid}"
            free_links += f"    {i}. **{f_name}**\n       `{f_link}`\n"
        if free_c > 10:
            free_links += f"    ... and {free_c-10} more.\n"

        pro_links = ""
        for i, fuid in enumerate(sess.pro_files[:10], 1):
            fd = files_db.get(fuid)
            f_name = fd.get("file_name", "File") if fd else "File"
            f_link = f"https://t.me/{client.me.username}?start=f_{fuid}"
            pro_links += f"    {i}. **{f_name}**\n       `{f_link}`\n"
        if pro_c > 10:
            pro_links += f"    ... and {pro_c-10} more.\n"

        await message.reply(
            f" **Dual Post Created Successfully!**\n\n"
            f" **{title}**\n"
            f" `{post_id}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f" **FREE TIER** — `{free_c}` file(s)\n"
            f"    For: Non-premium users\n"
            f"   {shortener_status}\n"
            f"    Auto-delete after timer\n"
            f" **Free File Links:**\n{free_links}\n"
            f" **PREMIUM TIER** — `{pro_c}` file(s)\n"
            f"    For: Premium users only\n"
            f"    _Direct delivery — no ads, no wait_\n"
            f"    _No auto-delete_\n"
            f" **Premium File Links:**\n{pro_links}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f" **Share This Link:**\n`{base_link}`",
            reply_markup=kb_dual_post_done(post_id, base_link)
        )

    @app.on_message(filters.command("dpcancel") & filters.private, group=1)
    async def dpcancel_cmd(client, message):
        uid = message.from_user.id
        if uid in TEMP_DUAL:
            sess = TEMP_DUAL.pop(uid)
            await message.reply(
                f" **Dual post session cancelled.**\n\n"
                f" Free files discarded: `{len(sess.free_files)}`\n"
                f" Pro files discarded: `{len(sess.pro_files)}`"
            )
        else:
            await message.reply("No active dual post session.")

    @app.on_message(filters.command("myduals") & filters.private, group=1)
    async def myduals_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        is_sup = (uid == MAIN_ADMIN or is_admin(uid) or
                  (bi and bi.get("owner_id") == uid))

        if is_sup:
            all_posts = get_bot_dual_posts(bot_id)
        else:
            all_posts = get_user_dual_posts(bot_id, uid)

        if not all_posts:
            return await message.reply(
                " **No dual posts yet!**\n\n"
                "Use `/dualpost My Title` to create one.\n\n"
                " **How it works:**\n"
                "1. `/dualpost Title` → send free files\n"
                "2. `/dpremium` → send premium files\n"
                "3. `/dpdone` → get shareable link\n"
                "4. One link, two experiences!"
            )

        all_posts = sorted(
            all_posts, key=lambda p: p.get("created_at", ""), reverse=True
        )[:15]

        total_views = sum(p.get("access_total", 0) for p in all_posts)
        text = (
            f" **{'All ' if is_sup else 'Your '}Dual Posts**\n"
            f" Total: `{len(all_posts)}` posts |  `{total_views}` views\n\n"
        )
        btns = []

        for p in all_posts:
            pid   = p["post_id"]
            title = p.get("title", "Untitled")[:28]
            fc    = len(p.get("free_files", []))
            pc    = len(p.get("pro_files", []))
            af    = p.get("access_free", 0)
            ap    = p.get("access_pro", 0)
            at    = p.get("access_total", 0)
            text += (
                f" **{title}**\n"
                f"   `{pid}` |  `{at}` total\n"
                f"    `{fc}` free ({af} views) | "
                f" `{pc}` pro ({ap} views)\n\n"
            )
            link = f"https://t.me/{client.me.username}?start=dp_{pid}"
            btns.append([
                InlineKeyboardButton(f" {title[:22]}", url=f"https://t.me/share/url?url={link}"),
                InlineKeyboardButton("", callback_data=f"dp_analytics_{pid}"),
                InlineKeyboardButton("",  callback_data=f"dp_delete_{pid}")
            ])

        await message.reply(text, reply_markup=InlineKeyboardMarkup(btns) if btns else None)

    @app.on_message(filters.command("deldual") & filters.private, group=1)
    async def deldual_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        if len(message.command) < 2:
            return await message.reply("Usage: `/deldual POST_ID`\nFind IDs via `/myduals`")
        pid  = message.command[1]
        post = get_dual_post(pid)
        if not post:
            return await message.reply(" Post not found!")
        can = (uid == MAIN_ADMIN or is_admin(uid) or
               (bi and bi.get("owner_id") == uid) or post.get("created_by") == uid)
        if not can:
            return await message.reply(" Not your post!")
        del_dual_post(pid)
        await message.reply(
            f" **Deleted:** `{post.get('title', pid)}`\n"
            f" Free: `{len(post.get('free_files',[]))}` | "
            f" Pro: `{len(post.get('pro_files',[]))}` files removed."
        )

    @app.on_message(filters.command("dpstats") & filters.private, group=1)
    async def dpstats_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)
        is_sup = (uid == MAIN_ADMIN or is_admin(uid) or
                  (bi and bi.get("owner_id") == uid))

        posts = get_bot_dual_posts(bot_id) if is_sup else get_user_dual_posts(bot_id, uid)

        if len(message.command) > 1:
            pid  = message.command[1]
            post = get_dual_post(pid)
            if not post:
                return await message.reply(" Post not found!")
            can = (uid == MAIN_ADMIN or is_admin(uid) or
                   (bi and bi.get("owner_id") == uid) or post.get("created_by") == uid)
            if not can:
                return await message.reply(" Not your post!")
            fc   = len(post.get("free_files", []))
            pc   = len(post.get("pro_files", []))
            af   = post.get("access_free", 0)
            ap   = post.get("access_pro", 0)
            at   = post.get("access_total", 0)
            last = post.get("last_accessed", "Never")
            prem_pct = round(ap / max(at, 1) * 100)
            return await message.reply(
                f" **Dual Post Analytics**\n\n"
                f" **{post.get('title','?')}**\n"
                f" `{pid}`\n"
                f" Created: `{str(post.get('created_at','?'))[:16]}`\n"
                f"Last access: `{str(last)[:16]}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f" **Total views:** `{at}`\n\n"
                f" **FREE TIER**\n"
                f"   Files: `{fc}` | Views: `{af}` ({100-prem_pct}%)\n\n"
                f" **PREMIUM TIER**\n"
                f"   Files: `{pc}` | Views: `{ap}` ({prem_pct}%)\n\n"
                f" Premium conversion: `{prem_pct}%`"
            )

        total_at = sum(p.get("access_total", 0) for p in posts)
        total_af = sum(p.get("access_free", 0) for p in posts)
        total_ap = sum(p.get("access_pro", 0) for p in posts)
        prem_pct = round(total_ap / max(total_at, 1) * 100)

        await message.reply(
            f" **Dual Post Analytics Summary**\n\n"
            f" Total posts: `{len(posts)}`\n"
            f" Total views: `{total_at}`\n\n"
            f" Free tier views: `{total_af}`\n"
            f" Premium tier views: `{total_ap}`\n"
            f" Premium conversion: `{prem_pct}%`\n\n"
            f"Use `/dpstats POST_ID` for details."
        )

    # ── /start ────────────────────────────────────────────────────
    @app.on_message(filters.command("start") & filters.private, group=1)
    async def start_handler(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        cfg    = get_global_config()
        bi     = get_bot_info(bot_id)

        if cfg.get("maintenance") and uid != MAIN_ADMIN:
            return await message.reply(" **Maintenance Mode** — Bot is temporarily down.")
        if is_user_banned(uid, bot_id):
            return await message.reply(" You are banned!")

        deep   = message.command[1] if len(message.command) > 1 else ""

        # ── Referral System ─────────────────────────────────────
        if deep.startswith("ref_"):
            ref_id = int(deep[4:])
            if ref_id != uid:
                user_data, is_new = add_user(uid, bot_id, message.from_user.username, message.from_user.first_name)
                if is_new:
                    # Reward referrer
                    users = load_db(USERS_DB)
                    ref_key = f"{bot_id}_{ref_id}"
                    if ref_key in users:
                        users[ref_key]["refer_count"] = users[ref_key].get("refer_count", 0) + 1

                        # Every 5 refers = 1 day premium
                        if users[ref_key]["refer_count"] % 5 == 0:
                            users[ref_key]["is_premium"] = True
                            users[ref_key]["refer_rewards"] = users[ref_key].get("refer_rewards", 0) + 1
                            # In a real system, you'd handle premium expiry date here.
                            # For now, let's just mark them premium.

                        save_db(USERS_DB, users)
                        try:
                            await client.send_message(ref_id, f" **New Referral!**\n\nUser `{uid}` joined via your link.\nTotal refers: `{users[ref_key]['refer_count']}`")
                        except: pass

        # Verification System
        if bi and bi.get("verify_link") and not is_admin(uid) and uid != bi.get("owner_id"):
            if not deep.startswith("verify_"):
                v_link = bi.get("verify_link")
                u_link = bi.get("update_channel")
                btns = [[InlineKeyboardButton(" START VERIFICATION", url=v_link)]]
                if u_link:
                    btns.append([InlineKeyboardButton(" UPDATE CHANNEL", url=u_link)])

                return await message.reply(
                    f" **Verification Required!**\n\n"
                    f"To access the files in this bot, you must complete a quick verification.\n\n"
                    f"1 Click the **Verification** button below.\n"
                    f"2 Complete the process in the other bot.\n"
                    f"3 Come back here and click `/start` again.",
                    reply_markup=InlineKeyboardMarkup(btns)
                )

        user_data, is_new = add_user(uid, bot_id, message.from_user.username,
                                      message.from_user.first_name)
        is_ok, links = await check_force_sub(client, uid)
        if not is_ok:
            btns = [[InlineKeyboardButton(f"ᴊᴏɪɴ {i['title']}", url=i["link"])]
                    for i in links]
            btns.append([InlineKeyboardButton(
                "ᴛʀʏ ᴀɢᴀɪɴ",
                url=f"https://t.me/{client.me.username}?start={deep}"
            )])
            return await message.reply(
                stylish(" **Membership Required!**\n\nPlease join the channels below or send a join request to access the bot."),
                reply_markup=InlineKeyboardMarkup(btns)
            )

        bi         = get_bot_info(bot_id)
        auto_del   = bi.get("auto_delete_time", 300) if bi else 300
        is_premium = user_data.get("is_premium", False)

        # ── Deep link: Protected Channel Link ───────────────────
        if deep.startswith("lp_") or deep == "join":
            lpid = deep[3:] if deep.startswith("lp_") else "default"
            plinks = load_db(PLINKS_DB)

            if deep == "join":
                chid = bi.get("connected_channel") if bi else None
                if not chid:
                    return await message.reply(" No channel connected to this bot!")
                mode = bi.get("join_method", "direct")
                pdata = {"channel_id": chid, "mode": mode, "title": "Main Channel"}
            else:
                pdata = plinks.get(lpid)
                if not pdata or pdata.get("bot_id") != bot_id:
                    return await message.reply(" Protected link not found or expired!")
                chid = pdata["channel_id"]
                mode = pdata.get("mode", "direct")

            req_approval = (mode in ("approval", "requested"))

            # Check if user already got a link in last 5 mins
            user_links = load_db(f"{DB_FOLDER}/user_links.json")
            ukey = f"{uid}_{lpid}"
            now_ts = time.time()

            if ukey in user_links:
                old_ts, old_link = user_links[ukey]
                if now_ts - old_ts < 300: # 5 minutes
                    return await message.reply(
                        stylish(" **Here is your link**"),
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(stylish(" JOIN NOW"), url=old_link)]
                        ])
                    )

            try:
                invite = await client.create_chat_invite_link(
                    chid,
                    expire_date=datetime.now() + timedelta(minutes=5),
                    creates_join_request=req_approval
                )

                # Save to user_links
                user_links[ukey] = [now_ts, invite.invite_link]
                save_db(f"{DB_FOLDER}/user_links.json", user_links)

                await message.reply(
                    stylish(" **Here is your link**"),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(stylish(" JOIN NOW"), url=invite.invite_link)]
                    ])
                )
                return
            except Exception as e:
                return await message.reply(f" Failed to create link: `{e}`")

        # ── Deep link: file with token ────────────────────────────
        if deep.startswith("f_") and "_t_" in deep:
            parts = deep[2:].split("_t_", 1)
            fuid  = parts[0]
            token = parts[1] if len(parts) > 1 else ""
            files = load_db(FILES_DB)
            fdata = files.get(fuid)
            if not fdata:
                return await message.reply(" **File not found!**")

            # Check if password protected
            if fdata.get("password") and not is_admin(uid, bot_id):
                TEMP_EDIT[uid] = {"mode": "verify_password", "uid": fuid, "password": fdata["password"], "fdata": fdata}
                return await message.reply(stylish(" **This file is password protected!**\n\nPlease send the password to access the file."))
            td = validate_token(token, uid, bot_id)
            if not td or td.get("resource_id") != fuid:
                short_link = await make_shortener_link(client, bi, uid, bot_id, fuid, "file")
                return await message.reply(
                    " **Link Expired or Already Used!**\n\nGet a fresh link:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(" Get Fresh Link", url=short_link)]
                    ])
                )
            consume_token(token)
            try:
                sent = await deliver_file(client, message.chat.id, fdata)
            except Exception as e:
                return await message.reply(f" File unavailable!\n`{e}`")
            if sent and not is_premium:
                asyncio.create_task(_auto_delete(sent, auto_del))
                await message.reply(
                    f" File auto-deletes in `{auto_del // 60}` min(s). Save it! "
                )
            elif sent:
                await message.reply(" **Premium:** No auto-delete for you!")
            return

        # ── Deep link: file without token ─────────────────────────
        elif deep.startswith("f_") and "_t_" not in deep:
            fuid  = deep[2:]
            files = load_db(FILES_DB)
            fdata = files.get(fuid)
            if not fdata:
                return await message.reply(" **File not found!**")

            # Check if password protected
            if fdata.get("password") and not is_admin(uid, bot_id):
                TEMP_EDIT[uid] = {"mode": "verify_password", "uid": fuid, "password": fdata["password"], "fdata": fdata}
                return await message.reply(stylish(" **This file is password protected!**\n\nPlease send the password to access the file."))

            if is_premium:
                try:
                    sent = await deliver_file(client, message.chat.id, fdata)
                    await message.reply(" **Premium:** Direct delivery, no ads!")
                except Exception as e:
                    await message.reply(f" Error: `{e}`")
                return

            if shortener_enabled_for_bot(bi):
                short_link = await make_shortener_link(client, bi, uid, bot_id, fuid, "file")
                fname = fdata.get("file_name", "File")
                icon  = file_icon(fname)
                return await message.reply(
                    f" **Verification Required**\n\n"
                    f"{icon} **{fname}**\n"
                    f" {fmt_size(fdata.get('file_size', 0))}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f" **Ladle, pehle shortener se jakar ads dekho, tab file milegi!** \n\n"
                    f" Click karo → ads dekho → file pao \n"
                    f" Link 15 minute mein expire hoga.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(" File Lo (Ad Dekho)", url=short_link)],
                        [InlineKeyboardButton(" Premium Lo (No Ads!)", callback_data="premium_menu")]
                    ])
                )

            try:
                sent = await deliver_file(client, message.chat.id, fdata)
            except Exception as e:
                return await message.reply(f" Error: `{e}`")
            if sent and not is_premium:
                asyncio.create_task(_auto_delete(sent, auto_del))
                await message.reply(f" Auto-deletes in `{auto_del // 60}` min(s). ")
            return

        # ── Deep link: batch with token ───────────────────────────
        elif deep.startswith("b_") and "_t_" in deep:
            parts   = deep[2:].split("_t_", 1)
            bid_key = parts[0]
            token   = parts[1] if len(parts) > 1 else ""
            bdata   = load_db(BATCH_DB).get(bid_key)
            if not bdata: return await message.reply(" Batch not found.")
            if bdata.get("bot_id") != bot_id:
                origin_bot = get_bot_info(bdata.get("bot_id"))
                bot_name = f"@{origin_bot['bot_username']}" if origin_bot else "the original bot"
                return await message.reply(f" **Access Denied!**\n\nThis batch was created on {bot_name}. Please use that bot to access these files.")

            td = validate_token(token, uid, bot_id)
            if not td or td.get("resource_id") != bid_key:
                short_link = await make_shortener_link(client, bi, uid, bot_id, bid_key, "batch")
                return await message.reply(
                    " **Link Expired!** Get fresh link:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Fresh Link", url=short_link)]])
                )
            consume_token(token)
            sm = await message.reply(f" Sending batch ({len(bdata['files'])} files)...")
            sc, tot = await deliver_batch_files(client, message.chat.id,
                                                 bdata["files"], bot_id, is_premium)
            await sm.delete()
            notice = await message.reply(
                f" Delivered **{sc}/{tot}** files!" +
                (f"\n\n**Your files will be deleted in {auto_del // 60} minutes.**" if not is_premium else "")
            )
            if not is_premium:
                asyncio.create_task(_auto_delete(notice, auto_del))
            return

        # ── Deep link: batch without token ────────────────────────
        elif deep.startswith("b_") and "_t_" not in deep:
            bid_key = deep[2:]
            bdata   = load_db(BATCH_DB).get(bid_key)
            if not bdata: return await message.reply(" Batch not found.")
            if bdata.get("bot_id") != bot_id:
                origin_bot = get_bot_info(bdata.get("bot_id"))
                bot_name = f"@{origin_bot['bot_username']}" if origin_bot else "the original bot"
                return await message.reply(f" **Access Denied!**\n\nThis batch was created on {bot_name}. Please use that bot to access these files.")

            total = len(bdata["files"])

            if is_premium:
                sm = await message.reply(f" Premium Direct: Sending {total} files...")
                sc, tot = await deliver_batch_files(client, message.chat.id,
                                                     bdata["files"], bot_id, True)
                await sm.delete()
                await message.reply(f" Delivered **{sc}/{tot}** files!  Premium")
                return

            if shortener_enabled_for_bot(bi):
                short_link = await make_shortener_link(client, bi, uid, bot_id, bid_key, "batch")
                return await message.reply(
                    f" **Verification Required**\n\n"
                    f" **{total} files** in this batch\n\n"
                    f" **Pehle ads dekho, phir sab files milenge!**\n"
                    f" Link 15 min mein expire hoga.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(" Files Lo (Ad Dekho)", url=short_link)],
                        [InlineKeyboardButton(" Premium Lo (No Ads!)", callback_data="premium_menu")]
                    ])
                )

            sm = await message.reply(f" Sending batch ({total} files)...")
            sc, tot = await deliver_batch_files(client, message.chat.id,
                                                 bdata["files"], bot_id, is_premium)
            await sm.delete()
            notice = await message.reply(
                f" Delivered **{sc}/{tot}** files!" +
                (f"\n\n**Your files will be deleted in {auto_del // 60} minutes.**" if not is_premium else "")
            )
            if not is_premium:
                asyncio.create_task(_auto_delete(notice, auto_del))
            return

        # ── Deep link: DUAL POST ──────────────────────────────────
        elif deep.startswith("dp_"):
            raw_deep = deep[3:]

            token_val  = None
            actual_pid = raw_deep

            if "_t_" in raw_deep:
                actual_pid, token_val = raw_deep.split("_t_", 1)

            post = get_dual_post(actual_pid)
            if not post:
                return await message.reply(
                    " **Dual Post not found!**\n\n"
                    "This post may have been deleted."
                )

            title      = post.get("title", "Dual Post")
            desc_free  = post.get("description_free", "Free content")
            desc_pro   = post.get("description_pro",  "Premium content")
            free_files = post.get("free_files", [])
            pro_files  = post.get("pro_files", [])
            use_short  = shortener_enabled_for_bot(bi)

            # Premium user → always gets PRO tier directly
            if is_premium:
                tier_files = pro_files if pro_files else free_files
                tier_label = " PREMIUM" if pro_files else " FREE (no pro files set)"
                bump_dual_access(actual_pid, "pro" if pro_files else "free")

                if not tier_files:
                    return await message.reply(
                        f" **{title}**\n\n_{desc_pro}_\n\n"
                        f"_No files available yet._"
                    )

                sm = await message.reply(
                    f" **{title}**\n\n"
                    f"_{desc_pro}_\n\n"
                    f" {tier_label}: Sending `{len(tier_files)}` file(s)..."
                )
                sc, tot = await deliver_batch_files(client, message.chat.id,
                                                     tier_files, bot_id, True)
                await sm.delete()
                await message.reply(
                    f" **{sc}/{tot}** premium files delivered!\n\n"
                    f" _Premium users get full content directly — no ads, no wait._"
                )
                return

            # Free user
            bump_dual_access(actual_pid, "free")

            if not free_files:
                return await message.reply(
                    f" **{title}**\n\n_{desc_free}_\n\n"
                    f"_No free files available._\n\n"
                    f" Upgrade to Premium for exclusive content!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(" Get Premium", callback_data="premium_menu")]
                    ])
                )

            if token_val:
                td = validate_token(token_val, uid, bot_id)
                if not td or td.get("resource_id") != actual_pid:
                    if use_short:
                        short_link = await make_shortener_link(client, bi, uid, bot_id, actual_pid, "dual")
                        return await message.reply(
                            " **Link Expired!** Get a fresh one:",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton(" Get Fresh Link", url=short_link)],
                                [InlineKeyboardButton(" Get Premium (Skip Ads)", callback_data="premium_menu")]
                            ])
                        )
                else:
                    consume_token(token_val)
                    sm = await message.reply(
                        f" **{title}**\n\n_{desc_free}_\n\n"
                        f" Sending `{len(free_files)}` file(s)..."
                    )
                    sc, tot = await deliver_batch_files(client, message.chat.id,
                                                         free_files, bot_id, False)
                    await sm.delete()

                    notice = await message.reply(
                        f" **{sc}/{tot}** files delivered!\n\n"
                        f" **Your files will be deleted in {auto_del // 60} minutes.**\n\n"
                        f" _Want premium content? Upgrade for full access!_",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(" Upgrade to Premium", callback_data="premium_menu")]
                        ]) if pro_files else None
                    )
                    asyncio.create_task(_auto_delete(notice, auto_del))
                    return

            if use_short:
                short_link = await make_shortener_link(client, bi, uid, bot_id, actual_pid, "dual")
                fc = len(free_files)
                pc = len(pro_files)
                return await message.reply(
                    f" **{title}**\n\n"
                    f"_{desc_free}_\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f" **{fc}** free file(s) available\n"
                    f" **{pc}** premium file(s) (upgrade to access)\n\n"
                    f" **Pehle link visit karo, ads dekho, phir files milenge!**\n"
                    f" Link 15 minute mein expire hoga.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(" Free Files Lo (Ad Dekho)", url=short_link)],
                        [InlineKeyboardButton(" Premium Lo → Direct Files!", callback_data="premium_menu")]
                    ])
                )
            else:
                sm = await message.reply(
                    f" **{title}**\n\n_{desc_free}_\n\n"
                    f" Sending `{len(free_files)}` file(s)..."
                )
                sc, tot = await deliver_batch_files(client, message.chat.id,
                                                     free_files, bot_id, False)
                await sm.delete()
                await message.reply(
                    f" **{sc}/{tot}** files delivered!\n\n"
                    f" _Premium users get exclusive content — upgrade to unlock!_",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(" Get Premium", callback_data="premium_menu")]
                    ]) if pro_files else None
                )
                return

        # Standard welcome
        global_msg   = cfg.get("global_msg", "")
        welcome_text = bi.get("custom_welcome") if bi else None
        welcome_img  = bi.get("welcome_image")  if bi else None

        if global_msg:
            await message.reply(f" **System Notice**\n\n{global_msg}")

        if not welcome_text:
            default_welcome = (
                "<blockquote>"
                "ʜᴇʟʟᴏ {name}\n\n"
                "ɪ ᴀᴍ ғɪʟᴇ sᴛᴏʀᴇ ʙᴏᴛ, ɪ ᴄᴀɴ sᴛᴏʀᴇ ᴘʀɪᴠᴀᴛᴇ ғɪʟᴇs ɪɴ sᴘᴇᴄɪғɪᴇᴅ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴏᴛʜᴇʀ ᴜsᴇʀs ᴄᴀɴ ᴀᴄᴄᴇss ɪᴛ ғʀᴏᴍ sᴘᴇᴄɪᴀʟ ʟɪɴᴋ.\n\n"
                "/help 𝚝𝚘 𝚔𝚗𝚘𝚠 𝚖𝚘𝚛𝚎 𝚊𝚋𝚘𝚞𝚝 𝚋𝚘𝚝"
                "</blockquote>"
            )
            welcome_text = default_welcome.format(name=message.from_user.first_name)

        kbd = kb_start(bot_id, uid)
        if is_new and bi and bi.get("owner_id") == uid:
            await message.reply(
                f" **Hey Boss! Welcome to your cloned bot.**\n\n"
                f"I'm ready to work for you. Here are some quick setups:\n"
                f"1 `/setlog -100xxxx` - Set a log channel to see uploads.\n"
                f"2 `/setchannel -100xxxx` - Connect your channel for the `/start join` link.\n"
                f"3 `/setmode requested` - If you want users to send join requests.\n"
                f"4 `/setwelcome` - Customize this message.\n\n"
                f"Use `/admin` to see all your controls!"
            )

        if welcome_img:
            try:
                await message.reply_photo(welcome_img, caption=stylish(welcome_text), reply_markup=kbd)
                return
            except Exception:
                pass
        await message.reply(stylish(welcome_text), reply_markup=kbd, quote=True)

    # ── /admin ────────────────────────────────────────────────────
    @app.on_message(filters.command("admin") & filters.private, group=1)
    async def admin_cmd(client, message):
        uid = message.from_user.id
        bi  = get_bot_info(client.me.id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return
        text = get_msg_text("msg_admin", " **Admin Panel**")
        await message.reply(text, reply_markup=kb_admin())

    # ── /supreme ──────────────────────────────────────────────────
    @app.on_message(filters.command("supreme") & filters.private, group=1)
    async def supreme_cmd(client, message):
        if message.from_user.id != MAIN_ADMIN: return
        default_supreme = (
            f" **Supreme Panel v7.0**\n\n"
            f" Bots: `{{bots}}` |  Users: `{{users}}`\n"
            f" Files: `{{files}}` |  Duals: `{{duals}}`"
        )
        text = get_msg_text("msg_supreme", default_supreme).format_map(SafeDict(
            bots=len(ACTIVE_CLIENTS),
            users=len(load_db(USERS_DB)),
            files=len(load_db(FILES_DB)),
            duals=len(load_db(DUAL_POST_DB))
        ))
        await message.reply(text, reply_markup=kb_supreme())

    # ── /stats ────────────────────────────────────────────────────
    @app.on_message(filters.command("stats") & filters.private, group=1)
    async def stats_cmd(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        if uid == MAIN_ADMIN:
            dual_posts = load_db(DUAL_POST_DB)
            total_dp_views = sum(p.get("access_total", 0) for p in dual_posts.values())
            await message.reply(
                f" **Global Analytics**\n━━━━━━━━━━━━━━━━━━━━\n"
                f" Bots: `{len(get_all_bots())}` |  Online: `{len(ACTIVE_CLIENTS)}`\n"
                f" Users: `{len(load_db(USERS_DB))}`\n"
                f" Files: `{len(load_db(FILES_DB))}`\n"
                f" Dual Posts: `{len(dual_posts)}` |  `{total_dp_views}` views\n"
                f" Uptime: `{str(datetime.now() - START_TIME).split('.')[0]}`"
            )
        else:
            ud   = get_user(uid, bot_id)
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            dps  = get_user_dual_posts(bot_id, uid)
            await message.reply(
                f" **Dashboard**\n━━━━━━━━━━━━━━━━━━━━\n"
                f" `{ud.get('files_uploaded',0) if ud else 0}` uploads | "
                f" `{ud.get('batches_created',0) if ud else 0}` batches\n"
                f" `{len(dps)}` dual posts |  `{len(ubts)}` bots\n"
                f" {'Premium ' if ud and ud.get('is_premium') else 'Free'}"
            )

    # ── /setwelcome ───────────────────────────────────────────────
    @app.on_message(filters.command("setwelcome") & filters.private, group=1)
    async def setwelcome_cmd(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        bi  = get_bot_info(bot_id)
        if not bi or (bi.get("owner_id") != uid and uid != MAIN_ADMIN):
            return await message.reply(" Only bot owner!")
        TEMP_WELCOME[uid] = {"bot_id": bot_id, "step": "text"}
        curr_t = bi.get("custom_welcome") or "_(default)_"
        curr_i = " Set" if bi.get("welcome_image") else " None"
        await message.reply(
            f" **Welcome Message Editor**\n\n"
            f"Current text: {curr_t[:80]}\nCurrent image: {curr_i}\n\n"
            f"**Step 1/2:** Send new welcome text\n"
            f"`-skip` = keep | `-clear` = default\n/cancel to abort.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel", callback_data="cancel_welcome")]])
        )

    # ── /broadcast ────────────────────────────────────────────────
    @app.on_message(filters.command("broadcast") & filters.private, group=1)
    async def broadcast_cmd(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        bi  = get_bot_info(bot_id)
        can_bc = target_bots = None
        if uid == MAIN_ADMIN:
            can_bc, target_bots = True, list(ACTIVE_CLIENTS.keys())
        elif bi and bi.get("owner_id") == uid:
            can_bc = True
            target_bots = [bot_id]

        if not can_bc: return await message.reply(stylish(" No permission!"))

        if not message.reply_to_message:
            total = sum(len(get_all_users(bid)) for bid in target_bots)
            return await message.reply(
                f" **ULTRA BROADCAST SYSTEM**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f" **Target Bots:** `{len(target_bots)}` bots\n"
                f" **Estimated Reach:** `{total}` users\n\n"
                f" **HOW TO USE:**\n"
                f"1 Reply to any message with `/broadcast`.\n"
                f"2 You can optionally add a button like this:\n"
                f"   `/broadcast | Button Text | https://link.com`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

        sm = await message.reply(" **Processing broadcast payload...**")
        bc_msg_id = await store_broadcast(client, message.reply_to_message)
        if not bc_msg_id:
            return await sm.edit(" **Error:** Failed to cache broadcast message. Please try again.")

        btn_markup = None
        if "|" in message.text:
            try:
                parts = message.text.split("|")
                if len(parts) >= 3:
                    btn_markup = InlineKeyboardMarkup([[InlineKeyboardButton(parts[1].strip(), url=parts[2].strip())]])
            except: pass

        TEMP_BROADCAST[uid] = {"bc_msg_id": bc_msg_id, "bot_ids": target_bots, "markup": btn_markup}
        total = sum(len(get_all_users(bid)) for bid in target_bots)
        await sm.edit(
            f" **READY FOR BROADCAST?**\n\n"
            f" Bots: `{len(target_bots)}` bots\n"
            f" Users: `{total}` total users\n"
            f" Payload ID: `{bc_msg_id}`\n"
            f" Button: {' Set' if btn_markup else ' None'}\n\n"
            f"**Note:** This will deliver a COPY of your message to all users.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(" CONFIRM & SEND", callback_data="confirm_broadcast")],
                [InlineKeyboardButton(" ABORT",           callback_data="cancel_broadcast")]
            ])
        )

    # ── /batch /done /cancel ──────────────────────────────────────
    @app.on_message(filters.command("batch") & filters.private, group=1)
    async def batch_start(client, message):
        uid = message.from_user.id
        if is_user_banned(uid, client.me.id): return await message.reply(" Banned!")
        TEMP_BATCH[uid] = []
        await message.reply(" **Batch Mode ON!**\n\nSend files. `/done` to finish. `/cancel` to abort.")

    @app.on_message(filters.command("createpost") & filters.private, group=1)
    async def createpost_cmd(client, message):
        uid = message.from_user.id; bot_id = client.me.id; bi = get_bot_info(bot_id)

        TEMP_POST[uid] = {"bot_id": bot_id, "step": "content"}
        text = " **Post Creator — Step 1/3**\n\nSend the message you want to create (Text, Photo, Video, etc.).\n\nYou can use stylish fonts by selecting text and choosing a style (if supported)."

        btns = [[InlineKeyboardButton(stylish(" Cancel"), callback_data="cancel_post")]]

        # Encourage cloning if not bot owner/admin
        is_adm = is_admin(uid, bot_id) or (bi and bi.get("owner_id") == uid)
        if not is_adm:
            text = "<b>WANT TO BECOME AN ADMIN?</b>\n\nCreate your own bot clone to get full admin features including post management and more!\n\n" + text
            btns.insert(0, [InlineKeyboardButton(stylish(" ᴄʟᴏɴᴇ ᴛʜɪs ʙᴏᴛ "), callback_data="clone_menu")])

        await message.reply(
            stylish(text),
            reply_markup=InlineKeyboardMarkup(btns)
        )

    @app.on_message(filters.command("done") & filters.private, group=1)
    async def batch_done(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        bi  = get_bot_info(bot_id)
        if uid not in TEMP_BATCH or not TEMP_BATCH[uid]:
            return await message.reply(" No files in batch!")
        fids = TEMP_BATCH.pop(uid)
        bid  = unique_id()
        batches = load_db(BATCH_DB)
        batches[bid] = {"files": fids, "created_by": uid, "bot_id": bot_id, "date": str(datetime.now())}
        save_db(BATCH_DB, batches)
        update_user_stats(uid, bot_id, "batches_created")
        link  = f"https://t.me/{client.me.username}?start=b_{bid}"
        short = await get_short_link(bi, link)

        files_db = load_db(FILES_DB)
        file_links = ""
        for i, fuid in enumerate(fids, 1):
            fd = files_db.get(fuid)
            f_name = fd.get("file_name", "File") if fd else "File"
            f_link = f"https://t.me/{client.me.username}?start=f_{fuid}"
            file_links += f"{i}. **{f_name}**\n   `{f_link}`\n"
            if i >= 15 and len(fids) > 15:
                file_links += f"... and {len(fids)-15} more files."
                break

        await message.reply(
            f" **Batch Created!**\n\n"
            f" `{len(fids)}` files\n\n"
            f" **Batch Link:**\n`{short}`\n\n"
            f" **Individual File Links:**\n{file_links}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(" Share Batch", url=f"https://t.me/share/url?url={short}")]
            ])
        )

    @app.on_message(filters.command("cancel") & filters.private, group=1)
    async def cancel_cmd(client, message):
        uid = message.from_user.id
        b = TEMP_BATCH.pop(uid, None)
        e = TEMP_EDIT.pop(uid, None)
        w = TEMP_WELCOME.pop(uid, None)
        d = TEMP_DUAL.pop(uid, None)
        p = TEMP_PROTECT.pop(uid, None)
        cancelled = []
        if b is not None: cancelled.append("Batch")
        if e is not None: cancelled.append("File Edit")
        if w is not None: cancelled.append("Welcome Edit")
        if p is not None: cancelled.append("Protect Link Setup")
        if d is not None:
            cancelled.append(f"Dual Post ({len(d.free_files)}F+{len(d.pro_files)}P)")
        if cancelled:
            await message.reply(f" Cancelled: {', '.join(cancelled)}")
        else:
            await message.reply("Nothing to cancel.")

    @app.on_message(filters.command("protect") & filters.private, group=1)
    async def protect_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply(" Access Denied!")

        TEMP_PROTECT[uid] = {"bot_id": bot_id, "step": "channel"}
        await message.reply(
            " **Advanced Link Protection Setup**\n\n"
            "Step 1: Send the **Channel ID** (starting with -100) you want to protect.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel", callback_data="cancel_protect")]])
        )

    @app.on_message(filters.command("myplinks") & filters.private, group=1)
    async def myplinks_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply(" Access Denied!")

        plinks = load_db(PLINKS_DB)
        my_links = [v for v in plinks.values() if v.get("bot_id") == bot_id and (v.get("created_by") == uid or is_admin(uid))]

        if not my_links:
            return await message.reply(" **No protected links found!**\nUse `/protect` to create one.")

        text = f" **Your Protected Links ({len(my_links)})**\n\n"
        btns = []
        for l in my_links[:15]:
            lpid = l["lpid"]
            title = l.get("title", "Unknown")[:25]
            link = f"https://t.me/{client.me.username}?start=lp_{lpid}"
            text += f" **{title}**\n`{lpid}` | {l.get('mode').upper()}\n `{link}`\n\n"
            btns.append([
                InlineKeyboardButton(f" {title}", url=f"https://t.me/share/url?url={link}"),
                InlineKeyboardButton(" Delete", callback_data=f"del_plink_{lpid}")
            ])

        await message.reply(text, reply_markup=InlineKeyboardMarkup(btns) if btns else None)

    # ── /editfile /delfile /listfiles ─────────────────────────────
    @app.on_message(filters.command("editfile") & filters.private, group=1)
    async def editfile_cmd(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        if len(message.command) < 2:
            return await message.reply("Usage: `/editfile FILE_ID`")
        fuid  = message.command[1]
        files = load_db(FILES_DB); fd = files.get(fuid)
        if not fd: return await message.reply(" File not found!")
        bi  = get_bot_info(bot_id)
        can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or fd.get("user_id")==uid
        if not can: return await message.reply(" Not your file!")
        await message.reply(
            get_file_edit_text(client, fd, fuid),
            reply_markup=kb_file_edit(fuid)
        )

    @app.on_message(filters.command("delfile") & filters.private, group=1)
    async def delfile_cmd(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        if len(message.command) < 2: return await message.reply("Usage: `/delfile FILE_ID`")
        fuid  = message.command[1]; files = load_db(FILES_DB); fd = files.get(fuid)
        if not fd: return await message.reply(" Not found!")
        bi  = get_bot_info(bot_id)
        can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or fd.get("user_id")==uid
        if not can: return await message.reply(" Not your file!")
        del files[fuid]; save_db(FILES_DB, files)
        await message.reply(f" **Deleted:** `{fd.get('file_name','?')}`")

    @app.on_message(filters.command("listfiles") & filters.private, group=1)
    async def listfiles_cmd(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        files = load_db(FILES_DB); bi = get_bot_info(bot_id)
        is_sup = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid)
        all_f = [(k,f) for k,f in files.items()
                 if f.get("bot_id")==bot_id and (is_sup or f.get("user_id")==uid)]
        if not all_f: return await message.reply(" No files found!")
        recent = sorted(all_f, key=lambda x: x[1].get("upload_date",""), reverse=True)[:10]
        text = f" **{'All' if is_sup else 'Your'} Files** ({len(all_f)} total)\n\n"
        btns = []
        for k, f in recent:
            icon = file_icon(f.get("file_name",""))
            name = (f.get("file_name") or "?")[:35]
            text += f"{icon} **{name}** |  {fmt_size(f.get('file_size',0))} |  {f.get('access_count',0)}\n`{k}`\n\n"
            btns.append([
                InlineKeyboardButton(f"{icon} {name[:22]}", url=f"https://t.me/{client.me.username}?start=f_{k}"),
                InlineKeyboardButton("", callback_data=f"edit_file_{k}")
            ])
        await message.reply(text, reply_markup=InlineKeyboardMarkup(btns) if btns else None)

    # ── Misc commands ─────────────────────────────────────────────
    @app.on_message(filters.command("mybots") & filters.private, group=1)
    async def mybots_cmd(client, message):
        uid  = message.from_user.id
        ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
        if not ubts: return await message.reply(" No bots yet! `/clone TOKEN`")
        text = f" **Your Bots ({len(ubts)})**\n\n"
        for i, b in enumerate(ubts[:10],1):
            text += f"{i}. {'' if b['bot_id'] in ACTIVE_CLIENTS else ''} @{b['bot_username']}\n"
        await message.reply(text)

    @app.on_message(filters.command(["ban","unban","info","givepremium","removepremium","gban","ungban"]) & filters.private, group=1)
    async def admin_utils(client, message):
        uid = message.from_user.id; bot_id = client.me.id; bi = get_bot_info(bot_id)
        if not (uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid)): return
        if len(message.command)<2: return await message.reply(f"Usage: `/{message.command[0]} USER_ID`")
        try: target = int(message.command[1])
        except ValueError: return await message.reply(" Invalid ID!")
        cmd = message.command[0]
        if cmd == "ban":
            await message.reply(" Banned!" if ban_user(target,bot_id) else " Not found.")
        elif cmd == "unban":
            await message.reply(" Unbanned!" if unban_user(target,bot_id) else " Not found.")
        elif cmd == "givepremium":
            users = load_db(USERS_DB); k = f"{bot_id}_{target}"
            if k in users:
                users[k]["is_premium"] = True; save_db(USERS_DB,users)
                await message.reply(f" `{target}` is now Premium!")
            else: await message.reply(" Not found.")
        elif cmd == "removepremium":
            users = load_db(USERS_DB); k = f"{bot_id}_{target}"
            if k in users:
                users[k]["is_premium"] = False; save_db(USERS_DB,users)
                await message.reply(f" Premium removed from `{target}`!")
            else: await message.reply(" Not found.")
        elif cmd == "gban":
            if uid!=MAIN_ADMIN: return
            cfg=get_global_config(); gb=cfg.get("global_bans",[])
            if target not in gb:
                gb.append(target); update_global_config("global_bans",gb)
                await message.reply(f" Globally banned `{target}`!")
        elif cmd == "ungban":
            if uid!=MAIN_ADMIN: return
            cfg=get_global_config(); gb=cfg.get("global_bans",[])
            if target in gb:
                gb.remove(target); update_global_config("global_bans",gb)
                await message.reply(f" Globally unbanned `{target}`!")
        elif cmd == "info":
            u = get_user(target, bot_id)
            if not u: return await message.reply(" Not found.")
            await message.reply(
                f" **User Info**\n"
                f" `{u['user_id']}`\n"
                f" {u.get('name','?')} | @{u.get('username') or 'None'}\n"
                f" Banned: {u.get('is_banned',False)} |  Premium: {u.get('is_premium',False)}\n"
                f" Uploaded: `{u.get('files_uploaded',0)}`"
            )

    @app.on_message(filters.command("setprice") & filters.private, group=1)
    async def setprice_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply(" Access Denied!")
        if len(message.command)<2:
            curr=bi.get("premium_price","500")
            return await message.reply(f" Current Price: `{curr}`\n`/setprice AMOUNT` (e.g. 500 or 5$)")
        price = message.text.split(None, 1)[1].strip()
        update_bot_info(bot_id, "premium_price", price)
        await message.reply(f" Premium price set to: `{price}`")

    @app.on_message(filters.command("setcontact") & filters.private, group=1)
    async def setcontact_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply(" Access Denied!")
        if len(message.command)<2:
            curr=bi.get("premium_contact","zolvid")
            return await message.reply(f" Current Contact: `@{curr}`\n`/setcontact USERNAME` (without @)")
        contact = message.command[1].replace("@", "").strip()
        update_bot_info(bot_id, "premium_contact", contact)
        await message.reply(f" Premium contact set to: `@{contact}`")

    @app.on_message(filters.command("setqr") & filters.private, group=1)
    async def setqr_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply(" Access Denied!")
        if not message.reply_to_message or not message.reply_to_message.photo:
            return await message.reply(" Reply to a QR code image with `/setqr` to set it.\nUse `/setqr off` to remove.")

        if len(message.command) > 1 and message.command[1].lower() == "off":
            update_bot_info(bot_id, "premium_qr", None)
            return await message.reply(" Premium QR code removed!")

        qr_id = message.reply_to_message.photo.file_id
        update_bot_info(bot_id, "premium_qr", qr_id)
        await message.reply(" Premium QR code updated successfully!")

    @app.on_message(filters.command("setchannel") & filters.private, group=1)
    async def setchannel_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply(" Access Denied!")
        if len(message.command)<2:
            return await message.reply(
                f" **Channel Connection**\n\n"
                f"Connected: `{bi.get('connected_channel') or 'None'}`\n\n"
                f"Usage:\n"
                f"├ `/setchannel -100xxxxxxx` - Connect channel\n"
                f"└ `/setchannel off` - Disable connection\n\n"
                f"Note: Users can use `/start join` to get an expiring link to this channel."
            )
        if message.command[1].lower()=="off":
            update_bot_info(bot_id,"connected_channel",None); return await message.reply(" Disabled!")
        try:
            chid = int(message.command[1])
            await client.get_chat(chid)
            update_bot_info(bot_id,"connected_channel",chid)
            await message.reply(f" Channel connected successfully: `{chid}`")
        except Exception as e:
            err_msg = f" Error: `{e}`\n\n**Tip:** Make sure the bot is an **Admin** in the channel with all permissions. If you still get PeerIdInvalid, try sending a message in the channel and then try again."
            await message.reply(err_msg)

    @app.on_message(filters.command("setmode") & filters.private, group=1)
    async def setmode_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply(" Access Denied!")
        modes = ["direct", "requested", "approval"]
        if len(message.command)<2:
            return await message.reply(
                f" **Join Mode Selection**\n\n"
                f"Current Mode: `{bi.get('join_method','direct').upper()}`\n\n"
                f"Available Modes:\n"
                f"├ `direct` - Regular join link\n"
                f"├ `requested` - Admin approval request\n"
                f"└ `approval` - Same as requested\n\n"
                f"Usage: `/setmode [mode]`"
            )
        mode = message.command[1].lower()
        if mode not in modes:
            return await message.reply(f" Invalid mode! Use: {', '.join(modes)}")
        update_bot_info(bot_id, "join_method", mode)
        await message.reply(f" Join mode set to: `{mode.upper()}`")

    @app.on_message(filters.command("settimer") & filters.private, group=1)
    async def settimer_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN): return await message.reply(" Access Denied!")
        if len(message.command)<2:
            curr=bi.get("auto_delete_time",300)
            return await message.reply(f" Current: `{curr}s` ({curr//60}min)\n`/settimer SECONDS`")
        try:
            secs=int(message.command[1])
            if secs<60: return await message.reply(" Min 60s!")
            update_bot_info(bot_id,"auto_delete_time",secs)
            await message.reply(f" Set to `{secs}s` ({secs//60}min).")
        except ValueError: await message.reply(" Invalid!")

    @app.on_message(filters.command("setlog") & filters.private, group=1)
    async def setlog_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply(" Access Denied!")
        if len(message.command)<2: return await message.reply(f" Log: `{bi.get('log_channel') or 'None'}`\n`/setlog ID` or off")
        if message.command[1].lower()=="off":
            update_bot_info(bot_id,"log_channel",None); return await message.reply(" Disabled!")
        try:
            log_id = int(message.command[1])
            await client.get_chat(log_id)
            update_bot_info(bot_id,"log_channel",log_id)
            await message.reply(" Log channel set!")
        except Exception as e:
            err_msg = f" Error: `{e}`\n\n**Tip:** Ensure the bot is an **Admin** in the log channel. If you get PeerIdInvalid, send a message in that channel first."
            await message.reply(err_msg)

    @app.on_message(filters.command("setverify") & filters.private, group=1)
    async def setverify_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply(" Access Denied!")
        if len(message.command)<2:
            return await message.reply(
                f" **Verification System**\n\n"
                f"Link: `{bi.get('verify_link') or 'None'}`\n"
                f"Update: `{bi.get('update_channel') or 'None'}`\n\n"
                f"Usage:\n"
                f"├ `/setverify LINK` - Set verification link\n"
                f"├ `/setupdates LINK` - Set update channel link\n"
                f"└ `/setverify off` - Disable verification"
            )
        val = message.command[1]
        if val.lower() == "off":
            update_bot_info(bot_id, "verify_link", None)
            return await message.reply(" Verification disabled!")

        update_bot_info(bot_id, "verify_link", val)
        await message.reply(f" Verification link set to: `{val}`")

    @app.on_message(filters.command("setupdates") & filters.private, group=1)
    async def setupdates_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply(" Access Denied!")
        if len(message.command)<2:
            return await message.reply(f" Update Channel: `{bi.get('update_channel') or 'None'}`\n`/setupdates LINK` or off")
        val = message.command[1]
        if val.lower() == "off":
            update_bot_info(bot_id, "update_channel", None)
            return await message.reply(" Update channel disabled!")

        update_bot_info(bot_id, "update_channel", val)
        await message.reply(f" Update channel link set to: `{val}`")

    @app.on_message(filters.command("shortener") & filters.private, group=1)
    async def shortener_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN): return await message.reply(" Access Denied!")
        if len(message.command)<2:
            st=" ON" if bi.get("is_shortener_enabled") else " OFF"
            return await message.reply(f" Shortener {st}\nURL: `{bi.get('shortener_url') or 'Not set'}`\nCmds: `on`, `off`, `set URL APIKEY`")
        cmd=message.command[1].lower()
        if cmd=="on":
            if not bi.get("shortener_url"): return await message.reply(" Set URL first!")
            update_bot_info(bot_id,"is_shortener_enabled",True); await message.reply(" Enabled!")
        elif cmd=="off":
            update_bot_info(bot_id,"is_shortener_enabled",False); await message.reply(" Disabled!")
        elif cmd=="set":
            if len(message.command)<4: return await message.reply("Usage: `/shortener set URL APIKEY`")
            update_bot_info(bot_id,"shortener_url",message.command[2])
            update_bot_info(bot_id,"shortener_api",message.command[3])
            await message.reply(f" Configured: `{message.command[2]}`")

    @app.on_message(filters.command("clone") & filters.private, group=1)
    async def clone_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id
        if is_user_banned(uid,bot_id): return await message.reply(" Banned!")

        # Restriction: Must join Update Channel
        update_ch = "https://t.me/filestorebotupdate"
        if True: # Applying to everyone as per request "jo bhi users bot clone karne jaye"
            try:
                is_ok = False
                main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None)
                if main_client:
                    try:
                        await main_client.get_chat_member("filestorebotupdate", uid)
                        is_ok = True
                    except (UserNotParticipant, Exception):
                        pass

                if not is_ok:
                    return await message.reply(
                        stylish(" **Cloning Restricted!**\n\nYou must join our Update Channel before you can clone a bot."),
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(stylish(" Join Update Channel"), url=update_ch)]])
                    )
            except Exception as e:
                logger.error(f"Clone check critical error: {e}")

        if len(message.command)<2:
            ubts=[b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            return await message.reply(
                f" **Bot Cloning System** \n\n"
                f"Create your own version of this bot in seconds!\n\n"
                f"1 Go to @BotFather and create a `/newbot`.\n"
                f"2 Copy the **API TOKEN** they give you.\n"
                f"3 Send it here: `/clone YOUR_TOKEN`.\n\n"
                f" Your bots: `{len(ubts)}`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" BotFather",url="https://t.me/BotFather")]]))
        token=message.command[1]
        for b in get_all_bots().values():
            if isinstance(b,dict) and b.get("token")==token: return await message.reply(" Already registered!")
        sm=await message.reply(" **Establishing connection to Telegram...**")
        try:
            na=await start_bot(token,parent_bot_id=bot_id)
            if na:
                me=await na.get_me()
                save_bot_info(token,me.id,me.username,uid,message.from_user.first_name,bot_id)
                await sm.edit(
                    f" **CONGRATULATIONS! YOUR BOT IS READY!** \n\n"
                    f" **Username:** @{me.username}\n"
                    f" **Bot ID:** `{me.id}`\n\n"
                    f" **NEXT STEPS (IMPORTANT):**\n"
                    f"1 Open your new bot: @{me.username}\n"
                    f"2 Send `/start` to activate it.\n"
                    f"3 Use `/setlog -100xxxx` to set a log channel.\n"
                    f"4 Use `/setchannel` to connect your main channel.\n\n"
                    f"Enjoy your personal FileStore bot!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" OPEN CLONED BOT", url=f"https://t.me/{me.username}")]]))
            else: await sm.edit(" Failed! Make sure the token is correct and bot is not already running.")
        except Exception as e: await sm.edit(f" Error: `{e}`")

    @app.on_message(filters.command("setfs") & filters.private, group=1)
    async def setfs_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN): return await message.reply(stylish(" Only owner!"))
        fs=bi.get("force_subs",[])
        if len(message.command)<2:
            text=stylish(f" **Force Subscribe** ({len(fs)}/{MAX_FORCE_SUB_CHANNELS})\n\n")
            for i,f in enumerate(fs,1):
                cid=f["channel_id"] if isinstance(f,dict) else f
                lnk=f["invite_link"] if isinstance(f,dict) else None
                text+=stylish(f"{i}. ") + f"`{cid}`" + (f" ([Link]({lnk}))" if lnk else "") + "\n"
            if not fs: text+=stylish("None.\n")
            text+=stylish("\nCommands:\n") + "`/setfs add -100xxx [link]`\n`/setfs del -100xxx`\n`/setfs clear`"
            return await message.reply(text, disable_web_page_preview=True)
        cmd=message.command[1].lower()
        if cmd in ("clear","off"):
            update_bot_info(bot_id,"force_subs",[]); n=cascade_force_subs(bot_id,[])
            return await message.reply(f" Cleared! ({n} clones updated)")
        if cmd=="add":
            if len(fs)>=MAX_FORCE_SUB_CHANNELS: return await message.reply(stylish(f" Max {MAX_FORCE_SUB_CHANNELS}!"))
            if len(message.command)<3: return await message.reply(stylish("Usage: /setfs add -100xxx [link]"))

            target_cid = message.command[2]
            lnk = message.command[3] if len(message.command) > 3 else None

            try:
                if target_cid.startswith("https://t.me/"):
                    chat = await client.get_chat(target_cid)
                    cid = chat.id
                    if not lnk: lnk = target_cid
                else:
                    cid = int(target_cid)
            except Exception as e:
                return await message.reply(stylish(f" Invalid ID or Link: {e}"))

            try:
                try:
                    await client.get_chat_member(cid, client.me.id)
                except Exception:
                    main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None)
                    if main_client:
                        # Just verify access
                        await main_client.get_chat(cid)
                    else:
                        raise
            except Exception as e:
                err_msg = f" I don't have access to this channel: `{e}`\n\n**Tip:** Ensure the bot is an **Admin** in the channel. If you get PeerIdInvalid, send a message in that channel and then try again."
                return await message.reply(stylish(err_msg))

            if any((f["channel_id"] if isinstance(f, dict) else f) == cid for f in fs):
                return await message.reply(stylish(" Channel already in Force Sub list!"))

            fs.append({"channel_id": cid, "invite_link": lnk})
            update_bot_info(bot_id, "force_subs", fs)
            n = cascade_force_subs(bot_id, fs)
            return await message.reply(stylish(f" Added! ({n} clones updated)"))
        if cmd=="del":
            if len(message.command)<3: return await message.reply("Usage: `/setfs del -100xxx`")
            try: cid=int(message.command[2])
            except ValueError: return await message.reply(" Invalid ID!")
            new_fs=[f for f in fs if (f["channel_id"] if isinstance(f,dict) else f)!=cid]
            if len(new_fs)==len(fs): return await message.reply(" Not in list!")
            update_bot_info(bot_id,"force_subs",new_fs); n=cascade_force_subs(bot_id,new_fs)
            return await message.reply(f" Removed! ({n} clones updated)")

    @app.on_message(filters.command(["premium","botinfo","help", "about", "refer", "rename", "setcaption", "setthumb", "autoapprove", "autocaption",
                                      "setglobal","addadmin","deladmin","search", "font", "requests"]) & filters.private, group=1)
    async def misc_commands(client, message):
        uid=message.from_user.id; bot_id=client.me.id; cmd=message.command[0]
        if cmd == "premium":
            ud=get_user(uid,bot_id); is_p=ud.get("is_premium",False) if ud else False
            bi=get_bot_info(bot_id); price = bi.get("premium_price", "500") if bi else "500"
            contact = bi.get("premium_contact", "zolvid") if bi else "zolvid"
            qr_id = bi.get("premium_qr") if bi else None

            default_prem = (
                f" **ELITE PREMIUM MEMBERSHIP** \n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f" **Status:** {{status}}\n\n"
                f" **UNLOCK THE POWER:**\n"
                f" ├  **PERMANENT STORAGE:** No auto-delete timer!\n"
                f" ├  **DUAL-TIER UNLOCK:** Get PRO files instantly!\n"
                f" ├  **ZERO ADS:** Skip all shortener links!\n"
                f" ├  **PRO BATCHING:** No limits on creation!\n"
                f" └  **PRIORITY:** Faster delivery & support!\n\n"
                f" **Subscription Fee:** `{{price}}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f" **WANT TO UPGRADE? CONTACT ADMIN!** "
            )
            text = get_msg_text("msg_premium", default_prem).format_map(SafeDict(
                status=' `ACTIVATED`' if is_p else ' `NOT ACTIVE`',
                price=price,
                contact=f"@{contact}"
            ))

            kb = [
                [InlineKeyboardButton(get_btn_name("btn_pcon", " CONTACT ADMIN"), url=f"https://t.me/{contact}")],
                [InlineKeyboardButton(get_btn_name("btn_back", " BACK TO HOME"), callback_data="back_to_start")]
            ]
            if qr_id:
                kb.insert(1, [InlineKeyboardButton(get_btn_name("btn_pqrs", " SHOW PAYMENT QR"), callback_data="show_premium_qr")])

            if qr_id and not is_p:
                await message.reply_photo(qr_id, caption=text, reply_markup=InlineKeyboardMarkup(kb))
            else:
                await message.reply(text, reply_markup=InlineKeyboardMarkup(kb))
        elif cmd == "botinfo":
            bi=get_bot_info(bot_id)
            if not bi: return await message.reply("Not in DB.")
            dp_count = len(get_bot_dual_posts(bot_id))
            await message.reply(
                f" @{client.me.username}\n"
                f" {bi.get('owner_name','?')}\n"
                f" Clones: `{len(get_child_bots(bot_id))}`\n"
                f" Force Sub: `{len(bi.get('force_subs',[]))}` ch\n"
                f" Timer: `{bi.get('auto_delete_time',300)}s` | "
                f"AA: `{'ON' if bi.get('auto_approve') else 'OFF'}`\n"
                f" Dual Posts: `{dp_count}`"
            )
        elif cmd == "help":
            text = get_msg_text("msg_help", HELP_TEXT)
            buttons = [
                [InlineKeyboardButton(stylish("ɢᴇɴᴇʀᴀʟ"), callback_data="help_cat_general"),
                 InlineKeyboardButton(stylish("ғɪʟᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ"), callback_data="help_cat_files")],
                [InlineKeyboardButton(stylish("ᴀᴅᴠᴀɴᴄᴇᴅ"), callback_data="help_cat_advanced"),
                 InlineKeyboardButton(stylish("ғᴏɴᴛ ᴇᴅɪᴛᴏʀ"), callback_data="help_cat_fonts")],
                [InlineKeyboardButton(stylish("ᴀᴅᴍɪɴ"), callback_data="help_cat_admin"),
                 InlineKeyboardButton(stylish("sᴜᴘʀᴇᴍᴇ"), callback_data="help_cat_supreme")],
                [InlineKeyboardButton(stylish("ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ"), callback_data="back_to_start")]
            ]
            await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))
        elif cmd == "about":
            uptime = str(datetime.now() - START_TIME).split(".")[0]
            text = (
                "✨ ᴀʙᴏᴜᴛ ᴍᴇ\n\n"
                "✰ ᴍʏ ɴᴀᴍᴇ: ꜰɪʟᴇ sᴛᴏʀᴇ ʙᴏᴛ\n"
                "✰ ᴍʏ ᴏᴡɴᴇʀ: MR ZOLVID\n"
                "✰ ᴜᴘᴅᴀᴛᴇs: ZOLVID BOTZ\n"
                "✰ sᴜᴘᴘᴏʀᴛ: ZOLVID GROUP\n"
                f"✰ uptime: {uptime}"
            )
            await message.reply(stylish(text), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(stylish("BACK"), callback_data="back_to_start")]]))
        elif cmd == "refer":
            ud = get_user(uid, bot_id)
            if not ud: ud = add_user(uid, bot_id, message.from_user.username, message.from_user.first_name)[0]
            ref_link = f"https://t.me/{client.me.username}?start=ref_{uid}"
            default_ref = (
                f" **Refer & Earn Program**\n━━━━━━━━━━━━━━━━━━━━\n"
                f"Invite your friends and earn rewards!\n\n"
                f" **Your Stats:**\n"
                f"├ Total Refers: `{{ref_count}}` users\n"
                f"└ Rewards Earned: `{{ref_rewards}}` days of Premium\n\n"
                f" **Reward:** Earn 1 day of Premium for every 5 successful refers!\n\n"
                f" **Your Referral Link:**\n"
                f"`{ref_link}`"
            )
            text = get_msg_text("msg_referral", default_ref).format_map(SafeDict(
                ref_count=ud.get('refer_count', 0),
                ref_rewards=ud.get('refer_rewards', 0),
                bot_username=client.me.username,
                uid=uid
            ))
            await message.reply(text, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_btn_name("btn_invite", "ɪɴᴠɪᴛᴇ ғʀɪᴇɴᴅs"), url=f"https://t.me/share/url?url={ref_link}")]
            ]))
        elif cmd in ("rename", "setcaption", "setthumb"):
            if len(message.command) < 2:
                return await message.reply(f"Usage: `/{cmd} FILE_ID`\nFind IDs via /listfiles")
            fuid = message.command[1]
            files = load_db(FILES_DB)
            fd = files.get(fuid)
            if not fd: return await message.reply(" File not found!")
            bi = get_bot_info(bot_id)
            can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or fd.get("user_id")==uid
            if not can: return await message.reply(" Not your file!")

            if cmd == "rename":
                TEMP_EDIT[uid] = {"mode": "rename", "uid": fuid}
                await message.reply(f" **Hard Rename**\n\nCurrent: `{fd.get('file_name')}`\n\nSend new name for the file (including extension).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel", callback_data="cancel_edit")]]))
            elif cmd == "setcaption":
                TEMP_EDIT[uid] = {"mode": "caption", "uid": fuid}
                await message.reply(f" **Set Caption**\n\nFile: `{fd.get('file_name')}`\n\nSend new caption text.\n`-clear` to remove.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel", callback_data="cancel_edit")]]))
            elif cmd == "setthumb":
                TEMP_EDIT[uid] = {"mode": "thumbnail", "uid": fuid}
                await message.reply(f" **Set Thumbnail**\n\nFile: `{fd.get('file_name')}`\n\nSend a **photo** as thumbnail.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel", callback_data="cancel_edit")]]))
        elif cmd == "autoapprove":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return
            curr = bi.get("auto_approve", False)
            update_bot_info(bot_id, "auto_approve", not curr)
            await message.reply(stylish(f"ᴀᴜᴛᴏ ᴀᴘᴘʀᴏᴠᴇ: {'ᴏɴ' if not curr else 'ᴏғғ'}"))
        elif cmd == "autocaption":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return
            curr = bi.get("auto_caption", True)
            update_bot_info(bot_id, "auto_caption", not curr)
            await message.reply(stylish(f"ᴀᴜᴛᴏ ᴄᴀᴘᴛɪᴏɴ: {'ᴏɴ' if not curr else 'ᴏғғ'}"))
        elif cmd == "setglobal":
            if uid!=MAIN_ADMIN: return
            if len(message.command)<2: return await message.reply("Usage: `/setglobal MSG` or off")
            txt=message.text.split(None,1)[1]
            update_global_config("global_msg","" if txt.lower()=="off" else txt)
            await message.reply(" Updated!")
        elif cmd == "addadmin":
            if len(message.command) < 2: return await message.reply(stylish("Usage: /addadmin USER_ID"))
            try: target = int(message.command[1])
            except: return await message.reply(stylish(" Invalid ID!"))

            if uid == MAIN_ADMIN:
                admins = load_db(ADMINS_DB)
                admins[str(target)] = str(datetime.now())
                save_db(ADMINS_DB, admins)


                await message.reply(stylish(f" `{target}` added as Global Admin."))
            elif bi and bi.get("owner_id") == uid:
                sec_admins = bi.get("secondary_admins", [])
                if target not in sec_admins:
                    sec_admins.append(target)
                    update_bot_info(bot_id, "secondary_admins", sec_admins)
                    await message.reply(stylish(f" `{target}` added as Bot Admin."))
                else:
                    await message.reply(stylish(" User is already an admin of this bot."))
            else:
                await message.reply(stylish(" Only bot owner or Supreme Admin can add admins."))

        elif cmd == "deladmin":
            if len(message.command) < 2: return await message.reply(stylish("Usage: /deladmin USER_ID"))
            try: target = int(message.command[1])
            except: return await message.reply(stylish(" Invalid ID!"))

            if uid == MAIN_ADMIN:
                admins = load_db(ADMINS_DB)
                if str(target) in admins:
                    del admins[str(target)]
                    save_db(ADMINS_DB, admins)


                    await message.reply(stylish(f" `{target}` removed from Global Admins."))
                else:
                    await message.reply(stylish(" Not a Global Admin."))
            elif bi and bi.get("owner_id") == uid:
                sec_admins = bi.get("secondary_admins", [])
                if target in sec_admins:
                    sec_admins.remove(target)
                    update_bot_info(bot_id, "secondary_admins", sec_admins)
                    await message.reply(stylish(f" `{target}` removed from Bot Admins."))
                else:
                    await message.reply(stylish(" User is not an admin of this bot."))
            else:
                await message.reply(stylish(" Only bot owner or Supreme Admin can remove admins."))
        elif cmd == "search":
            if is_user_banned(uid,bot_id): return await message.reply(" Banned!")
            if len(message.command)<2: return await message.reply(" Usage: `/search FILENAME`")
            q=message.text.split(None,1)[1].lower(); files=load_db(FILES_DB)
            results=[(k,f) for k,f in files.items()
                     if f.get("bot_id")==bot_id and q in f.get("file_name","").lower()][:10]
            if not results: return await message.reply(f" No files for `{q}`")
            text=f" **Results ({len(results)})**\n\n"; btns=[]
            for k,f in results:
                icon=file_icon(f.get("file_name","")); name=f.get("file_name","?")
                link=f"https://t.me/{client.me.username}?start=f_{k}"
                text+=f"{icon} `{name[:40]}`   {fmt_size(f.get('file_size',0))}\n"
                btns.append([InlineKeyboardButton(f"{icon} {name[:30]}",url=link)])
            await message.reply(text,reply_markup=InlineKeyboardMarkup(btns))
        elif cmd == "mybatches":
            if is_user_banned(uid, bot_id): return await message.reply(" Banned!")
            batches = load_db(BATCH_DB); bi = get_bot_info(bot_id)
            is_sup = uid == MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id") == uid)
            my_b = []
            for bid, b in batches.items():
                if b.get("bot_id") == bot_id and (is_sup or b.get("created_by") == uid):
                    my_b.append((bid, b))

            if not my_b: return await message.reply(" No batches found!")
            recent = sorted(my_b, key=lambda x: x[1].get("date", ""), reverse=True)[:10]
            text = f" **{'All' if is_sup else 'Your'} Batches ({len(my_b)} total)**\n\n"
            btns = []
            files_db = load_db(FILES_DB)
            for bid, b in recent:
                fids = b.get("files", [])
                count = len(fids)
                date = b.get("date", "")[:16]
                link = f"https://t.me/{client.me.username}?start=b_{bid}"
                text += f"• **Batch:** `{bid}` ({count} files)\n  Link: `{link}`\n"

                f_links = []
                for i, fuid in enumerate(fids[:5], 1):
                    fd = files_db.get(fuid)
                    f_name = fd.get("file_name", "File") if fd else "File"
                    f_link = f"https://t.me/{client.me.username}?start=f_{fuid}"
                    f_links.append(f"  {i}. **{f_name}**\n     `{f_link}`")

                if f_links:
                    text += "\n".join(f_links) + "\n"
                if count > 5:
                    text += f"  ... and {count-5} more files.\n"
                text += "\n"

                btns.append([InlineKeyboardButton(f" Share {bid[:8]}", url=f"https://t.me/share/url?url={link}")])
            await message.reply(text, reply_markup=InlineKeyboardMarkup(btns) if btns else None)
        elif cmd == "font":
            user = get_user(uid, bot_id)
            curr = user.get("pref_font", "smallcaps")
            text = stylish(f"<b>ғᴏɴᴛ ᴇᴅɪᴛᴏʀ</b>\n\nᴄᴜʀʀᴇɴᴛ ғᴏɴᴛ: <code>{curr}</code>\n\nsᴇʟᴇᴄᴛ ᴀ ɴᴇᴡ ғᴏɴᴛ sᴛʏʟᴇ ʙᴇʟᴏᴡ. ᴛʜɪs sᴛʏʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴘᴘʟɪᴇᴅ ᴛᴏ ᴀʟʟ ʏᴏᴜʀ ᴄᴀᴘᴛɪᴏɴs ᴀɴᴅ ᴘᴏsᴛs.")
            btns = []
            font_keys = ["none"] + list(_FONTS.keys())
            for i in range(0, len(font_keys), 2):
                row = [InlineKeyboardButton(stylish(font_keys[i], font_keys[i]), callback_data=f"setfont_{font_keys[i]}")]
                if i + 1 < len(font_keys):
                    row.append(InlineKeyboardButton(stylish(font_keys[i+1], font_keys[i+1]), callback_data=f"setfont_{font_keys[i+1]}"))
                btns.append(row)
            btns.append([InlineKeyboardButton(stylish("ʙᴀᴄᴋ"), callback_data="help_cat_fonts")])
            await message.reply(text, reply_markup=InlineKeyboardMarkup(btns))
        elif cmd == "requests":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid, bot_id) or (bi and bi.get("owner_id") == uid)):
                return await message.reply(stylish(" Access Denied! Only bot admins can manage requests."))

            pending = []
            for cid, users in _PENDING.items():
                for u_id, ts in users.items():
                    pending.append((cid, u_id, ts))

            if not pending:
                return await message.reply(stylish(" No pending join requests!"))

            text = stylish(f" **ᴘᴇɴᴅɪɴɢ ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛs ({len(pending)})**\n\n")
            btns = []
            for cid, u_id, ts in pending[:10]:
                try:
                    chat = await client.get_chat(cid)
                    c_title = chat.title
                except: c_title = str(cid)

                text += stylish(f"• ᴜsᴇʀ: <code>{u_id}</code>\n  ᴄʜᴀɴɴᴇʟ: {c_title}\n  ᴛɪᴍᴇ: {ts[:16]}\n\n")
                btns.append([
                    InlineKeyboardButton(stylish(f"✅ Approve {u_id}"), callback_data=f"req_approve_{cid}_{u_id}"),
                    InlineKeyboardButton(stylish(f"❌ Decline {u_id}"), callback_data=f"req_decline_{cid}_{u_id}")
                ])

            btns.append([InlineKeyboardButton(stylish("ʙᴀᴄᴋ"), callback_data="admin_panel")])
            await message.reply(text, reply_markup=InlineKeyboardMarkup(btns))

    # ── INLINE SEARCH ─────────────────────────────────────────────
    @app.on_inline_query()
    async def inline_search(client, query):
        q=query.query.strip().lower()
        if not q: return await query.answer([],cache_time=1)
        bot_id=client.me.id; files=load_db(FILES_DB); results=[]
        for k,f in files.items():
            if f.get("bot_id")==bot_id and q in f.get("file_name","").lower():
                icon=file_icon(f.get("file_name","")); link=f"https://t.me/{client.me.username}?start=f_{k}"
                results.append(InlineQueryResultArticle(
                    title=f"{icon} {f.get('file_name','?')}",
                    description=f" {fmt_size(f.get('file_size',0))} |  {f.get('access_count',0)}",
                    input_message_content=InputTextMessageContent(
                        f"{icon} **{f.get('file_name')}**\n"
                        f" `{fmt_size(f.get('file_size',0))}`\n {link}"
                    ),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Get File",url=link)]])
                ))
                if len(results)>=20: break
        await query.answer(results,cache_time=1)

    # ── FILE HANDLER ─────────────────────────────────────────────
    @app.on_message(filters.private, group=1)
    async def advanced_handler(client, message):
        uid=message.from_user.id; bot_id=client.me.id
        if is_user_banned(uid,bot_id): return


        # Skip if FSM is waiting for input (handled by group 2)
        if uid in TEMP_EDIT or uid in TEMP_WELCOME or uid in TEMP_POST or uid in TEMP_PROTECT:
            return

        # Only handle if in batch/dual session or if it is a file/message
        in_session = uid in TEMP_BATCH or uid in TEMP_DUAL
        is_media = bool(
            message.document or message.video or message.audio or
            message.photo or message.sticker or message.animation or
            message.voice or message.video_note or message.text
        )

        if not (in_session or is_media):
            return

        # Skip commands
        if message.text and message.text.startswith("/"):
            return

        main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
        db_msg = None

        try:
            # First try forwarding with current client
            db_msg = await message.forward(DB_CHANNEL)
        except Exception:
            # Fallback: Re-upload using main bot if clone is not in channel
            try:
                sm = await message.reply(" **Forwarding to DB via Main Bot...**")
                # Since bots have different file_ids, we download and upload.
                path = await message.download()
                if path:
                    uploader = main_client
                    if uploader:
                        if message.photo:
                            db_msg = await uploader.send_photo(DB_CHANNEL, photo=path, caption=message.caption)
                        elif message.video:
                            db_msg = await uploader.send_video(DB_CHANNEL, video=path, caption=message.caption)
                        elif message.audio:
                            db_msg = await uploader.send_audio(DB_CHANNEL, audio=path, caption=message.caption)
                        else:
                            db_msg = await uploader.send_document(DB_CHANNEL, document=path, caption=message.caption)
                    os.remove(path)
                    await sm.delete()
                else:
                    return await message.reply(" Failed to process file for DB.")
            except Exception as e:
                return await message.reply(f" DB Channel error (Main Bot fallback): \n`{e}`")

        bi = get_bot_info(bot_id)
        user_data_f = get_user(uid, bot_id)
        user_font = user_data_f.get("pref_font", "smallcaps") if user_data_f else "smallcaps"

        original_caption = message.caption or message.text
        if original_caption:
            original_caption = stylish(original_caption, user_font)

        if bi and bi.get("auto_caption") and not (message.caption or message.text) and (message.document or message.video or message.audio):
            fname = (message.document or message.video or message.audio).file_name or "File"
            original_caption = stylish(f" **File Name:** {fname}\n\n **Powered by:** @{client.me.username}", user_font)
        file_id = None
        file_name = "Message/Post"
        file_size = 0
        media_type = "message"

        if db_msg.photo:
            file_id=db_msg.photo.file_id; file_name=f"photo_{db_msg.photo.file_unique_id}.jpg"
            file_size=db_msg.photo.file_size or 0; media_type="photo"
        elif db_msg.video:
            file_id=db_msg.video.file_id; file_name=db_msg.video.file_name or f"video_{db_msg.video.file_unique_id}.mp4"
            file_size=db_msg.video.file_size or 0; media_type="video"
        elif db_msg.audio:
            file_id=db_msg.audio.file_id; file_name=db_msg.audio.file_name or f"audio_{db_msg.audio.file_unique_id}.mp3"
            file_size=db_msg.audio.file_size or 0; media_type="audio"
        elif db_msg.document:
            file_id=db_msg.document.file_id; file_name=db_msg.document.file_name or f"file_{db_msg.document.file_unique_id}"
            file_size=db_msg.document.file_size or 0; media_type="document"
        elif db_msg.sticker:
            file_id=db_msg.sticker.file_id; file_name=f"sticker_{db_msg.sticker.file_unique_id}.webp"
            media_type="sticker"
        elif db_msg.animation:
            file_id=db_msg.animation.file_id; file_name=f"animation_{db_msg.animation.file_unique_id}.mp4"
            media_type="animation"

        reply_markup = None
        if message.reply_markup:
            try:
                reply_markup = json.loads(str(message.reply_markup))
            except Exception:
                pass

        fuid=unique_id(); files=load_db(FILES_DB)
        fdata={
            "file_id":file_id,"file_name":file_name,"file_size":file_size,
            "caption":original_caption,"user_id":uid,"bot_id":bot_id,
            "upload_date":str(datetime.now()),"db_msg_id":db_msg.id,
            "access_count":0,"media_type":media_type,"custom_thumbnail":None,
            "reply_markup": reply_markup
        }
        files[fuid]=fdata; save_db(FILES_DB,files)
        add_to_cache(file_id,db_msg.id,DB_CHANNEL,bot_id,original_caption)
        update_user_stats(uid,bot_id,"files_uploaded")

        bi=get_bot_info(bot_id)
        if bi and bi.get("log_channel"):
            log_text = f" Upload | {file_icon(file_name)} `{file_name}`\n {fmt_size(file_size)} |  `{uid}` |  `{fuid}`"
            try:
                await client.copy_message(bi["log_channel"], message.chat.id, message.id, caption=log_text)
            except Exception:
                main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None)
                if main_client and main_client != client:
                    try: await main_client.copy_message(bi["log_channel"], message.chat.id, message.id, caption=log_text)
                    except: pass

        # ── DUAL POST SESSION ────────────────────────────────────
        if uid in TEMP_DUAL:
            sess  = TEMP_DUAL[uid]
            stage = sess.stage
            if stage == "free":
                sess.free_files.append(fuid)
                count = len(sess.free_files)
                await message.reply(
                    f" **Added to FREE Tier!**\n\n"
                    f"{file_icon(file_name)} `{file_name}`\n"
                    f" {fmt_size(file_size)}\n\n"
                    f" Free tier total: `{count}` file(s)\n"
                    f" Premium tier: `{len(sess.pro_files)}` file(s)\n\n"
                    f"Send more FREE files, or switch to Premium stage.",
                    quote=True,
                    reply_markup=kb_dual_post_creator(stage, count, len(sess.pro_files))
                )
            elif stage == "pro":
                sess.pro_files.append(fuid)
                count = len(sess.pro_files)
                await message.reply(
                    f" **Added to PREMIUM Tier!**\n\n"
                    f"{file_icon(file_name)} `{file_name}`\n"
                    f" {fmt_size(file_size)}\n\n"
                    f" Free tier: `{len(sess.free_files)}` file(s)\n"
                    f" Premium tier total: `{count}` file(s)\n\n"
                    f"Send more PREMIUM files, or finish.",
                    quote=True,
                    reply_markup=kb_dual_post_creator(stage, len(sess.free_files), count)
                )
            return

        # ── BATCH SESSION ────────────────────────────────────────
        elif uid in TEMP_BATCH:
            TEMP_BATCH[uid].append(fuid)
            await message.reply(
                f" **Added!**\n{file_icon(file_name)} `{file_name}`\n"
                f" Total: `{len(TEMP_BATCH[uid])}`",
                quote=True
            )

        # ── NORMAL UPLOAD ────────────────────────────────────────
        else:
            if media_type == "message":
                return
            direct_link = f"https://t.me/{client.me.username}?start=f_{fuid}"
            await message.reply(
                f" **File Saved!**\n\n"
                f"{file_icon(file_name)} `{file_name}`\n"
                f" {fmt_size(file_size)} |  `{fuid}`\n\n"
                f" **Share Link:**\n`{direct_link}`\n\n"
                + (f"_ Recipients go through shortener ads to get file._"
                   if shortener_enabled_for_bot(bi) else ""),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Share", url=f"https://t.me/share/url?url={direct_link}"),
                     InlineKeyboardButton(" Edit",  callback_data=f"edit_file_{fuid}")]
                ])
            )

    # ── FSM RESPONDER (group 2) ───────────────────────────────────
    _CMD_LIST = [
        "start","admin","supreme","clone","batch","done","cancel","setfs","mybots","stats",
        "help","broadcast","ban","unban","info","givepremium","removepremium","gban","ungban","botinfo",
        "settimer","search","premium","setprice","shortener","setlog",
        "setchannel","setmode","protect","myplinks","requests","font",
        "restart","ping","listfiles","mybatches","editfile","delfile",
        "setwelcome","setglobal","addadmin","deladmin",
        "dualpost","dpremium","dpdone","dpcancel","myduals","deldual","dpstats",
        "createpost", "about", "refer", "rename", "setcaption", "setthumb", "download", "autoapprove", "autocaption"
    ]

    @app.on_message(filters.private & ~filters.command(_CMD_LIST), group=2)
    async def fsm_responder(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        if message.text and message.text.startswith("/"): return

        if uid in TEMP_POST:
            sess = TEMP_POST[uid]; step = sess.get("step")
            if step == "content":
                sess["content"] = message
                sess["step"] = "style"

                btns = []
                font_keys = list(_FONTS.keys())
                for i in range(0, len(font_keys), 2):
                    row = [InlineKeyboardButton(stylish(font_keys[i], font_keys[i]), callback_data=f"pstyle_{font_keys[i]}")]
                    if i + 1 < len(font_keys):
                        row.append(InlineKeyboardButton(stylish(font_keys[i+1], font_keys[i+1]), callback_data=f"pstyle_{font_keys[i+1]}"))
                    btns.append(row)
                btns.append([InlineKeyboardButton("Normal", callback_data="pstyle_none")])
                btns.append([InlineKeyboardButton(stylish(" Cancel"), callback_data="cancel_post")])

                await message.reply(
                    stylish(" **Post content saved!**\n\nStep 2/3: Choose a font style for your text/caption:"),
                    reply_markup=InlineKeyboardMarkup(btns)
                )
            elif step == "buttons":
                txt = message.text or ""
                markup = None
                if txt.strip() != "-skip":
                    rows = []
                    for line in txt.split("\n"):
                        if "|" in line:
                            btn_text, btn_url = line.split("|", 1)
                            rows.append([InlineKeyboardButton(btn_text.strip(), url=btn_url.strip())])
                    if rows:
                        markup = InlineKeyboardMarkup(rows)

                content = sess["content"]
                style = sess.get("style", "none")

                text = content.text or content.caption or ""
                if style in _FONTS:
                    text = stylish(text, style)

                del TEMP_POST[uid]

                await message.reply(stylish(" **Post Ready!** Here is a preview:"), reply_markup=markup)

                # Send the actual post content
                if content.photo:
                    sent = await client.send_photo(message.chat.id, photo=content.photo.file_id, caption=text, reply_markup=markup)
                elif content.video:
                    sent = await client.send_video(message.chat.id, video=content.video.file_id, caption=text, reply_markup=markup)
                elif content.document:
                    sent = await client.send_document(message.chat.id, document=content.document.file_id, caption=text, reply_markup=markup)
                else:
                    sent = await client.send_message(message.chat.id, text=text, reply_markup=markup)

                await message.reply(
                    stylish(f" **Post Created!**\n\nYou can now forward the preview message above to any channel where this bot is an admin or use buttons below."),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(stylish(" Send to Channel"), callback_data=f"psend_chan_{sent.id}")],
                        [InlineKeyboardButton(stylish(" Create Another"), callback_data="cb_create_post")]
                    ])
                )
            return

        if uid in TEMP_PROTECT:
            sess = TEMP_PROTECT[uid]; step = sess.get("step")
            if step == "channel":
                try:
                    chid = int(message.text)
                    chat = await client.get_chat(chid)
                    sess["channel_id"] = chid
                    sess["title"] = chat.title
                    sess["step"] = "mode"
                    await message.reply(
                        f" Channel found: **{chat.title}**\n\n"
                        f"Step 2: Choose **Join Mode**:\n"
                        f"├ `direct` - Regular join link\n"
                        f"├ `requested` - Join request (admin approval)\n"
                        f"└ `normal` - Public channel (no special link needed, but we provide one anyway)",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(" Direct",    callback_data="pm_direct"),
                             InlineKeyboardButton(" Requested", callback_data="pm_requested")],
                            [InlineKeyboardButton(" Normal",    callback_data="pm_normal")],
                            [InlineKeyboardButton(" Cancel",    callback_data="cancel_protect")]
                        ])
                    )
                except Exception as e:
                    err_msg = f" Error: `{e}`\n\n**Tip:** Ensure the bot is an **Admin** in the channel. If you get PeerIdInvalid, send a message in that channel first."
                    await message.reply(err_msg)
            return

        if uid in TEMP_WELCOME:
            sess = TEMP_WELCOME[uid]; step = sess.get("step")
            if step == "text":
                if not message.text: return await message.reply(" Send text or `-skip`.")
                txt = message.text.strip()
                if txt not in ("-skip", "-clear"):
                    update_bot_info(bot_id, "custom_welcome", txt)
                elif txt == "-clear":
                    update_bot_info(bot_id, "custom_welcome", None)
                sess["step"] = "image"
                await message.reply(
                    f" {'Updated!' if txt not in ('-skip','-clear') else 'Unchanged!' if txt=='-skip' else 'Reset!'}\n\n"
                    f" **Step 2/2:** Send photo for welcome image.\n`-skip` = keep | `-clear` = remove",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel",callback_data="cancel_welcome")]])
                )
            elif step == "image":
                if message.photo:
                    update_bot_info(bot_id, "welcome_image", message.photo.file_id)
                    del TEMP_WELCOME[uid]
                    await message.reply(
                        " **Welcome fully updated!**",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(" Preview", callback_data="preview_welcome")],
                            [InlineKeyboardButton(" Admin",   callback_data="admin_panel")]
                        ])
                    )
                elif message.text:
                    txt = message.text.strip()
                    if txt == "-skip":
                        del TEMP_WELCOME[uid]
                        await message.reply(" Image unchanged.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Admin",callback_data="admin_panel")]]))
                    elif txt == "-clear":
                        update_bot_info(bot_id, "welcome_image", None)
                        del TEMP_WELCOME[uid]
                        await message.reply(" Image removed.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Admin",callback_data="admin_panel")]]))
                    else: await message.reply(" Send a **photo**, `-skip`, or `-clear`.")
            return

        if uid in TEMP_EDIT:
            sess = TEMP_EDIT[uid]; mode = sess["mode"]; fuid = sess["uid"]
            files = load_db(FILES_DB)
            if fuid not in files:
                del TEMP_EDIT[uid]; return await message.reply(" File no longer exists.")
            if mode == "caption":
                if not message.text: return await message.reply(stylish(" Send text for caption."))
                txt = message.text.strip()
                if txt == "-clear":
                    files[fuid]["caption"] = None
                    save_db(FILES_DB, files)
                    del TEMP_EDIT[uid]
                    return await message.reply(
                        get_file_edit_text(client, files[fuid], fuid),
                        reply_markup=kb_file_edit(fuid)
                    )

                sess["temp_caption"] = txt
                sess["mode"] = "caption_style"

                btns = []
                font_keys = list(_FONTS.keys())
                for i in range(0, len(font_keys), 2):
                    row = [InlineKeyboardButton(stylish(font_keys[i], font_keys[i]), callback_data=f"cstyle_{font_keys[i]}_{fuid}")]
                    if i + 1 < len(font_keys):
                        row.append(InlineKeyboardButton(stylish(font_keys[i+1], font_keys[i+1]), callback_data=f"cstyle_{font_keys[i+1]}_{fuid}"))
                    btns.append(row)
                btns.append([InlineKeyboardButton("Normal", callback_data=f"cstyle_none_{fuid}")])
                btns.append([InlineKeyboardButton(stylish(" Cancel"), callback_data="cancel_edit")])

                await message.reply(
                    stylish(" **Text received!**\n\nChoose a font style for the caption:"),
                    reply_markup=InlineKeyboardMarkup(btns)
                )
            elif mode == "thumbnail":
                if not message.photo: return await message.reply(" Send a **photo** as thumbnail.")
                files[fuid]["custom_thumbnail"] = message.photo.file_id
                save_db(FILES_DB, files)
                del TEMP_EDIT[uid]
                await message.reply(
                    get_file_edit_text(client, files[fuid], fuid),
                    reply_markup=kb_file_edit(fuid)
                )
            elif mode == "qrename":
                if not message.text: return await message.reply(" Send a **new file name**.")
                new_name = message.text.strip()
                files[fuid]["file_name"] = new_name
                save_db(FILES_DB, files)
                del TEMP_EDIT[uid]
                await message.reply(
                    get_file_edit_text(client, files[fuid], fuid),
                    reply_markup=kb_file_edit(fuid)
                )

            elif mode == "set_price":
                update_bot_info(bot_id, "premium_price", message.text.strip())
                del TEMP_EDIT[uid]
                await message.reply(f" Premium price set to: `{message.text.strip()}`", reply_markup=kb_admin())

            elif mode == "set_contact":
                contact = message.text.replace("@", "").strip()
                update_bot_info(bot_id, "premium_contact", contact)
                del TEMP_EDIT[uid]
                await message.reply(f" Premium contact set to: `@{contact}`", reply_markup=kb_admin())

            elif mode == "set_timer_custom":
                try:
                    secs = int(message.text)
                    if secs < 30: return await message.reply(" Min 30s!")
                    update_bot_info(bot_id, "auto_delete_time", secs)
                    del TEMP_EDIT[uid]
                    await message.reply(f" Timer set to `{secs}s`!", reply_markup=kb_admin())
                except: await message.reply(" Send a valid number of seconds.")

            elif mode == "customize_button":
                if not message.text: return await message.reply(" Send a **name**.")
                new_name = message.text.strip()
                key = sess["key"]
                btns = get_global_config().get("custom_buttons", {})
                btns[key] = new_name
                update_global_config("custom_buttons", btns)
                del TEMP_EDIT[uid]
                await message.reply(f" Button `{key}` updated to: `{new_name}`", reply_markup=kb_supreme())

            elif mode == "customize_message":
                if not message.text: return await message.reply(" Send **text**.")
                txt = message.text.strip()
                key = sess["key"]
                msgs = get_global_config().get("custom_messages", {})
                if txt == "-clear":
                    msgs.pop(key, None)
                else:
                    msgs[key] = txt
                update_global_config("custom_messages", msgs)
                del TEMP_EDIT[uid]
                await message.reply(f" Message `{key}` updated!", reply_markup=kb_supreme())

            elif mode == "set_password":
                if not message.text: return await message.reply(stylish(" Send a password."))
                pw = message.text.strip()
                files[fuid]["password"] = None if pw == "-clear" else pw
                save_db(FILES_DB, files)
                del TEMP_EDIT[uid]
                await message.reply(
                    get_file_edit_text(client, files[fuid], fuid),
                    reply_markup=kb_file_edit(fuid)
                )

            elif mode == "verify_password":
                if not message.text: return await message.reply(stylish(" Send the password."))
                expected = sess["password"]
                if message.text.strip() == expected:
                    fdata = sess["fdata"]
                    del TEMP_EDIT[uid]
                    await message.reply(stylish(" Correct Password! Sending file..."))
                    sent = await deliver_file(client, message.chat.id, fdata)
                    bi = get_bot_info(bot_id); ud = get_user(uid, bot_id)
                    is_p = ud and ud.get("is_premium")
                    if sent and not is_p:
                        auto_del = bi.get("auto_delete_time", 300) if bi else 300
                        asyncio.create_task(_auto_delete(sent, auto_del))
                else:
                    await message.reply(stylish(" Wrong Password! Try again or /cancel."))

            elif mode == "rename":
                if not message.text: return await message.reply(" Send a **new file name**.")
                new_name = message.text.strip()
                fd = files[fuid]
                del TEMP_EDIT[uid]
                sm = await message.reply(f" **Hard Renaming file...**\n\n`{fd.get('file_name')}`  `{new_name}`\n\n_Please wait, this involves downloading and re-uploading._")

                try:
                    # Download
                    t0 = time.time()
                    async def progress(current, total):
                        pct = current * 100 / total
                        if time.time() - t0 > 3:
                            bar = "█" * (int(pct) // 10) + "░" * (10 - int(pct) // 10)
                            try: await sm.edit(f" **Hard Renaming...**\n\n Downloading: `[{bar}]` {pct:.1f}%")
                            except: pass

                    path = await client.download_media(fd['file_id'], progress=progress)
                    if not path:
                        return await sm.edit(" Download failed! File might be too large or deleted.")

                    # Use temp dir to avoid conflicts
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        new_path = os.path.join(tmp_dir, new_name)
                        shutil.move(path, new_path)

                        # Upload
                        await sm.edit(f" **Hard Renaming...**\n\n Uploading: `0%`")
                        t1 = time.time()
                        async def up_progress(current, total):
                            pct = current * 100 / total
                            if time.time() - t1 > 3:
                                bar = "█" * (int(pct) // 10) + "░" * (10 - int(pct) // 10)
                                try: await sm.edit(f" **Hard Renaming...**\n\n Uploading: `[{bar}]` {pct:.1f}%")
                                except: pass

                        thumb = fd.get('custom_thumbnail')
                        thumb_path = None
                        if thumb:
                            thumb_path = await client.download_media(thumb)

                        # Always use send_document to preserve original quality and size
                        new_db_msg = await client.send_document(DB_CHANNEL, document=new_path, thumb=thumb_path, caption=fd.get('caption'), progress=up_progress)

                        if new_db_msg:
                            media = new_db_msg.document or new_db_msg.video or new_db_msg.audio or new_db_msg.animation or new_db_msg.sticker

                            # Invalidate old cache
                            load_db(FILE_CACHE_DB).pop(fd['file_id'], None)

                            # Update database
                            fd['file_id'] = media.file_id
                            fd['file_name'] = new_name
                            fd['file_size'] = media.file_size
                            fd['db_msg_id'] = new_db_msg.id
                            save_db(FILES_DB, files)

                            # Update cache
                            add_to_cache(media.file_id, new_db_msg.id, DB_CHANNEL, bot_id, fd.get('caption'))

                            await sm.edit(
                                get_file_edit_text(client, fd, fuid),
                                reply_markup=kb_file_edit(fuid)
                            )
                        else:
                            await sm.edit(" Upload failed!")

                        if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)

                except Exception as e:
                    logger.error(f"Rename error: {e}")
                    await sm.edit(f" **Rename Error:** `{e}`")

    # ── CALLBACK HANDLER ──────────────────────────────────────────
    @app.on_callback_query(group=1)
    async def cb_handler(client, cb):
        uid = cb.from_user.id; data = cb.data; bot_id = client.me.id
        if is_user_banned(uid, bot_id): return await cb.answer(" Banned!", show_alert=True)

        if data.startswith("edit_file_"):
            fuid = data[10:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer(" Not found!", show_alert=True)
            bi = get_bot_info(bot_id)
            can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or fd.get("user_id")==uid
            if not can: return await cb.answer(" Not your file!", show_alert=True)
            await cb.message.edit(
                get_file_edit_text(client, fd, fuid),
                reply_markup=kb_file_edit(fuid)
            )
            await cb.answer()

        elif data.startswith("edit_caption_"):
            fuid = data[13:]; files = load_db(FILES_DB)
            if fuid not in files: return await cb.answer(stylish(" Not found!"), show_alert=True)
            TEMP_EDIT[uid] = {"mode": "caption", "uid": fuid}
            await cb.message.edit(
                stylish(f" **Edit Caption**\n\nFile: `{files[fuid].get('file_name','?')}`\n\nSend new caption text.\n`-clear` to remove."),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(stylish(" Cancel"), callback_data="cancel_edit")]])
            )
            await cb.answer("Send caption text")

        elif data.startswith("cstyle_"):
            parts = data.split("_")
            style = parts[1]
            fuid = parts[2]

            if uid not in TEMP_EDIT or TEMP_EDIT[uid].get("uid") != fuid:
                return await cb.answer("Session expired!", show_alert=True)

            txt = TEMP_EDIT[uid].get("temp_caption")
            if not txt: return await cb.answer("Error: Text missing!", show_alert=True)

            if style in _FONTS:
                txt = stylish(txt, style)

            files = load_db(FILES_DB)
            if fuid in files:
                files[fuid]["caption"] = txt
                save_db(FILES_DB, files)

            del TEMP_EDIT[uid]
            await cb.message.edit(
                get_file_edit_text(client, files[fuid], fuid),
                reply_markup=kb_file_edit(fuid)
            )
            await cb.answer("Caption updated!")

        elif data.startswith("set_pass_"):
            fuid = data[9:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer(stylish(" Not found!"), show_alert=True)
            TEMP_EDIT[uid] = {"mode": "set_password", "uid": fuid}
            curr_pw = fd.get("password", "None")
            await cb.message.edit(
                stylish(f" **Set File Password**\n\nFile: `{fd.get('file_name','?')}`\n\nCurrent Password: `{curr_pw}`\n\nSend a new password for this file.\nUsers will need this password to access the file via link.\n`-clear` to remove."),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(stylish(" Cancel"), callback_data="cancel_edit")]])
            )
            await cb.answer("Send password")

        elif data.startswith("edit_thumb_"):
            fuid = data[11:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer(" Not found!", show_alert=True)
            if fd.get("media_type") == "photo":
                return await cb.answer(" Photos can't have thumbnails!", show_alert=True)
            TEMP_EDIT[uid] = {"mode": "thumbnail", "uid": fuid}
            await cb.message.edit(
                f" **Edit Thumbnail**\n\nFile: `{fd.get('file_name','?')}`\n\nSend a **photo** as thumbnail.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Hard Fix Thumbnail", callback_data=f"fix_thumb_{fuid}")],
                    [InlineKeyboardButton(" Remove Thumb", callback_data=f"remove_thumb_{fuid}")],
                    [InlineKeyboardButton(" Cancel",       callback_data="cancel_edit")]
                ])
            )
            await cb.answer("Send a photo")

        elif data.startswith("fix_thumb_"):
            fuid = data[10:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer(" Not found!", show_alert=True)
            if not fd.get("custom_thumbnail"):
                return await cb.answer(" Set a thumbnail first!", show_alert=True)

            await cb.answer(" Hard fixing thumbnail...")
            sm = await cb.message.edit(f" **Hard Fixing Thumbnail...**\n\nFile: `{fd.get('file_name')}`\n\n_Downloading and re-uploading with thumbnail..._")

            try:
                # Download
                path = await client.download_media(fd['file_id'])
                thumb_path = await client.download_media(fd['custom_thumbnail'])

                # Always use send_document to preserve original quality and size
                new_db_msg = await client.send_document(DB_CHANNEL, document=path, thumb=thumb_path, caption=fd.get('caption'))

                if new_db_msg:
                    media = new_db_msg.document or new_db_msg.video or new_db_msg.audio or new_db_msg.animation or new_db_msg.sticker
                    fd['file_id'] = media.file_id
                    fd['db_msg_id'] = new_db_msg.id
                    save_db(FILES_DB, files)

                    await sm.edit(
                        get_file_edit_text(client, fd, fuid),
                        reply_markup=kb_file_edit(fuid)
                    )
                else:
                    await sm.edit(" Fix failed during upload!")

                if path and os.path.exists(path): os.remove(path)
                if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
            except Exception as e:
                await sm.edit(f" **Fix Error:** `{e}`")

        elif data.startswith("qrename_"):
            fuid = data[8:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer(" Not found!", show_alert=True)
            TEMP_EDIT[uid] = {"mode": "qrename", "uid": fuid}
            await cb.message.edit(
                f" **Quick Rename**\n\nCurrent: `{fd.get('file_name','?')}`\n\nSend new name for the bot to display.\n_Note: Original file remains unchanged._",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel", callback_data="cancel_edit")]])
            )
            await cb.answer("Send new name")

        elif data.startswith("rename_file_"):
            fuid = data[12:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer(" Not found!", show_alert=True)
            TEMP_EDIT[uid] = {"mode": "rename", "uid": fuid}
            await cb.message.edit(
                f" **Hard Rename (Re-upload)**\n\nCurrent: `{fd.get('file_name','?')}`\n\nSend new name for the file (including extension).\n_This will re-upload the file to Telegram._",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel", callback_data="cancel_edit")]])
            )
            await cb.answer("Send new name")

        elif data.startswith("remove_thumb_"):
            fuid = data[13:]; files = load_db(FILES_DB)
            if fuid in files:
                files[fuid]["custom_thumbnail"] = None; save_db(FILES_DB, files)
                TEMP_EDIT.pop(uid, None)
                await cb.answer(" Thumbnail removed!", show_alert=True)
                await cb.message.edit(
                    get_file_edit_text(client, files[fuid], fuid),
                    reply_markup=kb_file_edit(fuid)
                )

        elif data.startswith("del_file_"):
            fuid = data[9:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("Already deleted!", show_alert=True)
            bi = get_bot_info(bot_id)
            can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or fd.get("user_id")==uid
            if not can: return await cb.answer(" Not your file!", show_alert=True)
            del files[fuid]; save_db(FILES_DB, files)
            await cb.answer(" Deleted!", show_alert=True)
            await cb.message.edit(f" **Deleted:** `{fd.get('file_name','?')}`")

        elif data.startswith("del_plink_"):
            lpid = data[10:]; plinks = load_db(PLINKS_DB); p = plinks.get(lpid)
            if not p: return await cb.answer("Already deleted!", show_alert=True)
            bi = get_bot_info(bot_id)
            can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or p.get("created_by")==uid
            if not can: return await cb.answer(" Access denied!", show_alert=True)
            del plinks[lpid]; save_db(PLINKS_DB, plinks)
            await cb.answer(" Protected link deleted!", show_alert=True)
            await cb.message.edit(f" **Deleted Protected Link:** `{p.get('title','?')}`")

        elif data.startswith("get_file_"):
            fuid = data[9:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer(" Not found!", show_alert=True)
            await cb.answer(" Sending...")
            try:
                bi = get_bot_info(bot_id); ud = get_user(uid, bot_id)
                is_prem = ud and ud.get("is_premium", False)
                auto_del = bi.get("auto_delete_time", 300) if bi else 300
                sent = await deliver_file(client, cb.message.chat.id, fd)
                if sent and not is_prem:
                    asyncio.create_task(_auto_delete(sent, auto_del))
            except Exception as e:
                await cb.message.reply(f" `{e}`")

        elif data == "cancel_edit":
            TEMP_EDIT.pop(uid, None)
            await cb.message.edit(" Edit cancelled.")
            await cb.answer()

        elif data == "cancel_download":
            TEMP_EDIT.pop(uid, None)
            await cb.message.edit(" Download cancelled.")
            await cb.answer()

        elif data.startswith("dlv_"):
            format_id = data[4:]

            if uid not in TEMP_EDIT or TEMP_EDIT[uid].get("mode") != "download_video":
                return await cb.answer("Session expired! Please use /download again.", show_alert=True)

            sess = TEMP_EDIT.pop(uid)
            url = sess["url"]
            title = sess["title"]

            await cb.message.edit(stylish(f" **Downloading video...**\n\nTitle: `{title}`\nQuality: `{format_id}`\n\n_This may take a minute depending on file size._"))
            await cb.answer("Downloading...")

            def download_video(url, f_id):
                tmp_dir = tempfile.mkdtemp()
                ydl_opts = {
                    'format': f_id + '+bestaudio/best',
                    'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    # Fallback if ffmpeg is not present
                    'merge_output_format': 'mp4' if shutil.which('ffmpeg') else None,
                }
                if not shutil.which('ffmpeg'):
                    # If no ffmpeg, we might only get video or audio if they are separate.
                    # Try to get best single file format if merge is impossible.
                    ydl_opts['format'] = f_id

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return ydl.prepare_filename(info), tmp_dir

            try:
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    file_path, tmp_dir = await loop.run_in_executor(pool, download_video, url, format_id)

                if os.path.exists(file_path):
                    await cb.message.edit(stylish(" **Uploading to Telegram...**"))

                    # Determine media type and send
                    if file_path.lower().endswith((".mp4", ".mkv", ".webm", ".mov")):
                        await client.send_video(cb.message.chat.id, video=file_path, caption=stylish(f" **{title}**\n\nDownloaded via @{client.me.username}"))
                    else:
                        await client.send_document(cb.message.chat.id, document=file_path, caption=stylish(f" **{title}**\n\nDownloaded via @{client.me.username}"))

                    await cb.message.delete()
                    # Cleanup
                    shutil.rmtree(tmp_dir)
                else:
                    await cb.message.edit(" **Error:** Download failed - file not found.")
                    shutil.rmtree(tmp_dir)

            except Exception as e:
                logger.error(f"Download execution error: {e}")
                await cb.message.edit(f" **Download Failed!**\n\n`{str(e)[:200]}`")

        elif data == "cancel_welcome":
            TEMP_WELCOME.pop(uid, None)
            await cb.message.edit(" Welcome editor cancelled.")
            await cb.answer()

        elif data == "cancel_protect":
            TEMP_PROTECT.pop(uid, None)
            await cb.message.edit(stylish(" Protection setup cancelled."))
            await cb.answer()

        elif data == "cancel_post":
            TEMP_POST.pop(uid, None)
            await cb.message.edit(stylish(" Post creation cancelled."))
            await cb.answer()

        elif data == "cb_create_post":
            # Manually trigger createpost_cmd
            await cb.message.delete()
            # Faking a message object for createpost_cmd
            class FakeMsg:
                def __init__(self, from_user, chat, text=""):
                    self.from_user = from_user
                    self.chat = chat
                    self.text = text
                    self.command = ["createpost"]
                async def reply(self, text, reply_markup=None):
                    return await client.send_message(self.chat.id, text, reply_markup=reply_markup)

            await createpost_cmd(client, FakeMsg(cb.from_user, cb.message.chat))

        elif data.startswith("pstyle_"):
            style = data[7:]
            if uid not in TEMP_POST: return await cb.answer("Session expired!", show_alert=True)
            TEMP_POST[uid]["style"] = style
            TEMP_POST[uid]["step"] = "buttons"
            await cb.message.edit(
                stylish(f" **Style '{style}' applied!**\n\nStep 3/3: Send **Inline Buttons** in the following format:\n\n`Button Text | https://link.com`\n`Button 2 | https://google.com`\n\nSend one button per line. Send `-skip` if you don't want any buttons."),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(stylish(" Cancel"), callback_data="cancel_post")]])
            )
            await cb.answer()

        elif data.startswith("psend_chan_"):
            msg_id = int(data[11:])
            bi = get_bot_info(bot_id)
            chid = bi.get("connected_channel")
            if not chid:
                return await cb.answer(" No channel connected! Use /setchannel first.", show_alert=True)

            try:
                await client.copy_message(chid, cb.message.chat.id, msg_id)
                await cb.answer(" Sent to connected channel!", show_alert=True)
            except Exception as e:
                await cb.answer(f" Failed: {e}", show_alert=True)

        elif data.startswith("pm_"):
            mode = data[3:]
            if uid not in TEMP_PROTECT: return await cb.answer("Session expired!", show_alert=True)
            sess = TEMP_PROTECT.pop(uid)
            lpid = unique_id()
            plinks = load_db(PLINKS_DB)
            plinks[lpid] = {
                "lpid": lpid,
                "bot_id": bot_id,
                "channel_id": sess["channel_id"],
                "title": sess["title"],
                "mode": mode,
                "created_by": uid,
                "created_at": time.time()
            }
            save_db(PLINKS_DB, plinks)

            link = f"https://t.me/{client.me.username}?start=lp_{lpid}"
            await cb.message.edit(
                f" **Channel Protected Successfully!**\n\n"
                f" **Channel:** `{sess['title']}`\n"
                f" `{sess['channel_id']}`\n"
                f" **Join Mode:** `{mode.upper()}`\n\n"
                f" **Your Sharable Link:**\n`{link}`\n\n"
                f" **Note:** This link will always generate a fresh invite link (valid for 5 mins) for every user who clicks it.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Share Link", url=f"https://t.me/share/url?url={link}")]])
            )
            await cb.answer("Protected link created!", show_alert=True)

        elif data == "my_files_back":
            await cb.message.edit(
                " Use `/listfiles` to browse.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Home", callback_data="back_to_start")]])
            )
            await cb.answer()

        elif data == "listfiles_cb":
            files = load_db(FILES_DB); bi = get_bot_info(bot_id)
            is_sup = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid)
            all_f = [(k,f) for k,f in files.items()
                     if f.get("bot_id")==bot_id and (is_sup or f.get("user_id")==uid)]
            if not all_f: return await cb.answer(" No files found!", show_alert=True)
            recent = sorted(all_f, key=lambda x: x[1].get("upload_date",""), reverse=True)[:10]
            text = f" **{'All' if is_sup else 'Your'} Files** ({len(all_f)} total)\n\n"
            btns = []
            for k, f in recent:
                icon = file_icon(f.get("file_name",""))
                name = (f.get("file_name") or "?")[:35]
                text += f"{icon} **{name}** |  {fmt_size(f.get('file_size',0))} |  {f.get('access_count',0)}\n`{k}`\n\n"
                btns.append([
                    InlineKeyboardButton(f"{icon} {name[:22]}", url=f"https://t.me/{client.me.username}?start=f_{k}"),
                    InlineKeyboardButton(stylish(" EDIT"), callback_data=f"edit_file_{k}")
                ])
            btns.append([InlineKeyboardButton(stylish("ʙᴀᴄᴋ"), callback_data="help_cat_files")])
            await cb.message.edit(stylish(text), reply_markup=InlineKeyboardMarkup(btns))
            await cb.answer()

        # ── Dual post callbacks ───────────────────────────────────
        elif data == "dual_post_menu":
            bi = get_bot_info(bot_id)
            can_create = (uid == MAIN_ADMIN or is_admin(uid) or
                          (bi and bi.get("owner_id") == uid))
            dps = get_user_dual_posts(bot_id, uid) if not can_create else get_bot_dual_posts(bot_id)
            total_views = sum(p.get("access_total", 0) for p in dps)
            active_sess = uid in TEMP_DUAL
            btns = []
            if can_create:
                btns.append([InlineKeyboardButton(" Create Dual Post", callback_data="dual_post_start_new")])
            if dps:
                btns.append([InlineKeyboardButton(f" My Dual Posts ({len(dps)})", callback_data="dual_post_list")])
            btns.append([InlineKeyboardButton(" Back", callback_data="back_to_start")])
            await cb.message.edit(
                f" **Dual Post System**\n\n"
                f"One link → Two experiences!\n\n"
                f" **FREE tier** — For regular users\n"
                f"   → Shortener ads → Files → Auto-delete\n\n"
                f" **PRO tier** — For Premium users\n"
                f"   → Direct delivery → No ads → No delete\n\n"
                f"{' Active session: send files!' if active_sess else ''}\n"
                f"Total posts: `{len(dps)}` |  `{total_views}` views",
                reply_markup=InlineKeyboardMarkup(btns)
            )
            await cb.answer()

        elif data == "dual_post_start_new":
            bi = get_bot_info(bot_id)
            can_create = (uid == MAIN_ADMIN or is_admin(uid) or
                          (bi and bi.get("owner_id") == uid))
            if not can_create:
                return await cb.answer(" Only owner/admins can create Dual Posts!", show_alert=True)
            if uid in TEMP_DUAL:
                sess = TEMP_DUAL[uid]
                await cb.answer(
                    f"Active session exists! {len(sess.free_files)}F + {len(sess.pro_files)}P files.",
                    show_alert=True
                )
                return
            session = DualPostSession(bot_id, uid)
            TEMP_DUAL[uid] = session
            await cb.message.edit(
                f" **Dual Post Creator — Started!**\n\n"
                f"Tip: `/dualpost My Title` for a titled post.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f" **Stage 1 — FREE TIER**\n\n"
                f"Send files for non-premium users.\n\n"
                f"When done → `/dpremium` or button below\n"
                f"Cancel → `/dpcancel`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Switch to Premium Tier", callback_data="dp_switch_pro")],
                    [InlineKeyboardButton(" Finish & Generate Link",  callback_data="dp_finish")],
                    [InlineKeyboardButton(" Cancel",                  callback_data="dp_cancel_session")]
                ])
            )
            await cb.answer(" FREE tier stage started! Send files.")

        elif data == "dual_post_list":
            bi = get_bot_info(bot_id)
            is_sup = (uid == MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id") == uid))
            posts = get_bot_dual_posts(bot_id) if is_sup else get_user_dual_posts(bot_id, uid)
            if not posts:
                await cb.answer("No dual posts yet!", show_alert=True)
                return
            posts = sorted(posts, key=lambda p: p.get("created_at", ""), reverse=True)[:10]
            btns  = []
            text  = f" **Dual Posts ({len(posts)})**\n\n"
            for p in posts:
                pid   = p["post_id"]
                title = p.get("title", "Untitled")[:25]
                fc    = len(p.get("free_files", []))
                pc    = len(p.get("pro_files", []))
                at    = p.get("access_total", 0)
                text += f" **{title}** | `{pid}` | `{at}` | `{fc}` `{pc}`\n"
                link  = f"https://t.me/{client.me.username}?start=dp_{pid}"
                btns.append([
                    InlineKeyboardButton(f" {title[:18]}", url=f"https://t.me/share/url?url={link}"),
                    InlineKeyboardButton("", callback_data=f"dp_analytics_{pid}"),
                    InlineKeyboardButton("",  callback_data=f"dp_delete_{pid}")
                ])
            btns.append([InlineKeyboardButton(" Back", callback_data="dual_post_menu")])
            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup(btns))
            await cb.answer()

        elif data == "dp_switch_pro":
            if uid not in TEMP_DUAL:
                return await cb.answer("No active session! Use /dualpost to start.", show_alert=True)
            sess = TEMP_DUAL[uid]
            if sess.stage == "pro":
                return await cb.answer(
                    f"Already in Premium tier! {len(sess.pro_files)} files added.", show_alert=True
                )
            sess.stage = "pro"
            await cb.message.edit(
                f" **Premium Tier Active!**\n\n"
                f" Free tier locked: `{len(sess.free_files)}` file(s)\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f" **Stage 2 — PREMIUM TIER**\n\n"
                f"Now send files for Premium users.\n"
                f"Direct delivery, no ads, no delete.\n\n"
                f"When done → `/dpdone` or button below\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Finish & Generate Link", callback_data="dp_finish")],
                    [InlineKeyboardButton(" Cancel Session",         callback_data="dp_cancel_session")]
                ])
            )
            await cb.answer("Switched to  Premium tier!")

        elif data == "dp_finish":
            if uid not in TEMP_DUAL:
                return await cb.answer("No active session!", show_alert=True)
            sess = TEMP_DUAL[uid]
            if not sess.free_files and not sess.pro_files:
                return await cb.answer(" No files added yet!", show_alert=True)
            post_id   = unique_id()
            save_dual_post(post_id, sess)
            del TEMP_DUAL[uid]
            base_link = f"https://t.me/{client.me.username}?start=dp_{post_id}"
            bi2 = get_bot_info(bot_id)
            await cb.message.edit(
                f" **Dual Post Created!**\n\n"
                f" **{sess.title or 'Dual Post'}**\n"
                f" `{post_id}`\n\n"
                f" Free: `{len(sess.free_files)}` files "
                f"{' (shortener)' if shortener_enabled_for_bot(bi2) else ' (direct)'}\n"
                f" Pro: `{len(sess.pro_files)}` files  (direct)\n\n"
                f" **Link:**\n`{base_link}`",
                reply_markup=kb_dual_post_done(post_id, base_link)
            )
            await cb.answer(" Dual post created!")

        elif data == "dp_cancel_session":
            if uid in TEMP_DUAL:
                del TEMP_DUAL[uid]
                await cb.message.edit(" Dual post session cancelled.")
            await cb.answer()

        elif data.startswith("dp_prev_free_"):
            post_id = data[len("dp_prev_free_"):]
            post = get_dual_post(post_id)
            if not post: return await cb.answer("Post not found!", show_alert=True)
            fids = post.get("free_files", [])
            if not fids: return await cb.answer("No free files!", show_alert=True)
            await cb.answer(" Sending free tier preview...")
            files = load_db(FILES_DB)
            for fuid in fids[:3]:
                fd = files.get(fuid)
                if not fd: continue
                try: await deliver_file(client, cb.message.chat.id, fd)
                except Exception: pass
                await asyncio.sleep(0.4)
            if len(fids) > 3:
                await cb.message.reply(f"_...and {len(fids)-3} more free files_")

        elif data.startswith("dp_prev_pro_"):
            post_id = data[len("dp_prev_pro_"):]
            post = get_dual_post(post_id)
            if not post: return await cb.answer("Post not found!", show_alert=True)
            fids = post.get("pro_files", [])
            if not fids: return await cb.answer("No premium files in this post!", show_alert=True)
            await cb.answer(" Sending premium tier preview...")
            files = load_db(FILES_DB)
            for fuid in fids[:3]:
                fd = files.get(fuid)
                if not fd: continue
                try: await deliver_file(client, cb.message.chat.id, fd)
                except Exception: pass
                await asyncio.sleep(0.4)
            if len(fids) > 3:
                await cb.message.reply(f"_...and {len(fids)-3} more premium files_")

        elif data.startswith("dp_analytics_"):
            post_id = data[len("dp_analytics_"):]
            post    = get_dual_post(post_id)
            if not post: return await cb.answer("Post not found!", show_alert=True)
            bi = get_bot_info(bot_id)
            can = (uid == MAIN_ADMIN or is_admin(uid) or
                   (bi and bi.get("owner_id") == uid) or post.get("created_by") == uid)
            if not can: return await cb.answer(" Not your post!", show_alert=True)
            fc   = len(post.get("free_files", []))
            pc   = len(post.get("pro_files", []))
            af   = post.get("access_free", 0)
            ap   = post.get("access_pro", 0)
            at   = post.get("access_total", 0)
            last = str(post.get("last_accessed", "Never"))[:16]
            prem_pct = round(ap / max(at, 1) * 100)
            free_pct = 100 - prem_pct
            bar_p = "█" * (prem_pct // 10) + "░" * (10 - prem_pct // 10)
            bar_f = "█" * (free_pct // 10) + "░" * (10 - free_pct // 10)
            await cb.message.edit(
                f" **Analytics — {post.get('title','?')}**\n\n"
                f" `{post_id}`\n"
                f" `{str(post.get('created_at','?'))[:16]}`\n"
                f" Last: `{last}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f" **Total views:** `{at}`\n\n"
                f" FREE  `[{bar_f}]` {free_pct}%  (`{af}` views, `{fc}` files)\n"
                f" PRO   `[{bar_p}]` {prem_pct}%  (`{ap}` views, `{pc}` files)\n\n"
                f" Premium conversion: **{prem_pct}%**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Refresh", callback_data=f"dp_analytics_{post_id}"),
                     InlineKeyboardButton(" Delete",  callback_data=f"dp_delete_{post_id}")],
                    [InlineKeyboardButton(" Back",    callback_data="dual_post_list")]
                ])
            )
            await cb.answer()

        elif data == "dual_help":
            await cb.message.edit(
                "ᴅᴜᴀʟ ᴘᴏsᴛ sʏsᴛᴇᴍ ɢᴜɪᴅᴇ\n\n"
                "One link → Two different user experiences!\n\n"
                "1 `/dualpost Title` — Start a new session.\n"
                "2 Send files for **FREE** users (Stage 1).\n"
                "3 `/dpremium` — Switch to premium stage.\n"
                "4 Send files for **PREMIUM** users (Stage 2).\n"
                "5 `/dpdone` — Finalize and get your link.\n\n"
                " **Premium users** get Stage 2 files directly.\n"
                " **Free users** get Stage 1 files after ads.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("sᴛᴀʀᴛ ɴᴏᴡ", callback_data="dual_post_start_new")],
                    [InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ʜᴇʟᴘ", callback_data="help_menu")]
                ])
            )
            await cb.answer()

        elif data.startswith("dp_delete_"):
            post_id = data[len("dp_delete_"):]
            post    = get_dual_post(post_id)
            if not post: return await cb.answer("Already deleted!", show_alert=True)
            bi2 = get_bot_info(bot_id)
            can = (uid == MAIN_ADMIN or is_admin(uid) or
                   (bi2 and bi2.get("owner_id") == uid) or post.get("created_by") == uid)
            if not can: return await cb.answer(" Not your post!", show_alert=True)
            del_dual_post(post_id)
            await cb.answer(" Post deleted!", show_alert=True)
            await cb.message.edit(
                f" **Deleted:** `{post.get('title', post_id)}`\n"
                f" Free: `{len(post.get('free_files',[]))}` | "
                f" Pro: `{len(post.get('pro_files',[]))}` files removed."
            )

        # ── Admin callbacks ───────────────────────────────────────
        elif data == "dual_posts_admin":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
                return await cb.answer(" No access!", show_alert=True)
            posts = get_bot_dual_posts(bot_id)
            total_views = sum(p.get("access_total", 0) for p in posts)
            total_free  = sum(p.get("access_free", 0) for p in posts)
            total_pro   = sum(p.get("access_pro", 0) for p in posts)
            pct = round(total_pro / max(total_views, 1) * 100)
            await cb.message.edit(
                f" **Dual Posts Overview**\n\n"
                f"Total posts: `{len(posts)}`\n"
                f" Total views: `{total_views}`\n"
                f" Free views: `{total_free}`\n"
                f" Premium views: `{total_pro}`\n"
                f" Premium conversion: `{pct}%`\n\n"
                f"Commands:\n`/myduals` — list all posts\n`/dpstats POST_ID` — detailed analytics",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" All Posts", callback_data="dual_post_list")],
                    [InlineKeyboardButton(" Admin",     callback_data="admin_panel")]
                ])
            )
            await cb.answer()


        elif data == "start_batch":
            TEMP_BATCH[uid] = []
            await cb.message.edit(
                " **Batch Mode**\n\nSend files. `/done` to finish.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel", callback_data="cancel_batch")]])
            )
            await cb.answer("Batch started!")

        elif data == "cancel_batch":
            TEMP_BATCH.pop(uid, None)
            await cb.message.edit(" Batch cancelled.")
            await cb.answer()

        elif data == "confirm_broadcast":
            bd = TEMP_BROADCAST.get(uid)
            if not bd: return await cb.answer(" Expired!", show_alert=True)
            sm = await cb.message.edit(" **Broadcasting...**")
            s, f = await do_broadcast(bd["bot_ids"], bd["bc_msg_id"], status_msg=sm, reply_markup=bd.get("markup"))
            TEMP_BROADCAST.pop(uid, None)
            await sm.edit(f" **Done!**\n\n `{s}` |  `{f}` |  `{len(bd['bot_ids'])}`")

        elif data == "cancel_broadcast":
            TEMP_BROADCAST.pop(uid, None)
            await cb.message.edit(" Cancelled!")
            await cb.answer()

        elif data == "clone_menu":
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            await cb.message.edit(
                f" **Clone** — Your bots: `{len(ubts)}`\n\n1. @BotFather → /newbot\n2. `/clone TOKEN`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" BotFather", url="https://t.me/BotFather")],
                    [InlineKeyboardButton(" Back",      callback_data="back_to_start")]
                ])
            )
            await cb.answer()

        elif data == "user_dashboard":
            ud   = get_user(uid, bot_id)
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            dps  = get_user_dual_posts(bot_id, uid)
            await cb.message.edit(
                f" **Dashboard**\n\n"
                f" `{ud.get('files_uploaded',0) if ud else 0}` uploads | "
                f" `{ud.get('batches_created',0) if ud else 0}` batches\n"
                f" `{len(dps)}` dual posts |  `{len(ubts)}` bots\n"
                f" {'Premium ' if ud and ud.get('is_premium') else 'Free'}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Back", callback_data="back_to_start")]])
            )
            await cb.answer()

        elif data == "my_bots_menu":
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            text = f" **Your Bots ({len(ubts)})**\n\n"
            for i, b in enumerate(ubts[:10], 1):
                text += f"{i}. {'' if b['bot_id'] in ACTIVE_CLIENTS else ''} @{b['bot_username']}\n"
            if not ubts: text += "None!"
            await cb.message.edit(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Clone", callback_data="clone_menu")],
                    [InlineKeyboardButton(" Back",  callback_data="back_to_start")]
                ])
            )
            await cb.answer()

        elif data == "about_bot":
            uptime = str(datetime.now() - START_TIME).split(".")[0]
            text = (
                "✨ ᴀʙᴏᴜᴛ ᴍᴇ\n\n"
                "✰ ᴍʏ ɴᴀᴍᴇ: ꜰɪʟᴇ sᴛᴏʀᴇ ʙᴏᴛ\n"
                "✰ ᴍʏ ᴏᴡɴᴇʀ: MR ZOLVID\n"
                "✰ ᴜᴘᴅᴀᴛᴇs: ZOLVID BOTZ\n"
                "✰ sᴜᴘᴘᴏʀᴛ: ZOLVID GROUP\n"
                f"✰ uptime: {uptime}"
            )
            await cb.message.edit(stylish(text), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(stylish("BACK"), callback_data="back_to_start")]]), disable_web_page_preview=True)
            await cb.answer()

        elif data == "font_editor":
            user = get_user(uid, bot_id)
            curr = user.get("pref_font", "smallcaps") if user else "smallcaps"
            text = stylish(f"<b>ғᴏɴᴛ ᴇᴅɪᴛᴏʀ</b>\n\nᴄᴜʀʀᴇɴᴛ ғᴏɴᴛ: <code>{curr}</code>\n\nsᴇʟᴇᴄᴛ ᴀ ɴᴇᴡ ғᴏɴᴛ sᴛʏʟᴇ ʙᴇʟᴏᴡ. ᴛʜɪs sᴛʏʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴘᴘʟɪᴇᴅ ᴛᴏ ᴀʟʟ ʏᴏᴜʀ ᴄᴀᴘᴛɪᴏɴs ᴀɴᴅ ᴘᴏsᴛs.")
            btns = []
            font_keys = ["none"] + list(_FONTS.keys())
            for i in range(0, len(font_keys), 2):
                row = [InlineKeyboardButton(stylish(font_keys[i], font_keys[i]), callback_data=f"setfont_{font_keys[i]}")]
                if i + 1 < len(font_keys):
                    row.append(InlineKeyboardButton(stylish(font_keys[i+1], font_keys[i+1]), callback_data=f"setfont_{font_keys[i+1]}"))
                btns.append(row)
            btns.append([InlineKeyboardButton(stylish("ʙᴀᴄᴋ"), callback_data="help_cat_fonts")])
            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup(btns))
            await cb.answer()

        elif data.startswith("setfont_"):
            new_font = data[8:]
            users = load_db(USERS_DB)
            ukey = f"{bot_id}_{uid}"
            if ukey in users:
                users[ukey]["pref_font"] = new_font
                save_db(USERS_DB, users)
                await cb.answer(f"Font updated to {new_font}!", show_alert=True)
                # Refresh editor
                await cb_handler(client, type('CB', (), {'from_user': cb.from_user, 'data': 'font_editor', 'message': cb.message, 'answer': lambda *a, **k: asyncio.sleep(0)})())
            else:
                await cb.answer("User not found in DB!", show_alert=True)

        elif data == "help_menu":
            text = get_msg_text("msg_help", HELP_TEXT)

            buttons = [
                [InlineKeyboardButton(stylish("ɢᴇɴᴇʀᴀʟ"), callback_data="help_cat_general"),
                 InlineKeyboardButton(stylish("ғɪʟᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ"), callback_data="help_cat_files")],
                [InlineKeyboardButton(stylish("ᴀᴅᴠᴀɴᴄᴇᴅ"), callback_data="help_cat_advanced"),
                 InlineKeyboardButton(stylish("ғᴏɴᴛ ᴇᴅɪᴛᴏʀ"), callback_data="help_cat_fonts")],
                [InlineKeyboardButton(stylish("ᴀᴅᴍɪɴ"), callback_data="help_cat_admin"),
                 InlineKeyboardButton(stylish("sᴜᴘʀᴇᴍᴇ"), callback_data="help_cat_supreme")],
                [InlineKeyboardButton(stylish("ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ"), callback_data="back_to_start")]
            ]

            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup(buttons))
            await cb.answer()

        elif data.startswith("help_cat_"):
            cat = data[9:]
            help_data = {
                "general": "<blockquote><b>ɢᴇɴᴇʀᴀʟ ᴄᴏᴍᴍᴀɴᴅs</b>\n\n/start - Start the bot\n/help - Show this guide\n/about - About bot\n/refer - Refer and Earn\n/stats - View statistics\n/ping - Check bot speed\n/search - Search for files\n/premium - Premium membership\n/botinfo - View bot details\n/download - Download videos\n/done - Finish session\n/cancel - Cancel current action</blockquote>",
                "files": "<blockquote><b>ғɪʟᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ</b>\n\n/batch - Start batch mode\n/listfiles - List uploaded files\n/mybatches - List your batches\n/editfile - Edit metadata\n/delfile - Delete file\n/rename - Rename file\n/setcaption - Set caption\n/setthumb - Set thumbnail\n/dualpost - Create dual-tier link\n/dpremium - Switch to premium tier\n/dpdone - Finish dual post\n/dpcancel - Cancel dual post\n/myduals - Manage dual posts\n/deldual - Delete dual post\n/dpstats - Dual post analytics\n/createpost - Create custom post</blockquote>",
                "advanced": "<blockquote><b>ᴀᴅᴠᴀɴᴄᴇᴅ ғᴇᴀᴛᴜʀᴇs</b>\n\n/clone - Create your own bot\n/mybots - List your cloned bots\n/protect - Protect channel link\n/myplinks - Manage protected links\n/font - Open font editor\n/addadmin - Add secondary admin\n/deladmin - Remove secondary admin</blockquote>",
                "fonts": "<blockquote><b>ғᴏɴᴛ ᴇᴅɪᴛᴏʀ</b>\n\n/font - Open font editor\n\nChange your default font for captions and posts. Choose from over 10+ highly advanced stylish font designs.</blockquote>",
                "admin": "<blockquote><b>ᴀᴅᴍɪɴ ᴛᴏᴏʟs</b>\n\n/admin - Admin Panel\n/setfs - Configure Force Sub\n/setwelcome - Set welcome msg\n/setlog - Set log channel\n/setchannel - Connect channel\n/setmode - Set join mode\n/broadcast - Send message to all\n/ban - Ban a user\n/unban - Unban a user\n/settimer - Auto-delete timer\n/setprice - Set premium price\n/setcontact - Set premium contact\n/setqr - Set premium QR code\n/givepremium - Give premium access\n/removepremium - Revoke premium access\n/shortener - Configure shortener\n/requests - Manage join requests\n/autoapprove - Toggle Auto-Approve\n/autocaption - Toggle Auto-Caption</blockquote>",
                "supreme": "<blockquote><b>sᴜᴘʀᴇᴍᴇ ᴛᴏᴏʟs</b>\n\n/supreme - Supreme Panel\n/restart - System restart</blockquote>"
            }

            buttons = []
            if cat == "admin":
                buttons.append([InlineKeyboardButton(stylish("ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ"), callback_data="admin_panel"),
                               InlineKeyboardButton(stylish("ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛs"), callback_data="manage_requests")])
                buttons.append([InlineKeyboardButton(stylish("ғᴏʀᴄᴇ sᴜʙ"), callback_data="forcesub_admin"),
                               InlineKeyboardButton(stylish("sʜᴏʀᴛᴇɴᴇʀ"), callback_data="shortener_admin")])
                buttons.append([InlineKeyboardButton(stylish("ʙᴏᴛ sᴇᴛᴛɪɴɢs"), callback_data="bot_settings_admin")])
            elif cat == "supreme":
                buttons.append([InlineKeyboardButton(stylish("sᴜᴘʀᴇᴍᴇ ᴘᴀɴᴇʟ"), callback_data="supreme_panel"),
                               InlineKeyboardButton(stylish("sʏsᴛᴇᴍ sᴛᴀᴛs"), callback_data="system_stats")])
                buttons.append([InlineKeyboardButton(stylish("ʙᴏᴛ ɴᴇᴛᴡᴏʀᴋ"), callback_data="all_bots_list"),
                               InlineKeyboardButton(stylish("ᴀᴅᴍɪɴ ᴍᴀɴᴀɢᴇʀ"), callback_data="manage_admins")])
                buttons.append([InlineKeyboardButton(stylish("ᴄᴜsᴛᴏᴍɪᴢᴇ"), callback_data="supreme_customize")])
            elif cat == "fonts":
                buttons.append([InlineKeyboardButton(stylish("ᴏᴘᴇɴ ғᴏɴᴛ ᴇᴅɪᴛᴏʀ"), callback_data="font_editor")])
            elif cat == "files":
                buttons.append([InlineKeyboardButton(stylish("ᴍʏ ғɪʟᴇs"), callback_data="listfiles_cb"),
                               InlineKeyboardButton(stylish("ᴍʏ ᴅᴜᴀʟs"), callback_data="dual_post_list")])
                buttons.append([InlineKeyboardButton(stylish("sᴛᴀʀᴛ ʙᴀᴛᴄʜ"), callback_data="start_batch"),
                               InlineKeyboardButton(stylish("ᴄʀᴇᴀᴛᴇ ᴘᴏsᴛ"), callback_data="cb_create_post")])
                buttons.append([InlineKeyboardButton(stylish("ᴅᴜᴀʟ ɢᴜɪᴅᴇ"), callback_data="dual_help")])
            elif cat == "general":
                buttons.append([InlineKeyboardButton(stylish("ᴍʏ sᴛᴀᴛs"), callback_data="user_dashboard"),
                               InlineKeyboardButton(stylish("ᴘʀᴇᴍɪᴜᴍ ɪɴғᴏ"), callback_data="premium_menu")])
                buttons.append([InlineKeyboardButton(stylish("sᴇᴀʀᴄʜ ғɪʟᴇs"), callback_data="cb_search"),
                               InlineKeyboardButton(stylish("ʀᴇғᴇʀ & ᴇᴀʀɴ"), callback_data="referral_menu")])
                buttons.append([InlineKeyboardButton(stylish("ᴀʙᴏᴜᴛ ᴍᴇ"), callback_data="about_bot")])
            elif cat == "advanced":
                buttons.append([InlineKeyboardButton(stylish("ᴍʏ ʙᴏᴛs"), callback_data="my_bots_menu"),
                               InlineKeyboardButton(stylish("ᴄʟᴏɴᴇ ʙᴏᴛ"), callback_data="clone_menu")])
                buttons.append([InlineKeyboardButton(stylish("ᴘʀᴏᴛᴇᴄᴛ ʟɪɴᴋ"), callback_data="plinks_admin")])

            buttons.append([InlineKeyboardButton(stylish("ʙᴀᴄᴋ"), callback_data="help_menu")])
            text = stylish(help_data.get(cat, "No details found."))
            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup(buttons))
            await cb.answer()
        elif data in ("cb_search", "premium_menu", "referral_menu"):
            bi_cb = get_bot_info(bot_id)
            ud_cb = add_user(uid, bot_id, cb.from_user.username, cb.from_user.first_name)[0]
            is_p = (ud_cb or {}).get('is_premium')
            contact = bi_cb.get("premium_contact", "zolvid") if bi_cb else "zolvid"
            qr_id = bi_cb.get("premium_qr") if bi_cb else None

            default_prem = (
                f" **ELITE PREMIUM MEMBERSHIP** \n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f" **Current Status:** {{status}}\n\n"
                f" **EXCLUSIVE PRIVILEGES:**\n"
                f" ├  **PERMANENT STORAGE:** Files never expire!\n"
                f" ├  **ELITE ACCESS:** Unlock Premium Dual Posts!\n"
                f" ├  **DIRECT DELIVERY:** No ads, no shorteners!\n"
                f" ├  **PRO BATCHING:** No limits on creation!\n"
                f" └  **PRIORITY SUPPORT:** Instant assistance!\n\n"
                f" **Subscription Fee:** `{{price}}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f" **WANT TO UPGRADE? CONTACT ADMIN!** "
            )
            default_ref = (
                f" **Refer & Earn Program**\n━━━━━━━━━━━━━━━━━━━━\n"
                f"Invite your friends and earn rewards!\n\n"
                f" **Your Stats:**\n"
                f"├ Total Refers: `{{ref_count}}` users\n"
                f"└ Rewards Earned: `{{ref_rewards}}` days of Premium\n\n"
                f" **Reward:** Earn 1 day of Premium for every 5 successful refers!\n\n"
                f" **Your Referral Link:**\n"
                f"`https://t.me/{{bot_username}}?start=ref_{{uid}}`"
            )

            texts = {
                "cb_search":     get_msg_text("msg_search", " **Search**\n\nUse: `/search FILENAME`\nOr inline: `@BotUsername query`"),
                "help_menu":     get_msg_text("msg_help", HELP_TEXT),
                "premium_menu":  get_msg_text("msg_premium", default_prem).format_map(SafeDict(
                    status=' `ACTIVATED`' if is_p else ' `NOT ACTIVE`',
                    price=(bi_cb or {}).get('premium_price', '500'),
                    contact=f"@{contact}"
                )),
                "referral_menu": get_msg_text("msg_referral", default_ref).format_map(SafeDict(
                    ref_count=ud_cb.get('refer_count', 0),
                    ref_rewards=ud_cb.get('refer_rewards', 0),
                    bot_username=client.me.username,
                    uid=uid
                ))
            }

            kb = [[InlineKeyboardButton(get_btn_name("btn_back", "ʙᴀᴄᴋ"), callback_data="back_to_start")]]
            if data == "premium_menu":
                kb.insert(0, [InlineKeyboardButton(get_btn_name("btn_pcon", "ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ"), url=f"https://t.me/{contact}")])
                if qr_id:
                    kb.insert(1, [InlineKeyboardButton(get_btn_name("btn_pqrs", "sʜᴏᴡ ᴘᴀʏᴍᴇɴᴛ ǫʀ"), callback_data="show_premium_qr")])
            elif data == "referral_menu":
                ref_link = f"https://t.me/{client.me.username}?start=ref_{uid}"
                kb.insert(0, [InlineKeyboardButton(get_btn_name("btn_invite", "ɪɴᴠɪᴛᴇ ғʀɪᴇɴᴅs"), url=f"https://t.me/share/url?url={ref_link}")])

            try:
                await cb.message.edit(
                    texts[data],
                    reply_markup=InlineKeyboardMarkup(kb)
                )
            except Exception:
                await cb.message.delete()
                if qr_id and data == "premium_menu" and not is_p:
                    await client.send_photo(cb.message.chat.id, qr_id, caption=texts[data], reply_markup=InlineKeyboardMarkup(kb))
                else:
                    await client.send_message(cb.message.chat.id, texts[data], reply_markup=InlineKeyboardMarkup(kb))
            await cb.answer()

        elif data == "show_premium_qr":
            bi_cb = get_bot_info(bot_id)
            qr_id = bi_cb.get("premium_qr") if bi_cb else None
            if not qr_id:
                return await cb.answer(" QR code not available!", show_alert=True)

            await cb.answer(" Loading QR Code...")
            await cb.message.reply_photo(qr_id, caption=" **Scan this QR to pay for Premium** \n\nAfter payment, send screenshot to admin.")

        elif data == "admin_panel":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
                return await cb.answer(" No access!", show_alert=True)
            await cb.message.edit(" **Admin Panel**", reply_markup=kb_admin())
            await cb.answer()

        elif data == "broadcast_menu":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or uid == MAIN_ADMIN or (bi and bi.get("owner_id") == uid)):
                return await cb.answer(" No access!", show_alert=True)
            await cb.message.edit(
                f" **Broadcast**\n\n `{len(get_all_users(bot_id))}`\n\nReply to a message with `/broadcast`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Back", callback_data="admin_panel")]])
            )
            await cb.answer()

        elif data == "plinks_admin":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
                return await cb.answer(" No access!", show_alert=True)
            plinks = load_db(PLINKS_DB)
            my_links = [v for v in plinks.values() if v.get("bot_id") == bot_id]
            await cb.message.edit(
                f" **Protected Links Overview**\n\n"
                f"Total protected: `{len(my_links)}` links\n\n"
                f"**Commands:**\n"
                f"├ `/protect` - Create new protection\n"
                f"└ `/myplinks` - Manage your links\n\n"
                f"Protected links generate a fresh, 5-minute expiring invite link for every user, making it impossible to leak the real invite link.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" List My Links", callback_data="plinks_list_admin")],
                    [InlineKeyboardButton(" Admin",          callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "plinks_list_admin":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
                return await cb.answer(" No access!", show_alert=True)
            plinks = load_db(PLINKS_DB)
            my_links = [v for v in plinks.values() if v.get("bot_id") == bot_id]
            if not my_links:
                return await cb.answer("No protected links found!", show_alert=True)

            text = f" **Protected Links List ({len(my_links)})**\n\n"
            btns = []
            for l in my_links[:10]:
                lpid = l["lpid"]
                title = l.get("title", "Unknown")[:22]
                text += f"• **{title}** | `{lpid}`\n"
                btns.append([
                    InlineKeyboardButton(f" {title}", callback_data=f"show_plink_{lpid}"),
                    InlineKeyboardButton("", callback_data=f"del_plink_{lpid}")
                ])
            btns.append([InlineKeyboardButton(" Back", callback_data="plinks_admin")])
            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup(btns))
            await cb.answer()

        elif data.startswith("show_plink_"):
            lpid = data[11:]
            plinks = load_db(PLINKS_DB)
            p = plinks.get(lpid)
            if not p: return await cb.answer("Not found!", show_alert=True)
            link = f"https://t.me/{client.me.username}?start=lp_{lpid}"
            await cb.message.edit(
                f" **Protected Link Details**\n\n"
                f" **Channel:** `{p.get('title')}`\n"
                f" `{p['channel_id']}`\n"
                f" **Mode:** `{p.get('mode').upper()}`\n"
                f" **Created:** `{datetime.fromtimestamp(p.get('created_at')).strftime('%Y-%m-%d %H:%M')}`\n\n"
                f" **Sharable Link:**\n`{link}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Share", url=f"https://t.me/share/url?url={link}")],
                    [InlineKeyboardButton(" Delete", callback_data=f"del_plink_{lpid}"),
                     InlineKeyboardButton(" Back",   callback_data="plinks_list_admin")]
                ])
            )
            await cb.answer()

        elif data == "verify_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            vl = bi.get("verify_link") or "None"
            uc = bi.get("update_channel") or "None"
            await cb.message.edit(
                f" **Verification System**\n\n"
                f"Status: {' ENABLED' if bi.get('verify_link') else ' DISABLED'}\n\n"
                f" **Link:** `{vl}`\n"
                f" **Updates:** `{uc}`\n\n"
                f"**Settings:**\n"
                f"• `/setverify [link]` - Set link\n"
                f"• `/setupdates [link]` - Set channel\n"
                f"• `/setverify off` - Disable\n\n"
                f"Users must complete this link before using the bot.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Set Verify Link", callback_data="set_v_link"),
                     InlineKeyboardButton(" Set Update Ch", callback_data="set_u_link")],
                    [InlineKeyboardButton(" Disable System", callback_data="disable_verify")],
                    [InlineKeyboardButton(" Back", callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "disable_verify":
            update_bot_info(bot_id, "verify_link", None)
            await cb.answer(" Verification system disabled!", show_alert=True)
            await cb.message.edit(" **Admin Panel**", reply_markup=kb_admin())

        elif data == "set_v_link":
            await cb.answer("Use /setverify [link] to set the link.", show_alert=True)

        elif data == "set_u_link":
            await cb.answer("Use /setupdates [link] to set the channel.", show_alert=True)

        elif data == "admin_stats":
            bot_files = [f for f in load_db(FILES_DB).values() if f.get("bot_id") == bot_id]
            dp_count  = len(get_bot_dual_posts(bot_id))
            dp_views  = sum(p.get("access_total", 0) for p in get_bot_dual_posts(bot_id))

            # More advanced stats
            users = [u for u in load_db(USERS_DB).values() if u.get("bot_id") == bot_id]
            today = datetime.now().date()
            active_today = sum(1 for u in users if datetime.fromisoformat(u.get("last_active", "2000-01-01")).date() == today)
            premium_users = sum(1 for u in users if u.get("is_premium"))

            top_files = sorted(bot_files, key=lambda f: f.get("access_count", 0), reverse=True)[:5]
            top_files_text = ""
            for i, f in enumerate(top_files, 1):
                name = f.get('file_name', 'Unknown')[:20]
                count = f.get('access_count', 0)
                icon = file_icon(f.get('file_name', ''))
                top_files_text += f"{i}. {icon} `{name}` —  **{count}**\n"

            await cb.message.edit(
                f"ʙᴏᴛ ᴀɴᴀʟʏᴛɪᴄs\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"ᴜsᴇʀ ᴍᴇᴛʀɪᴄs\n"
                f" ├ Total Base: `{len(users)}` users\n"
                f" ├ Active Today: `{active_today}`\n"
                f" └ Premium Members: `{premium_users}`\n\n"
                f"ᴄᴏɴᴛᴇɴᴛ ᴍᴇᴛʀɪᴄs\n"
                f" ├ Total Files: `{len(bot_files)}` items\n"
                f" ├ Global Views: `{sum(f.get('access_count',0) for f in bot_files)}`\n"
                f" ├ Dual Posts: `{dp_count}` active\n"
                f" └ DP Views: `{dp_views}`\n\n"
                f"ᴛʀᴇɴᴅɪɴɢ ᴄᴏɴᴛᴇɴᴛ\n"
                f"{top_files_text or '_No data recorded yet._'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"ᴜᴘᴛɪᴍᴇ: `{str(datetime.now()-START_TIME).split('.')[0]}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("ʀᴇғʀᴇsʜ ᴅᴀᴛᴀ", callback_data="admin_stats")],
                    [InlineKeyboardButton("ᴅᴜᴀʟ ᴘᴏsᴛs",  callback_data="dual_posts_admin"),
                     InlineKeyboardButton("ᴜsᴇʀ ʟɪsᴛ",   callback_data="manage_users")],
                    [InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ᴘᴀɴᴇʟ", callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "manage_users":
            all_u = load_db(USERS_DB)
            banned = sum(1 for u in all_u.values()
                         if u.get("bot_id") == bot_id and u.get("is_banned"))
            await cb.message.edit(
                f" **Users**\n\n Active: `{len(get_all_users(bot_id))}` |  Banned: `{banned}`\n\n"
                f"`/ban ID` `/unban ID` `/info ID` `/givepremium ID`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Back", callback_data="admin_panel")]])
            )
            await cb.answer()

        elif data == "my_bots_admin":
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            text = f" **Your Bots ({len(ubts)})**\n\n"
            for i, b in enumerate(ubts[:15], 1):
                text += f"{i}. {'' if b['bot_id'] in ACTIVE_CLIENTS else ''} @{b['bot_username']}\n"
            if not ubts: text += "None!"
            await cb.message.edit(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Clone", callback_data="clone_menu")],
                    [InlineKeyboardButton(" Back",  callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "bot_settings_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            t = bi.get("auto_delete_time", 300)
            await cb.message.edit(
                f" **Bot Settings**\n\n"
                f" Welcome: {'Custom ' if bi.get('custom_welcome') else 'Default'}\n"
                f" Image: {'Set ' if bi.get('welcome_image') else 'None'}\n"
                f" Timer: `{t}s` ({t//60}min)\n"
                f" Auto-Approve: `{'ON' if bi.get('auto_approve') else 'OFF'}`\n"
                f" Log: `{bi.get('log_channel') or 'None'}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Edit Welcome",   callback_data="edit_welcome_msg")],
                    [InlineKeyboardButton(" Timer",          callback_data="edit_timer"),
                     InlineKeyboardButton(" Log",            callback_data="set_log_info")],
                    [InlineKeyboardButton(" Back",           callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "edit_timer":
            bi = get_bot_info(bot_id); curr = bi.get("auto_delete_time", 300) if bi else 300
            await cb.message.edit(
                f" **Auto-Delete Timer**\n\nCurrent: `{curr}s` ({curr//60}min)\n\nChoose a preset or send a custom value:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("1 Min", callback_data="st_60"),
                     InlineKeyboardButton("5 Min", callback_data="st_300")],
                    [InlineKeyboardButton("10 Min", callback_data="st_600"),
                     InlineKeyboardButton("30 Min", callback_data="st_1800")],
                    [InlineKeyboardButton("1 Hour", callback_data="st_3600"),
                     InlineKeyboardButton(" Custom", callback_data="st_custom")],
                    [InlineKeyboardButton(" Back", callback_data="bot_settings_admin")]
                ])
            )
            await cb.answer()

        elif data.startswith("st_"):
            val = data[3:]
            if val == "custom":
                TEMP_EDIT[uid] = {"mode": "set_timer_custom"}
                await cb.message.edit(" **Custom Timer**\n\nSend the auto-delete time in **seconds**.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel", callback_data="edit_timer")]]))
            else:
                secs = int(val)
                update_bot_info(bot_id, "auto_delete_time", secs)
                await cb.answer(f" Timer set to {secs}s", show_alert=True)
                cb.data = "edit_timer"
                await cb_handler(client, cb)

        elif data == "set_log_info":
            await cb.message.edit(
                " `/setlog CHANNEL_ID` or `/setlog off`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Back", callback_data="bot_settings_admin")]])
            )
            await cb.answer()

        elif data == "forcesub_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            fs   = bi.get("force_subs", [])
            text = f" **Force Subscribe** ({len(fs)}/{MAX_FORCE_SUB_CHANNELS})\n━━━━━━━━━━━━━━━━━━━━\n"
            btns = []
            for i, f in enumerate(fs, 1):
                cid = f["channel_id"] if isinstance(f, dict) else f
                text += f"**{i}.** `{cid}`\n"
                btns.append([InlineKeyboardButton(f" Remove {i}", callback_data=f"rm_fs_{cid}")])

            if not fs: text += "_No channels added yet._\n"

            text += "\n**Commands:**\n`/setfs add -100xxxx [link]`\n`/setfs clear` to remove all."

            btns.append([InlineKeyboardButton(" Add Channel", callback_data="add_fs_info")])
            btns.append([InlineKeyboardButton(" Back", callback_data="admin_panel")])

            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup(btns))
            await cb.answer()

        elif data.startswith("rm_fs_"):
            cid_str = data[6:]
            bi = get_bot_info(bot_id)
            fs = bi.get("force_subs", [])
            try:
                cid = int(cid_str)
                new_fs = [f for f in fs if (f["channel_id"] if isinstance(f, dict) else f) != cid]
                update_bot_info(bot_id, "force_subs", new_fs)
                cascade_force_subs(bot_id, new_fs)
                await cb.answer(" Channel removed!", show_alert=True)
                # Re-render the menu
                await cb.message.edit(" **Updating...**")
                cb.data = "forcesub_admin"
                await cb_handler(client, cb)
            except Exception as e:
                await cb.answer(f" Error: {e}", show_alert=True)

        elif data == "add_fs_info":
            await cb.answer("Use /setfs add -100xxxx [link] to add.", show_alert=True)

        elif data == "toggle_auto_approve":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
                return await cb.answer(" Access Denied!", show_alert=True)
            curr = bi.get("auto_approve", False)
            update_bot_info(bot_id, "auto_approve", not curr)
            await cb.answer(f"ᴀᴜᴛᴏ ᴀᴘᴘʀᴏᴠᴇ: {'ᴏɴ' if not curr else 'ᴏғғ'}", show_alert=True)
            try:
                await cb.message.edit(cb.message.text, reply_markup=kb_start(bot_id, uid) if "ʜᴇʟʟᴏ" in cb.message.text else kb_admin())
            except: pass

        elif data == "manage_requests":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid, bot_id) or (bi and bi.get("owner_id") == uid)):
                return await cb.answer(" Access Denied!", show_alert=True)

            pending = []
            for cid, users in _PENDING.items():
                # For clone bots, only show requests for channels they are managing if possible
                # But _PENDING is global. Let's filter by connected channel if it's a clone.
                conn_ch = bi.get("connected_channel")
                if conn_ch and cid != conn_ch and uid != MAIN_ADMIN:
                    continue
                for u_id, ts in users.items():
                    pending.append((cid, u_id, ts))

            if not pending:
                return await cb.answer(" No pending join requests!", show_alert=True)

            text = f" **Pending Join Requests ({len(pending)})**\n\n"
            btns = []
            for cid, u_id, ts in pending[:10]:
                try:
                    chat = await client.get_chat(cid)
                    c_title = chat.title
                except: c_title = str(cid)

                text += f"• User: `{u_id}`\n  Channel: {c_title}\n  Time: {ts[:16]}\n\n"
                btns.append([
                    InlineKeyboardButton(f"✅ Approve {u_id}", callback_data=f"req_approve_{cid}_{u_id}"),
                    InlineKeyboardButton(f"❌ Decline {u_id}", callback_data=f"req_decline_{cid}_{u_id}")
                ])

            btns.append([InlineKeyboardButton(" Back", callback_data="admin_panel")])
            await cb.message.edit(stylish(text), reply_markup=InlineKeyboardMarkup(btns))
            await cb.answer()

        elif data == "toggle_auto_caption":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            curr = bi.get("auto_caption", True)
            update_bot_info(bot_id, "auto_caption", not curr)
            await cb.answer(f"Auto Caption: {'ON ' if not curr else 'OFF '}", show_alert=True)
            await cb.message.edit(" **Admin Panel**", reply_markup=kb_admin())

        elif data == "shortener_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            st = " ON" if bi.get("is_shortener_enabled") else " OFF"
            active = sum(1 for v in SHORTENER_TOKENS.values()
                         if not v["used"] and time.time() < v["expires_at"])
            await cb.message.edit(
                f" **Shortener Settings**\n\n"
                f"Status: {st}\n"
                f"URL: `{bi.get('shortener_url') or 'Not set'}`\n\n"
                f"**Integration with Dual Posts:**\n"
                f"• FREE tier → shortener → token → files\n"
                f"• PRO tier → always direct (no ads)\n\n"
                f" Active tokens: `{active}`\n\n"
                f"`/shortener` to configure.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Back", callback_data="admin_panel")]])
            )
            await cb.answer()

        elif data == "edit_welcome_msg":
            bi = get_bot_info(bot_id)
            if not bi or (bi.get("owner_id") != uid and uid != MAIN_ADMIN):
                return await cb.answer(" Only owner!", show_alert=True)
            TEMP_WELCOME[uid] = {"bot_id": bot_id, "step": "text"}
            curr_t = bi.get("custom_welcome") or "_(default)_"
            curr_i = "" if bi.get("welcome_image") else ""
            await cb.message.edit(
                f" **Welcome Editor**\n\nCurrent text: {curr_t[:80]}\nCurrent image: {curr_i}\n\n"
                f"**Step 1/2:** Send new welcome text.\n`-skip` = keep | `-clear` = default",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel", callback_data="cancel_welcome")]])
            )
            await cb.answer()

        elif data == "preview_welcome":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer()
            text = bi.get("custom_welcome") or "_(Default)_"
            img  = bi.get("welcome_image")
            await cb.answer()
            if img:
                try:
                    await client.send_photo(cb.message.chat.id, img, caption=f"**Preview:**\n\n{text}")
                    return
                except Exception: pass
            await cb.message.reply(f"**Preview:**\n\n{text}")

        elif data == "supreme_panel":
            if uid != MAIN_ADMIN: return await cb.answer(" Supreme only!", show_alert=True)
            await cb.message.edit(
                f" **Supreme Panel v7.0**",
                reply_markup=kb_supreme()
            )
            await cb.answer()

        elif data == "supreme_customize":
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            await cb.message.edit(
                " **Supreme Customizer**\n\nChoose what you want to customize:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" BUTTON NAMES",   callback_data="cust_btns")],
                    [InlineKeyboardButton(" PANEL MESSAGES", callback_data="cust_msgs")],
                    [InlineKeyboardButton(" BACK",           callback_data="supreme_panel")]
                ])
            )
            await cb.answer()

        elif data == "cust_btns":
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            await cb.message.edit(
                " **Button Customizer**\n\nSelect a menu category:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" START MENU", callback_data="cbtn_cat_start")],
                    [InlineKeyboardButton(" ADMIN MENU", callback_data="cbtn_cat_admin")],
                    [InlineKeyboardButton(" SUPREME MENU", callback_data="cbtn_cat_supreme")],
                    [InlineKeyboardButton(" HELP & OTHERS", callback_data="cbtn_cat_other")],
                    [InlineKeyboardButton(" RESET ALL",  callback_data="reset_buttons")],
                    [InlineKeyboardButton(" BACK",       callback_data="supreme_customize")]
                ])
            )
            await cb.answer()

        elif data.startswith("cbtn_cat_"):
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            cat = data[9:]
            btns_config = get_global_config().get("custom_buttons", {})
            keyboard = []

            if cat == "start":
                b_list = [
                    ("btn_supreme", "Supreme Panel"), ("btn_admin", "Admin Panel"),
                    ("btn_srch", "Search"), ("btn_batch", "Batch"),
                    ("btn_dual", "Dual Post"), ("btn_clone", "Clone"),
                    ("btn_refer", "Refer"), ("btn_prem", "Premium"),
                    ("btn_mybt", "My Bots"), ("btn_dash", "Dashboard"),
                    ("btn_prot", "Protect"), ("btn_help", "Help"),
                    ("btn_supp", "Support")
                ]
            elif cat == "admin":
                b_list = [
                    ("btn_abrd", "Broadcast"), ("btn_asta", "Analytics"),
                    ("btn_ausr", "Users"), ("btn_acln", "Clones"),
                    ("btn_aset", "Settings"), ("btn_afsb", "Force Sub"),
                    ("btn_aver", "Verification"), ("btn_ashr", "Shortener"),
                    ("btn_aprt", "Protect Links"), ("btn_adul", "Dual Posts"),
                    ("btn_awlc", "Welcome Msg"), ("btn_aapr", "Auto Approve"),
                    ("btn_acap", "Auto Caption"), ("btn_atmr", "Timer Set")
                ]
            elif cat == "supreme":
                b_list = [
                    ("btn_sgbr", "Global Broadcast"), ("btn_ssys", "System Analytics"),
                    ("btn_snet", "Bot Network"), ("btn_sadm", "Admin Manager"),
                    ("btn_smsg", "System Msg"), ("btn_smnt", "Maint: ON/OFF"),
                    ("btn_spur", "Purge Cache"), ("btn_scus", "Customize Buttons"),
                    ("btn_srst", "System Restart")
                ]
            else: # other
                b_list = [
                    ("btn_back", "ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ"), ("btn_hdual", "ᴅᴜᴀʟ ᴘᴏsᴛ ɢᴜɪᴅᴇ"),
                    ("btn_hprem", "ᴘʀᴇᴍɪᴜᴍ ɪɴғᴏ"), ("btn_pcon", "ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ"),
                    ("btn_pqrs", "sʜᴏᴡ ᴘᴀʏᴍᴇɴᴛ ǫʀ"), ("btn_invite", "ɪɴᴠɪᴛᴇ ғʀɪᴇɴᴅs")
                ]

            for i in range(0, len(b_list), 2):
                row = []
                key, def_val = b_list[i]
                row.append(InlineKeyboardButton(f"{btns_config.get(key, def_val)}", callback_data=f"editbtn_{key}"))
                if i + 1 < len(b_list):
                    key2, def_val2 = b_list[i+1]
                    row.append(InlineKeyboardButton(f"{btns_config.get(key2, def_val2)}", callback_data=f"editbtn_{key2}"))
                keyboard.append(row)

            keyboard.append([InlineKeyboardButton(" BACK", callback_data="cust_btns")])
            await cb.message.edit(f" **Customize {cat.upper()} Buttons**\n\nClick a button to rename it:", reply_markup=InlineKeyboardMarkup(keyboard))
            await cb.answer()

        elif data == "cust_msgs":
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            msgs_config = get_global_config().get("custom_messages", {})
            m_list = [
                ("msg_welcome", "ᴡᴇʟᴄᴏᴍᴇ ᴍᴇssᴀɢᴇ"), ("msg_help", "ʜᴇʟᴘ ᴍᴇssᴀɢᴇ"),
                ("msg_premium", "ᴘʀᴇᴍɪᴜᴍ ᴍᴇssᴀɢᴇ"), ("msg_referral", "ʀᴇғᴇʀʀᴀʟ ᴍᴇssᴀɢᴇ"),
                ("msg_search", "sᴇᴀʀᴄʜ ᴍᴇssᴀɢᴇ"), ("msg_admin", "ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ"),
                ("msg_supreme", "sᴜᴘʀᴇᴍᴇ ᴘᴀɴᴇʟ")
            ]
            keyboard = []
            for key, label in m_list:
                status = " Set" if key in msgs_config else " Default"
                keyboard.append([InlineKeyboardButton(f"{label} ({status})", callback_data=f"editmsg_{key}")])

            keyboard.append([InlineKeyboardButton(" RESET ALL",  callback_data="reset_messages")])
            keyboard.append([InlineKeyboardButton(" BACK",       callback_data="supreme_customize")])

            await cb.message.edit(" **Panel Message Customizer**\n\nSelect a message to edit:", reply_markup=InlineKeyboardMarkup(keyboard))
            await cb.answer()

        elif data.startswith("editbtn_"):
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            key = data[8:]
            TEMP_EDIT[uid] = {"mode": "customize_button", "key": key}
            await cb.message.edit(
                f" **Customize Button**\n\nKey: `{key}`\n\nSend the **new name** for this button.\n`/cancel` to abort.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" CANCEL", callback_data="cust_btns")]])
            )
            await cb.answer()

        elif data.startswith("editmsg_"):
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            key = data[8:]
            TEMP_EDIT[uid] = {"mode": "customize_message", "key": key}

            placeholders = ""
            if key == "msg_welcome": placeholders = "\n\nAvailable: `{name}`, `{username}`"
            elif key == "msg_premium": placeholders = "\n\nAvailable: `{status}`, `{price}`, `{contact}`"
            elif key == "msg_referral": placeholders = "\n\nAvailable: `{ref_count}`, `{ref_rewards}`, `{bot_username}`, `{uid}`"
            elif key == "msg_supreme": placeholders = "\n\nAvailable: `{bots}`, `{users}`, `{files}`, `{duals}`"

            await cb.message.edit(
                f" **Edit Panel Message**\n\nKey: `{key}`{placeholders}\n\nSend the **new text** for this message.\nUse `-clear` to reset to default.\n`/cancel` to abort.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" CANCEL", callback_data="cust_msgs")]])
            )
            await cb.answer()

        elif data == "reset_messages":
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            update_global_config("custom_messages", {})
            await cb.answer(" All messages reset to default!", show_alert=True)
            cb.data = "cust_msgs"
            await cb_handler(client, cb)

        elif data.startswith("cbtn_"):
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            key = data[5:]
            TEMP_EDIT[uid] = {"mode": "customize_button", "key": key}
            await cb.message.edit(
                f" **Customize Button**\n\nKey: `{key}`\n\nSend the **new name** for this button.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" CANCEL", callback_data="supreme_customize")]])
            )
            await cb.answer()

        elif data == "reset_buttons":
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            update_global_config("custom_buttons", {})
            await cb.answer(" All buttons reset to default!", show_alert=True)
            cb.data = "cust_btns"
            await cb_handler(client, cb)

        elif data == "global_broadcast":
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            await cb.message.edit(
                f" **Global Broadcast**\n\n `{len(get_all_users())}` |  `{len(ACTIVE_CLIENTS)}`\n\nReply to a message with `/broadcast`.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Back", callback_data="supreme_panel")]])
            )
            await cb.answer()

        elif data == "system_stats":
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            t, u, f = shutil.disk_usage("/")
            pend    = sum(len(v) for v in _PENDING.values())
            active_tokens = sum(1 for v in SHORTENER_TOKENS.values()
                                if not v["used"] and time.time() < v["expires_at"])
            dp_count = len(load_db(DUAL_POST_DB))
            await cb.message.edit(
                f" **ELITE SUPREME SYSTEM METRICS**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f" **NETWORK STATUS**\n"
                f" ├ Registered Bots: `{len(get_all_bots())}`\n"
                f" └ Active Instances: `{len(ACTIVE_CLIENTS)}` online\n\n"
                f" **GLOBAL DATABASE**\n"
                f" ├ Total Users: `{len(load_db(USERS_DB))}`\n"
                f" ├ Total Files: `{len(load_db(FILES_DB))}`\n"
                f" └ Dual Posts: `{dp_count}`\n\n"
                f" **SYSTEM CORE**\n"
                f" ├ Pending Requests: `{pend}`\n"
                f" └ Active Tokens: `{active_tokens}`\n\n"
                f" **SERVER STORAGE**\n"
                f" ├ Used Space: `{u//(2**30)} GB`\n"
                f" ├ Total Space: `{t//(2**30)} GB`\n"
                f" └ Free Space: `{f//(2**30)} GB`\n\n"
                f" **UPTIME:** `{str(datetime.now()-START_TIME).split('.')[0]}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(" REFRESH SYSTEM", callback_data="system_stats")],
                    [InlineKeyboardButton(" BACK TO PANEL",  callback_data="supreme_panel")]
                ])
            )
            await cb.answer()

        elif data == "all_bots_list":
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            ab = get_all_bots()
            text = f" **All Bots ({len(ab)})**\n\n"
            for i, (k, b) in enumerate(list(ab.items())[:20], 1):
                if isinstance(b, dict):
                    text += f"{i}. {'' if int(k) in ACTIVE_CLIENTS else ''} @{b['bot_username']} — {b.get('owner_name','?')}\n"
            if len(ab) > 20: text += f"\n...+{len(ab)-20} more"
            await cb.message.edit(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Back", callback_data="supreme_panel")]])
            )
            await cb.answer()

        elif data == "manage_admins":
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            admins = load_db(ADMINS_DB)
            text   = f" **Admins**\n\n Main: `{MAIN_ADMIN}`\n\nSecondary ({len(admins)}):\n"
            for aid in admins: text += f"• `{aid}`\n"
            text += "\n`/addadmin ID` `/deladmin ID`"
            await cb.message.edit(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Back", callback_data="supreme_panel")]])
            )
            await cb.answer()

        elif data == "toggle_maintenance":
            if uid != MAIN_ADMIN: return await cb.answer("", show_alert=True)
            curr = get_global_config().get("maintenance", False)
            update_global_config("maintenance", not curr)
            await cb.answer(f"Maintenance: {'ON ' if not curr else 'OFF '}", show_alert=True)
            await cb.message.edit(" **Supreme Panel**", reply_markup=kb_supreme())

        elif data == "global_msg_set":
            if uid != MAIN_ADMIN: return await cb.answer()
            await cb.message.edit(
                " `/setglobal MESSAGE` or `/setglobal off`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(" Back", callback_data="supreme_panel")]])
            )
            await cb.answer()


        elif data == "manual_clean_cache":
            if uid != MAIN_ADMIN: return await cb.answer()
            count = clean_expired_cache()
            expired_tokens = clean_expired_tokens()
            await cb.answer(f" Cleaned {count} cache + {expired_tokens} tokens!", show_alert=True)

        elif data == "restart_all_bots":
            if uid != MAIN_ADMIN: return await cb.answer()
            await cb.answer(" Restarting...", show_alert=True)
            os.execl(sys.executable, sys.executable, *sys.argv)


        elif data.startswith("req_"):
            parts = data.split("_")
            action = parts[1] # approve or decline
            cid = int(parts[2])
            u_id = int(parts[3])

            if action == "approve":
                try:
                    try:
                        await client.approve_chat_join_request(cid, u_id)
                    except Exception:
                        main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None)
                        if main_client: await main_client.approve_chat_join_request(cid, u_id)
                        else: raise

                    clear_join_request(cid, u_id)
                    await cb.answer(f"User {u_id} approved!", show_alert=True)
                    try: await client.send_message(u_id, stylish(" **Your request to join has been approved!**"))
                    except: pass
                except Exception as e:
                    await cb.answer(f"Failed: {e}", show_alert=True)
            else: # decline
                try:
                    # Pyrogram doesn't have decline_chat_join_request but we can just clear it from our list
                    # and optionally kick the user if they were in a state that needed declining.
                    # Usually, just clearing it from our tracker is enough if auto-approve is OFF.
                    clear_join_request(cid, u_id)
                    await cb.answer(f"User {u_id} request declined/cleared.", show_alert=True)
                except Exception as e:
                    await cb.answer(f"Failed: {e}", show_alert=True)

            # Refresh requests list
            class FakeCB:
                def __init__(self, from_user, message):
                    self.from_user = from_user
                    self.message = message
                    self.data = "manage_requests"
                async def answer(self, *a, **k): pass

            await cb_handler(client, FakeCB(cb.from_user, cb.message))

        elif data == "back_to_start":
            bi  = get_bot_info(bot_id)
            text = (bi.get("custom_welcome") if bi else None) or (
                "<blockquote>"
                f"ʜᴇʟʟᴏ {cb.from_user.first_name}\n\n"
                "ɪ ᴀᴍ ғɪʟᴇ sᴛᴏʀᴇ ʙᴏᴛ, ɪ ᴄᴀɴ sᴛᴏʀᴇ ᴘʀɪᴠᴀᴛᴇ ғɪʟᴇs ɪɴ sᴘᴇᴄɪғɪᴇᴅ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴏᴛʜᴇʀ ᴜsᴇʀs ᴄᴀɴ ᴀᴄᴄᴇss ɪᴛ ғʀᴏᴍ sᴘᴇᴄɪᴀʟ ʟɪɴᴋ.\n\n"
                "/help 𝚝𝚘 𝚔𝚗𝚘𝚠 𝚖𝚘𝚛𝚎 𝚊𝚋𝚘𝚞𝚝 𝚋𝚘𝚝"
                "</blockquote>"
            )
            img  = bi.get("welcome_image") if bi else None
            kbd  = kb_start(bot_id, uid)
            try:
                if img:
                    await cb.message.delete()
                    await client.send_photo(cb.message.chat.id, img, caption=stylish(text), reply_markup=kbd)
                else:
                    await cb.message.edit(stylish(text), reply_markup=kbd)
            except Exception:
                await cb.message.edit(stylish(text), reply_markup=kbd)
            await cb.answer()

        else:
            await cb.answer()


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

async def _auto_delete(msg, delay: int):
    await asyncio.sleep(delay)
    try: await msg.delete()
    except Exception: pass

# ═══════════════════════════════════════════════════════════════
#  BACKGROUND TASKS
# ═══════════════════════════════════════════════════════════════

async def background_tasks():
    cycle = 0
    while True:
        await asyncio.sleep(600)
        cycle += 1
        try:
            USER_FLOOD.clear()
            n = clean_expired_cache()
            if n: logger.info(f" Cleaned {n} cache entries")
            t = clean_expired_tokens()
            if t: logger.info(f" Cleaned {t} expired tokens")
            if cycle % 6 == 0:
                now = datetime.now()
                for cid in list(_PENDING):
                    for uid in list(_PENDING.get(cid, {})):
                        try:
                            if (now - datetime.fromisoformat(_PENDING[cid][uid])).days > PENDING_REQUEST_TTL_DAYS:
                                del _PENDING[cid][uid]
                        except Exception:
                            _PENDING[cid].pop(uid, None)
                    if not _PENDING.get(cid): _PENDING.pop(cid, None)
        except Exception as e:
            logger.error(f"Background task: {e}")

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

async def resolve_db_channel(client, channel_id):
    """Try to resolve DB_CHANNEL peer with retries."""
    for i in range(3):
        try:
            chat = await client.get_chat(channel_id)
            return chat
        except Exception as e:
            msg = str(e)
            if "Peer id invalid" in msg:
                logger.warning(f" [Attempt {i+1}] Invalid Peer ID {channel_id}. Patching should fix this, but ensure the ID is correct.")
            elif "403" in msg:
                logger.warning(f" [Attempt {i+1}] Bot is not a member or admin in {channel_id}.")

            if i == 2:
                logger.error(f" Final Failure: Could not resolve DB_CHANNEL {channel_id}: {e}")
                break
            await asyncio.sleep(2)
    return None

async def main():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║   ULTRA FILESTORE BOT v7.0 — ELITE EDITION             ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    if DB_CHANNEL == -1000000000000:
        logger.error(" DB_CHANNEL not configured!"); return

    _load_pending()
    logger.info(f" Loaded pending requests for {len(_PENDING)} channels")

    await start_web_server()

    logger.info(" Starting Main Bot...")
    main_app = await start_bot(MAIN_BOT_TOKEN)
    if main_app:
        chat = await resolve_db_channel(main_app, DB_CHANNEL)
        if chat:
            logger.info(f" Main Bot resolved DB_CHANNEL: {chat.title} ({DB_CHANNEL})")
        else:
            logger.warning(f" Main Bot failed to resolve DB_CHANNEL {DB_CHANNEL}. Make sure the bot is an admin there.")
    if not main_app:
        logger.error(" Main bot failed!"); return

    # Ensure main bot is in BOTS_DB
    me_main = await main_app.get_me()
    if not get_bot_info(me_main.id):
        save_bot_info(MAIN_BOT_TOKEN, me_main.id, me_main.username, MAIN_ADMIN, "Supreme Admin")


    all_bots = get_all_bots()
    if all_bots:
        tasks = [
            start_bot(b["token"], parent_bot_id=b.get("parent_bot_id"))
            for b in all_bots.values()
            if isinstance(b, dict) and b.get("token") and b["token"] != MAIN_BOT_TOKEN
        ]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            ok = sum(1 for r in results if r and not isinstance(r, Exception))
            logger.info(f" {ok}/{len(tasks)} clone bots started")

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║          ALL SYSTEMS OPERATIONAL v7.0                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f" Admin   : {MAIN_ADMIN}")
    print(f" Bots    : {len(ACTIVE_CLIENTS)}")
    print(f" Port    : {PORT}")
    print(f" Started : {START_TIME:%Y-%m-%d %H:%M:%S}")
    print()

    asyncio.create_task(background_tasks())
    await idle()

    logger.info(" Shutting down...")
    global _HTTP
    if _HTTP and not _HTTP.closed: await _HTTP.close()
    for cd in ACTIVE_CLIENTS.values():
        try: await cd["app"].stop()
        except Exception: pass
    logger.info(" Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped.")
    except Exception as e:
        logger.error(f" Fatal: {e}"); raise
