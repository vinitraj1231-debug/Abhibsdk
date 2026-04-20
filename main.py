"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 ULTRA ADVANCED FILESTORE BOT v6.0 — ELITE EDITION
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
✅ CLONE + REFERRAL + PREMIUM + ANALYTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, sys, json, asyncio, hashlib, logging, random, shutil, time
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
MAIN_ADMIN     = int(os.environ.get("MAIN_ADMIN",     "8756786934"))
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
    "pending_requests.json","dual_posts.json"
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
    BotCommand("givepremium", "💎 Give Premium (Admin)"),
    BotCommand("removepremium", "❌ Remove Premium (Admin)"),
    BotCommand("shortener",   "🔗 URL Shortener"),
    BotCommand("setlog",      "📝 Log Channel"),
    BotCommand("setchannel",  "📢 Connect Channel"),
    BotCommand("setmode",     "⚙️ Set Join Mode"),
    BotCommand("rebuild",     "🔄 Rebuild DB from channel"),
    BotCommand("backup",      "💾 Force backup now"),
    BotCommand("restart",     "♻️ Restart (Supreme)"),
    BotCommand("ping",        "🏓 Ping"),
    BotCommand("listfiles",   "📋 List files"),
    BotCommand("editfile",    "✏️ Edit file"),
    BotCommand("delfile",     "🗑 Delete file"),
    BotCommand("setwelcome",  "👋 Set welcome message"),
    # ── DUAL POST ──────────────────────────────────────────
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
            "is_premium": False
        }
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
        "connected_channel": None,
        "join_method": "direct", # direct, requested, approval
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
    if not name: return "📁"
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
#
# Ek link → 2 alag experiences:
#
#  FREE  TIER  → Non-premium users
#               → Shortener ads (agar configured ho)
#               → Auto-delete files
#               → Limited content
#
#  PRO   TIER  → Premium users
#               → Direct delivery, no ads
#               → No auto-delete
#               → Full/exclusive content
#
# Creator workflow:
#   /dualpost [title]    → free tier stage start
#   (files bhejo)        → free tier mein add hote hain
#   /dpremium            → pro tier stage switch
#   (files bhejo)        → pro tier mein add hote hain
#   /dpdone              → finalize + link generate
#
# Link format: ?start=dp_POSTID
# Token flow:  ?start=dp_POSTID_t_TOKEN  (shortener ke baad)
# ═══════════════════════════════════════════════════════════════

class DualPostSession:
    """Active dual post creation state for one user."""
    def __init__(self, bot_id: int, created_by: int, title: str = None):
        self.bot_id      = bot_id
        self.created_by  = created_by
        self.free_files  = []     # list of file unique_ids (free tier)
        self.pro_files   = []     # list of file unique_ids (premium tier)
        self.stage       = "free" # "free" | "pro"
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
        # Analytics
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
    """Increment view counters for a dual post."""
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

SHORTENER_TOKENS: dict = {}  # {token: {...}}

def generate_token(uid: int, bot_id: int, resource_id: str) -> str:
    raw = f"{uid}:{bot_id}:{resource_id}:{time.time()}:{random.randint(0, 999999)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]

def store_token(token: str, uid: int, bot_id: int, resource_id: str, rtype: str = "file"):
    """rtype: 'file' | 'batch' | 'dual'"""
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
    """
    Generate token → build bot deep link → shorten it.
    rtype: 'file' | 'batch' | 'dual'
    """
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
    client = bot_client or next(
        (d["app"] for d in ACTIVE_CLIENTS.values() if d.get("is_main")), None
    )
    if not client: return 0
    count = 0
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
    caption    = file_data.get("caption") or None
    thumb_fid  = file_data.get("custom_thumbnail")
    media_type = file_data.get("media_type", "document")
    file_id    = file_data["file_id"]
    db_msg_id  = file_data.get("db_msg_id")

    # 1. Custom Thumbnail
    if thumb_fid and media_type in ("document", "video", "audio"):
        try:
            thumb_io = await client.download_media(thumb_fid, in_memory=True)
            thumb_io.seek(0)
            if media_type == "document":
                return await client.send_document(chat_id, document=file_id,
                                                  thumb=thumb_io, caption=caption)
            elif media_type == "video":
                return await client.send_video(chat_id, video=file_id,
                                               thumb=thumb_io, caption=caption)
            elif media_type == "audio":
                return await client.send_audio(chat_id, audio=file_id,
                                               thumb=thumb_io, caption=caption)
        except Exception as e:
            logger.warning(f"Thumb delivery: {e}")

    # 2. DB Channel copy
    if db_msg_id:
        try:
            return await client.copy_message(
                chat_id=chat_id, from_chat_id=DB_CHANNEL,
                message_id=db_msg_id, caption=caption
            )
        except Exception as e:
            logger.warning(f"DB copy: {e}")

    # 3. Cache copy
    cached = get_from_cache(file_id)
    if cached and cached["bot_id"] in ACTIVE_CLIENTS:
        try:
            ca = ACTIVE_CLIENTS[cached["bot_id"]]["app"]
            return await ca.copy_message(chat_id, cached["chat_id"],
                                         cached["message_id"], caption=caption)
        except Exception as e:
            logger.warning(f"Cache delivery: {e}")

    # 4. send_cached_media fallback
    if file_id:
        return await client.send_cached_media(
            chat_id=chat_id, file_id=file_id,
            caption=caption or f"📁 {file_data.get('file_name', 'File')}"
        )
    return None

async def deliver_batch_files(client, chat_id: int, file_ids: list,
                               bot_id: int, is_premium: bool) -> tuple:
    """Deliver multiple files. Returns (sent_count, total)."""
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

async def do_broadcast(bot_ids: list, bc_msg_id: int, status_msg=None) -> tuple:
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
                await app.copy_message(uid, DB_CHANNEL, bc_msg_id)
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
TEMP_BATCH:     dict = {}
TEMP_BROADCAST: dict = {}
TEMP_EDIT:      dict = {}
TEMP_WELCOME:   dict = {}
TEMP_DUAL:      dict = {}   # uid → DualPostSession
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

def kb_start(bot_id, user_id):
    bi = get_bot_info(bot_id)
    is_owner = bi and bi.get("owner_id") == user_id
    rows = []
    if user_id == MAIN_ADMIN:
        rows.append([InlineKeyboardButton("👑 SUPREME PANEL", callback_data="supreme_panel")])
    if is_admin(user_id) or is_owner:
        rows.append([InlineKeyboardButton("⚡ ADMIN PANEL", callback_data="admin_panel")])
    rows += [
        [InlineKeyboardButton("📦 BATCH",      callback_data="start_batch"),
         InlineKeyboardButton("🤖 CLONE",      callback_data="clone_menu")],
        [InlineKeyboardButton("🎭 DUAL POST",  callback_data="dual_post_menu"),
         InlineKeyboardButton("📊 DASHBOARD",  callback_data="user_dashboard")],
        [InlineKeyboardButton("🎁 REFERRAL",   callback_data="referral_menu"),
         InlineKeyboardButton("🎯 MY BOTS",    callback_data="my_bots_menu")],
        [InlineKeyboardButton("💎 PREMIUM",    callback_data="premium_menu"),
         InlineKeyboardButton("🔍 SEARCH",     callback_data="cb_search")],
        [InlineKeyboardButton("ℹ️ HELP",        callback_data="help_menu")],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 BROADCAST",   callback_data="broadcast_menu"),
         InlineKeyboardButton("📊 STATS",       callback_data="admin_stats")],
        [InlineKeyboardButton("👥 USERS",        callback_data="manage_users"),
         InlineKeyboardButton("🤖 CLONES",       callback_data="my_bots_admin")],
        [InlineKeyboardButton("⚙️ SETTINGS",     callback_data="bot_settings_admin"),
         InlineKeyboardButton("🔒 FORCE SUB",    callback_data="forcesub_admin")],
        [InlineKeyboardButton("🔗 SHORTENER",    callback_data="shortener_admin"),
         InlineKeyboardButton("⏱ TIMER",         callback_data="edit_timer")],
        [InlineKeyboardButton("👋 WELCOME MSG",  callback_data="edit_welcome_msg"),
         InlineKeyboardButton("✅ AUTO APPROVE", callback_data="toggle_auto_approve")],
        [InlineKeyboardButton("🎭 DUAL POSTS",   callback_data="dual_posts_admin")],
        [InlineKeyboardButton("🔙 HOME",          callback_data="back_to_start")],
    ])

def kb_supreme():
    maint = get_global_config().get("maintenance", False)
    sess  = "✅" if SESSION_STRING else "❌"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 GLOBAL BC",    callback_data="global_broadcast"),
         InlineKeyboardButton("🖥 SYS STATS",    callback_data="system_stats")],
        [InlineKeyboardButton("🤖 ALL BOTS",      callback_data="all_bots_list"),
         InlineKeyboardButton("👑 ADMINS",         callback_data="manage_admins")],
        [InlineKeyboardButton(f"🛠 MAINT: {'ON ⚠️' if maint else 'OFF ✅'}",
                              callback_data="toggle_maintenance"),
         InlineKeyboardButton("📢 GLOBAL MSG",    callback_data="global_msg_set")],
        [InlineKeyboardButton("💾 BACKUP NOW",     callback_data="manual_backup"),
         InlineKeyboardButton("🧹 CLEAN CACHE",   callback_data="manual_clean_cache")],
        [InlineKeyboardButton(f"🔄 REBUILD DB (Session:{sess})",
                              callback_data="confirm_rebuild")],
        [InlineKeyboardButton("♻️ RESTART",        callback_data="restart_all_bots"),
         InlineKeyboardButton("🔙 HOME",           callback_data="back_to_start")],
    ])

def kb_dual_post_creator(stage: str, free_count: int, pro_count: int):
    """Keyboard shown while creating a dual post."""
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
        [InlineKeyboardButton("🗑 Delete",    callback_data=f"del_file_{uid}"),
         InlineKeyboardButton("📤 Get File", callback_data=f"get_file_{uid}")],
        [InlineKeyboardButton("🔙 Back",      callback_data="my_files_back")],
    ])

# ═══════════════════════════════════════════════════════════════
# 📝 HANDLERS
# ═══════════════════════════════════════════════════════════════

def register_handlers(app: Client):

    # ── FLOOD CONTROL ────────────────────────────────────────────
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

    # ── /restart ─────────────────────────────────────────────────
    @app.on_message(filters.command("restart") & filters.private, group=1)
    async def restart_cmd(client, message):
        if message.from_user.id != MAIN_ADMIN: return
        await message.reply("♻️ Restarting...")
        os.execl(sys.executable, sys.executable, *sys.argv)

    # ── /backup ───────────────────────────────────────────────────
    @app.on_message(filters.command("backup") & filters.private, group=1)
    async def backup_cmd(client, message):
        uid = message.from_user.id
        if not is_admin(uid): return await message.reply("❌ Admin only!")
        sm = await message.reply("💾 **Backing up all databases...**")
        count = await do_backup(client)
        await sm.edit(
            f"✅ **Backup Complete!**\n\n"
            f"📦 Files backed up: `{count}/{len(BACKUP_FILES)}`\n"
            f"📅 `{datetime.now():%Y-%m-%d %H:%M:%S}`"
        )

    # ── /rebuild ─────────────────────────────────────────────────
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
        """
        Start creating a dual-tier post.
        Usage: /dualpost [Title of the post]
        """
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
        """Switch dual post session to premium-tier file collection."""
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
        """Finalize dual post and generate the shareable link."""
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

        # Save metadata for rebuild
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

        # Summary for all posts
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

    # ── /start (main handler with dual post deep links) ────────────
    @app.on_message(filters.command("start") & filters.private, group=1)
    async def start_handler(client, message):
        uid    = message.from_user.id
        bot_id = client.me.id
        cfg    = get_global_config()

        if cfg.get("maintenance") and uid != MAIN_ADMIN:
            return await message.reply("🚧 **Maintenance Mode** — Bot is temporarily down.")
        if is_user_banned(uid, bot_id):
            return await message.reply("🚫 You are banned!")

        deep   = message.command[1] if len(message.command) > 1 else ""
        ref_by = None
        if deep.startswith("ref_"):
            try:
                r = int(deep[4:])
                if r != uid: ref_by = r
            except ValueError:
                pass

        user_data, is_new = add_user(uid, bot_id, message.from_user.username,
                                      message.from_user.first_name, ref_by)
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

        # ── Deep link: Join Channel (expiring link) ──────────────
        if deep == "join":
            chid = bi.get("connected_channel") if bi else None
            if not chid:
                return await message.reply("❌ No channel connected to this bot!")
            
            mode = bi.get("join_method", "direct")
            req_approval = (mode == "approval")
            
            try:
                invite = await client.create_chat_invite_link(
                    chid, 
                    expire_date=datetime.now() + timedelta(minutes=5),
                    creates_join_request=req_approval
                )
                
                await message.reply(
                    f"🔗 **Your Temporary Join Link**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"✨ This link will expire in **5 minutes**.\n"
                    f"📢 Channel: `{chid}`\n"
                    f"⚙️ Mode: `{mode.capitalize()}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👇 **Click the button below to join** 👇",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 JOIN CHANNEL NOW", url=invite.invite_link)]
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
            files[fuid]["access_count"] = files[fuid].get("access_count", 0) + 1
            save_db(FILES_DB, files)
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
                files[fuid]["access_count"] = files[fuid].get("access_count", 0) + 1
                save_db(FILES_DB, files)
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

            files[fuid]["access_count"] = files[fuid].get("access_count", 0) + 1
            save_db(FILES_DB, files)
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

        # ════════════════════════════════════════════════════════
        # ── Deep link: DUAL POST ──────────────────────────────
        # Format: dp_POSTID  OR  dp_POSTID_t_TOKEN (from shortener)
        # ════════════════════════════════════════════════════════

        elif deep.startswith("dp_"):
            raw_deep = deep[3:]  # strip "dp_"

            # Check if token is embedded
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

            # ── PREMIUM USER → Always gets PRO tier directly ────
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

            # ── FREE USER ────────────────────────────────────────
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

            # Token already validated (coming back from shortener)
            if token_val:
                td = validate_token(token_val, uid, bot_id)
                if not td or td.get("resource_id") != actual_pid:
                    # Token expired — generate fresh
                    if use_short:
                        short_link = await make_shortener_link(client, bi, uid, bot_id, actual_pid, "dual")
                        return await message.reply(
                            "⏱ **Link Expired!** Get a fresh one:",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("🔗 Get Fresh Link", url=short_link)],
                                [InlineKeyboardButton("💎 Get Premium (Skip Ads)", callback_data="premium_menu")]
                            ])
                        )
                    # No shortener — deliver directly
                else:
                    # Valid token — deliver free files
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

            # No token yet — decide route
            if use_short:
                # Generate token + shorten
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
                # No shortener — deliver free files directly
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
            welcome_text = (
                f"✨ **{'Welcome' if is_new else 'Welcome Back'}, {message.from_user.first_name}!**\n\n"
                f"🚀 **FileStore Bot v6.0**\n\n"
                f" ├ 📂 Unlimited Cloud Storage\n"
                f" ├ 📦 Batch Mode (many files → 1 link)\n"
                f" ├ 🎭 Dual Post (FREE + PREMIUM in one link)\n"
                f" ├ ✏️ Caption & Thumbnail Editor\n"
                f" ├ 🤖 Bot Cloning System\n"
                f" └ ⚡ Smart Auto-Destruct"
            )

        kbd = kb_start(bot_id, uid)
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
        await message.reply("⚡ **Admin Panel**", reply_markup=kb_admin())

    # ── /supreme ──────────────────────────────────────────────────
    @app.on_message(filters.command("supreme") & filters.private, group=1)
    async def supreme_cmd(client, message):
        if message.from_user.id != MAIN_ADMIN: return
        sess = "✅ Set" if SESSION_STRING else "❌ Not Set"
        await message.reply(
            f"👑 **Supreme Panel v6.0**\n\n"
            f"🤖 Bots: `{len(ACTIVE_CLIENTS)}` | 👥 Users: `{len(load_db(USERS_DB))}`\n"
            f"📁 Files: `{len(load_db(FILES_DB))}` | 🎭 Duals: `{len(load_db(DUAL_POST_DB))}`\n"
            f"🔑 Session: {sess}",
            reply_markup=kb_supreme()
        )

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
                f"📢 **Broadcast**\n\n🤖 Bots: `{len(target_bots)}` | 👥 Users: `{total}`\n\nReply to a message with `/broadcast`."
            )
        sm = await message.reply("⏳ Storing broadcast...")
        bc_msg_id = await store_broadcast(client, message.reply_to_message)
        if not bc_msg_id:
            return await sm.edit("❌ Failed to store!")
        TEMP_BROADCAST[uid] = {"bc_msg_id": bc_msg_id, "bot_ids": target_bots}
        total = sum(len(get_all_users(bid)) for bid in target_bots)
        await sm.edit(
            f"⚠️ **Confirm Broadcast?**\n\n🤖 `{len(target_bots)}` bots | 👥 `{total}` users",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Send!", callback_data="confirm_broadcast"),
                 InlineKeyboardButton("❌ Cancel",     callback_data="cancel_broadcast")]
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
        cancelled = []
        if b is not None: cancelled.append("Batch")
        if e is not None: cancelled.append("File Edit")
        if w is not None: cancelled.append("Welcome Edit")
        if d is not None:
            cancelled.append(f"Dual Post ({len(d.free_files)}F+{len(d.pro_files)}P)")
        if cancelled:
            await message.reply(f"❌ Cancelled: {', '.join(cancelled)}")
        else:
            await message.reply("Nothing to cancel.")

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
                f"👤 **User Info**\n🆔 `{u["user_id"]}`\n"
                f"🏷 {u.get("name","?")} | @{u.get("username") or "None"}\n"
                f"🚫 Banned: {u.get("is_banned",False)} | 💎 Premium: {u.get("is_premium",False)}\n"
                f"📤 Uploaded: `{u.get("files_uploaded",0)}`"
            )

    @app.on_message(filters.command("setprice") & filters.private, group=1)
    async def setprice_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN): return await message.reply("❌ Access Denied!")
        if len(message.command)<2:
            curr=bi.get("premium_price","500")
            return await message.reply(f"💰 Current Price: `{curr}`\n`/setprice AMOUNT` (e.g. 500 or 5$)")
        price = message.text.split(None, 1)[1].strip()
        update_bot_info(bot_id, "premium_price", price)
        await message.reply(f"✅ Premium price set to: `{price}`")

    @app.on_message(filters.command("setchannel") & filters.private, group=1)
    async def setchannel_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN): return await message.reply("❌ Access Denied!")
        if len(message.command)<2: return await message.reply(f"📢 Channel: `{bi.get("connected_channel") or "None"}`\n`/setchannel ID` or off")
        if message.command[1].lower()=="off":
            update_bot_info(bot_id,"connected_channel",None); return await message.reply("✅ Disabled!")
        try:
            chid = int(message.command[1])
            await client.get_chat(chid)
            update_bot_info(bot_id,"connected_channel",chid)
            await message.reply(f"✅ Channel connected: `{chid}`")
        except Exception as e: await message.reply(f"❌ Error: `{e}`")

    @app.on_message(filters.command("setmode") & filters.private, group=1)
    async def setmode_cmd(client, message):
        uid=message.from_user.id; bot_id=client.me.id; bi=get_bot_info(bot_id)
        if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN): return await message.reply("❌ Access Denied!")
        modes = ["direct", "requested", "approval"]
        if len(message.command)<2: 
            return await message.reply(f"⚙️ Join Mode: `{bi.get("join_method","direct")}`\nAvailable: `direct`, `requested`, `approval`\nUsage: `/setmode [mode]`")
        mode = message.command[1].lower()
        if mode not in modes: return await message.reply(f"❌ Invalid mode! Use: {", ".join(modes)}")
        update_bot_info(bot_id, "join_method", mode)
        await message.reply(f"✅ Join mode set to: `{mode}`")

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
        if not bi or (bi.get("owner_id")!=uid and uid!=MAIN_ADMIN): return await message.reply("❌ Access Denied!")
        if len(message.command)<2: return await message.reply(f"📝 Log: `{bi.get('log_channel') or 'None'}`\n`/setlog ID` or off")
        if message.command[1].lower()=="off":
            update_bot_info(bot_id,"log_channel",None); return await message.reply("✅ Disabled!")
        try:
            update_bot_info(bot_id,"log_channel",int(message.command[1]))
            await message.reply("✅ Log channel set!")
        except ValueError: await message.reply("❌ Invalid ID!")

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
                f"🤖 **Clone** — Your bots: `{len(ubts)}`\n\n1. @BotFather → /newbot\n2. `/clone TOKEN`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🤖 BotFather",url="https://t.me/BotFather")]]))
        token=message.command[1]
        for b in get_all_bots().values():
            if isinstance(b,dict) and b.get("token")==token: return await message.reply("❌ Already registered!")
        sm=await message.reply("🔄 Cloning...")
        try:
            na=await start_bot(token,parent_bot_id=bot_id)
            if na:
                me=await na.get_me()
                save_bot_info(token,me.id,me.username,uid,message.from_user.first_name,bot_id)
                await sm.edit(f"✅ **Cloned!**\n🤖 @{me.username} | `{me.id}`",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Open",url=f"https://t.me/{me.username}")]]))
            else: await sm.edit("❌ Failed! Invalid token?")
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
            await message.reply(
                    f"👑 **ULTRA PREMIUM EXPERIENCE**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Status: {'💎 **ACTIVE**' if (get_user(uid,bot_id) or {}).get('is_premium') else '🆓 **FREE**'}\n\n"
                    f"✨ **Exclusive Elite Perks:\n"
                    f" ├ 🚀 **Permanent Storage:** No auto-delete!\n"
                    f" ├ 🎭 **Elite Access:** Premium Dual Posts!\n"
                    f" ├ ⚡ **Direct Link:** No Ads / Shorteners!\n"
                    f" └ 📦 **Unlimited batching capabilities!**\n\n"
                    f"💰 **Current Price:** `{(get_bot_info(bot_id) or {}).get('premium_price','500')}`\n"
                    f"Contact Admin to upgrade now!"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Status: {'✅ **ACTIVE**' if is_p else '❌ **INACTIVE**'}\n\n"
                f"💎 **Exclusive Benefits:\n"
                f" ├ 🚀 **No Auto-Delete:** Files stay forever!\n"
                f" ├ 🎭 **Dual Tier Access:** Get premium content!\n"
                f" ├ ⚡ **No Ads:** Direct delivery, zero wait!\n"
                f" └ 📦 **Unlimited Batches:** No restrictions!\n\n"
                f"💰 **Pricing:** `{price}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"To purchase, contact the admin or owner."
            )
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
            sess="✅" if SESSION_STRING else "❌"
            await message.reply(
                "🚀 **FileStore v6.0 — Help**\n\n"
                "**Files:** Send → get link\n"
                "**Batch:** `/batch` → files → `/done`\n"
                "**Edit:** `/editfile ID` → caption/thumbnail\n\n"
                "🎭 **Dual Post (Premium vs Free):**\n"
                "`/dualpost Title` → send FREE files\n"
                "`/dpremium` → switch to PREMIUM stage\n"
                "`/dpdone` → finalize + get link\n"
                "`/myduals` → manage all dual posts\n"
                "`/dpstats` → view analytics\n\n"
                f"**Rebuild:** `/rebuild` (Session:{sess})\n"
                "**Backup:** `/backup`\n"
                "**Welcome:** `/setwelcome`\n"
                "**Clone:** `/clone TOKEN`"
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
        
        # Only handle if in batch/dual session or if it is a file
        in_session = uid in TEMP_BATCH or uid in TEMP_DUAL
        is_media = bool(message.document or message.video or message.audio or message.photo or message.sticker or message.animation or message.voice or message.video_note)
        
        if not (in_session or is_media):
            return

        # Skip commands
        if message.text and message.text.startswith("/"):
            return

        # Skip if FSM is waiting for photo
        if uid in TEMP_EDIT and TEMP_EDIT[uid].get("mode")=="thumbnail" and message.photo: return
        if uid in TEMP_WELCOME and TEMP_WELCOME[uid].get("step")=="image" and message.photo: return

        try:
            db_msg=await message.forward(DB_CHANNEL)
        except Exception as e:
            return await message.reply(f"❌ DB Channel error!\n`{e}`")

        try:
            db_msg=await message.forward(DB_CHANNEL)
        except Exception as e:
            return await message.reply(f"❌ DB Channel error!\n`{e}`")

        original_caption=message.caption
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

        fuid=unique_id(); files=load_db(FILES_DB)
        fdata={
            "file_id":file_id,"file_name":file_name,"file_size":file_size,
            "caption":original_caption,"user_id":uid,"bot_id":bot_id,
            "upload_date":str(datetime.now()),"db_msg_id":db_msg.id,
            "access_count":0,"media_type":media_type,"custom_thumbnail":None
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

        # ── DUAL POST SESSION — add file to current stage ────────
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
        uid = message.from_user.id

        if uid in TEMP_WELCOME:
            sess = TEMP_WELCOME[uid]; bot_id = sess["bot_id"]; step = sess.get("step")
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

    # ── CALLBACK HANDLER ──────────────────────────────────────────
    @app.on_callback_query(group=1)
    async def cb_handler(client, cb):
        uid = cb.from_user.id; data = cb.data; bot_id = client.me.id
        if is_user_banned(uid, bot_id): return await cb.answer("🚫 Banned!", show_alert=True)

        # ── File management callbacks ─────────────────────────────
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
                    [InlineKeyboardButton("🗑 Remove Thumb", callback_data=f"remove_thumb_{fuid}")],
                    [InlineKeyboardButton("❌ Cancel",       callback_data="cancel_edit")]
                ])
            )
            await cb.answer("Send a photo")

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
            s, f = await do_broadcast(bd["bot_ids"], bd["bc_msg_id"], status_msg=sm)
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

        elif data in ("cb_search", "help_menu", "referral_menu", "premium_menu"):
            texts = {
                "cb_search":    "🔍 **Search**\n\nUse: `/search FILENAME`\nOr inline: `@BotUsername query`",
                "help_menu":    (
                    "ℹ️ **Help**\n\n"
                    "Send file → link | `/batch` → multi link\n"
                    "🎭 **Dual Post:**\n"
                    "`/dualpost` → FREE files → `/dpremium` → PRO files → `/dpdone`\n"
                    "`/myduals` → manage | `/dpstats` → analytics"
                ),
                "help_menu": (
                    f"🚀 **FILESTORE ULTRA v6.0 — ELITE EDITION**\n\n"
                    f"**Elite Commands:**\n"
                    f" ├ Send any content → Get link\n"
                    f" ├ /batch → Create collection\n"
                    f" ├ /dualpost → Free vs Premium link\n"
                    f" └ /setchannel → Connect your channel\n\n"
                    f"**Premium Features:**\n"
                    f" ├ No Auto-Delete / Zero Ads\n"
                    f" └ Unlimited Access\n\n"
                    f"**Support:** Contact @Admin for upgrades."
                ),
                "premium_menu": (
                    f"👑 **ULTRA PREMIUM EXPERIENCE**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Status: {'💎 **ACTIVE**' if (get_user(uid,bot_id) or {}).get('is_premium') else '🆓 **FREE**'}\n\n"
                    f"✨ **Exclusive Elite Perks:\n"
                    f" ├ 🚀 **Permanent Storage:** No auto-delete!\n"
                    f" ├ 🎭 **Elite Access:** Premium Dual Posts!\n"
                    f" ├ ⚡ **Direct Link:** No Ads / Shorteners!\n"
                    f" └ 📦 **Unlimited batching capabilities!**\n\n"
                    f"💰 **Current Price:** `{(get_bot_info(bot_id) or {}).get('premium_price','500')}`\n"
                    f"Contact Admin to upgrade now!"
                ),
            }
            await cb.message.edit(
                texts[data],
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
            )
            await cb.answer()

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

        elif data == "admin_stats":
            bot_files = [f for f in load_db(FILES_DB).values() if f.get("bot_id") == bot_id]
            dp_count  = len(get_bot_dual_posts(bot_id))
            dp_views  = sum(p.get("access_total", 0) for p in get_bot_dual_posts(bot_id))
            await cb.message.edit(
                f"📊 **Bot Stats**\n\n"
                f"👥 `{len(get_all_users(bot_id))}` | 📁 `{len(bot_files)}` | "
                f"👁 `{sum(f.get('access_count',0) for f in bot_files)}`\n"
                f"🎭 Dual Posts: `{dp_count}` | 👁 `{dp_views}` views\n"
                f"⏳ `{str(datetime.now()-START_TIME).split('.')[0]}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh",    callback_data="admin_stats"),
                     InlineKeyboardButton("🎭 Dual Posts", callback_data="dual_posts_admin")],
                    [InlineKeyboardButton("🔙 Back",       callback_data="admin_panel")]
                ])
            )
            await cb.answer()

        elif data == "manage_users":
            all_u = load_db(USERS_DB)
            banned = sum(1 for u in all_u.values()
                         if u.get("bot_id") == bot_id and u.get("is_banned"))
            await cb.message.edit(
                f"👥 **Users**\n\n🟢 Active: `{len(get_all_users(bot_id))}` | 🚫 Banned: `{banned}`\n\n"
                f"`/ban ID` `/unban ID` `/info ID` `/setpremium ID`",
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
                f"⏱ Current: `{curr}s` ({curr//60}min)\n\n`/settimer SECONDS`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]])
            )
            await cb.answer()

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
            text = f"🔒 **Force Subscribe** ({len(fs)}/{MAX_FORCE_SUB_CHANNELS})\n\n"
            for i, f in enumerate(fs, 1):
                cid = f["channel_id"] if isinstance(f, dict) else f
                text += f"{i}. `{cid}`\n"
            if not fs: text += "None.\n"
            text += "\n🆕 Pending join requests = access!\n`/setfs` to manage."
            await cb.message.edit(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]])
            )
            await cb.answer()

        elif data == "toggle_auto_approve":
            bi = get_bot_info(bot_id)
            if not bi: return await cb.answer("Not found!", show_alert=True)
            curr = bi.get("auto_approve", False)
            update_bot_info(bot_id, "auto_approve", not curr)
            await cb.answer(f"Auto-Approve: {'ON ✅' if not curr else 'OFF ❌'}", show_alert=True)
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
                f"👑 **Supreme Panel v6.0**\n🔑 Session: {sess}",
                reply_markup=kb_supreme()
            )
            await cb.answer()

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
            sess    = "✅" if SESSION_STRING else "❌"
            active_tokens = sum(1 for v in SHORTENER_TOKENS.values()
                                if not v["used"] and time.time() < v["expires_at"])
            dp_count = len(load_db(DUAL_POST_DB))
            await cb.message.edit(
                f"🖥 **System Stats v6.0**\n━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 `{len(get_all_bots())}` bots | 🟢 `{len(ACTIVE_CLIENTS)}` online\n"
                f"👥 `{len(load_db(USERS_DB))}` | 📁 `{len(load_db(FILES_DB))}` | "
                f"🎭 `{dp_count}` duals\n"
                f"⏳ Pending joins: `{pend}` | 🔑 Tokens: `{active_tokens}`\n"
                f"🔑 Session: {sess}\n"
                f"💾 Disk: `{u//(2**30)}GB/{t//(2**30)}GB` (Free:`{f//(2**30)}GB`)\n"
                f"⏱ Uptime: `{str(datetime.now()-START_TIME).split('.')[0]}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh", callback_data="system_stats")],
                    [InlineKeyboardButton("🔙 Back",    callback_data="supreme_panel")]
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
    print("║  🚀 ULTRA FILESTORE BOT v6.0 — ELITE EDITION         ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    if DB_CHANNEL == -1000000000000:
        logger.error("❌ DB_CHANNEL not configured!"); return

    _load_pending()
    logger.info(f"📋 Loaded pending requests for {len(_PENDING)} channels")
    logger.info(f"🔑 SESSION_STRING: {'✅ Set' if SESSION_STRING else '❌ Not set'}")

    await start_web_server()

    logger.info("🔥 Starting Main Bot...")
    if not await start_bot(MAIN_BOT_TOKEN):
        logger.error("❌ Main bot failed!"); return

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
    print("║         ✅ ALL SYSTEMS OPERATIONAL v6.0 ✅                ║")
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
