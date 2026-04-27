"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 ULTRA ADVANCED FILESTORE BOT v7.0 — ELITE EDITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DUAL TIER POST SYSTEM
   ├─ EK LINK → 2 experiences: FREE + PREMIUM
   ├─ FREE users  → shortener ads → free files (auto-delete)
   ├─ PREMIUM users → direct delivery → pro files (no delete)
   ├─ Creator workflow: /dualpost → files → /dpremium → files → /dpdone
   ├─ Dual post preview, analytics, delete
   └─ Token-secured shortener bypass

✅ SHORTENER TOKEN SYSTEM  — 15min expiry, one-time use
✅ SMART 2-PHASE REBUILD   — backup JSON restore + #FS_META scan
✅ REBUILD NEVER HANGS     — manual pagination, FloodWait handled
✅ RENDER READY            — aiohttp health-check on $PORT
✅ BROADCAST               — stored in DB_CHANNEL, copy per-bot
✅ THUMBNAIL               — BytesIO in_memory → thumb param
✅ CAPTION EDITOR          — FSM, -clear support
✅ WELCOME EDITOR          — /setwelcome interactive 2-step
✅ JOIN REQUEST ACCESS     — pending = bot access
✅ ADVANCED LINK PROTECT   — dynamic invite link with expiry
✅ FILE RENAMER            — renaming with download & re-upload
✅ CLONE + REFERRAL + PREMIUM + ANALYTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, sys, json, asyncio, hashlib, logging, random, shutil, time, tempfile
import aiohttp
from aiohttp import web
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, BotCommand,
    InlineQueryResultArticle, InputTextMessageContent
)
from pyrogram.errors import FloodWait, UserNotParticipant, SlowmodeWait
from pyrogram.enums import ChatMemberStatus

# ═══════════════════════════════════════════════════════════════
# 🔧 CONFIGURATION
# ═══════════════════════════════════════════════════════════════

API_ID         = int(os.environ.get("API_ID",         "23790796"))
API_HASH       = os.environ.get("API_HASH",            "626eb31c9057007df4c2851b3074f27f")
MAIN_BOT_TOKEN = os.environ.get("MAIN_BOT_TOKEN",     "8607033631:AAEEHymSzeLeP8wpH1TR4vnZSyai3kI1DTE")
MAIN_ADMIN     = int(os.environ.get("MAIN_ADMIN",     "7915069238"))
DB_CHANNEL     = int(os.environ.get("DB_CHANNEL",     "-1003982754680"))
PORT           = int(os.environ.get("PORT",            "8080"))
SESSION_STRING = os.environ.get("SESSION_STRING",     "")

FILE_CACHE_DURATION      = 3600
MAX_FORCE_SUB_CHANNELS   = 3
PENDING_REQUEST_TTL_DAYS = 30
METADATA_TAG             = "#FS_META"
MAX_BROADCAST_RATE       = 0.05
SHORTENER_TOKEN_EXPIRY   = 900   # 15 minutes

BACKUP_FILES = [
    "files.json","batches.json","bots.json","users.json",
    "admins.json","file_cache.json","config.json",
    "pending_requests.json","dual_posts.json","protected_links.json","user_links.json"
]

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
    BotCommand("start",       "🚀 Start the bot"),
    BotCommand("admin",       "⚡ Admin Panel"),
    BotCommand("supreme",     "👑 Supreme Panel"),
    BotCommand("clone",       "🤖 Clone your bot"),
    BotCommand("batch",       "📦 Batch mode"),
    BotCommand("done",        "✅ Finish batch"),
    BotCommand("cancel",      "❌ Cancel"),
    BotCommand("setfs",       "⚙️ Force subscribe"),
    BotCommand("mybots",      "🤖 Your cloned bots"),
    BotCommand("stats",       "📊 Statistics"),
    BotCommand("help",        "ℹ️ Help"),
    BotCommand("broadcast",   "📢 Broadcast"),
    BotCommand("ban",         "🚫 Ban user"),
    BotCommand("unban",       "✅ Unban user"),
    BotCommand("botinfo",     "ℹ️ Bot info"),
    BotCommand("settimer",    "⏱ Auto-delete timer"),
    BotCommand("search",      "🔍 Search files"),
    BotCommand("premium",     "🌟 Premium"),
    BotCommand("setprice",    "💰 Set Premium Price (Admin)"),
    BotCommand("setcontact",  "📞 Set Premium Contact (Admin)"),
    BotCommand("setqr",       "🖼 Set Premium QR Code (Admin)"),
    BotCommand("givepremium", "💎 Give Premium (Admin)"),
    BotCommand("removepremium", "❌ Remove Premium (Admin)"),
    BotCommand("shortener",   "🔗 URL Shortener"),
    BotCommand("setlog",      "📝 Log Channel"),
    BotCommand("setchannel",  "📢 Connect Channel"),
    BotCommand("setmode",     "⚙️ Set Join Mode"),
    BotCommand("protect",     "🛡 Protect Channel Link"),
    BotCommand("myplinks",    "📋 My Protected Links"),
    BotCommand("rebuild",     "🔄 Rebuild DB from channel"),
    BotCommand("backup",      "💾 Force backup now"),
    BotCommand("restart",     "♻️ Restart (Supreme)"),
    BotCommand("ping",        "🏓 Ping"),
    BotCommand("listfiles",   "📋 List files"),
    BotCommand("editfile",    "✏️ Edit file"),
    BotCommand("delfile",     "🗑 Delete file"),
    BotCommand("setwelcome",  "👋 Set welcome message"),
    BotCommand("dualpost",    "🎭 Create dual-tier post"),
    BotCommand("dpremium",    "💎 Switch to premium tier"),
    BotCommand("dpdone",      "✅ Finish dual post"),
    BotCommand("dpcancel",    "❌ Cancel dual post"),
    BotCommand("myduals",     "📋 My dual posts"),
    BotCommand("deldual",     "🗑 Delete dual post"),
    BotCommand("dpstats",     "📊 Dual post analytics"),
]

# ═══════════════════════════════════════════════════════════════
# 📝 LOGGING
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("FS")

# ═══════════════════════════════════════════════════════════════
# 💾 DATABASE — Atomic JSON with in-memory cache
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
            "last_active": str(datetime.now())
        }
    else:
        users[key]["last_active"] = str(datetime.now())
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

def fmt_size(size) -> str:
    if not size: return "N/A"
    for unit in ["B","KB","MB","GB","TB"]:
        if size < 1024: return f"{size:.2f} {unit}"
        size /= 1024

def unique_id() -> str:
    return hashlib.md5(str(time.time() + random.random()).encode()).hexdigest()[:12]

def file_icon(name: str) -> str:
    if not name or name == "Message/Post": return "✉️"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return {
        "pdf":"📄","doc":"📝","docx":"📝","txt":"📃","xlsx":"📊","pptx":"📑","csv":"📊",
        "mp4":"🎬","mkv":"🎬","avi":"🎬","mov":"🎬","webm":"🎬",
        "mp3":"🎵","flac":"🎵","wav":"🎵","aac":"🎵","m4a":"🎵",
        "jpg":"🖼","jpeg":"🖼","png":"🖼","gif":"🖼","webp":"🖼",
        "zip":"🗜","rar":"🗜","7z":"🗜","tar":"🗜","gz":"🗜",
        "apk":"📱","exe":"💻","py":"🐍","js":"🌐","html":"🌐",
    }.get(ext, "📁")

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
# 🎭 DUAL POST SYSTEM
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
        return "📂 FREE" if self.stage == "free" else "💎 PREMIUM"


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
# 🔑 SHORTENER TOKEN SYSTEM
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
# 💾 BACKUP
# ═══════════════════════════════════════════════════════════════

async def do_backup(bot_client=None) -> int:
    # Always prioritize the main bot for backups to ensure DB_CHANNEL access
    main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None)
    client = main_client or bot_client

    if not client:
        logger.error("💾 Backup failed: No active bot client found.")
        return 0

    count = 0
    # Create a zip of the database folder for extra safety
    backup_zip = f"database_backup_{int(time.time())}.zip"
    try:
        shutil.make_archive(backup_zip.replace(".zip", ""), 'zip', DB_FOLDER)
        await client.send_document(
            DB_CHANNEL, document=backup_zip,
            caption=f"📦 **FULL DB BUNDLE** | `{backup_zip}`\n📅 {datetime.now():%Y-%m-%d %H:%M:%S}"
        )
        os.remove(backup_zip)
        logger.info(f"💾 Zip backup sent to DB_CHANNEL")
    except Exception as e:
        logger.error(f"Zip backup failed: {e}")

    for fname in BACKUP_FILES:
        path = f"{DB_FOLDER}/{fname}"
        if not os.path.exists(path): continue
        try:
            await client.send_document(
                DB_CHANNEL, document=path,
                caption=f"📂 **DB Backup** | `{fname}` | {datetime.now():%Y-%m-%d %H:%M:%S}"
            )
            count += 1
            await asyncio.sleep(0.5)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await client.send_document(DB_CHANNEL, document=path,
                    caption=f"📂 **DB Backup** | `{fname}`")
                count += 1
            except Exception as ex:
                logger.error(f"Backup retry failed {fname}: {ex}")
        except Exception as e:
            logger.error(f"Backup failed {fname}: {e}")

    logger.info(f"💾 Backup complete: {count} files")
    return count

# ═══════════════════════════════════════════════════════════════
# 📤 DELIVER FILE
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

            # Fallback 2: Use Userbot if available
            if GLOBAL_USERBOT:
                try:
                    return await GLOBAL_USERBOT.copy_message(
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
            caption=caption or f"📁 {file_data.get('file_name', 'File')}",
            reply_markup=reply_markup
        )
    return None

async def deliver_batch_files(client, chat_id: int, file_ids: list,
                               bot_id: int, is_premium: bool) -> tuple:
    files  = load_db(FILES_DB)
    bi     = get_bot_info(bot_id)
    auto_del = bi.get("auto_delete_time", 600) if bi else 600
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

# ═══════════════════════════════════════════════════════════════
# 💾 METADATA
# ═══════════════════════════════════════════════════════════════

async def save_meta(client, meta: dict) -> bool:
    try:
        txt = f"{METADATA_TAG}\n{json.dumps(meta, ensure_ascii=False)}"
        await client.send_message(DB_CHANNEL, txt)
        return True
    except Exception as e:
        logger.error(f"Meta save: {e}")
        return False

# ═══════════════════════════════════════════════════════════════
# 🔄 SMART 2-PHASE DB REBUILD
# ═══════════════════════════════════════════════════════════════

BATCH_SIZE  = 100
MSG_TIMEOUT = 20

async def _fetch_batch(userbot, chat_id: int, offset_id: int) -> list:
    try:
        msgs = await asyncio.wait_for(
            userbot.get_messages(
                chat_id,
                message_ids=list(range(max(1, offset_id - BATCH_SIZE), offset_id))
            ),
            timeout=MSG_TIMEOUT
        )
        result = [m for m in (msgs if isinstance(msgs, list) else [msgs]) if m and m.id]
        return sorted(result, key=lambda m: m.id, reverse=True)
    except asyncio.TimeoutError:
        logger.warning(f"Batch fetch timeout at offset {offset_id}")
        return []
    except FloodWait as e:
        await asyncio.sleep(e.value + 2)
        return []
    except Exception as e:
        logger.warning(f"Batch fetch error: {e}")
        return []

async def _get_latest_msg_id(userbot, chat_id: int) -> int:
    try:
        async for m in userbot.get_chat_history(chat_id, limit=1):
            return m.id
    except Exception:
        pass
    return 0

async def rebuild_phase1(userbot, upd_fn) -> dict:
    await upd_fn("📥 **Phase 1: Finding backup files...**")
    latest_id = await _get_latest_msg_id(userbot, DB_CHANNEL)
    if not latest_id:
        latest_id = 99999

    found    = {}
    offset_id = latest_id + 1
    scanned  = 0
    MAX_SCAN = 5000

    while offset_id > 1 and scanned < MAX_SCAN and len(found) < len(BACKUP_FILES):
        batch = await _fetch_batch(userbot, DB_CHANNEL, offset_id)
        if not batch:
            if offset_id <= BATCH_SIZE: break
            offset_id -= BATCH_SIZE
            await asyncio.sleep(0.3)
            continue

        for msg in batch:
            scanned += 1
            try:
                doc = msg.document
                if doc and doc.file_name in BACKUP_FILES:
                    fname = doc.file_name
                    if fname not in found:
                        found[fname] = {
                            "msg_id": msg.id, "date": msg.date,
                            "file_id": doc.file_id, "size": doc.file_size or 0
                        }
            except Exception:
                pass

        offset_id = batch[-1].id
        await upd_fn(
            f"📥 **Phase 1** | Scanned: `{scanned}` | Found: `{len(found)}/{len(BACKUP_FILES)}`\n"
            f"Current ID: `{offset_id}`"
        )
        if len(found) == len(BACKUP_FILES): break
        await asyncio.sleep(0.1)

    restored = {}
    for i, (fname, info) in enumerate(found.items(), 1):
        try:
            path       = f"{DB_FOLDER}/{fname}"
            data_bytes = await asyncio.wait_for(
                userbot.download_media(info["file_id"], in_memory=True), timeout=30
            )
            data_bytes.seek(0)
            content = json.loads(data_bytes.read().decode("utf-8"))
            save_db(path, content)
            invalidate_cache(path)
            restored[fname] = info["date"]
            await upd_fn(f"📥 **Phase 1** | ✅ `{i}/{len(found)}` restored | `{fname}`")
        except Exception as e:
            logger.error(f"Failed to restore {fname}: {e}")

    return restored

async def rebuild_phase2(userbot, upd_fn, since_date=None, latest_id: int = 0) -> dict:
    stats   = {"files": 0, "batches": 0, "duals": 0, "errors": 0}
    files   = load_db(FILES_DB)
    batches = load_db(BATCH_DB)
    duals   = load_db(DUAL_POST_DB)

    since_ts  = since_date.timestamp() if since_date else 0
    if not latest_id:
        latest_id = await _get_latest_msg_id(userbot, DB_CHANNEL)
        if not latest_id:
            return stats

    offset_id = latest_id + 1
    scanned   = 0
    stopped   = False

    while offset_id > 1 and not stopped:
        batch = await _fetch_batch(userbot, DB_CHANNEL, offset_id)
        if not batch:
            if offset_id <= BATCH_SIZE: break
            offset_id -= BATCH_SIZE
            await asyncio.sleep(0.3)
            continue

        for msg in batch:
            scanned += 1
            if since_ts and msg.date and msg.date.timestamp() < since_ts:
                stopped = True
                break
            try:
                text = msg.text or msg.caption
                if not text: continue
                text = str(text).strip()
                if not text.startswith(METADATA_TAG): continue
                raw  = text[len(METADATA_TAG):].strip()
                meta = json.loads(raw)
                if "unique_id" not in meta: continue
                uid  = meta["unique_id"]

                mtype = meta.get("type", "file")
                if mtype == "dual_post":
                    if uid not in duals:
                        duals[uid] = meta
                        stats["duals"] += 1
                elif mtype == "batch":
                    if uid not in batches:
                        batches[uid] = {
                            "files": meta.get("files", []),
                            "created_by": meta.get("created_by"),
                            "bot_id": meta.get("bot_id"),
                            "date": meta.get("date", str(datetime.now()))
                        }
                        stats["batches"] += 1
                else:
                    if uid not in files:
                        files[uid] = {
                            "file_id": meta["file_id"],
                            "file_name": meta.get("file_name", "Unknown"),
                            "file_size": meta.get("file_size", 0),
                            "caption": meta.get("caption"),
                            "user_id": meta.get("user_id"),
                            "bot_id": meta.get("bot_id"),
                            "upload_date": meta.get("upload_date", str(datetime.now())),
                            "db_msg_id": meta.get("db_msg_id"),
                            "access_count": meta.get("access_count", 0),
                            "media_type": meta.get("media_type", "document"),
                            "custom_thumbnail": meta.get("custom_thumbnail"),
                        }
                        stats["files"] += 1
            except Exception:
                stats["errors"] += 1

        offset_id = batch[-1].id
        await upd_fn(
            f"🔍 **Phase 2** | `{scanned}` msgs | "
            f"Files: `{stats['files']}` | Batches: `{stats['batches']}` | "
            f"Duals: `{stats['duals']}`"
        )
        await asyncio.sleep(0.1)

    save_db(FILES_DB, files)
    save_db(BATCH_DB, batches)
    save_db(DUAL_POST_DB, duals)
    invalidate_cache(FILES_DB)
    invalidate_cache(BATCH_DB)
    invalidate_cache(DUAL_POST_DB)
    global _GLOBAL_CFG
    _GLOBAL_CFG = load_db(CONFIG_DB)
    return stats

async def smart_rebuild(status_msg=None) -> dict:
    async def upd(text):
        if status_msg:
            try: await status_msg.edit(text)
            except Exception: pass

    if not SESSION_STRING:
        await upd(
            "❌ **SESSION_STRING not configured!**\n\n"
            "1️⃣ `python generate_session.py`\n"
            "2️⃣ Set `SESSION_STRING` env var\n"
            "3️⃣ Restart → `/rebuild` works"
        )
        raise ValueError("SESSION_STRING not set")

    combined = {"phase1_restored": 0, "phase2_files": 0, "phase2_batches": 0,
                "phase2_duals": 0, "phase2_errors": 0, "backup_date": None}

    try:
        async with Client(
            "userbot_rebuild", api_id=API_ID, api_hash=API_HASH,
            session_string=SESSION_STRING, in_memory=True
        ) as userbot:
            await upd("✅ Userbot connected!\n\n📥 Starting Phase 1...")
            latest_id = await _get_latest_msg_id(userbot, DB_CHANNEL)

            restored = await rebuild_phase1(userbot, upd)
            combined["phase1_restored"] = len(restored)

            backup_date = None
            if restored:
                dates = [d for d in restored.values() if d]
                if dates: backup_date = max(dates)
            combined["backup_date"] = str(backup_date) if backup_date else None

            await upd(
                f"✅ **Phase 1 Done!** `{len(restored)}` files restored\n\n"
                f"🔍 Phase 2: Scanning #FS_META..."
            )
            await asyncio.sleep(1)

            stats2 = await rebuild_phase2(userbot, upd, since_date=backup_date,
                                          latest_id=latest_id)
            combined["phase2_files"]   = stats2["files"]
            combined["phase2_batches"] = stats2["batches"]
            combined["phase2_duals"]   = stats2.get("duals", 0)
            combined["phase2_errors"]  = stats2["errors"]

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Rebuild error: {e}")
        await upd(f"❌ **Rebuild failed!**\n\n`{e}`")
        raise

    return combined

# ═══════════════════════════════════════════════════════════════
# 📢 BROADCAST
# ═══════════════════════════════════════════════════════════════

async def store_broadcast(client, original_msg) -> int | None:
    try:
        stored = await original_msg.forward(DB_CHANNEL)
        return stored.id
    except Exception as e:
        logger.error(f"Broadcast store: {e}")
        return None

async def do_broadcast(bot_ids: list, bc_msg_id: int, status_msg=None, reply_markup=None) -> tuple:
    total_ok = total_fail = 0
    t0 = datetime.now()
    for b_idx, bot_id in enumerate(bot_ids, 1):
        if bot_id not in ACTIVE_CLIENTS: continue
        app   = ACTIVE_CLIENTS[bot_id]["app"]
        uname = ACTIVE_CLIENTS[bot_id]["username"]
        users = get_all_users(bot_id)
        for u_idx, user in enumerate(users, 1):
            uid = user["user_id"]
            try:
                await app.copy_message(uid, DB_CHANNEL, bc_msg_id, reply_markup=reply_markup)
                total_ok += 1
            except FloodWait as e:
                await asyncio.sleep(e.value + 2)
                try:
                    await app.copy_message(uid, DB_CHANNEL, bc_msg_id, reply_markup=reply_markup)
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
                        f"📢 **Broadcast**\n\n`[{bar}]` {pct}%\n"
                        f"🤖 Bot {b_idx}/{len(bot_ids)}: @{uname}\n"
                        f"✅ `{total_ok}` | ❌ `{total_fail}` | ⏱ `{elapsed}s`"
                    )
                except Exception:
                    pass
            await asyncio.sleep(MAX_BROADCAST_RATE)
    return total_ok, total_fail

# ═══════════════════════════════════════════════════════════════
# 🌐 HEALTH CHECK SERVER
# ═══════════════════════════════════════════════════════════════

async def health_handler(request):
    uptime = str(datetime.now() - START_TIME).split(".")[0]
    return web.json_response({
        "status": "ok", "uptime": uptime,
        "bots_online": len(ACTIVE_CLIENTS),
        "ts": datetime.now().isoformat()
    })

async def start_web_server():
    app = web.Application()
    app.router.add_get("/",       health_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/ping",   health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f"🌐 Health-check on port {PORT}")

# ═══════════════════════════════════════════════════════════════
# 🤖 BOT MANAGEMENT
# ═══════════════════════════════════════════════════════════════

START_TIME      = datetime.now()
ACTIVE_CLIENTS: dict = {}
GLOBAL_USERBOT: Client = None
TEMP_BATCH:     dict = {}
TEMP_BROADCAST: dict = {}
TEMP_EDIT:      dict = {}
TEMP_WELCOME:   dict = {}
TEMP_DUAL:      dict = {}
TEMP_PROTECT:   dict = {}
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
    for fs in force_subs:
        ch_id = fs["channel_id"] if isinstance(fs, dict) else fs
        try:
            m = await client.get_chat_member(ch_id, user_id)
            if m.status in (ChatMemberStatus.BANNED, ChatMemberStatus.LEFT):
                must_join.append(fs)
        except UserNotParticipant:
            if has_pending_request(ch_id, user_id): continue
            must_join.append(fs)
        except Exception:
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
        logger.error(f"Bot start [{token[:12]}...]: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# 🎨 KEYBOARDS
# ═══════════════════════════════════════════════════════════════

def get_btn_name(key: str, default: str) -> str:
    btns = get_global_config().get("custom_buttons", {})
    return btns.get(key, default)

def get_msg_text(key: str, default: str) -> str:
    msgs = get_global_config().get("custom_messages", {})
    return msgs.get(key, default)

class SafeDict(dict):
    def __missing__(self, key): return '{' + key + '}'

def kb_start(bot_id, user_id):
    bi = get_bot_info(bot_id)
    is_owner = bi and bi.get("owner_id") == user_id
    rows = []

    if user_id == MAIN_ADMIN:
        rows.append([InlineKeyboardButton(get_btn_name("btn_supreme", "👑 SUPREME PANEL"), callback_data="supreme_panel")])
    if is_admin(user_id) or is_owner:
        rows.append([InlineKeyboardButton(get_btn_name("btn_admin", "⚡ ADMIN PANEL"), callback_data="admin_panel")])

    rows += [
        [InlineKeyboardButton(get_btn_name("btn_batch", "📦 BATCH MODE"),   callback_data="start_batch"),
         InlineKeyboardButton(get_btn_name("btn_clone", "🤖 CLONE BOT"),    callback_data="clone_menu")],
        [InlineKeyboardButton(get_btn_name("btn_dual",  "🎭 DUAL POST"),    callback_data="dual_post_menu"),
         InlineKeyboardButton(get_btn_name("btn_refer", "👥 REFER & EARN"), callback_data="referral_menu")],
        [InlineKeyboardButton(get_btn_name("btn_dash",  "📊 DASHBOARD"),    callback_data="user_dashboard"),
         InlineKeyboardButton(get_btn_name("btn_help",  "ℹ️ HELP"),         callback_data="help_menu")],
        [InlineKeyboardButton(get_btn_name("btn_prot",  "🛡 PROTECT"),     callback_data="plinks_admin"),
         InlineKeyboardButton(get_btn_name("btn_srch",  "🔍 SEARCH"),       callback_data="cb_search")],
        [InlineKeyboardButton(get_btn_name("btn_prem",  "💎 BUY PREMIUM"),  callback_data="premium_menu"),
         InlineKeyboardButton(get_btn_name("btn_mybt",  "🎯 MY BOTS"),      callback_data="my_bots_menu")],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_btn_name("btn_abrd", "📢 BROADCAST"),   callback_data="broadcast_menu"),
         InlineKeyboardButton(get_btn_name("btn_asta", "📊 ANALYTICS"),   callback_data="admin_stats")],
        [InlineKeyboardButton(get_btn_name("btn_ausr", "👥 USERS"),        callback_data="manage_users"),
         InlineKeyboardButton(get_btn_name("btn_acln", "🤖 CLONES"),       callback_data="my_bots_admin")],
        [InlineKeyboardButton(get_btn_name("btn_aset", "⚙️ SETTINGS"),     callback_data="bot_settings_admin"),
         InlineKeyboardButton(get_btn_name("btn_afsb", "🔒 FORCE SUB"),    callback_data="forcesub_admin")],
        [InlineKeyboardButton(get_btn_name("btn_aver", "🛡 VERIFICATION"), callback_data="verify_admin"),
         InlineKeyboardButton(get_btn_name("btn_ashr", "🔗 SHORTENER"),    callback_data="shortener_admin")],
        [InlineKeyboardButton(get_btn_name("btn_aprt", "🛡 PROTECT LINKS"), callback_data="plinks_admin"),
         InlineKeyboardButton(get_btn_name("btn_adul", "🎭 DUAL POSTS"),   callback_data="dual_posts_admin")],
        [InlineKeyboardButton(get_btn_name("btn_awlc", "👋 WELCOME MSG"),  callback_data="edit_welcome_msg"),
         InlineKeyboardButton(get_btn_name("btn_aapr", "✅ AUTO APPROVE"), callback_data="toggle_auto_approve")],
        [InlineKeyboardButton(get_btn_name("btn_acap", "📝 AUTO CAPTION"), callback_data="toggle_auto_caption"),
         InlineKeyboardButton(get_btn_name("btn_atmr", "⏱ TIMER SET"),    callback_data="edit_timer")],
        [InlineKeyboardButton(get_btn_name("btn_back", "🔙 BACK TO HOME"), callback_data="back_to_start")],
    ])

def kb_supreme():
    maint = get_global_config().get("maintenance", False)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_btn_name("btn_sgbr", "🌍 GLOBAL BROADCAST"), callback_data="global_broadcast")],
        [InlineKeyboardButton(get_btn_name("btn_ssys", "🖥 SYSTEM ANALYTICS"), callback_data="system_stats"),
         InlineKeyboardButton(get_btn_name("btn_snet", "🤖 BOT NETWORK"),    callback_data="all_bots_list")],
        [InlineKeyboardButton(get_btn_name("btn_sadm", "👑 ADMIN MANAGER"),    callback_data="manage_admins"),
         InlineKeyboardButton(get_btn_name("btn_smsg", "📢 SYSTEM MSG"),      callback_data="global_msg_set")],
        [InlineKeyboardButton(get_btn_name("btn_smnt", f"🛠 MAINT: {'ON' if maint else 'OFF'}"), callback_data="toggle_maintenance"),
         InlineKeyboardButton(get_btn_name("btn_sbak", "💾 FULL BACKUP"),    callback_data="manual_backup")],
        [InlineKeyboardButton(get_btn_name("btn_spur", "🧹 PURGE CACHE"),      callback_data="manual_clean_cache"),
         InlineKeyboardButton(get_btn_name("btn_srbd", "🔄 SMART REBUILD"),    callback_data="confirm_rebuild")],
        [InlineKeyboardButton(get_btn_name("btn_scus", "🎨 CUSTOMIZE BUTTONS"), callback_data="supreme_customize")],
        [InlineKeyboardButton(get_btn_name("btn_srst", "♻️ SYSTEM RESTART"),    callback_data="restart_all_bots")],
        [InlineKeyboardButton(get_btn_name("btn_back", "🔙 BACK TO HOME"),     callback_data="back_to_start")],
    ])

def kb_dual_post_creator(stage: str, free_count: int, pro_count: int):
    rows = []
    if stage == "free":
        rows.append([InlineKeyboardButton(
            f"💎 Switch to Premium Tier ({pro_count} files)",
            callback_data="dp_switch_pro"
        )])
    rows.append([InlineKeyboardButton(
        f"✅ Generate Link ({free_count}F + {pro_count}P files)",
        callback_data="dp_finish"
    )])
    rows.append([InlineKeyboardButton("❌ Cancel Session", callback_data="dp_cancel_session")])
    return InlineKeyboardMarkup(rows)

def kb_dual_post_done(post_id: str, share_link: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share Link",        url=f"https://t.me/share/url?url={share_link}")],
        [InlineKeyboardButton("👁 Preview FREE",      callback_data=f"dp_prev_free_{post_id}"),
         InlineKeyboardButton("💎 Preview PRO",       callback_data=f"dp_prev_pro_{post_id}")],
        [InlineKeyboardButton("📊 Analytics",         callback_data=f"dp_analytics_{post_id}"),
         InlineKeyboardButton("🗑 Delete",            callback_data=f"dp_delete_{post_id}")],
        [InlineKeyboardButton("🎭 Create Another",    callback_data="dual_post_start_new")],
    ])

def kb_file_edit(uid: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Caption",   callback_data=f"edit_caption_{uid}"),
         InlineKeyboardButton("🖼 Thumbnail", callback_data=f"edit_thumb_{uid}")],
        [InlineKeyboardButton("📝 Quick Rename", callback_data=f"qrename_{uid}"),
         InlineKeyboardButton("🚀 Hard Rename",  callback_data=f"rename_file_{uid}")],
        [InlineKeyboardButton("📤 Get File", callback_data=f"get_file_{uid}"),
         InlineKeyboardButton("🗑 Delete",    callback_data=f"del_file_{uid}")],
        [InlineKeyboardButton("🔙 Back",      callback_data="my_files_back")],
    ])

# ═══════════════════════════════════════════════════════════════
# 📝 HANDLERS
# ═══════════════════════════════════════════════════════════════

def register_handlers(app: Client):

    @app.on_message(filters.private, group=0)
    async def flood_ctrl(client, message):
        uid = message.from_user.id
        now = time.time()
        USER_FLOOD[uid] = [t for t in USER_FLOOD.get(uid, []) if now - t < 5]
        USER_FLOOD[uid].append(now)
        if len(USER_FLOOD[uid]) > 5:
            await message.reply("⚠️ **Anti-Flood!** Please slow down.")
            message.stop_propagation()

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

    @app.on_message(filters.command("ping") & filters.private, group=1)
    async def ping_cmd(client, message):
        t0   = time.time()
        sent = await message.reply("🏓 Pong...")
        ms   = round((time.time() - t0) * 1000, 2)
        sess = "✅" if SESSION_STRING else "❌ (rebuild disabled)"
        active_tokens = sum(1 for v in SHORTENER_TOKENS.values()
                            if not v["used"] and time.time() < v["expires_at"])
        await sent.edit(
            f"🏓 **Pong!**\n\n"
            f"⚡ `{ms}ms`\n"
            f"⏳ Uptime: `{str(datetime.now() - START_TIME).split('.')[0]}`\n"
            f"🤖 Bots: `{len(ACTIVE_CLIENTS)}`\n"
            f"🎭 Dual Posts: `{len(load_db(DUAL_POST_DB))}`\n"
            f"🔑 Session: {sess}\n"
            f"🔐 Active tokens: `{active_tokens}`"
        )

    @app.on_message(filters.command("restart") & filters.private, group=1)
    async def restart_cmd(client, message):
        if message.from_user.id != MAIN_ADMIN: return
        await message.reply("♻️ Restarting...")
        os.execl(sys.executable, sys.executable, *sys.argv)

    @app.on_message(filters.command("backup") & filters.private, group=1)
    async def backup_cmd(client, message):
        uid = message.from_user.id
        if not is_admin(uid): return await message.reply("❌ Admin only!")

        sm = await message.reply("💾 **Initializing backup process...**")
        try:
            count = await do_backup(client)
            if count > 0:
                await sm.edit(
                    f"✅ **Backup Successful!**\n\n"
                    f"📦 Files backed up: `{count}`\n"
                    f"📢 Target: `DB_CHANNEL`\n"
                    f"📅 `{datetime.now():%Y-%m-%d %H:%M:%S}`\n\n"
                    f"Tip: You can also send JSON database files directly to me to restore them!"
                )
            else:
                await sm.edit("❌ **Backup Failed!**\n\nCould not send files to DB_CHANNEL. Ensure the main bot is an admin in the channel.")
        except Exception as e:
            await sm.edit(f"❌ **Backup Error:**\n`{e}`")

    @app.on_message(filters.command("rebuild") & filters.private, group=1)
    async def rebuild_cmd(client, message):
        uid = message.from_user.id
        if not is_admin(uid): return await message.reply("❌ Admin only!")
        if not SESSION_STRING:
            return await message.reply(
                "❌ **SESSION_STRING not set!**\n\n"
                "1️⃣ `pip install pyrogram TgCrypto`\n"
                "2️⃣ `python generate_session.py`\n"
                "3️⃣ Set `SESSION_STRING` env var\n"
                "4️⃣ Restart → `/rebuild` will work"
            )
        sm = await message.reply("🔄 **Smart DB Rebuild Starting...**")
        try:
            stats = await smart_rebuild(status_msg=sm)
            await sm.edit(
                f"🎉 **Smart Rebuild Complete!**\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"**Phase 1 — Backup Restore:**\n"
                f"📦 Restored: `{stats['phase1_restored']}/{len(BACKUP_FILES)}`\n"
                f"📅 Backup date: `{stats.get('backup_date', 'N/A')}`\n\n"
                f"**Phase 2 — Incremental Scan:**\n"
                f"📁 Files: `{stats['phase2_files']}`\n"
                f"📦 Batches: `{stats['phase2_batches']}`\n"
                f"🎭 Dual Posts: `{stats['phase2_duals']}`\n"
                f"❌ Errors: `{stats['phase2_errors']}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Database fully restored!\n"
                f"Run `/stats` to verify."
            )
        except ValueError:
            pass
        except Exception as e:
            await sm.edit(f"❌ Rebuild failed!\n\n`{e}`")

    # ═══════════════════════════════════════════════════════════
    # 🎭 DUAL POST COMMANDS
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
                "❌ **Access Denied!**\n\nOnly bot owner and admins can create Dual Posts."
            )

        if uid in TEMP_DUAL:
            sess = TEMP_DUAL[uid]
            return await message.reply(
                f"⚠️ **Active Session Found!**\n\n"
                f"📌 Title: **{sess.title or 'Untitled'}**\n"
                f"📂 Free: `{len(sess.free_files)}` files\n"
                f"💎 Pro: `{len(sess.pro_files)}` files\n"
                f"🎯 Stage: `{sess.stage_display()}`\n\n"
                f"Continue adding files, or use the buttons below.",
                reply_markup=kb_dual_post_creator(
                    sess.stage, len(sess.free_files), len(sess.pro_files)
                )
            )

        title = message.text.split(None, 1)[1].strip() if len(message.command) > 1 else None
        session = DualPostSession(bot_id, uid, title)
        TEMP_DUAL[uid] = session

        await message.reply(
            f"🎭 **Dual Post Creator — Started!**\n\n"
            f"📌 **Title:** {title or '_(not set — use `/dualpost My Title` next time)_'}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📂 **Stage 1 of 2 — FREE TIER**\n\n"
            f"Send files for **non-premium users**.\n"
            f"• These users see shortener ads (if configured)\n"
            f"• Files auto-delete after timer\n"
            f"• Basic/teaser content goes here\n\n"
            f"When done → `/dpremium` to switch to Premium tier\n"
            f"Cancel anytime → `/dpcancel`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Switch to Premium Tier", callback_data="dp_switch_pro")],
                [InlineKeyboardButton("✅ Finish & Generate Link",  callback_data="dp_finish")],
                [InlineKeyboardButton("❌ Cancel",                  callback_data="dp_cancel_session")]
            ])
        )

    @app.on_message(filters.command("dpremium") & filters.private, group=1)
    async def dpremium_cmd(client, message):
        uid = message.from_user.id
        if uid not in TEMP_DUAL:
            return await message.reply(
                "❌ No active dual post session.\n\nUse `/dualpost` to start one."
            )
        sess = TEMP_DUAL[uid]
        if sess.stage == "pro":
            return await message.reply(
                f"💎 **Already in Premium Tier!**\n\n"
                f"Premium files added: `{len(sess.pro_files)}`\n\n"
                f"Send more files, or `/dpdone` to finish."
            )
        sess.stage = "pro"
        await message.reply(
            f"💎 **Stage 2 of 2 — PREMIUM TIER**\n\n"
            f"✅ Free tier locked: `{len(sess.free_files)}` files\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Now send files for **Premium users**.\n"
            f"• Delivered directly — no ads, no redirect\n"
            f"• No auto-delete\n"
            f"• Exclusive/full quality content\n\n"
            f"When done → `/dpdone` to generate the link\n"
            f"Cancel → `/dpcancel`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Finish & Generate Link", callback_data="dp_finish")],
                [InlineKeyboardButton("❌ Cancel Session",         callback_data="dp_cancel_session")]
            ])
        )

    @app.on_message(filters.command("dpdone") & filters.private, group=1)
    async def dpdone_cmd(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        bi     = get_bot_info(bot_id)

        if uid not in TEMP_DUAL:
            return await message.reply("❌ No active session. Use `/dualpost` to start.")

        sess = TEMP_DUAL[uid]
        if not sess.free_files and not sess.pro_files:
            return await message.reply(
                "❌ **No files added!**\n\nSend at least one file before finishing."
            )

        post_id   = unique_id()
        post_data = save_dual_post(post_id, sess)
        del TEMP_DUAL[uid]

        main_client = next(
            (d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client
        )
        asyncio.create_task(save_meta(main_client, {
            **post_data, "unique_id": post_id, "type": "dual_post"
        }))

        base_link = f"https://t.me/{client.me.username}?start=dp_{post_id}"
        free_c    = len(sess.free_files)
        pro_c     = len(sess.pro_files)
        title     = sess.title or "Dual Post"

        shortener_status = (
            "🔗 _Free tier → Shortener (ads) → File delivery_"
            if shortener_enabled_for_bot(bi)
            else "📂 _Free tier → Direct delivery_"
        )

        await message.reply(
            f"🎉 **Dual Post Created Successfully!**\n\n"
            f"📌 **{title}**\n"
            f"🆔 `{post_id}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📂 **FREE TIER** — `{free_c}` file(s)\n"
            f"   👤 For: Non-premium users\n"
            f"   {shortener_status}\n"
            f"   ⏱ Auto-delete after timer\n\n"
            f"💎 **PREMIUM TIER** — `{pro_c}` file(s)\n"
            f"   👑 For: Premium users only\n"
            f"   ⚡ _Direct delivery — no ads, no wait_\n"
            f"   ♾ _No auto-delete_\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 **Share This Link:**\n`{base_link}`",
            reply_markup=kb_dual_post_done(post_id, base_link)
        )

    @app.on_message(filters.command("dpcancel") & filters.private, group=1)
    async def dpcancel_cmd(client, message):
        uid = message.from_user.id
        if uid in TEMP_DUAL:
            sess = TEMP_DUAL.pop(uid)
            await message.reply(
                f"❌ **Dual post session cancelled.**\n\n"
                f"📂 Free files discarded: `{len(sess.free_files)}`\n"
                f"💎 Pro files discarded: `{len(sess.pro_files)}`"
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
                "📭 **No dual posts yet!**\n\n"
                "Use `/dualpost My Title` to create one.\n\n"
                "📖 **How it works:**\n"
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
            f"🎭 **{'All ' if is_sup else 'Your '}Dual Posts**\n"
            f"📊 Total: `{len(all_posts)}` posts | 👁 `{total_views}` views\n\n"
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
                f"📌 **{title}**\n"
                f"   `{pid}` | 👁 `{at}` total\n"
                f"   📂 `{fc}` free ({af} views) | "
                f"💎 `{pc}` pro ({ap} views)\n\n"
            )
            link = f"https://t.me/{client.me.username}?start=dp_{pid}"
            btns.append([
                InlineKeyboardButton(f"📤 {title[:22]}", url=f"https://t.me/share/url?url={link}"),
                InlineKeyboardButton("📊", callback_data=f"dp_analytics_{pid}"),
                InlineKeyboardButton("🗑",  callback_data=f"dp_delete_{pid}")
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
            return await message.reply("❌ Post not found!")
        can = (uid == MAIN_ADMIN or is_admin(uid) or
               (bi and bi.get("owner_id") == uid) or post.get("created_by") == uid)
        if not can:
            return await message.reply("❌ Not your post!")
        del_dual_post(pid)
        await message.reply(
            f"🗑 **Deleted:** `{post.get('title', pid)}`\n"
            f"📂 Free: `{len(post.get('free_files',[]))}` | "
            f"💎 Pro: `{len(post.get('pro_files',[]))}` files removed."
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
                return await message.reply("❌ Post not found!")
            can = (uid == MAIN_ADMIN or is_admin(uid) or
                   (bi and bi.get("owner_id") == uid) or post.get("created_by") == uid)
            if not can:
                return await message.reply("❌ Not your post!")
            fc   = len(post.get("free_files", []))
            pc   = len(post.get("pro_files", []))
            af   = post.get("access_free", 0)
            ap   = post.get("access_pro", 0)
            at   = post.get("access_total", 0)
            last = post.get("last_accessed", "Never")
            prem_pct = round(ap / max(at, 1) * 100)
            return await message.reply(
                f"📊 **Dual Post Analytics**\n\n"
                f"📌 **{post.get('title','?')}**\n"
                f"🆔 `{pid}`\n"
                f"📅 Created: `{str(post.get('created_at','?'))[:16]}`\n"
                f"Last access: `{str(last)[:16]}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👁 **Total views:** `{at}`\n\n"
                f"📂 **FREE TIER**\n"
                f"   Files: `{fc}` | Views: `{af}` ({100-prem_pct}%)\n\n"
                f"💎 **PREMIUM TIER**\n"
                f"   Files: `{pc}` | Views: `{ap}` ({prem_pct}%)\n\n"
                f"📈 Premium conversion: `{prem_pct}%`"
            )

        total_at = sum(p.get("access_total", 0) for p in posts)
        total_af = sum(p.get("access_free", 0) for p in posts)
        total_ap = sum(p.get("access_pro", 0) for p in posts)
        prem_pct = round(total_ap / max(total_at, 1) * 100)

        await message.reply(
            f"📊 **Dual Post Analytics Summary**\n\n"
            f"🎭 Total posts: `{len(posts)}`\n"
            f"👁 Total views: `{total_at}`\n\n"
            f"📂 Free tier views: `{total_af}`\n"
            f"💎 Premium tier views: `{total_ap}`\n"
            f"📈 Premium conversion: `{prem_pct}%`\n\n"
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
            return await message.reply("🚧 **Maintenance Mode** — Bot is temporarily down.")
        if is_user_banned(uid, bot_id):
            return await message.reply("🚫 You are banned!")

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
                            await client.send_message(ref_id, f"🎊 **New Referral!**\n\nUser `{uid}` joined via your link.\nTotal refers: `{users[ref_key]['refer_count']}`")
                        except: pass

        # Verification System
        if bi and bi.get("verify_link") and not is_admin(uid) and uid != bi.get("owner_id"):
            if not deep.startswith("verify_"):
                v_link = bi.get("verify_link")
                u_link = bi.get("update_channel")
                btns = [[InlineKeyboardButton("🔐 START VERIFICATION", url=v_link)]]
                if u_link:
                    btns.append([InlineKeyboardButton("📢 UPDATE CHANNEL", url=u_link)])

                return await message.reply(
                    f"🛡 **Verification Required!**\n\n"
                    f"To access the files in this bot, you must complete a quick verification.\n\n"
                    f"1️⃣ Click the **Verification** button below.\n"
                    f"2️⃣ Complete the process in the other bot.\n"
                    f"3️⃣ Come back here and click `/start` again.",
                    reply_markup=InlineKeyboardMarkup(btns)
                )

        user_data, is_new = add_user(uid, bot_id, message.from_user.username,
                                      message.from_user.first_name)
        is_ok, links = await check_force_sub(client, uid)
        if not is_ok:
            btns = [[InlineKeyboardButton(f"📢 Join {i['title']}", url=i["link"])]
                    for i in links]
            btns.append([InlineKeyboardButton(
                "🔄 I Joined — Try Again",
                url=f"https://t.me/{client.me.username}?start={deep}"
            )])
            return await message.reply(
                "⚠️ **Membership Required!**\n\nJoin channels below.",
                reply_markup=InlineKeyboardMarkup(btns)
            )

        bi         = get_bot_info(bot_id)
        auto_del   = bi.get("auto_delete_time", 600) if bi else 600
        is_premium = user_data.get("is_premium", False)

        # ── Deep link: Protected Channel Link ───────────────────
        if deep.startswith("lp_") or deep == "join":
            lpid = deep[3:] if deep.startswith("lp_") else "default"
            plinks = load_db(PLINKS_DB)

            if deep == "join":
                chid = bi.get("connected_channel") if bi else None
                if not chid:
                    return await message.reply("❌ No channel connected to this bot!")
                mode = bi.get("join_method", "direct")
                pdata = {"channel_id": chid, "mode": mode, "title": "Main Channel"}
            else:
                pdata = plinks.get(lpid)
                if not pdata or pdata.get("bot_id") != bot_id:
                    return await message.reply("❌ Protected link not found or expired!")
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
                        f"✨ **YOUR EXCLUSIVE LINK IS STILL ACTIVE** ✨\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚠️ **Note:** This link will expire soon!\n\n"
                        f"📢 **Channel:** `{pdata.get('title', chid)}`\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👇 **CLICK BELOW TO JOIN** 👇",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔗 JOIN CHANNEL NOW", url=old_link)]
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
                    f"✨ **THIS IS YOUR EXCLUSIVE LINK** ✨\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚠️ **Note:** This link is valid for **5 minutes** only. Join before it expires!\n\n"
                    f"📢 **Channel:** `{pdata.get('title', chid)}`\n"
                    f"⚙️ **Join Mode:** `{mode.upper()}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👇 **CLICK BELOW TO JOIN** 👇",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔗 JOIN CHANNEL NOW", url=invite.invite_link)]
                    ])
                )
                return
            except Exception as e:
                return await message.reply(f"❌ Failed to create link: `{e}`")

        # ── Deep link: file with token ────────────────────────────
        if deep.startswith("f_") and "_t_" in deep:
            parts = deep[2:].split("_t_", 1)
            fuid  = parts[0]
            token = parts[1] if len(parts) > 1 else ""
            files = load_db(FILES_DB)
            fdata = files.get(fuid)
            if not fdata:
                return await message.reply("❌ **File not found!**")
            td = validate_token(token, uid, bot_id)
            if not td or td.get("resource_id") != fuid:
                short_link = await make_shortener_link(client, bi, uid, bot_id, fuid, "file")
                return await message.reply(
                    "⏱ **Link Expired or Already Used!**\n\nGet a fresh link:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔗 Get Fresh Link", url=short_link)]
                    ])
                )
            consume_token(token)
            try:
                sent = await deliver_file(client, message.chat.id, fdata)
            except Exception as e:
                return await message.reply(f"❌ File unavailable!\n`{e}`")
            if sent and not is_premium:
                asyncio.create_task(_auto_delete(sent, auto_del))
                await message.reply(
                    f"⏳ File auto-deletes in `{auto_del // 60}` min(s). Save it! 💾"
                )
            elif sent:
                await message.reply("🌟 **Premium:** No auto-delete for you!")
            return

        # ── Deep link: file without token ─────────────────────────
        elif deep.startswith("f_") and "_t_" not in deep:
            fuid  = deep[2:]
            files = load_db(FILES_DB)
            fdata = files.get(fuid)
            if not fdata:
                return await message.reply("❌ **File not found!**")

            if is_premium:
                try:
                    sent = await deliver_file(client, message.chat.id, fdata)
                    await message.reply("🌟 **Premium:** Direct delivery, no ads!")
                except Exception as e:
                    await message.reply(f"❌ Error: `{e}`")
                return

            if shortener_enabled_for_bot(bi):
                short_link = await make_shortener_link(client, bi, uid, bot_id, fuid, "file")
                fname = fdata.get("file_name", "File")
                icon  = file_icon(fname)
                return await message.reply(
                    f"🔗 **Verification Required**\n\n"
                    f"{icon} **{fname}**\n"
                    f"📊 {fmt_size(fdata.get('file_size', 0))}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚠️ **Ladle, pehle shortener se jakar ads dekho, tab file milegi!** 😄\n\n"
                    f"👇 Click karo → ads dekho → file pao 👇\n"
                    f"🕐 Link 15 minute mein expire hoga.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚡ File Lo (Ad Dekho)", url=short_link)],
                        [InlineKeyboardButton("💎 Premium Lo (No Ads!)", callback_data="premium_menu")]
                    ])
                )

            try:
                sent = await deliver_file(client, message.chat.id, fdata)
            except Exception as e:
                return await message.reply(f"❌ Error: `{e}`")
            if sent and not is_premium:
                asyncio.create_task(_auto_delete(sent, auto_del))
                await message.reply(f"⏳ Auto-deletes in `{auto_del // 60}` min(s). 💾")
            return

        # ── Deep link: batch with token ───────────────────────────
        elif deep.startswith("b_") and "_t_" in deep:
            parts   = deep[2:].split("_t_", 1)
            bid_key = parts[0]
            token   = parts[1] if len(parts) > 1 else ""
            bdata   = load_db(BATCH_DB).get(bid_key)
            if not bdata: return await message.reply("❌ Batch not found.")
            td = validate_token(token, uid, bot_id)
            if not td or td.get("resource_id") != bid_key:
                short_link = await make_shortener_link(client, bi, uid, bot_id, bid_key, "batch")
                return await message.reply(
                    "⏱ **Link Expired!** Get fresh link:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Fresh Link", url=short_link)]])
                )
            consume_token(token)
            sm = await message.reply(f"📦 Sending batch ({len(bdata['files'])} files)...")
            sc, tot = await deliver_batch_files(client, message.chat.id,
                                                 bdata["files"], bot_id, is_premium)
            await sm.delete()
            await message.reply(f"✅ Delivered **{sc}/{tot}** files!")
            return

        # ── Deep link: batch without token ────────────────────────
        elif deep.startswith("b_") and "_t_" not in deep:
            bid_key = deep[2:]
            bdata   = load_db(BATCH_DB).get(bid_key)
            if not bdata: return await message.reply("❌ Batch not found.")
            total = len(bdata["files"])

            if is_premium:
                sm = await message.reply(f"📦 Premium Direct: Sending {total} files...")
                sc, tot = await deliver_batch_files(client, message.chat.id,
                                                     bdata["files"], bot_id, True)
                await sm.delete()
                await message.reply(f"✅ Delivered **{sc}/{tot}** files! 🌟 Premium")
                return

            if shortener_enabled_for_bot(bi):
                short_link = await make_shortener_link(client, bi, uid, bot_id, bid_key, "batch")
                return await message.reply(
                    f"🔗 **Verification Required**\n\n"
                    f"📦 **{total} files** in this batch\n\n"
                    f"⚠️ **Pehle ads dekho, phir sab files milenge!**\n"
                    f"🕐 Link 15 min mein expire hoga.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚡ Files Lo (Ad Dekho)", url=short_link)],
                        [InlineKeyboardButton("💎 Premium Lo (No Ads!)", callback_data="premium_menu")]
                    ])
                )

            sm = await message.reply(f"📦 Sending batch ({total} files)...")
            sc, tot = await deliver_batch_files(client, message.chat.id,
                                                 bdata["files"], bot_id, is_premium)
            await sm.delete()
            await message.reply(f"✅ Delivered **{sc}/{tot}** files!")
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
                    "❌ **Dual Post not found!**\n\n"
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
                tier_label = "💎 PREMIUM" if pro_files else "📂 FREE (no pro files set)"
                bump_dual_access(actual_pid, "pro" if pro_files else "free")

                if not tier_files:
                    return await message.reply(
                        f"💎 **{title}**\n\n_{desc_pro}_\n\n"
                        f"_No files available yet._"
                    )

                sm = await message.reply(
                    f"💎 **{title}**\n\n"
                    f"_{desc_pro}_\n\n"
                    f"📦 {tier_label}: Sending `{len(tier_files)}` file(s)..."
                )
                sc, tot = await deliver_batch_files(client, message.chat.id,
                                                     tier_files, bot_id, True)
                await sm.delete()
                await message.reply(
                    f"✅ **{sc}/{tot}** premium files delivered!\n\n"
                    f"🌟 _Premium users get full content directly — no ads, no wait._"
                )
                return

            # Free user
            bump_dual_access(actual_pid, "free")

            if not free_files:
                return await message.reply(
                    f"📦 **{title}**\n\n_{desc_free}_\n\n"
                    f"_No free files available._\n\n"
                    f"💎 Upgrade to Premium for exclusive content!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💎 Get Premium", callback_data="premium_menu")]
                    ])
                )

            if token_val:
                td = validate_token(token_val, uid, bot_id)
                if not td or td.get("resource_id") != actual_pid:
                    if use_short:
                        short_link = await make_shortener_link(client, bi, uid, bot_id, actual_pid, "dual")
                        return await message.reply(
                            "⏱ **Link Expired!** Get a fresh one:",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("🔗 Get Fresh Link", url=short_link)],
                                [InlineKeyboardButton("💎 Get Premium (Skip Ads)", callback_data="premium_menu")]
                            ])
                        )
                else:
                    consume_token(token_val)
                    sm = await message.reply(
                        f"📂 **{title}**\n\n_{desc_free}_\n\n"
                        f"📦 Sending `{len(free_files)}` file(s)..."
                    )
                    sc, tot = await deliver_batch_files(client, message.chat.id,
                                                         free_files, bot_id, False)
                    await sm.delete()

                    notice = await message.reply(
                        f"✅ **{sc}/{tot}** files delivered!\n\n"
                        f"⏱ _Files will auto-delete in `{auto_del // 60}` min(s). Save them!_\n\n"
                        f"💎 _Want premium content? Upgrade for full access!_",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_menu")]
                        ]) if pro_files else None
                    )
                    asyncio.create_task(_auto_delete(notice, auto_del))
                    return

            if use_short:
                short_link = await make_shortener_link(client, bi, uid, bot_id, actual_pid, "dual")
                fc = len(free_files)
                pc = len(pro_files)
                return await message.reply(
                    f"🔗 **{title}**\n\n"
                    f"_{desc_free}_\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📂 **{fc}** free file(s) available\n"
                    f"💎 **{pc}** premium file(s) (upgrade to access)\n\n"
                    f"⚠️ **Pehle link visit karo, ads dekho, phir files milenge!**\n"
                    f"🕐 Link 15 minute mein expire hoga.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚡ Free Files Lo (Ad Dekho)", url=short_link)],
                        [InlineKeyboardButton("💎 Premium Lo → Direct Files!", callback_data="premium_menu")]
                    ])
                )
            else:
                sm = await message.reply(
                    f"📂 **{title}**\n\n_{desc_free}_\n\n"
                    f"📦 Sending `{len(free_files)}` file(s)..."
                )
                sc, tot = await deliver_batch_files(client, message.chat.id,
                                                     free_files, bot_id, False)
                await sm.delete()
                await message.reply(
                    f"✅ **{sc}/{tot}** files delivered!\n\n"
                    f"💎 _Premium users get exclusive content — upgrade to unlock!_",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💎 Get Premium", callback_data="premium_menu")]
                    ]) if pro_files else None
                )
                return

        # Standard welcome
        global_msg   = cfg.get("global_msg", "")
        welcome_text = bi.get("custom_welcome") if bi else None
        welcome_img  = bi.get("welcome_image")  if bi else None

        if global_msg:
            await message.reply(f"📢 **System Notice**\n\n{global_msg}")

        if not welcome_text:
            default_welcome = (
                f"✨ **Greetings, {message.from_user.first_name}!**\n\n"
                f"Welcome to the **ULTRA ADVANCED FILESTORE v7.0** 🚀\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"I am your elite assistant for managing and storing files with unparalleled efficiency.\n\n"
                f"🛡 **Elite Features:**\n"
                f" ├ ♾ **Unlimited Storage:** Secure & Permanent\n"
                f" ├ 📦 **Smart Batching:** Multiple files, one link\n"
                f" ├ 🎭 **Dual-Tier System:** Free & Premium access\n"
                f" ├ 🎨 **Full Customization:** Caption & Thumbs\n"
                f" ├ 🤖 **Bot Cloning:** Create your own network\n"
                f" └ ⚡ **Lightning Fast:** Instant file delivery\n\n"
                f"👇 **Choose an option below to get started!**"
            )
            welcome_text = get_msg_text("msg_welcome", default_welcome).format_map(SafeDict(
                name=message.from_user.first_name,
                username=f"@{client.me.username}"
            ))

        kbd = kb_start(bot_id, uid)
        if is_new and bi and bi.get("owner_id") == uid:
            await message.reply(
                f"👋 **Hey Boss! Welcome to your cloned bot.**\n\n"
                f"I'm ready to work for you. Here are some quick setups:\n"
                f"1️⃣ `/setlog -100xxxx` - Set a log channel to see uploads.\n"
                f"2️⃣ `/setchannel -100xxxx` - Connect your channel for the `/start join` link.\n"
                f"3️⃣ `/setmode requested` - If you want users to send join requests.\n"
                f"4️⃣ `/setwelcome` - Customize this message.\n\n"
                f"Use `/admin` to see all your controls!"
            )

        if welcome_img:
            try:
                await message.reply_photo(welcome_img, caption=welcome_text, reply_markup=kbd)
                return
            except Exception:
                pass
        await message.reply(welcome_text, reply_markup=kbd)

    # ── /admin ────────────────────────────────────────────────────
    @app.on_message(filters.command("admin") & filters.private, group=1)
    async def admin_cmd(client, message):
        uid = message.from_user.id
        bi  = get_bot_info(client.me.id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return
        text = get_msg_text("msg_admin", "⚡ **Admin Panel**")
        await message.reply(text, reply_markup=kb_admin())

    # ── /supreme ──────────────────────────────────────────────────
    @app.on_message(filters.command("supreme") & filters.private, group=1)
    async def supreme_cmd(client, message):
        if message.from_user.id != MAIN_ADMIN: return
        sess = "✅ Set" if SESSION_STRING else "❌ Not Set"
        default_supreme = (
            f"👑 **Supreme Panel v7.0**\n\n"
            f"🤖 Bots: `{{bots}}` | 👥 Users: `{{users}}`\n"
            f"📁 Files: `{{files}}` | 🎭 Duals: `{{duals}}`\n"
            f"🔑 Session: {{sess}}"
        )
        text = get_msg_text("msg_supreme", default_supreme).format_map(SafeDict(
            bots=len(ACTIVE_CLIENTS),
            users=len(load_db(USERS_DB)),
            files=len(load_db(FILES_DB)),
            duals=len(load_db(DUAL_POST_DB)),
            sess=sess
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
                f"🌐 **Global Analytics**\n━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bots: `{len(get_all_bots())}` | 🟢 Online: `{len(ACTIVE_CLIENTS)}`\n"
                f"👥 Users: `{len(load_db(USERS_DB))}`\n"
                f"📁 Files: `{len(load_db(FILES_DB))}`\n"
                f"🎭 Dual Posts: `{len(dual_posts)}` | 👁 `{total_dp_views}` views\n"
                f"⏳ Uptime: `{str(datetime.now() - START_TIME).split('.')[0]}`"
            )
        else:
            ud   = get_user(uid, bot_id)
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            dps  = get_user_dual_posts(bot_id, uid)
            await message.reply(
                f"📊 **Dashboard**\n━━━━━━━━━━━━━━━━━━━━\n"
                f"📤 `{ud.get('files_uploaded',0) if ud else 0}` uploads | "
                f"📦 `{ud.get('batches_created',0) if ud else 0}` batches\n"
                f"🎭 `{len(dps)}` dual posts | 🤖 `{len(ubts)}` bots\n"
                f"💎 {'Premium ✅' if ud and ud.get('is_premium') else 'Free'}"
            )

    # ── /setwelcome ───────────────────────────────────────────────
    @app.on_message(filters.command("setwelcome") & filters.private, group=1)
    async def setwelcome_cmd(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        bi  = get_bot_info(bot_id)
        if not bi or (bi.get("owner_id") != uid and uid != MAIN_ADMIN):
            return await message.reply("❌ Only bot owner!")
        TEMP_WELCOME[uid] = {"bot_id": bot_id, "step": "text"}
        curr_t = bi.get("custom_welcome") or "_(default)_"
        curr_i = "✅ Set" if bi.get("welcome_image") else "❌ None"
        await message.reply(
            f"👋 **Welcome Message Editor**\n\n"
            f"Current text: {curr_t[:80]}\nCurrent image: {curr_i}\n\n"
            f"**Step 1/2:** Send new welcome text\n"
            f"`-skip` = keep | `-clear` = default\n/cancel to abort.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_welcome")]])
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
            target_bots = [bot_id] + [
                d["bot_id"] for d in get_all_descendant_bots(bot_id)
                if d["bot_id"] in ACTIVE_CLIENTS
            ]

        if not can_bc: return await message.reply("❌ No permission!")

        if not message.reply_to_message:
            total = sum(len(get_all_users(bid)) for bid in target_bots)
            return await message.reply(
                f"📢 **ULTRA BROADCAST SYSTEM**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 **Target Bots:** `{len(target_bots)}` bots\n"
                f"👥 **Estimated Reach:** `{total}` users\n\n"
                f"👉 **HOW TO USE:**\n"
                f"1️⃣ Reply to any message with `/broadcast`.\n"
                f"2️⃣ You can optionally add a button like this:\n"
                f"   `/broadcast | Button Text | https://link.com`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

        sm = await message.reply("⏳ **Processing broadcast payload...**")
        bc_msg_id = await store_broadcast(client, message.reply_to_message)
        if not bc_msg_id:
            return await sm.edit("❌ **Error:** Failed to cache broadcast message. Please try again.")

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
            f"⚠️ **READY FOR BROADCAST?**\n\n"
            f"🤖 Bots: `{len(target_bots)}` bots\n"
            f"👥 Users: `{total}` total users\n"
            f"📦 Payload ID: `{bc_msg_id}`\n"
            f"🔘 Button: {'✅ Set' if btn_markup else '❌ None'}\n\n"
            f"**Note:** This will deliver a COPY of your message to all users.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ CONFIRM & SEND", callback_data="confirm_broadcast")],
                [InlineKeyboardButton("❌ ABORT",           callback_data="cancel_broadcast")]
            ])
        )

    # ── /batch /done /cancel ──────────────────────────────────────
    @app.on_message(filters.command("batch") & filters.private, group=1)
    async def batch_start(client, message):
        uid = message.from_user.id
        if is_user_banned(uid, client.me.id): return await message.reply("🚫 Banned!")
        TEMP_BATCH[uid] = []
        await message.reply("📦 **Batch Mode ON!**\n\nSend files. `/done` to finish. `/cancel` to abort.")

    @app.on_message(filters.command("done") & filters.private, group=1)
    async def batch_done(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        bi  = get_bot_info(bot_id)
        if uid not in TEMP_BATCH or not TEMP_BATCH[uid]:
            return await message.reply("❌ No files in batch!")
        fids = TEMP_BATCH.pop(uid)
        bid  = unique_id()
        batches = load_db(BATCH_DB)
        batches[bid] = {"files": fids, "created_by": uid, "bot_id": bot_id, "date": str(datetime.now())}
        save_db(BATCH_DB, batches)
        update_user_stats(uid, bot_id, "batches_created")
        main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
        asyncio.create_task(save_meta(main_client, {
            "type": "batch", "unique_id": bid, "files": fids,
            "created_by": uid, "bot_id": bot_id, "date": str(datetime.now())
        }))
        link  = f"https://t.me/{client.me.username}?start=b_{bid}"
        short = await get_short_link(bi, link)
        await message.reply(
            f"✅ **Batch Created!**\n\n📦 `{len(fids)}` files\n\n🔗 `{short}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={short}")]
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
            await message.reply(f"❌ Cancelled: {', '.join(cancelled)}")
        else:
            await message.reply("Nothing to cancel.")

    @app.on_message(filters.command("protect") & filters.private, group=1)
    async def protect_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply("❌ Access Denied!")

        TEMP_PROTECT[uid] = {"bot_id": bot_id, "step": "channel"}
        await message.reply(
            "🛡 **Advanced Link Protection Setup**\n\n"
            "Step 1: Send the **Channel ID** (starting with -100) you want to protect.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_protect")]])
        )

    @app.on_message(filters.command("myplinks") & filters.private, group=1)
    async def myplinks_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply("❌ Access Denied!")

        plinks = load_db(PLINKS_DB)
        my_links = [v for v in plinks.values() if v.get("bot_id") == bot_id and (v.get("created_by") == uid or is_admin(uid))]

        if not my_links:
            return await message.reply("📭 **No protected links found!**\nUse `/protect` to create one.")

        text = f"📋 **Your Protected Links ({len(my_links)})**\n\n"
        btns = []
        for l in my_links[:15]:
            lpid = l["lpid"]
            title = l.get("title", "Unknown")[:25]
            link = f"https://t.me/{client.me.username}?start=lp_{lpid}"
            text += f"🛡 **{title}**\n`{lpid}` | {l.get('mode').upper()}\n🔗 `{link}`\n\n"
            btns.append([
                InlineKeyboardButton(f"📤 {title}", url=f"https://t.me/share/url?url={link}"),
                InlineKeyboardButton("🗑 Delete", callback_data=f"del_plink_{lpid}")
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
        if not fd: return await message.reply("❌ File not found!")
        bi  = get_bot_info(bot_id)
        can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or fd.get("user_id")==uid
        if not can: return await message.reply("❌ Not your file!")
        icon = file_icon(fd.get("file_name","")); cap = fd.get("caption") or "_(none)_"
        thumb = "✅" if fd.get("custom_thumbnail") else "❌"
        await message.reply(
            f"✏️ **File Editor**\n\n{icon} **{fd.get('file_name','?')}**\n"
            f"🆔 `{fuid}` | 📊 {fmt_size(fd.get('file_size',0))}\n"
            f"💬 {cap} | 🖼 {thumb} | 👁 `{fd.get('access_count',0)}`",
            reply_markup=kb_file_edit(fuid)
        )

    @app.on_message(filters.command("delfile") & filters.private, group=1)
    async def delfile_cmd(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        if len(message.command) < 2: return await message.reply("Usage: `/delfile FILE_ID`")
        fuid  = message.command[1]; files = load_db(FILES_DB); fd = files.get(fuid)
        if not fd: return await message.reply("❌ Not found!")
        bi  = get_bot_info(bot_id)
        can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or fd.get("user_id")==uid
        if not can: return await message.reply("❌ Not your file!")
        del files[fuid]; save_db(FILES_DB, files)
        await message.reply(f"🗑 **Deleted:** `{fd.get('file_name','?')}`")

    @app.on_message(filters.command("listfiles") & filters.private, group=1)
    async def listfiles_cmd(client, message):
        uid = message.from_user.id; bot_id = client.me.id
        files = load_db(FILES_DB); bi = get_bot_info(bot_id)
        is_sup = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid)
        all_f = [(k,f) for k,f in files.items()
                 if f.get("bot_id")==bot_id and (is_sup or f.get("user_id")==uid)]
        if not all_f: return await message.reply("📭 No files found!")
        recent = sorted(all_f, key=lambda x: x[1].get("upload_date",""), reverse=True)[:10]
        text = f"📋 **{'All' if is_sup else 'Your'} Files** ({len(all_f)} total)\n\n"
        btns = []
        for k, f in recent:
            icon = file_icon(f.get("file_name",""))
            name = (f.get("file_name") or "?")[:35]
            text += f"{icon} **{name}** | 📊 {fmt_size(f.get('file_size',0))} | 👁 {f.get('access_count',0)}\n`{k}`\n\n"
            btns.append([
                InlineKeyboardButton(f"{icon} {name[:22]}", url=f"https://t.me/{client.me.username}?start=f_{k}"),
                InlineKeyboardButton("✏️", callback_data=f"edit_file_{k}")
            ])
        await message.reply(text, reply_markup=InlineKeyboardMarkup(btns) if btns else None)

    # ── Misc commands ─────────────────────────────────────────────
    @app.on_message(filters.command("mybots") & filters.private, group=1)
    async def mybots_cmd(client, message):
        uid  = message.from_user.id
        ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
        if not ubts: return await message.reply("🤖 No bots yet! `/clone TOKEN`")
        text = f"🤖 **Your Bots ({len(ubts)})**\n\n"
        for i, b in enumerate(ubts[:10],1):
            text += f"{i}. {'🟢' if b['bot_id'] in ACTIVE_CLIENTS else '🔴'} @{b['bot_username']}\n"
        await message.reply(text)

    @app.on_message(filters.command(["ban","unban","info","givepremium","removepremium","gban","ungban"]) & filters.private, group=1)
    async def admin_utils(client, message):
        uid = message.from_user.id; bot_id = client.me.id; bi = get_bot_info(bot_id)
        if not (uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid)): return
        if len(message.command)<2: return await message.reply(f"Usage: `/{message.command[0]} USER_ID`")
        try: target = int(message.command[1])
        except ValueError: return await message.reply("❌ Invalid ID!")
        cmd = message.command[0]
        if cmd == "ban":
            await message.reply("🚫 Banned!" if ban_user(target,bot_id) else "❌ Not found.")
        elif cmd == "unban":
            await message.reply("✅ Unbanned!" if unban_user(target,bot_id) else "❌ Not found.")
        elif cmd == "givepremium":
            users = load_db(USERS_DB); k = f"{bot_id}_{target}"
            if k in users:
                users[k]["is_premium"] = True; save_db(USERS_DB,users)
                await message.reply(f"💎 `{target}` is now Premium!")
            else: await message.reply("❌ Not found.")
        elif cmd == "removepremium":
            users = load_db(USERS_DB); k = f"{bot_id}_{target}"
            if k in users:
                users[k]["is_premium"] = False; save_db(USERS_DB,users)
                await message.reply(f"❌ Premium removed from `{target}`!")
            else: await message.reply("❌ Not found.")
        elif cmd == "gban":
            if uid!=MAIN_ADMIN: return
            cfg=get_global_config(); gb=cfg.get("global_bans",[])
            if target not in gb:
                gb.append(target); update_global_config("global_bans",gb)
                await message.reply(f"🌍 Globally banned `{target}`!")
        elif cmd == "ungban":
            if uid!=MAIN_ADMIN: return
            cfg=get_global_config(); gb=cfg.get("global_bans",[])
            if target in gb:
                gb.remove(target); update_global_config("global_bans",gb)
                await message.reply(f"✅ Globally unbanned `{target}`!")
        elif cmd == "info":
            u = get_user(target, bot_id)
            if not u: return await message.reply("❌ Not found.")
            await message.reply(
                f"👤 **User Info**\n"
                f"🆔 `{u['user_id']}`\n"
                f"🏷 {u.get('name','?')} | @{u.get('username') or 'None'}\n"
                f"🚫 Banned: {u.get('is_banned',False)} | 💎 Premium: {u.get('is_premium',False)}\n"
                f"📤 Uploaded: `{u.get('files_uploaded',0)}`"
            )

    @app.on_message(filters.command("setprice") & filters.private, group=1)
    async def setprice_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply("❌ Access Denied!")
        if len(message.command)<2:
            curr=bi.get("premium_price","500")
            return await message.reply(f"💰 Current Price: `{curr}`\n`/setprice AMOUNT` (e.g. 500 or 5$)")
        price = message.text.split(None, 1)[1].strip()
        update_bot_info(bot_id, "premium_price", price)
        await message.reply(f"✅ Premium price set to: `{price}`")

    @app.on_message(filters.command("setcontact") & filters.private, group=1)
    async def setcontact_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply("❌ Access Denied!")
        if len(message.command)<2:
            curr=bi.get("premium_contact","zolvid")
            return await message.reply(f"📞 Current Contact: `@{curr}`\n`/setcontact USERNAME` (without @)")
        contact = message.command[1].replace("@", "").strip()
        update_bot_info(bot_id, "premium_contact", contact)
        await message.reply(f"✅ Premium contact set to: `@{contact}`")

    @app.on_message(filters.command("setqr") & filters.private, group=1)
    async def setqr_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply("❌ Access Denied!")
        if not message.reply_to_message or not message.reply_to_message.photo:
            return await message.reply("🖼 Reply to a QR code image with `/setqr` to set it.\nUse `/setqr off` to remove.")

        if len(message.command) > 1 and message.command[1].lower() == "off":
            update_bot_info(bot_id, "premium_qr", None)
            return await message.reply("✅ Premium QR code removed!")

        qr_id = message.reply_to_message.photo.file_id
        update_bot_info(bot_id, "premium_qr", qr_id)
        await message.reply("✅ Premium QR code updated successfully!")

    @app.on_message(filters.command("setchannel") & filters.private, group=1)
    async def setchannel_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply("❌ Access Denied!")
        if len(message.command)<2:
            return await message.reply(
                f"📢 **Channel Connection**\n\n"
                f"Connected: `{bi.get('connected_channel') or 'None'}`\n\n"
                f"Usage:\n"
                f"├ `/setchannel -100xxxxxxx` - Connect channel\n"
                f"└ `/setchannel off` - Disable connection\n\n"
                f"Note: Users can use `/start join` to get an expiring link to this channel."
            )
        if message.command[1].lower()=="off":
            update_bot_info(bot_id,"connected_channel",None); return await message.reply("✅ Disabled!")
        try:
            chid = int(message.command[1])
            await client.get_chat(chid)
            update_bot_info(bot_id,"connected_channel",chid)
            await message.reply(f"✅ Channel connected successfully: `{chid}`")
        except Exception as e: await message.reply(f"❌ Error: Make sure bot is admin in channel!\n`{e}`")

    @app.on_message(filters.command("setmode") & filters.private, group=1)
    async def setmode_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply("❌ Access Denied!")
        modes = ["direct", "requested", "approval"]
        if len(message.command)<2:
            return await message.reply(
                f"⚙️ **Join Mode Selection**\n\n"
                f"Current Mode: `{bi.get('join_method','direct').upper()}`\n\n"
                f"Available Modes:\n"
                f"├ `direct` - Regular join link\n"
                f"├ `requested` - Admin approval request\n"
                f"└ `approval` - Same as requested\n\n"
                f"Usage: `/setmode [mode]`"
            )
        mode = message.command[1].lower()
        if mode not in modes:
            return await message.reply(f"❌ Invalid mode! Use: {', '.join(modes)}")
        update_bot_info(bot_id, "join_method", mode)
        await message.reply(f"✅ Join mode set to: `{mode.upper()}`")

    @app.on_message(filters.command("settimer") & filters.private, group=1)
    async def settimer_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN): return await message.reply("❌ Access Denied!")
        if len(message.command)<2:
            curr=bi.get("auto_delete_time",600)
            return await message.reply(f"⏱ Current: `{curr}s` ({curr//60}min)\n`/settimer SECONDS`")
        try:
            secs=int(message.command[1])
            if secs<60: return await message.reply("❌ Min 60s!")
            update_bot_info(bot_id,"auto_delete_time",secs)
            await message.reply(f"✅ Set to `{secs}s` ({secs//60}min).")
        except ValueError: await message.reply("❌ Invalid!")

    @app.on_message(filters.command("setlog") & filters.private, group=1)
    async def setlog_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply("❌ Access Denied!")
        if len(message.command)<2: return await message.reply(f"📝 Log: `{bi.get('log_channel') or 'None'}`\n`/setlog ID` or off")
        if message.command[1].lower()=="off":
            update_bot_info(bot_id,"log_channel",None); return await message.reply("✅ Disabled!")
        try:
            update_bot_info(bot_id,"log_channel",int(message.command[1]))
            await message.reply("✅ Log channel set!")
        except ValueError: await message.reply("❌ Invalid ID!")

    @app.on_message(filters.command("setverify") & filters.private, group=1)
    async def setverify_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply("❌ Access Denied!")
        if len(message.command)<2:
            return await message.reply(
                f"🛡 **Verification System**\n\n"
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
            return await message.reply("✅ Verification disabled!")

        update_bot_info(bot_id, "verify_link", val)
        await message.reply(f"✅ Verification link set to: `{val}`")

    @app.on_message(filters.command("setupdates") & filters.private, group=1)
    async def setupdates_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)): return await message.reply("❌ Access Denied!")
        if len(message.command)<2:
            return await message.reply(f"📢 Update Channel: `{bi.get('update_channel') or 'None'}`\n`/setupdates LINK` or off")
        val = message.command[1]
        if val.lower() == "off":
            update_bot_info(bot_id, "update_channel", None)
            return await message.reply("✅ Update channel disabled!")

        update_bot_info(bot_id, "update_channel", val)
        await message.reply(f"✅ Update channel link set to: `{val}`")

    @app.on_message(filters.command("shortener") & filters.private, group=1)
    async def shortener_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN): return await message.reply("❌ Access Denied!")
        if len(message.command)<2:
            st="✅ ON" if bi.get("is_shortener_enabled") else "❌ OFF"
            return await message.reply(f"🔗 Shortener {st}\nURL: `{bi.get('shortener_url') or 'Not set'}`\nCmds: `on`, `off`, `set URL APIKEY`")
        cmd=message.command[1].lower()
        if cmd=="on":
            if not bi.get("shortener_url"): return await message.reply("❌ Set URL first!")
            update_bot_info(bot_id,"is_shortener_enabled",True); await message.reply("✅ Enabled!")
        elif cmd=="off":
            update_bot_info(bot_id,"is_shortener_enabled",False); await message.reply("✅ Disabled!")
        elif cmd=="set":
            if len(message.command)<4: return await message.reply("Usage: `/shortener set URL APIKEY`")
            update_bot_info(bot_id,"shortener_url",message.command[2])
            update_bot_info(bot_id,"shortener_api",message.command[3])
            await message.reply(f"✅ Configured: `{message.command[2]}`")

    @app.on_message(filters.command("clone") & filters.private, group=1)
    async def clone_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id
        if is_user_banned(uid,bot_id): return await message.reply("🚫 Banned!")
        if len(message.command)<2:
            ubts=[b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            return await message.reply(
                f"🤖 **Bot Cloning System** 🤖\n\n"
                f"Create your own version of this bot in seconds!\n\n"
                f"1️⃣ Go to @BotFather and create a `/newbot`.\n"
                f"2️⃣ Copy the **API TOKEN** they give you.\n"
                f"3️⃣ Send it here: `/clone YOUR_TOKEN`.\n\n"
                f"✅ Your bots: `{len(ubts)}`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🤖 BotFather",url="https://t.me/BotFather")]]))
        token=message.command[1]
        for b in get_all_bots().values():
            if isinstance(b,dict) and b.get("token")==token: return await message.reply("❌ Already registered!")
        sm=await message.reply("🔄 **Establishing connection to Telegram...**")
        try:
            na=await start_bot(token,parent_bot_id=bot_id)
            if na:
                me=await na.get_me()
                save_bot_info(token,me.id,me.username,uid,message.from_user.first_name,bot_id)
                await sm.edit(
                    f"🎊 **CONGRATULATIONS! YOUR BOT IS READY!** 🎊\n\n"
                    f"🤖 **Username:** @{me.username}\n"
                    f"🆔 **Bot ID:** `{me.id}`\n\n"
                    f"🚀 **NEXT STEPS (IMPORTANT):**\n"
                    f"1️⃣ Open your new bot: @{me.username}\n"
                    f"2️⃣ Send `/start` to activate it.\n"
                    f"3️⃣ Use `/setlog -100xxxx` to set a log channel.\n"
                    f"4️⃣ Use `/setchannel` to connect your main channel.\n\n"
                    f"Enjoy your personal FileStore bot!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 OPEN CLONED BOT", url=f"https://t.me/{me.username}")]]))
            else: await sm.edit("❌ Failed! Make sure the token is correct and bot is not already running.")
        except Exception as e: await sm.edit(f"❌ Error: `{e}`")

    @app.on_message(filters.command("setfs") & filters.private, group=1)
    async def setfs_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN): return await message.reply("❌ Only owner!")
        fs=bi.get("force_subs",[])
        if len(message.command)<2:
            text=f"⚙️ **Force Subscribe** ({len(fs)}/{MAX_FORCE_SUB_CHANNELS})\n\n"
            for i,f in enumerate(fs,1):
                cid=f["channel_id"] if isinstance(f,dict) else f; text+=f"{i}. `{cid}`\n"
            if not fs: text+="None.\n"
            text+="\nCmds: `add -100xxx [link]`, `del -100xxx`, `clear`"
            return await message.reply(text)
        cmd=message.command[1].lower()
        if cmd in ("clear","off"):
            update_bot_info(bot_id,"force_subs",[]); n=cascade_force_subs(bot_id,[])
            return await message.reply(f"✅ Cleared! ({n} clones updated)")
        if cmd=="add":
            if len(fs)>=MAX_FORCE_SUB_CHANNELS: return await message.reply(f"❌ Max {MAX_FORCE_SUB_CHANNELS}!")
            if len(message.command)<3: return await message.reply("Usage: `/setfs add -100xxx [link]`")
            try: cid=int(message.command[2])
            except ValueError: return await message.reply("❌ Invalid ID!")
            lnk=message.command[3] if len(message.command)>3 else None
            try: await client.get_chat_member(cid,client.me.id)
            except Exception: return await message.reply("❌ I'm not admin there!")
            fs.append({"channel_id":cid,"invite_link":lnk})
            update_bot_info(bot_id,"force_subs",fs); n=cascade_force_subs(bot_id,fs)
            return await message.reply(f"✅ Added! ({n} clones updated)")
        if cmd=="del":
            if len(message.command)<3: return await message.reply("Usage: `/setfs del -100xxx`")
            try: cid=int(message.command[2])
            except ValueError: return await message.reply("❌ Invalid ID!")
            new_fs=[f for f in fs if (f["channel_id"] if isinstance(f,dict) else f)!=cid]
            if len(new_fs)==len(fs): return await message.reply("❌ Not in list!")
            update_bot_info(bot_id,"force_subs",new_fs); n=cascade_force_subs(bot_id,new_fs)
            return await message.reply(f"✅ Removed! ({n} clones updated)")

    @app.on_message(filters.command(["premium","botinfo","help",
                                      "setglobal","addadmin","deladmin","search"]) & filters.private, group=1)
    async def misc_commands(client, message):
        uid=message.from_user.id; bot_id=client.me.id; cmd=message.command[0]
        if cmd == "premium":
            ud=get_user(uid,bot_id); is_p=ud.get("is_premium",False) if ud else False
            bi=get_bot_info(bot_id); price = bi.get("premium_price", "500") if bi else "500"
            contact = bi.get("premium_contact", "zolvid") if bi else "zolvid"
            qr_id = bi.get("premium_qr") if bi else None

            default_prem = (
                f"🌟 **ELITE PREMIUM MEMBERSHIP** 🌟\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✨ **Status:** {{status}}\n\n"
                f"🚀 **UNLOCK THE POWER:**\n"
                f" ├ ♾ **PERMANENT STORAGE:** No auto-delete timer!\n"
                f" ├ 🎭 **DUAL-TIER UNLOCK:** Get PRO files instantly!\n"
                f" ├ ⚡ **ZERO ADS:** Skip all shortener links!\n"
                f" ├ 📦 **PRO BATCHING:** No limits on creation!\n"
                f" └ 💎 **PRIORITY:** Faster delivery & support!\n\n"
                f"💰 **Subscription Fee:** `{{price}}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👇 **WANT TO UPGRADE? CONTACT ADMIN!** 👇"
            )
            text = get_msg_text("msg_premium", default_prem).format_map(SafeDict(
                status='✅ `ACTIVATED`' if is_p else '❌ `NOT ACTIVE`',
                price=price,
                contact=f"@{contact}"
            ))

            kb = [
                [InlineKeyboardButton(get_btn_name("btn_pcon", "👑 CONTACT ADMIN"), url=f"https://t.me/{contact}")],
                [InlineKeyboardButton(get_btn_name("btn_back", "🔙 BACK TO HOME"), callback_data="back_to_start")]
            ]
            if qr_id:
                kb.insert(1, [InlineKeyboardButton(get_btn_name("btn_pqrs", "🖼 SHOW PAYMENT QR"), callback_data="show_premium_qr")])

            if qr_id and not is_p:
                await message.reply_photo(qr_id, caption=text, reply_markup=InlineKeyboardMarkup(kb))
            else:
                await message.reply(text, reply_markup=InlineKeyboardMarkup(kb))
        elif cmd == "botinfo":
            bi=get_bot_info(bot_id)
            if not bi: return await message.reply("Not in DB.")
            dp_count = len(get_bot_dual_posts(bot_id))
            await message.reply(
                f"ℹ️ @{client.me.username}\n"
                f"👤 {bi.get('owner_name','?')}\n"
                f"🌳 Clones: `{len(get_child_bots(bot_id))}`\n"
                f"📢 Force Sub: `{len(bi.get('force_subs',[]))}` ch\n"
                f"⏱ Timer: `{bi.get('auto_delete_time',600)}s` | "
                f"AA: `{'ON' if bi.get('auto_approve') else 'OFF'}`\n"
                f"🎭 Dual Posts: `{dp_count}`"
            )
        elif cmd == "help":
            help_text = "🚀 **FileStore v7.0 — Command List**\n\n"
            for command in BOT_COMMANDS:
                help_text += f"• `/{command.command}` — {command.description}\n"

            help_text += "\n💡 *Tip: You can use most commands by clicking the menu button or typing / followed by the command.*"

            await message.reply(
                help_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎭 DUAL POST GUIDE", callback_data="dual_help"),
                     InlineKeyboardButton("💎 PREMIUM INFO", callback_data="premium_menu")],
                    [InlineKeyboardButton("🔙 BACK TO HOME", callback_data="back_to_start")]
                ])
            )
        elif cmd == "setglobal":
            if uid!=MAIN_ADMIN: return
            if len(message.command)<2: return await message.reply("Usage: `/setglobal MSG` or off")
            txt=message.text.split(None,1)[1]
            update_global_config("global_msg","" if txt.lower()=="off" else txt)
            await message.reply("✅ Updated!")
        elif cmd == "addadmin":
            if uid!=MAIN_ADMIN: return
            if len(message.command)<2: return await message.reply("Usage: `/addadmin ID`")
            admins=load_db(ADMINS_DB); admins[message.command[1]]=str(datetime.now())
            save_db(ADMINS_DB,admins); await message.reply(f"✅ `{message.command[1]}` is Admin.")
        elif cmd == "deladmin":
            if uid!=MAIN_ADMIN: return
            if len(message.command)<2: return await message.reply("Usage: `/deladmin ID`")
            admins=load_db(ADMINS_DB)
            if message.command[1] in admins:
                del admins[message.command[1]]; save_db(ADMINS_DB,admins)
                await message.reply(f"✅ Removed `{message.command[1]}`.")
            else: await message.reply("❌ Not an admin!")
        elif cmd == "search":
            if is_user_banned(uid,bot_id): return await message.reply("🚫 Banned!")
            if len(message.command)<2: return await message.reply("🔍 Usage: `/search FILENAME`")
            q=message.text.split(None,1)[1].lower(); files=load_db(FILES_DB)
            results=[(k,f) for k,f in files.items()
                     if f.get("bot_id")==bot_id and q in f.get("file_name","").lower()][:10]
            if not results: return await message.reply(f"❌ No files for `{q}`")
            text=f"🔍 **Results ({len(results)})**\n\n"; btns=[]
            for k,f in results:
                icon=file_icon(f.get("file_name","")); name=f.get("file_name","?")
                link=f"https://t.me/{client.me.username}?start=f_{k}"
                text+=f"{icon} `{name[:40]}`  📊 {fmt_size(f.get('file_size',0))}\n"
                btns.append([InlineKeyboardButton(f"{icon} {name[:30]}",url=link)])
            await message.reply(text,reply_markup=InlineKeyboardMarkup(btns))

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
                    description=f"📊 {fmt_size(f.get('file_size',0))} | 👁 {f.get('access_count',0)}",
                    input_message_content=InputTextMessageContent(
                        f"{icon} **{f.get('file_name')}**\n"
                        f"📊 `{fmt_size(f.get('file_size',0))}`\n🔗 {link}"
                    ),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Get File",url=link)]])
                ))
                if len(results)>=20: break
        await query.answer(results,cache_time=1)

    # ── FILE HANDLER ─────────────────────────────────────────────
    @app.on_message(filters.private, group=1)
    async def advanced_handler(client, message):
        uid=message.from_user.id; bot_id=client.me.id
        if is_user_banned(uid,bot_id): return

        # ── DATABASE RESTORE FEATURE ──────────────────────────────
        if uid == MAIN_ADMIN and message.document and message.document.file_name in BACKUP_FILES:
            fname = message.document.file_name
            await message.reply(
                f"📂 **Database File Detected:** `{fname}`\n\n"
                f"Do you want to restore/overwrite the current `{fname}` with this one?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ YES, RESTORE", callback_data=f"confirm_import_{fname}"),
                     InlineKeyboardButton("❌ NO",           callback_data="cancel_import")]
                ])
            )
            return

        # Only handle if in batch/dual session or if it is a file/message
        in_session = uid in TEMP_BATCH or uid in TEMP_DUAL or uid in TEMP_EDIT or uid in TEMP_WELCOME
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

        # Skip if FSM is waiting for photo
        if uid in TEMP_EDIT and TEMP_EDIT[uid].get("mode")=="thumbnail" and message.photo: return
        if uid in TEMP_WELCOME and TEMP_WELCOME[uid].get("step")=="image" and message.photo: return

        main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
        db_msg = None

        try:
            # First try forwarding with current client
            db_msg = await message.forward(DB_CHANNEL)
        except Exception:
            # Fallback: Re-upload using main bot if clone is not in channel
            try:
                sm = await message.reply("🔄 **Forwarding to DB via Main Bot...**")
                # Since bots have different file_ids, we download and upload.
                path = await message.download()
                if path:
                    uploader = main_client or GLOBAL_USERBOT
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
                    return await message.reply("❌ Failed to process file for DB.")
            except Exception as e:
                return await message.reply(f"❌ DB Channel error (Main Bot fallback): \n`{e}`")

        bi = get_bot_info(bot_id)
        original_caption = message.caption or message.text
        if bi and bi.get("auto_caption") and not original_caption and (message.document or message.video or message.audio):
            fname = (message.document or message.video or message.audio).file_name or "File"
            original_caption = f"📁 **File Name:** `{fname}`\n\n⚡ **Powered by:** @{client.me.username}"
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

        main_client=next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")),client)
        asyncio.create_task(save_meta(main_client,{**fdata,"unique_id":fuid}))

        bi=get_bot_info(bot_id)
        if bi and bi.get("log_channel"):
            try:
                await client.copy_message(
                    bi["log_channel"],message.chat.id,message.id,
                    caption=f"📤 Upload | {file_icon(file_name)} `{file_name}`\n📊 {fmt_size(file_size)} | 👤 `{uid}` | 🆔 `{fuid}`"
                )
            except Exception: pass

        # ── DUAL POST SESSION ────────────────────────────────────
        if uid in TEMP_DUAL:
            sess  = TEMP_DUAL[uid]
            stage = sess.stage
            if stage == "free":
                sess.free_files.append(fuid)
                count = len(sess.free_files)
                await message.reply(
                    f"📂 **Added to FREE Tier!**\n\n"
                    f"{file_icon(file_name)} `{file_name}`\n"
                    f"📊 {fmt_size(file_size)}\n\n"
                    f"📂 Free tier total: `{count}` file(s)\n"
                    f"💎 Premium tier: `{len(sess.pro_files)}` file(s)\n\n"
                    f"Send more FREE files, or switch to Premium stage.",
                    quote=True,
                    reply_markup=kb_dual_post_creator(stage, count, len(sess.pro_files))
                )
            elif stage == "pro":
                sess.pro_files.append(fuid)
                count = len(sess.pro_files)
                await message.reply(
                    f"💎 **Added to PREMIUM Tier!**\n\n"
                    f"{file_icon(file_name)} `{file_name}`\n"
                    f"📊 {fmt_size(file_size)}\n\n"
                    f"📂 Free tier: `{len(sess.free_files)}` file(s)\n"
                    f"💎 Premium tier total: `{count}` file(s)\n\n"
                    f"Send more PREMIUM files, or finish.",
                    quote=True,
                    reply_markup=kb_dual_post_creator(stage, len(sess.free_files), count)
                )
            return

        # ── BATCH SESSION ────────────────────────────────────────
        elif uid in TEMP_BATCH:
            TEMP_BATCH[uid].append(fuid)
            await message.reply(
                f"✅ **Added!**\n{file_icon(file_name)} `{file_name}`\n"
                f"📦 Total: `{len(TEMP_BATCH[uid])}`",
                quote=True
            )

        # ── NORMAL UPLOAD ────────────────────────────────────────
        else:
            if media_type == "message":
                return
            direct_link = f"https://t.me/{client.me.username}?start=f_{fuid}"
            await message.reply(
                f"✅ **File Saved!**\n\n"
                f"{file_icon(file_name)} `{file_name}`\n"
                f"📊 {fmt_size(file_size)} | 🆔 `{fuid}`\n\n"
                f"🔗 **Share Link:**\n`{direct_link}`\n\n"
                + (f"_ℹ️ Recipients go through shortener ads to get file._"
                   if shortener_enabled_for_bot(bi) else ""),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={direct_link}"),
                     InlineKeyboardButton("✏️ Edit",  callback_data=f"edit_file_{fuid}")]
                ])
            )

    # ── FSM RESPONDER (group 2) ───────────────────────────────────
    _CMD_LIST = [
        "start","admin","supreme","clone","batch","done","cancel","setfs","mybots","stats",
        "help","broadcast","ban","unban","info","givepremium","removepremium","gban","ungban","botinfo",
        "settimer","search","premium","setprice","shortener","setlog",
        "setchannel","setmode",
        "rebuild","backup","restart","ping","listfiles","editfile","delfile",
        "setwelcome","setglobal","addadmin","deladmin",
        "dualpost","dpremium","dpdone","dpcancel","myduals","deldual","dpstats"
    ]

    @app.on_message(filters.private & ~filters.command(_CMD_LIST), group=2)
    async def fsm_responder(client, message):
        uid = message.from_user.id; bot_id = client.me.id

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
                        f"✅ Channel found: **{chat.title}**\n\n"
                        f"Step 2: Choose **Join Mode**:\n"
                        f"├ `direct` - Regular join link\n"
                        f"├ `requested` - Join request (admin approval)\n"
                        f"└ `normal` - Public channel (no special link needed, but we provide one anyway)",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔗 Direct",    callback_data="pm_direct"),
                             InlineKeyboardButton("📩 Requested", callback_data="pm_requested")],
                            [InlineKeyboardButton("📢 Normal",    callback_data="pm_normal")],
                            [InlineKeyboardButton("❌ Cancel",    callback_data="cancel_protect")]
                        ])
                    )
                except Exception as e:
                    await message.reply(f"❌ Invalid Channel ID or Bot is not admin there!\n`{e}`")
            return

        if uid in TEMP_WELCOME:
            sess = TEMP_WELCOME[uid]; step = sess.get("step")
            if step == "text":
                if not message.text: return await message.reply("❌ Send text or `-skip`.")
                txt = message.text.strip()
                if txt not in ("-skip", "-clear"):
                    update_bot_info(bot_id, "custom_welcome", txt)
                elif txt == "-clear":
                    update_bot_info(bot_id, "custom_welcome", None)
                sess["step"] = "image"
                await message.reply(
                    f"✅ {'Updated!' if txt not in ('-skip','-clear') else 'Unchanged!' if txt=='-skip' else 'Reset!'}\n\n"
                    f"🖼 **Step 2/2:** Send photo for welcome image.\n`-skip` = keep | `-clear` = remove",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel",callback_data="cancel_welcome")]])
                )
            elif step == "image":
                if message.photo:
                    update_bot_info(bot_id, "welcome_image", message.photo.file_id)
                    del TEMP_WELCOME[uid]
                    await message.reply(
                        "✅ **Welcome fully updated!**",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("👀 Preview", callback_data="preview_welcome")],
                            [InlineKeyboardButton("🔙 Admin",   callback_data="admin_panel")]
                        ])
                    )
                elif message.text:
                    txt = message.text.strip()
                    if txt == "-skip":
                        del TEMP_WELCOME[uid]
                        await message.reply("✅ Image unchanged.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin",callback_data="admin_panel")]]))
                    elif txt == "-clear":
                        update_bot_info(bot_id, "welcome_image", None)
                        del TEMP_WELCOME[uid]
                        await message.reply("✅ Image removed.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin",callback_data="admin_panel")]]))
                    else: await message.reply("❌ Send a **photo**, `-skip`, or `-clear`.")
            return

        if uid in TEMP_EDIT:
            sess = TEMP_EDIT[uid]; mode = sess["mode"]; fuid = sess["uid"]
            files = load_db(FILES_DB)
            if fuid not in files:
                del TEMP_EDIT[uid]; return await message.reply("❌ File no longer exists.")
            if mode == "caption":
                if not message.text: return await message.reply("❌ Send **text** for caption.")
                txt = message.text.strip()
                files[fuid]["caption"] = None if txt == "-clear" else txt
                save_db(FILES_DB, files)
                main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
                asyncio.create_task(save_meta(main_client, {**files[fuid], "unique_id": fuid}))
                del TEMP_EDIT[uid]
                await message.reply(
                    f"✅ Caption {'removed' if txt=='-clear' else 'updated'}!",
                    reply_markup=kb_file_edit(fuid)
                )
            elif mode == "thumbnail":
                if not message.photo: return await message.reply("❌ Send a **photo** as thumbnail.")
                files[fuid]["custom_thumbnail"] = message.photo.file_id
                save_db(FILES_DB, files)
                main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
                asyncio.create_task(save_meta(main_client, {**files[fuid], "unique_id": fuid}))
                del TEMP_EDIT[uid]
                await message.reply("✅ Thumbnail updated!", reply_markup=kb_file_edit(fuid))
            elif mode == "qrename":
                if not message.text: return await message.reply("❌ Send a **new file name**.")
                new_name = message.text.strip()
                files[fuid]["file_name"] = new_name
                save_db(FILES_DB, files)
                main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
                asyncio.create_task(save_meta(main_client, {**files[fuid], "unique_id": fuid}))
                del TEMP_EDIT[uid]
                await message.reply(f"✅ **Quick Rename Complete!**\n\n🆕 `{new_name}`\n_Note: This only changes how the bot displays the name._", reply_markup=kb_file_edit(fuid))

            elif mode == "set_price":
                update_bot_info(bot_id, "premium_price", message.text.strip())
                del TEMP_EDIT[uid]
                await message.reply(f"✅ Premium price set to: `{message.text.strip()}`", reply_markup=kb_admin())

            elif mode == "set_contact":
                contact = message.text.replace("@", "").strip()
                update_bot_info(bot_id, "premium_contact", contact)
                del TEMP_EDIT[uid]
                await message.reply(f"✅ Premium contact set to: `@{contact}`", reply_markup=kb_admin())

            elif mode == "set_timer_custom":
                try:
                    secs = int(message.text)
                    if secs < 30: return await message.reply("❌ Min 30s!")
                    update_bot_info(bot_id, "auto_delete_time", secs)
                    del TEMP_EDIT[uid]
                    await message.reply(f"✅ Timer set to `{secs}s`!", reply_markup=kb_admin())
                except: await message.reply("❌ Send a valid number of seconds.")

            elif mode == "customize_button":
                if not message.text: return await message.reply("❌ Send a **name**.")
                new_name = message.text.strip()
                key = sess["key"]
                btns = get_global_config().get("custom_buttons", {})
                btns[key] = new_name
                update_global_config("custom_buttons", btns)
                del TEMP_EDIT[uid]
                await message.reply(f"✅ Button `{key}` updated to: `{new_name}`", reply_markup=kb_supreme())

            elif mode == "customize_message":
                if not message.text: return await message.reply("❌ Send **text**.")
                txt = message.text.strip()
                key = sess["key"]
                msgs = get_global_config().get("custom_messages", {})
                if txt == "-clear":
                    msgs.pop(key, None)
                else:
                    msgs[key] = txt
                update_global_config("custom_messages", msgs)
                del TEMP_EDIT[uid]
                await message.reply(f"✅ Message `{key}` updated!", reply_markup=kb_supreme())

            elif mode == "rename":
                if not message.text: return await message.reply("❌ Send a **new file name**.")
                new_name = message.text.strip()
                fd = files[fuid]
                del TEMP_EDIT[uid]
                sm = await message.reply(f"⏳ **Hard Renaming file...**\n\n`{fd.get('file_name')}` ➡️ `{new_name}`\n\n_Please wait, this involves downloading and re-uploading._")

                try:
                    # Download
                    t0 = time.time()
                    async def progress(current, total):
                        pct = current * 100 / total
                        if time.time() - t0 > 3:
                            bar = "█" * (int(pct) // 10) + "░" * (10 - int(pct) // 10)
                            try: await sm.edit(f"⏳ **Hard Renaming...**\n\n📥 Downloading: `[{bar}]` {pct:.1f}%")
                            except: pass

                    path = await client.download_media(fd['file_id'], progress=progress)
                    if not path:
                        return await sm.edit("❌ Download failed! File might be too large or deleted.")

                    # Use temp dir to avoid conflicts
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        new_path = os.path.join(tmp_dir, new_name)
                        shutil.move(path, new_path)

                        # Upload
                        await sm.edit(f"⏳ **Hard Renaming...**\n\n📤 Uploading: `0%`")
                        t1 = time.time()
                        async def up_progress(current, total):
                            pct = current * 100 / total
                            if time.time() - t1 > 3:
                                bar = "█" * (int(pct) // 10) + "░" * (10 - int(pct) // 10)
                                try: await sm.edit(f"⏳ **Hard Renaming...**\n\n📤 Uploading: `[{bar}]` {pct:.1f}%")
                                except: pass

                        thumb = fd.get('custom_thumbnail')
                        thumb_path = None
                        if thumb:
                            thumb_path = await client.download_media(thumb)

                        mtype = fd.get('media_type', 'document')
                        new_db_msg = None
                        if mtype == "video":
                            new_db_msg = await client.send_video(DB_CHANNEL, video=new_path, thumb=thumb_path, caption=fd.get('caption'), progress=up_progress)
                        elif mtype == "audio":
                            new_db_msg = await client.send_audio(DB_CHANNEL, audio=new_path, thumb=thumb_path, caption=fd.get('caption'), progress=up_progress)
                        else:
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

                            main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
                            asyncio.create_task(save_meta(main_client, {**fd, "unique_id": fuid}))

                            await sm.edit(f"✅ **File Renamed Successfully!**\n\n🆕 Name: `{new_name}`", reply_markup=kb_file_edit(fuid))
                        else:
                            await sm.edit("❌ Upload failed!")

                        if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)

                except Exception as e:
                    logger.error(f"Rename error: {e}")
                    await sm.edit(f"❌ **Rename Error:** `{e}`")

    # ── CALLBACK HANDLER ──────────────────────────────────────────
    @app.on_callback_query(group=1)
    async def cb_handler(client, cb):
        uid = cb.from_user.id; data = cb.data; bot_id = client.me.id
        if is_user_banned(uid, bot_id): return await cb.answer("🚫 Banned!", show_alert=True)

        if data.startswith("edit_file_"):
            fuid = data[10:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("❌ Not found!", show_alert=True)
            bi = get_bot_info(bot_id)
            can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or fd.get("user_id")==uid
            if not can: return await cb.answer("❌ Not your file!", show_alert=True)
            icon = file_icon(fd.get("file_name","")); cap = fd.get("caption") or "_(none)_"
            thumb = "✅" if fd.get("custom_thumbnail") else "❌"
            await cb.message.edit(
                f"✏️ **File Editor**\n\n{icon} **{fd.get('file_name','?')}**\n"
                f"🆔 `{fuid}` | 📊 {fmt_size(fd.get('file_size',0))}\n"
                f"💬 {cap} | 🖼 {thumb} | 👁 `{fd.get('access_count',0)}`",
                reply_markup=kb_file_edit(fuid)
            )
            await cb.answer()

        elif data.startswith("edit_caption_"):
            fuid = data[13:]; files = load_db(FILES_DB)
            if fuid not in files: return await cb.answer("❌ Not found!", show_alert=True)
            TEMP_EDIT[uid] = {"mode": "caption", "uid": fuid}
            await cb.message.edit(
                f"✏️ **Edit Caption**\n\nFile: `{files[fuid].get('file_name','?')}`\n\n"
                f"Send new caption text.\n`-clear` to remove.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]])
            )
            await cb.answer("Send caption text")

        elif data.startswith("edit_thumb_"):
            fuid = data[11:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("❌ Not found!", show_alert=True)
            if fd.get("media_type") == "photo":
                return await cb.answer("❌ Photos can't have thumbnails!", show_alert=True)
            TEMP_EDIT[uid] = {"mode": "thumbnail", "uid": fuid}
            await cb.message.edit(
                f"🖼 **Edit Thumbnail**\n\nFile: `{fd.get('file_name','?')}`\n\nSend a **photo** as thumbnail.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚡ Hard Fix Thumbnail", callback_data=f"fix_thumb_{fuid}")],
                    [InlineKeyboardButton("🗑 Remove Thumb", callback_data=f"remove_thumb_{fuid}")],
                    [InlineKeyboardButton("❌ Cancel",       callback_data="cancel_edit")]
                ])
            )
            await cb.answer("Send a photo")

        elif data.startswith("fix_thumb_"):
            fuid = data[10:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("❌ Not found!", show_alert=True)
            if not fd.get("custom_thumbnail"):
                return await cb.answer("❌ Set a thumbnail first!", show_alert=True)

            await cb.answer("⏳ Hard fixing thumbnail...")
            sm = await cb.message.edit(f"⏳ **Hard Fixing Thumbnail...**\n\nFile: `{fd.get('file_name')}`\n\n_Downloading and re-uploading with thumbnail..._")

            try:
                # Download
                path = await client.download_media(fd['file_id'])
                thumb_path = await client.download_media(fd['custom_thumbnail'])

                mtype = fd.get('media_type', 'document')
                new_db_msg = None
                if mtype == "video":
                    new_db_msg = await client.send_video(DB_CHANNEL, video=path, thumb=thumb_path, caption=fd.get('caption'))
                elif mtype == "audio":
                    new_db_msg = await client.send_audio(DB_CHANNEL, audio=path, thumb=thumb_path, caption=fd.get('caption'))
                else:
                    new_db_msg = await client.send_document(DB_CHANNEL, document=path, thumb=thumb_path, caption=fd.get('caption'))

                if new_db_msg:
                    media = new_db_msg.document or new_db_msg.video or new_db_msg.audio or new_db_msg.animation or new_db_msg.sticker
                    fd['file_id'] = media.file_id
                    fd['db_msg_id'] = new_db_msg.id
                    save_db(FILES_DB, files)

                    main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
                    asyncio.create_task(save_meta(main_client, {**fd, "unique_id": fuid}))

                    await sm.edit("✅ **Thumbnail Hard-Fixed!**\n\nThe file has been re-uploaded with the thumbnail permanently attached.", reply_markup=kb_file_edit(fuid))
                else:
                    await sm.edit("❌ Fix failed during upload!")

                if path and os.path.exists(path): os.remove(path)
                if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
            except Exception as e:
                await sm.edit(f"❌ **Fix Error:** `{e}`")

        elif data.startswith("qrename_"):
            fuid = data[8:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("❌ Not found!", show_alert=True)
            TEMP_EDIT[uid] = {"mode": "qrename", "uid": fuid}
            await cb.message.edit(
                f"📝 **Quick Rename**\n\nCurrent: `{fd.get('file_name','?')}`\n\nSend new name for the bot to display.\n_Note: Original file remains unchanged._",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]])
            )
            await cb.answer("Send new name")

        elif data.startswith("rename_file_"):
            fuid = data[12:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("❌ Not found!", show_alert=True)
            TEMP_EDIT[uid] = {"mode": "rename", "uid": fuid}
            await cb.message.edit(
                f"🚀 **Hard Rename (Re-upload)**\n\nCurrent: `{fd.get('file_name','?')}`\n\nSend new name for the file (including extension).\n_This will re-upload the file to Telegram._",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]])
            )
            await cb.answer("Send new name")

        elif data.startswith("remove_thumb_"):
            fuid = data[13:]; files = load_db(FILES_DB)
            if fuid in files:
                files[fuid]["custom_thumbnail"] = None; save_db(FILES_DB, files)
                TEMP_EDIT.pop(uid, None)
                main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
                asyncio.create_task(save_meta(main_client, {**files[fuid], "unique_id": fuid}))
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

        elif data.startswith("del_plink_"):
            lpid = data[10:]; plinks = load_db(PLINKS_DB); p = plinks.get(lpid)
            if not p: return await cb.answer("Already deleted!", show_alert=True)
            bi = get_bot_info(bot_id)
            can = uid==MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id")==uid) or p.get("created_by")==uid
            if not can: return await cb.answer("❌ Access denied!", show_alert=True)
            del plinks[lpid]; save_db(PLINKS_DB, plinks)
            await cb.answer("🗑 Protected link deleted!", show_alert=True)
            await cb.message.edit(f"🗑 **Deleted Protected Link:** `{p.get('title','?')}`")

        elif data.startswith("get_file_"):
            fuid = data[9:]; files = load_db(FILES_DB); fd = files.get(fuid)
            if not fd: return await cb.answer("❌ Not found!", show_alert=True)
            await cb.answer("📤 Sending...")
            try:
                bi = get_bot_info(bot_id); ud = get_user(uid, bot_id)
                is_prem = ud and ud.get("is_premium", False)
                auto_del = bi.get("auto_delete_time", 600) if bi else 600
                sent = await deliver_file(client, cb.message.chat.id, fd)
                if sent and not is_prem:
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

        elif data == "cancel_protect":
            TEMP_PROTECT.pop(uid, None)
            await cb.message.edit("❌ Protection setup cancelled.")
            await cb.answer()

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
                f"🛡 **Channel Protected Successfully!**\n\n"
                f"📢 **Channel:** `{sess['title']}`\n"
                f"🆔 `{sess['channel_id']}`\n"
                f"⚙️ **Join Mode:** `{mode.upper()}`\n\n"
                f"🔗 **Your Sharable Link:**\n`{link}`\n\n"
                f"⚠️ **Note:** This link will always generate a fresh invite link (valid for 5 mins) for every user who clicks it.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={link}")]])
            )
            await cb.answer("Protected link created!", show_alert=True)

        elif data == "my_files_back":
            await cb.message.edit(
                "📋 Use `/listfiles` to browse.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Home", callback_data="back_to_start")]])
            )
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
                btns.append([InlineKeyboardButton("➕ Create Dual Post", callback_data="dual_post_start_new")])
            if dps:
                btns.append([InlineKeyboardButton(f"📋 My Dual Posts ({len(dps)})", callback_data="dual_post_list")])
            btns.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_start")])
            await cb.message.edit(
                f"🎭 **Dual Post System**\n\n"
                f"One link → Two experiences!\n\n"
                f"📂 **FREE tier** — For regular users\n"
                f"   → Shortener ads → Files → Auto-delete\n\n"
                f"💎 **PRO tier** — For Premium users\n"
                f"   → Direct delivery → No ads → No delete\n\n"
                f"{'⚡ Active session: send files!' if active_sess else ''}\n"
                f"Total posts: `{len(dps)}` | 👁 `{total_views}` views",
                reply_markup=InlineKeyboardMarkup(btns)
            )
            await cb.answer()

        elif data == "dual_post_start_new":
            bi = get_bot_info(bot_id)
            can_create = (uid == MAIN_ADMIN or is_admin(uid) or
                          (bi and bi.get("owner_id") == uid))
            if not can_create:
                return await cb.answer("❌ Only owner/admins can create Dual Posts!", show_alert=True)
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
                f"🎭 **Dual Post Creator — Started!**\n\n"
                f"Tip: `/dualpost My Title` for a titled post.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📂 **Stage 1 — FREE TIER**\n\n"
                f"Send files for non-premium users.\n\n"
                f"When done → `/dpremium` or button below\n"
                f"Cancel → `/dpcancel`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Switch to Premium Tier", callback_data="dp_switch_pro")],
                    [InlineKeyboardButton("✅ Finish & Generate Link",  callback_data="dp_finish")],
                    [InlineKeyboardButton("❌ Cancel",                  callback_data="dp_cancel_session")]
                ])
            )
            await cb.answer("📂 FREE tier stage started! Send files.")

        elif data == "dual_post_list":
            bi = get_bot_info(bot_id)
            is_sup = (uid == MAIN_ADMIN or is_admin(uid) or (bi and bi.get("owner_id") == uid))
            posts = get_bot_dual_posts(bot_id) if is_sup else get_user_dual_posts(bot_id, uid)
            if not posts:
                await cb.answer("No dual posts yet!", show_alert=True)
                return
            posts = sorted(posts, key=lambda p: p.get("created_at", ""), reverse=True)[:10]
            btns  = []
            text  = f"🎭 **Dual Posts ({len(posts)})**\n\n"
            for p in posts:
                pid   = p["post_id"]
                title = p.get("title", "Untitled")[:25]
                fc    = len(p.get("free_files", []))
                pc    = len(p.get("pro_files", []))
                at    = p.get("access_total", 0)
                text += f"📌 **{title}** | `{pid}` | 👁`{at}` | 📂`{fc}` 💎`{pc}`\n"
                link  = f"https://t.me/{client.me.username}?start=dp_{pid}"
                btns.append([
                    InlineKeyboardButton(f"📤 {title[:18]}", url=f"https://t.me/share/url?url={link}"),
                    InlineKeyboardButton("📊", callback_data=f"dp_analytics_{pid}"),
                    InlineKeyboardButton("🗑",  callback_data=f"dp_delete_{pid}")
                ])
            btns.append([InlineKeyboardButton("🔙 Back", callback_data="dual_post_menu")])
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
                f"💎 **Premium Tier Active!**\n\n"
                f"✅ Free tier locked: `{len(sess.free_files)}` file(s)\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 **Stage 2 — PREMIUM TIER**\n\n"
                f"Now send files for Premium users.\n"
                f"Direct delivery, no ads, no delete.\n\n"
                f"When done → `/dpdone` or button below\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Finish & Generate Link", callback_data="dp_finish")],
                    [InlineKeyboardButton("❌ Cancel Session",         callback_data="dp_cancel_session")]
                ])
            )
            await cb.answer("Switched to 💎 Premium tier!")

        elif data == "dp_finish":
            if uid not in TEMP_DUAL:
                return await cb.answer("No active session!", show_alert=True)
            sess = TEMP_DUAL[uid]
            if not sess.free_files and not sess.pro_files:
                return await cb.answer("❌ No files added yet!", show_alert=True)
            post_id   = unique_id()
            post_data = save_dual_post(post_id, sess)
            del TEMP_DUAL[uid]
            main_client = next((d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), client)
            asyncio.create_task(save_meta(main_client, {
                **post_data, "unique_id": post_id, "type": "dual_post"
            }))
            base_link = f"https://t.me/{client.me.username}?start=dp_{post_id}"
            bi2 = get_bot_info(bot_id)
            await cb.message.edit(
                f"🎉 **Dual Post Created!**\n\n"
                f"📌 **{sess.title or 'Dual Post'}**\n"
                f"🆔 `{post_id}`\n\n"
                f"📂 Free: `{len(sess.free_files)}` files "
                f"{'🔗 (shortener)' if shortener_enabled_for_bot(bi2) else '📂 (direct)'}\n"
                f"💎 Pro: `{len(sess.pro_files)}` files ⚡ (direct)\n\n"
                f"🔗 **Link:**\n`{base_link}`",
                reply_markup=kb_dual_post_done(post_id, base_link)
            )
            await cb.answer("✅ Dual post created!")

        elif data == "dp_cancel_session":
            if uid in TEMP_DUAL:
                del TEMP_DUAL[uid]
                await cb.message.edit("❌ Dual post session cancelled.")
            await cb.answer()

        elif data.startswith("dp_prev_free_"):
            post_id = data[len("dp_prev_free_"):]
            post = get_dual_post(post_id)
            if not post: return await cb.answer("Post not found!", show_alert=True)
            fids = post.get("free_files", [])
            if not fids: return await cb.answer("No free files!", show_alert=True)
            await cb.answer("📂 Sending free tier preview...")
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
            await cb.answer("💎 Sending premium tier preview...")
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
            if not can: return await cb.answer("❌ Not your post!", show_alert=True)
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
                f"📊 **Analytics — {post.get('title','?')}**\n\n"
                f"🆔 `{post_id}`\n"
                f"📅 `{str(post.get('created_at','?'))[:16]}`\n"
                f"🕐 Last: `{last}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👁 **Total views:** `{at}`\n\n"
                f"📂 FREE  `[{bar_f}]` {free_pct}%  (`{af}` views, `{fc}` files)\n"
                f"💎 PRO   `[{bar_p}]` {prem_pct}%  (`{ap}` views, `{pc}` files)\n\n"
                f"📈 Premium conversion: **{prem_pct}%**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh", callback_data=f"dp_analytics_{post_id}"),
                     InlineKeyboardButton("🗑 Delete",  callback_data=f"dp_delete_{post_id}")],
                    [InlineKeyboardButton("🔙 Back",    callback_data="dual_post_list")]
                ])
            )
            await cb.answer()

        elif data == "dual_help":
            await cb.message.edit(
                "🎭 **Dual Post System Guide**\n\n"
                "One link → Two different user experiences!\n\n"
                "1️⃣ `/dualpost Title` — Start a new session.\n"
                "2️⃣ Send files for **FREE** users (Stage 1).\n"
                "3️⃣ `/dpremium` — Switch to premium stage.\n"
                "4️⃣ Send files for **PREMIUM** users (Stage 2).\n"
                "5️⃣ `/dpdone` — Finalize and get your link.\n\n"
                "💎 **Premium users** get Stage 2 files directly.\n"
                "📂 **Free users** get Stage 1 files after ads.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ START NOW", callback_data="dual_post_start_new")],
                    [InlineKeyboardButton("🔙 BACK TO HELP", callback_data="help_menu")]
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
            if not can: return await cb.answer("❌ Not your post!", show_alert=True)
            del_dual_post(post_id)
            await cb.answer("🗑 Post deleted!", show_alert=True)
            await cb.message.edit(
                f"🗑 **Deleted:** `{post.get('title', post_id)}`\n"
                f"📂 Free: `{len(post.get('free_files',[]))}` | "
                f"💎 Pro: `{len(post.get('pro_files',[]))}` files removed."
            )

        # ── Admin callbacks ───────────────────────────────────────
        elif data == "dual_posts_admin":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
                return await cb.answer("❌ No access!", show_alert=True)
            posts = get_bot_dual_posts(bot_id)
            total_views = sum(p.get("access_total", 0) for p in posts)
            total_free  = sum(p.get("access_free", 0) for p in posts)
            total_pro   = sum(p.get("access_pro", 0) for p in posts)
            pct = round(total_pro / max(total_views, 1) * 100)
            await cb.message.edit(
                f"🎭 **Dual Posts Overview**\n\n"
                f"Total posts: `{len(posts)}`\n"
                f"👁 Total views: `{total_views}`\n"
                f"📂 Free views: `{total_free}`\n"
                f"💎 Premium views: `{total_pro}`\n"
                f"📈 Premium conversion: `{pct}%`\n\n"
                f"Commands:\n`/myduals` — list all posts\n`/dpstats POST_ID` — detailed analytics",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 All Posts", callback_data="dual_post_list")],
                    [InlineKeyboardButton("🔙 Admin",     callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "confirm_rebuild":
            if not is_admin(uid): return await cb.answer("❌ Admin only!", show_alert=True)
            if not SESSION_STRING: return await cb.answer("❌ SESSION_STRING not set!", show_alert=True)
            await cb.answer("🔄 Starting rebuild...", show_alert=True)
            sm = await cb.message.edit("🔄 **Smart Rebuild Starting...**")
            try:
                stats = await smart_rebuild(status_msg=sm)
                await sm.edit(
                    f"🎉 **Rebuild Complete!**\n\n"
                    f"📦 Phase 1: `{stats['phase1_restored']}/{len(BACKUP_FILES)}` restored\n"
                    f"📁 Phase 2: `{stats['phase2_files']}` files, "
                    f"`{stats['phase2_batches']}` batches, "
                    f"`{stats['phase2_duals']}` duals\n"
                    f"❌ Errors: `{stats['phase2_errors']}`"
                )
            except ValueError: pass
            except Exception as e: await sm.edit(f"❌ Failed!\n`{e}`")

        elif data == "start_batch":
            TEMP_BATCH[uid] = []
            await cb.message.edit(
                "📦 **Batch Mode**\n\nSend files. `/done` to finish.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_batch")]])
            )
            await cb.answer("Batch started!")

        elif data == "cancel_batch":
            TEMP_BATCH.pop(uid, None)
            await cb.message.edit("❌ Batch cancelled.")
            await cb.answer()

        elif data == "confirm_broadcast":
            bd = TEMP_BROADCAST.get(uid)
            if not bd: return await cb.answer("❌ Expired!", show_alert=True)
            sm = await cb.message.edit("📢 **Broadcasting...**")
            s, f = await do_broadcast(bd["bot_ids"], bd["bc_msg_id"], status_msg=sm, reply_markup=bd.get("markup"))
            TEMP_BROADCAST.pop(uid, None)
            await sm.edit(f"✅ **Done!**\n\n✅ `{s}` | ❌ `{f}` | 🤖 `{len(bd['bot_ids'])}`")

        elif data == "cancel_broadcast":
            TEMP_BROADCAST.pop(uid, None)
            await cb.message.edit("❌ Cancelled!")
            await cb.answer()

        elif data == "clone_menu":
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            await cb.message.edit(
                f"🤖 **Clone** — Your bots: `{len(ubts)}`\n\n1. @BotFather → /newbot\n2. `/clone TOKEN`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🤖 BotFather", url="https://t.me/BotFather")],
                    [InlineKeyboardButton("🔙 Back",      callback_data="back_to_start")]
                ])
            )
            await cb.answer()

        elif data == "user_dashboard":
            ud   = get_user(uid, bot_id)
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            dps  = get_user_dual_posts(bot_id, uid)
            await cb.message.edit(
                f"📊 **Dashboard**\n\n"
                f"📤 `{ud.get('files_uploaded',0) if ud else 0}` uploads | "
                f"📦 `{ud.get('batches_created',0) if ud else 0}` batches\n"
                f"🎭 `{len(dps)}` dual posts | 🤖 `{len(ubts)}` bots\n"
                f"💎 {'Premium ✅' if ud and ud.get('is_premium') else 'Free'}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
            )
            await cb.answer()

        elif data == "my_bots_menu":
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            text = f"🤖 **Your Bots ({len(ubts)})**\n\n"
            for i, b in enumerate(ubts[:10], 1):
                text += f"{i}. {'🟢' if b['bot_id'] in ACTIVE_CLIENTS else '🔴'} @{b['bot_username']}\n"
            if not ubts: text += "None!"
            await cb.message.edit(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Clone", callback_data="clone_menu")],
                    [InlineKeyboardButton("🔙 Back",  callback_data="back_to_start")]
                ])
            )
            await cb.answer()

        elif data in ("cb_search", "help_menu", "premium_menu", "referral_menu"):
            bi_cb = get_bot_info(bot_id)
            ud_cb = add_user(uid, bot_id, cb.from_user.username, cb.from_user.first_name)[0]
            is_p = (ud_cb or {}).get('is_premium')
            contact = bi_cb.get("premium_contact", "zolvid") if bi_cb else "zolvid"
            qr_id = bi_cb.get("premium_qr") if bi_cb else None

            default_help = (
                "🚀 **FileStore v7.0 — Command List**\n\n" +
                "\n".join([f"• `/{c.command}` — {c.description}" for c in BOT_COMMANDS[:15]]) +
                "\n\n*(Send /help for full list of all commands)*"
            )
            default_prem = (
                f"🌟 **ELITE PREMIUM MEMBERSHIP** 🌟\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✨ **Current Status:** {{status}}\n\n"
                f"🚀 **EXCLUSIVE PRIVILEGES:**\n"
                f" ├ ♾ **PERMANENT STORAGE:** Files never expire!\n"
                f" ├ 🎭 **ELITE ACCESS:** Unlock Premium Dual Posts!\n"
                f" ├ ⚡ **DIRECT DELIVERY:** No ads, no shorteners!\n"
                f" ├ 📦 **PRO BATCHING:** No limits on creation!\n"
                f" └ 💎 **PRIORITY SUPPORT:** Instant assistance!\n\n"
                f"💰 **Subscription Fee:** `{{price}}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👇 **WANT TO UPGRADE? CONTACT ADMIN!** 👇"
            )
            default_ref = (
                f"👥 **Refer & Earn Program**\n━━━━━━━━━━━━━━━━━━━━\n"
                f"Invite your friends and earn rewards!\n\n"
                f"📊 **Your Stats:**\n"
                f"├ Total Refers: `{{ref_count}}` users\n"
                f"└ Rewards Earned: `{{ref_rewards}}` days of Premium\n\n"
                f"🎁 **Reward:** Earn 1 day of Premium for every 5 successful refers!\n\n"
                f"🔗 **Your Referral Link:**\n"
                f"`https://t.me/{{bot_username}}?start=ref_{{uid}}`"
            )

            texts = {
                "cb_search":     get_msg_text("msg_search", "🔍 **Search**\n\nUse: `/search FILENAME`\nOr inline: `@BotUsername query`"),
                "help_menu":     get_msg_text("msg_help", default_help),
                "premium_menu":  get_msg_text("msg_premium", default_prem).format_map(SafeDict(
                    status='✅ `ACTIVATED`' if is_p else '❌ `NOT ACTIVE`',
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

            kb = [[InlineKeyboardButton(get_btn_name("btn_back", "🔙 Back"), callback_data="back_to_start")]]
            if data == "premium_menu":
                kb.insert(0, [InlineKeyboardButton(get_btn_name("btn_pcon", "👑 CONTACT ADMIN"), url=f"https://t.me/{contact}")])
                if qr_id:
                    kb.insert(1, [InlineKeyboardButton(get_btn_name("btn_pqrs", "🖼 SHOW PAYMENT QR"), callback_data="show_premium_qr")])
            elif data == "referral_menu":
                ref_link = f"https://t.me/{client.me.username}?start=ref_{uid}"
                kb.insert(0, [InlineKeyboardButton(get_btn_name("btn_invite", "📤 Invite Friends"), url=f"https://t.me/share/url?url={ref_link}")])

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
                return await cb.answer("❌ QR code not available!", show_alert=True)

            await cb.answer("🖼 Loading QR Code...")
            await cb.message.reply_photo(qr_id, caption="✨ **Scan this QR to pay for Premium** ✨\n\nAfter payment, send screenshot to admin.")

        elif data == "admin_panel":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
                return await cb.answer("❌ No access!", show_alert=True)
            await cb.message.edit("⚡ **Admin Panel**", reply_markup=kb_admin())
            await cb.answer()

        elif data == "broadcast_menu":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or uid == MAIN_ADMIN or (bi and bi.get("owner_id") == uid)):
                return await cb.answer("❌ No access!", show_alert=True)
            await cb.message.edit(
                f"📢 **Broadcast**\n\n👥 `{len(get_all_users(bot_id))}`\n\nReply to a message with `/broadcast`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]])
            )
            await cb.answer()

        elif data == "plinks_admin":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
                return await cb.answer("❌ No access!", show_alert=True)
            plinks = load_db(PLINKS_DB)
            my_links = [v for v in plinks.values() if v.get("bot_id") == bot_id]
            await cb.message.edit(
                f"🛡 **Protected Links Overview**\n\n"
                f"Total protected: `{len(my_links)}` links\n\n"
                f"**Commands:**\n"
                f"├ `/protect` - Create new protection\n"
                f"└ `/myplinks` - Manage your links\n\n"
                f"Protected links generate a fresh, 5-minute expiring invite link for every user, making it impossible to leak the real invite link.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 List My Links", callback_data="plinks_list_admin")],
                    [InlineKeyboardButton("🔙 Admin",          callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "plinks_list_admin":
            bi = get_bot_info(bot_id)
            if not (is_admin(uid) or (bi and bi.get("owner_id") == uid)):
                return await cb.answer("❌ No access!", show_alert=True)
            plinks = load_db(PLINKS_DB)
            my_links = [v for v in plinks.values() if v.get("bot_id") == bot_id]
            if not my_links:
                return await cb.answer("No protected links found!", show_alert=True)

            text = f"🛡 **Protected Links List ({len(my_links)})**\n\n"
            btns = []
            for l in my_links[:10]:
                lpid = l["lpid"]
                title = l.get("title", "Unknown")[:22]
                text += f"• **{title}** | `{lpid}`\n"
                btns.append([
                    InlineKeyboardButton(f"🔗 {title}", callback_data=f"show_plink_{lpid}"),
                    InlineKeyboardButton("🗑", callback_data=f"del_plink_{lpid}")
                ])
            btns.append([InlineKeyboardButton("🔙 Back", callback_data="plinks_admin")])
            await cb.message.edit(text, reply_markup=InlineKeyboardMarkup(btns))
            await cb.answer()

        elif data.startswith("show_plink_"):
            lpid = data[11:]
            plinks = load_db(PLINKS_DB)
            p = plinks.get(lpid)
            if not p: return await cb.answer("Not found!", show_alert=True)
            link = f"https://t.me/{client.me.username}?start=lp_{lpid}"
            await cb.message.edit(
                f"🛡 **Protected Link Details**\n\n"
                f"📢 **Channel:** `{p.get('title')}`\n"
                f"🆔 `{p['channel_id']}`\n"
                f"⚙️ **Mode:** `{p.get('mode').upper()}`\n"
                f"📅 **Created:** `{datetime.fromtimestamp(p.get('created_at')).strftime('%Y-%m-%d %H:%M')}`\n\n"
                f"🔗 **Sharable Link:**\n`{link}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={link}")],
                    [InlineKeyboardButton("🗑 Delete", callback_data=f"del_plink_{lpid}"),
                     InlineKeyboardButton("🔙 Back",   callback_data="plinks_list_admin")]
                ])
            )
            await cb.answer()

        elif data == "verify_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            vl = bi.get("verify_link") or "None"
            uc = bi.get("update_channel") or "None"
            await cb.message.edit(
                f"🛡 **Verification System**\n\n"
                f"Status: {'✅ ENABLED' if bi.get('verify_link') else '❌ DISABLED'}\n\n"
                f"🔗 **Link:** `{vl}`\n"
                f"📢 **Updates:** `{uc}`\n\n"
                f"**Settings:**\n"
                f"• `/setverify [link]` - Set link\n"
                f"• `/setupdates [link]` - Set channel\n"
                f"• `/setverify off` - Disable\n\n"
                f"Users must complete this link before using the bot.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Set Verify Link", callback_data="set_v_link"),
                     InlineKeyboardButton("📢 Set Update Ch", callback_data="set_u_link")],
                    [InlineKeyboardButton("❌ Disable System", callback_data="disable_verify")],
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "disable_verify":
            update_bot_info(bot_id, "verify_link", None)
            await cb.answer("✅ Verification system disabled!", show_alert=True)
            await cb.message.edit("⚡ **Admin Panel**", reply_markup=kb_admin())

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
                top_files_text += f"{i}. {icon} `{name}` — 👁 **{count}**\n"

            await cb.message.edit(
                f"📊 **ELITE BOT ANALYTICS**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👥 **USER METRICS**\n"
                f" ├ Total Base: `{len(users)}` users\n"
                f" ├ Active Today: `{active_today}`\n"
                f" └ Premium Members: `{premium_users}`\n\n"
                f"📁 **CONTENT METRICS**\n"
                f" ├ Total Files: `{len(bot_files)}` items\n"
                f" ├ Global Views: `{sum(f.get('access_count',0) for f in bot_files)}`\n"
                f" ├ Dual Posts: `{dp_count}` active\n"
                f" └ DP Views: `{dp_views}`\n\n"
                f"🔝 **TRENDING CONTENT (TOP 5)**\n"
                f"{top_files_text or '_No data recorded yet._'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱ **System Uptime:** `{str(datetime.now()-START_TIME).split('.')[0]}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 REFRESH DATA", callback_data="admin_stats")],
                    [InlineKeyboardButton("🎭 DUAL POSTS",  callback_data="dual_posts_admin"),
                     InlineKeyboardButton("👥 USER LIST",   callback_data="manage_users")],
                    [InlineKeyboardButton("🔙 BACK TO PANEL", callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "manage_users":
            all_u = load_db(USERS_DB)
            banned = sum(1 for u in all_u.values()
                         if u.get("bot_id") == bot_id and u.get("is_banned"))
            await cb.message.edit(
                f"👥 **Users**\n\n🟢 Active: `{len(get_all_users(bot_id))}` | 🚫 Banned: `{banned}`\n\n"
                f"`/ban ID` `/unban ID` `/info ID` `/givepremium ID`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]])
            )
            await cb.answer()

        elif data == "my_bots_admin":
            ubts = [b for b in get_all_bots().values() if isinstance(b,dict) and b.get("owner_id")==uid]
            text = f"🤖 **Your Bots ({len(ubts)})**\n\n"
            for i, b in enumerate(ubts[:15], 1):
                text += f"{i}. {'🟢' if b['bot_id'] in ACTIVE_CLIENTS else '🔴'} @{b['bot_username']}\n"
            if not ubts: text += "None!"
            await cb.message.edit(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Clone", callback_data="clone_menu")],
                    [InlineKeyboardButton("🔙 Back",  callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "bot_settings_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            t = bi.get("auto_delete_time", 600)
            await cb.message.edit(
                f"⚙️ **Bot Settings**\n\n"
                f"👋 Welcome: {'Custom ✅' if bi.get('custom_welcome') else 'Default'}\n"
                f"🖼 Image: {'Set ✅' if bi.get('welcome_image') else 'None'}\n"
                f"⏱ Timer: `{t}s` ({t//60}min)\n"
                f"✅ Auto-Approve: `{'ON' if bi.get('auto_approve') else 'OFF'}`\n"
                f"📝 Log: `{bi.get('log_channel') or 'None'}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👋 Edit Welcome",   callback_data="edit_welcome_msg")],
                    [InlineKeyboardButton("⏱ Timer",          callback_data="edit_timer"),
                     InlineKeyboardButton("📝 Log",            callback_data="set_log_info")],
                    [InlineKeyboardButton("🔙 Back",           callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "edit_timer":
            bi = get_bot_info(bot_id); curr = bi.get("auto_delete_time", 600) if bi else 600
            await cb.message.edit(
                f"⏱ **Auto-Delete Timer**\n\nCurrent: `{curr}s` ({curr//60}min)\n\nChoose a preset or send a custom value:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("1 Min", callback_data="st_60"),
                     InlineKeyboardButton("5 Min", callback_data="st_300")],
                    [InlineKeyboardButton("10 Min", callback_data="st_600"),
                     InlineKeyboardButton("30 Min", callback_data="st_1800")],
                    [InlineKeyboardButton("1 Hour", callback_data="st_3600"),
                     InlineKeyboardButton("✏️ Custom", callback_data="st_custom")],
                    [InlineKeyboardButton("🔙 Back", callback_data="bot_settings_admin")]
                ])
            )
            await cb.answer()

        elif data.startswith("st_"):
            val = data[3:]
            if val == "custom":
                TEMP_EDIT[uid] = {"mode": "set_timer_custom"}
                await cb.message.edit("⏱ **Custom Timer**\n\nSend the auto-delete time in **seconds**.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="edit_timer")]]))
            else:
                secs = int(val)
                update_bot_info(bot_id, "auto_delete_time", secs)
                await cb.answer(f"✅ Timer set to {secs}s", show_alert=True)
                cb.data = "edit_timer"
                await cb_handler(client, cb)

        elif data == "set_log_info":
            await cb.message.edit(
                "📝 `/setlog CHANNEL_ID` or `/setlog off`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="bot_settings_admin")]])
            )
            await cb.answer()

        elif data == "forcesub_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            fs   = bi.get("force_subs", [])
            text = f"🔒 **Force Subscribe** ({len(fs)}/{MAX_FORCE_SUB_CHANNELS})\n━━━━━━━━━━━━━━━━━━━━\n"
            btns = []
            for i, f in enumerate(fs, 1):
                cid = f["channel_id"] if isinstance(f, dict) else f
                text += f"**{i}.** `{cid}`\n"
                btns.append([InlineKeyboardButton(f"🗑 Remove {i}", callback_data=f"rm_fs_{cid}")])

            if not fs: text += "_No channels added yet._\n"

            text += "\n**Commands:**\n`/setfs add -100xxxx [link]`\n`/setfs clear` to remove all."

            btns.append([InlineKeyboardButton("➕ Add Channel", callback_data="add_fs_info")])
            btns.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])

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
                await cb.answer("✅ Channel removed!", show_alert=True)
                # Re-render the menu
                await cb.message.edit("🔒 **Updating...**")
                cb.data = "forcesub_admin"
                await cb_handler(client, cb)
            except Exception as e:
                await cb.answer(f"❌ Error: {e}", show_alert=True)

        elif data == "add_fs_info":
            await cb.answer("Use /setfs add -100xxxx [link] to add.", show_alert=True)

        elif data == "toggle_auto_approve":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            curr = bi.get("auto_approve", False)
            update_bot_info(bot_id, "auto_approve", not curr)
            await cb.answer(f"Auto-Approve: {'ON ✅' if not curr else 'OFF ❌'}", show_alert=True)
            await cb.message.edit("⚡ **Admin Panel**", reply_markup=kb_admin())

        elif data == "toggle_auto_caption":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            curr = bi.get("auto_caption", True)
            update_bot_info(bot_id, "auto_caption", not curr)
            await cb.answer(f"Auto Caption: {'ON ✅' if not curr else 'OFF ❌'}", show_alert=True)
            await cb.message.edit("⚡ **Admin Panel**", reply_markup=kb_admin())

        elif data == "shortener_admin":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            st = "✅ ON" if bi.get("is_shortener_enabled") else "❌ OFF"
            active = sum(1 for v in SHORTENER_TOKENS.values()
                         if not v["used"] and time.time() < v["expires_at"])
            await cb.message.edit(
                f"🔗 **Shortener Settings**\n\n"
                f"Status: {st}\n"
                f"URL: `{bi.get('shortener_url') or 'Not set'}`\n\n"
                f"**Integration with Dual Posts:**\n"
                f"• FREE tier → shortener → token → files\n"
                f"• PRO tier → always direct (no ads)\n\n"
                f"🔑 Active tokens: `{active}`\n\n"
                f"`/shortener` to configure.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]])
            )
            await cb.answer()

        elif data == "edit_welcome_msg":
            bi = get_bot_info(bot_id)
            if not bi or (bi.get("owner_id") != uid and uid != MAIN_ADMIN):
                return await cb.answer("❌ Only owner!", show_alert=True)
            TEMP_WELCOME[uid] = {"bot_id": bot_id, "step": "text"}
            curr_t = bi.get("custom_welcome") or "_(default)_"
            curr_i = "✅" if bi.get("welcome_image") else "❌"
            await cb.message.edit(
                f"👋 **Welcome Editor**\n\nCurrent text: {curr_t[:80]}\nCurrent image: {curr_i}\n\n"
                f"**Step 1/2:** Send new welcome text.\n`-skip` = keep | `-clear` = default",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_welcome")]])
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
            if uid != MAIN_ADMIN: return await cb.answer("❌ Supreme only!", show_alert=True)
            sess = "✅" if SESSION_STRING else "❌"
            await cb.message.edit(
                f"👑 **Supreme Panel v7.0**\n🔑 Session: {sess}",
                reply_markup=kb_supreme()
            )
            await cb.answer()

        elif data == "supreme_customize":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            await cb.message.edit(
                "🎨 **Supreme Customizer**\n\nChoose what you want to customize:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔘 BUTTON NAMES",   callback_data="cust_btns")],
                    [InlineKeyboardButton("📝 PANEL MESSAGES", callback_data="cust_msgs")],
                    [InlineKeyboardButton("🔙 BACK",           callback_data="supreme_panel")]
                ])
            )
            await cb.answer()

        elif data == "cust_btns":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            await cb.message.edit(
                "🔘 **Button Customizer**\n\nSelect a menu category:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 START MENU", callback_data="cbtn_cat_start")],
                    [InlineKeyboardButton("⚡ ADMIN MENU", callback_data="cbtn_cat_admin")],
                    [InlineKeyboardButton("👑 SUPREME MENU", callback_data="cbtn_cat_supreme")],
                    [InlineKeyboardButton("ℹ️ HELP & OTHERS", callback_data="cbtn_cat_other")],
                    [InlineKeyboardButton("♻️ RESET ALL",  callback_data="reset_buttons")],
                    [InlineKeyboardButton("🔙 BACK",       callback_data="supreme_customize")]
                ])
            )
            await cb.answer()

        elif data.startswith("cbtn_cat_"):
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            cat = data[9:]
            btns_config = get_global_config().get("custom_buttons", {})
            keyboard = []

            if cat == "start":
                b_list = [
                    ("btn_supreme", "👑 SUPREME PANEL"), ("btn_admin", "⚡ ADMIN PANEL"),
                    ("btn_batch", "📦 BATCH MODE"), ("btn_clone", "🤖 CLONE BOT"),
                    ("btn_dual", "🎭 DUAL POST"), ("btn_refer", "👥 REFER & EARN"),
                    ("btn_dash", "📊 DASHBOARD"), ("btn_help", "ℹ️ HELP"),
                    ("btn_prot", "🛡 PROTECT"), ("btn_srch", "🔍 SEARCH"),
                    ("btn_prem", "💎 BUY PREMIUM"), ("btn_mybt", "🎯 MY BOTS")
                ]
            elif cat == "admin":
                b_list = [
                    ("btn_abrd", "📢 BROADCAST"), ("btn_asta", "📊 ANALYTICS"),
                    ("btn_ausr", "👥 USERS"), ("btn_acln", "🤖 CLONES"),
                    ("btn_aset", "⚙️ SETTINGS"), ("btn_afsb", "🔒 FORCE SUB"),
                    ("btn_aver", "🛡 VERIFICATION"), ("btn_ashr", "🔗 SHORTENER"),
                    ("btn_aprt", "🛡 PROTECT LINKS"), ("btn_adul", "🎭 DUAL POSTS"),
                    ("btn_awlc", "👋 WELCOME MSG"), ("btn_aapr", "✅ AUTO APPROVE"),
                    ("btn_acap", "📝 AUTO CAPTION"), ("btn_atmr", "⏱ TIMER SET")
                ]
            elif cat == "supreme":
                b_list = [
                    ("btn_sgbr", "🌍 GLOBAL BROADCAST"), ("btn_ssys", "🖥 SYSTEM ANALYTICS"),
                    ("btn_snet", "🤖 BOT NETWORK"), ("btn_sadm", "👑 ADMIN MANAGER"),
                    ("btn_smsg", "📢 SYSTEM MSG"), ("btn_smnt", "🛠 MAINT: ON/OFF"),
                    ("btn_sbak", "💾 FULL BACKUP"), ("btn_spur", "🧹 PURGE CACHE"),
                    ("btn_srbd", "🔄 SMART REBUILD"), ("btn_scus", "🎨 CUSTOMIZE BUTTONS"),
                    ("btn_srst", "♻️ SYSTEM RESTART")
                ]
            else: # other
                b_list = [
                    ("btn_back", "🔙 BACK TO HOME"), ("btn_hdual", "🎭 DUAL POST GUIDE"),
                    ("btn_hprem", "💎 PREMIUM INFO"), ("btn_pcon", "👑 CONTACT ADMIN"),
                    ("btn_pqrs", "🖼 SHOW PAYMENT QR"), ("btn_invite", "📤 Invite Friends")
                ]

            for i in range(0, len(b_list), 2):
                row = []
                key, def_val = b_list[i]
                row.append(InlineKeyboardButton(f"{btns_config.get(key, def_val)}", callback_data=f"editbtn_{key}"))
                if i + 1 < len(b_list):
                    key2, def_val2 = b_list[i+1]
                    row.append(InlineKeyboardButton(f"{btns_config.get(key2, def_val2)}", callback_data=f"editbtn_{key2}"))
                keyboard.append(row)

            keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="cust_btns")])
            await cb.message.edit(f"🔘 **Customize {cat.upper()} Buttons**\n\nClick a button to rename it:", reply_markup=InlineKeyboardMarkup(keyboard))
            await cb.answer()

        elif data == "cust_msgs":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            msgs_config = get_global_config().get("custom_messages", {})
            m_list = [
                ("msg_welcome", "👋 Welcome Message"), ("msg_help", "ℹ️ Help Message"),
                ("msg_premium", "💎 Premium Message"), ("msg_referral", "👥 Referral Message"),
                ("msg_search", "🔍 Search Message"), ("msg_admin", "⚡ Admin Panel"),
                ("msg_supreme", "👑 Supreme Panel")
            ]
            keyboard = []
            for key, label in m_list:
                status = "✅ Set" if key in msgs_config else "⚪ Default"
                keyboard.append([InlineKeyboardButton(f"{label} ({status})", callback_data=f"editmsg_{key}")])

            keyboard.append([InlineKeyboardButton("♻️ RESET ALL",  callback_data="reset_messages")])
            keyboard.append([InlineKeyboardButton("🔙 BACK",       callback_data="supreme_customize")])

            await cb.message.edit("📝 **Panel Message Customizer**\n\nSelect a message to edit:", reply_markup=InlineKeyboardMarkup(keyboard))
            await cb.answer()

        elif data.startswith("editbtn_"):
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            key = data[8:]
            TEMP_EDIT[uid] = {"mode": "customize_button", "key": key}
            await cb.message.edit(
                f"📝 **Customize Button**\n\nKey: `{key}`\n\nSend the **new name** for this button.\n`/cancel` to abort.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data="cust_btns")]])
            )
            await cb.answer()

        elif data.startswith("editmsg_"):
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            key = data[8:]
            TEMP_EDIT[uid] = {"mode": "customize_message", "key": key}

            placeholders = ""
            if key == "msg_welcome": placeholders = "\n\nAvailable: `{name}`, `{username}`"
            elif key == "msg_premium": placeholders = "\n\nAvailable: `{status}`, `{price}`, `{contact}`"
            elif key == "msg_referral": placeholders = "\n\nAvailable: `{ref_count}`, `{ref_rewards}`, `{bot_username}`, `{uid}`"
            elif key == "msg_supreme": placeholders = "\n\nAvailable: `{bots}`, `{users}`, `{files}`, `{duals}`, `{sess}`"

            await cb.message.edit(
                f"📝 **Edit Panel Message**\n\nKey: `{key}`{placeholders}\n\nSend the **new text** for this message.\nUse `-clear` to reset to default.\n`/cancel` to abort.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data="cust_msgs")]])
            )
            await cb.answer()

        elif data == "reset_messages":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            update_global_config("custom_messages", {})
            await cb.answer("✅ All messages reset to default!", show_alert=True)
            cb.data = "cust_msgs"
            await cb_handler(client, cb)

        elif data.startswith("cbtn_"):
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            key = data[5:]
            TEMP_EDIT[uid] = {"mode": "customize_button", "key": key}
            await cb.message.edit(
                f"📝 **Customize Button**\n\nKey: `{key}`\n\nSend the **new name** for this button.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data="supreme_customize")]])
            )
            await cb.answer()

        elif data == "reset_buttons":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            update_global_config("custom_buttons", {})
            await cb.answer("✅ All buttons reset to default!", show_alert=True)
            cb.data = "cust_btns"
            await cb_handler(client, cb)

        elif data == "global_broadcast":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            await cb.message.edit(
                f"🌍 **Global Broadcast**\n\n👥 `{len(get_all_users())}` | 🤖 `{len(ACTIVE_CLIENTS)}`\n\nReply to a message with `/broadcast`.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="supreme_panel")]])
            )
            await cb.answer()

        elif data == "system_stats":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            t, u, f = shutil.disk_usage("/")
            pend    = sum(len(v) for v in _PENDING.values())
            sess    = "✅ ACTIVATED" if SESSION_STRING else "❌ NOT SET"
            active_tokens = sum(1 for v in SHORTENER_TOKENS.values()
                                if not v["used"] and time.time() < v["expires_at"])
            dp_count = len(load_db(DUAL_POST_DB))
            await cb.message.edit(
                f"🖥 **ELITE SUPREME SYSTEM METRICS**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🤖 **NETWORK STATUS**\n"
                f" ├ Registered Bots: `{len(get_all_bots())}`\n"
                f" └ Active Instances: `{len(ACTIVE_CLIENTS)}` online\n\n"
                f"📊 **GLOBAL DATABASE**\n"
                f" ├ Total Users: `{len(load_db(USERS_DB))}`\n"
                f" ├ Total Files: `{len(load_db(FILES_DB))}`\n"
                f" └ Dual Posts: `{dp_count}`\n\n"
                f"⚙️ **SYSTEM CORE**\n"
                f" ├ Pending Requests: `{pend}`\n"
                f" ├ Active Tokens: `{active_tokens}`\n"
                f" └ Session String: `{sess}`\n\n"
                f"💾 **SERVER STORAGE**\n"
                f" ├ Used Space: `{u//(2**30)} GB`\n"
                f" ├ Total Space: `{t//(2**30)} GB`\n"
                f" └ Free Space: `{f//(2**30)} GB`\n\n"
                f"⏱ **UPTIME:** `{str(datetime.now()-START_TIME).split('.')[0]}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 REFRESH SYSTEM", callback_data="system_stats")],
                    [InlineKeyboardButton("🔙 BACK TO PANEL",  callback_data="supreme_panel")]
                ])
            )
            await cb.answer()

        elif data == "all_bots_list":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            ab = get_all_bots()
            text = f"🤖 **All Bots ({len(ab)})**\n\n"
            for i, (k, b) in enumerate(list(ab.items())[:20], 1):
                if isinstance(b, dict):
                    text += f"{i}. {'🟢' if int(k) in ACTIVE_CLIENTS else '🔴'} @{b['bot_username']} — {b.get('owner_name','?')}\n"
            if len(ab) > 20: text += f"\n...+{len(ab)-20} more"
            await cb.message.edit(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="supreme_panel")]])
            )
            await cb.answer()

        elif data == "manage_admins":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            admins = load_db(ADMINS_DB)
            text   = f"👑 **Admins**\n\n🌟 Main: `{MAIN_ADMIN}`\n\nSecondary ({len(admins)}):\n"
            for aid in admins: text += f"• `{aid}`\n"
            text += "\n`/addadmin ID` `/deladmin ID`"
            await cb.message.edit(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="supreme_panel")]])
            )
            await cb.answer()

        elif data == "toggle_maintenance":
            if uid != MAIN_ADMIN: return await cb.answer("❌", show_alert=True)
            curr = get_global_config().get("maintenance", False)
            update_global_config("maintenance", not curr)
            await cb.answer(f"Maintenance: {'ON ⚠️' if not curr else 'OFF ✅'}", show_alert=True)
            await cb.message.edit("👑 **Supreme Panel**", reply_markup=kb_supreme())

        elif data == "global_msg_set":
            if uid != MAIN_ADMIN: return await cb.answer()
            await cb.message.edit(
                "📢 `/setglobal MESSAGE` or `/setglobal off`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="supreme_panel")]])
            )
            await cb.answer()

        elif data == "manual_backup":
            if uid != MAIN_ADMIN: return await cb.answer()
            await cb.answer("⏳ Backing up...", show_alert=True)
            asyncio.create_task(do_backup())

        elif data == "manual_clean_cache":
            if uid != MAIN_ADMIN: return await cb.answer()
            count = clean_expired_cache()
            expired_tokens = clean_expired_tokens()
            await cb.answer(f"🧹 Cleaned {count} cache + {expired_tokens} tokens!", show_alert=True)

        elif data == "restart_all_bots":
            if uid != MAIN_ADMIN: return await cb.answer()
            await cb.answer("♻️ Restarting...", show_alert=True)
            os.execl(sys.executable, sys.executable, *sys.argv)

        elif data.startswith("confirm_import_"):
            if uid != MAIN_ADMIN: return await cb.answer("❌ Only Supreme Admin!", show_alert=True)
            fname = data[15:]
            if fname not in BACKUP_FILES: return await cb.answer("Invalid file!", show_alert=True)

            # Find the message with the document
            msg = cb.message.reply_to_message
            if not msg:
                # Attempt to fetch it manually if it's not cached in the callback object
                try:
                    msg = await client.get_messages(cb.message.chat.id, cb.message.reply_to_message_id)
                except Exception:
                    msg = None

            if not msg or not msg.document or msg.document.file_name != fname:
                return await cb.message.edit("❌ **Error:** Original file message not found. Please send the file again.")

            await cb.answer(f"⏳ Restoring {fname}...", show_alert=True)
            await cb.message.edit(f"⏳ **Restoring `{fname}`... Please wait.**")

            try:
                path = await msg.download(file_name=f"{DB_FOLDER}/{fname}.new")
                if path:
                    # Validate JSON
                    with open(path, "r") as f:
                        json.load(f)

                    # Replace old file
                    old_path = f"{DB_FOLDER}/{fname}"
                    if os.path.exists(old_path):
                        os.replace(path, old_path)
                    else:
                        os.rename(path, old_path)

                    invalidate_cache(old_path)
                    await cb.message.edit(f"✅ **Database Restored!**\n\nFile `{fname}` has been successfully updated.\n\nRestarting system to apply changes...")
                    await asyncio.sleep(2)
                    os.execl(sys.executable, sys.executable, *sys.argv)
                else:
                    await cb.message.edit("❌ **Download failed!**")
            except Exception as e:
                await cb.message.edit(f"❌ **Restore Error:**\n`{e}`")

        elif data == "cancel_import":
            await cb.message.edit("❌ Import cancelled.")
            await cb.answer()

        elif data == "back_to_start":
            bi  = get_bot_info(bot_id)
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
                await cb.message.edit("👋 **Welcome Back!**", reply_markup=kbd)
            await cb.answer()

        else:
            await cb.answer()


# ═══════════════════════════════════════════════════════════════
# 🔧 HELPERS
# ═══════════════════════════════════════════════════════════════

async def _auto_delete(msg, delay: int):
    await asyncio.sleep(delay)
    try: await msg.delete()
    except Exception: pass

# ═══════════════════════════════════════════════════════════════
# ⏰ BACKGROUND TASKS
# ═══════════════════════════════════════════════════════════════

async def background_tasks():
    cycle = 0
    while True:
        await asyncio.sleep(600)
        cycle += 1
        try:
            USER_FLOOD.clear()
            n = clean_expired_cache()
            if n: logger.info(f"🗑 Cleaned {n} cache entries")
            t = clean_expired_tokens()
            if t: logger.info(f"🔑 Cleaned {t} expired tokens")
            await do_backup()
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
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  🚀 ULTRA FILESTORE BOT v7.0 — ELITE EDITION             ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    if DB_CHANNEL == -1000000000000:
        logger.error("❌ DB_CHANNEL not configured!"); return

    _load_pending()
    logger.info(f"📋 Loaded pending requests for {len(_PENDING)} channels")
    logger.info(f"🔑 SESSION_STRING: {'✅ Set' if SESSION_STRING else '❌ Not set'}")

    await start_web_server()

    if SESSION_STRING:
        try:
            global GLOBAL_USERBOT
            GLOBAL_USERBOT = Client(
                "global_userbot", api_id=API_ID, api_hash=API_HASH,
                session_string=SESSION_STRING, in_memory=True
            )
            await GLOBAL_USERBOT.start()
            logger.info("✅ Persistent Userbot Started!")
        except Exception as e:
            logger.error(f"❌ Userbot failed to start: {e}")

    logger.info("🔥 Starting Main Bot...")
    main_app = await start_bot(MAIN_BOT_TOKEN)
    if not main_app:
        logger.error("❌ Main bot failed!"); return

    # Check if bots.json exists and has data, if not, try to rebuild
    if not os.path.exists(BOTS_DB) or os.path.getsize(BOTS_DB) < 5:
        logger.warning("⚠️ Bots database missing or empty! Attempting auto-restore...")
        if SESSION_STRING:
            try:
                await smart_rebuild()
                logger.info("✅ Auto-restore complete!")
            except Exception as e:
                logger.error(f"❌ Auto-restore failed: {e}")
        else:
            logger.error("❌ SESSION_STRING missing! Cannot auto-restore bots.")

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
            logger.info(f"✅ {ok}/{len(tasks)} clone bots started")

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║         ✅ ALL SYSTEMS OPERATIONAL v7.0 ✅                ║")
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
    if _HTTP and not _HTTP.closed: await _HTTP.close()
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
