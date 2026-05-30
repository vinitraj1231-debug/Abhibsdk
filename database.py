import os
import json
import asyncio
import datetime
from typing import List, Optional, Any, Union, Dict
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Text, JSON,
    ForeignKey, Integer, select, update, delete, func, or_, desc
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import NullPool

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')

# If DATABASE_URL is not provided, default to SQLite with WAL mode
if not DATABASE_URL:
    # Use SQLite for development/sandbox
    DB_PATH = 'database/bot_database.db'
    os.makedirs('database', exist_ok=True)
    DATABASE_URL = f'sqlite+aiosqlite:///{DB_PATH}'

# For PostgreSQL, we want to ensure we use the asyncpg driver
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')

# Engine configuration
if 'sqlite' in DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={'timeout': 30},
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        pool_recycle=3600,
        pool_pre_ping=True
    )

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    bot_id = Column(BigInteger, nullable=False)
    username = Column(String(255))
    name = Column(String(255))
    join_date = Column(DateTime, default=datetime.datetime.now)
    is_banned = Column(Boolean, default=False)
    files_uploaded = Column(Integer, default=0)
    batches_created = Column(Integer, default=0)
    bots_cloned = Column(Integer, default=0)
    is_premium = Column(Boolean, default=False)
    refer_count = Column(Integer, default=0)
    refer_rewards = Column(Integer, default=0)
    last_active = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    pref_font = Column(String(50), default='smallcaps')

class Bot(Base):
    __tablename__ = 'bots'

    bot_id = Column(BigInteger, primary_key=True)
    token = Column(String(255), nullable=False)
    bot_username = Column(String(255))
    owner_id = Column(BigInteger, nullable=False)
    owner_name = Column(String(255))
    parent_bot_id = Column(BigInteger)
    created_on = Column(DateTime, default=datetime.datetime.now)
    is_active = Column(Boolean, default=True)
    custom_welcome = Column(Text)
    welcome_image = Column(String(255))
    auto_delete_time = Column(Integer, default=300)
    auto_approve = Column(Boolean, default=False)
    premium_price = Column(String(50), default='500')
    premium_contact = Column(String(255), default='zolvid')
    premium_qr = Column(String(255))
    auto_caption = Column(Boolean, default=True)
    connected_channel = Column(BigInteger)
    join_method = Column(String(50), default='direct')
    verify_link = Column(Text)
    update_channel = Column(Text)
    force_subs = Column(JSON, default=list)
    shortener_api = Column(String(255))
    shortener_url = Column(String(255))
    is_shortener_enabled = Column(Boolean, default=False)
    log_channel = Column(BigInteger)
    secondary_admins = Column(JSON, default=list)

class StoredFile(Base):
    __tablename__ = 'files'

    fuid = Column(String(20), primary_key=True)
    file_id = Column(String(255))
    file_name = Column(String(255))
    file_size = Column(BigInteger, default=0)
    caption = Column(Text)
    user_id = Column(BigInteger)
    bot_id = Column(BigInteger)
    upload_date = Column(DateTime, default=datetime.datetime.now)
    db_msg_id = Column(BigInteger)
    access_count = Column(Integer, default=0)
    media_type = Column(String(50))
    custom_thumbnail = Column(String(255))
    reply_markup = Column(JSON)
    entities = Column(JSON)
    caption_entities = Column(JSON)
    password = Column(String(255))

class Batch(Base):
    __tablename__ = 'batches'

    bid = Column(String(20), primary_key=True)
    files = Column(JSON)
    created_by = Column(BigInteger)
    bot_id = Column(BigInteger)
    date = Column(DateTime, default=datetime.datetime.now)

class DualPost(Base):
    __tablename__ = 'dual_posts'

    post_id = Column(String(20), primary_key=True)
    bot_id = Column(BigInteger)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.datetime.now)
    title = Column(String(255))
    free_files = Column(JSON)
    pro_files = Column(JSON)
    description_free = Column(Text)
    description_pro = Column(Text)
    access_free = Column(Integer, default=0)
    access_pro = Column(Integer, default=0)
    access_total = Column(Integer, default=0)
    last_accessed = Column(DateTime)

class ProtectedLink(Base):
    __tablename__ = 'protected_links'

    lpid = Column(String(20), primary_key=True)
    bot_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    title = Column(String(255))
    mode = Column(String(50))
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.datetime.now)

class GlobalConfig(Base):
    __tablename__ = 'config'

    key = Column(String(255), primary_key=True)
    value = Column(JSON)

class Admin(Base):
    __tablename__ = 'admins'

    user_id = Column(BigInteger, primary_key=True)
    added_at = Column(DateTime, default=datetime.datetime.now)

class PendingRequest(Base):
    __tablename__ = 'pending_requests'

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger)
    user_id = Column(BigInteger)
    timestamp = Column(DateTime, default=datetime.datetime.now)

class FileCache(Base):
    __tablename__ = 'file_cache'

    file_id = Column(String(255), primary_key=True)
    message_id = Column(BigInteger)
    chat_id = Column(BigInteger)
    bot_id = Column(BigInteger)
    caption = Column(Text)
    expires_at = Column(DateTime)

from contextlib import asynccontextmanager

@asynccontextmanager
async def get_session():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        if 'sqlite' in DATABASE_URL:
            await conn.exec_driver_sql('PRAGMA journal_mode=WAL')
            await conn.exec_driver_sql('PRAGMA synchronous=NORMAL')
            await conn.exec_driver_sql('PRAGMA busy_timeout=30000')

        await conn.run_sync(Base.metadata.create_all)

def _to_dict(obj):
    if obj is None: return None
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for k, v in d.items():
        if isinstance(v, datetime.datetime):
            d[k] = v.isoformat()
    return d

# --- USER FUNCTIONS ---

async def db_add_user(user_id, bot_id, username=None, name=None):
    async with get_session() as session:
        stmt = select(User).where(User.user_id == user_id, User.bot_id == bot_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        is_new = False
        if not user:
            user = User(user_id=user_id, bot_id=bot_id, username=username, name=name)
            session.add(user)
            is_new = True
        else:
            user.username = username
            user.name = name
            user.last_active = datetime.datetime.now()
        await session.flush()
        return _to_dict(user), is_new

async def db_get_user(user_id, bot_id):
    async with get_session() as session:
        stmt = select(User).where(User.user_id == user_id, User.bot_id == bot_id)
        result = await session.execute(stmt)
        return _to_dict(result.scalar_one_or_none())

async def db_update_user_stats(user_id, bot_id, field, delta=1):
    async with get_session() as session:
        stmt = update(User).where(User.user_id == user_id, User.bot_id == bot_id).values({field: getattr(User, field) + delta})
        await session.execute(stmt)

async def db_update_user(user_id, bot_id, data):
    async with get_session() as session:
        stmt = update(User).where(User.user_id == user_id, User.bot_id == bot_id).values(**data)
        await session.execute(stmt)

async def db_get_all_users(bot_id=None):
    async with get_session() as session:
        stmt = select(User)
        if bot_id: stmt = stmt.where(User.bot_id == bot_id)
        stmt = stmt.where(User.is_banned == False)
        result = await session.execute(stmt)
        return [_to_dict(u) for u in result.scalars().all()]

async def db_ban_user(user_id, bot_id, ban=True):
    async with get_session() as session:
        stmt = update(User).where(User.user_id == user_id, User.bot_id == bot_id).values(is_banned=ban)
        await session.execute(stmt)
        return True

async def db_is_admin(user_id):
    async with get_session() as session:
        stmt = select(Admin).where(Admin.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

async def db_add_admin(user_id):
    async with get_session() as session:
        admin = Admin(user_id=user_id)
        session.add(admin)

async def db_del_admin(user_id):
    async with get_session() as session:
        stmt = delete(Admin).where(Admin.user_id == user_id)
        await session.execute(stmt)

async def db_get_all_admins():
    async with get_session() as session:
        result = await session.execute(select(Admin))
        return [str(a.user_id) for a in result.scalars().all()]

# --- BOT FUNCTIONS ---

async def db_save_bot_info(bot_data):
    async with get_session() as session:
        if 'created_on' in bot_data and isinstance(bot_data['created_on'], str):
            bot_data['created_on'] = datetime.datetime.fromisoformat(bot_data['created_on'])
        stmt = select(Bot).where(Bot.bot_id == bot_data['bot_id'])
        res = await session.execute(stmt)
        bot = res.scalar_one_or_none()
        if not bot:
            session.add(Bot(**bot_data))
        else:
            for k, v in bot_data.items(): setattr(bot, k, v)
        return True

async def db_get_bot_info(bot_id):
    async with get_session() as session:
        stmt = select(Bot).where(Bot.bot_id == bot_id)
        result = await session.execute(stmt)
        return _to_dict(result.scalar_one_or_none())

async def db_get_all_bots():
    async with get_session() as session:
        result = await session.execute(select(Bot))
        return {str(b.bot_id): _to_dict(b) for b in result.scalars().all()}

async def db_update_bot_info(bot_id, field, value):
    async with get_session() as session:
        stmt = update(Bot).where(Bot.bot_id == bot_id).values({field: value})
        await session.execute(stmt)
        return True

# --- FILE FUNCTIONS ---

async def db_save_file(fuid, fdata):
    async with get_session() as session:
        if 'upload_date' in fdata and isinstance(fdata['upload_date'], str):
            fdata['upload_date'] = datetime.datetime.fromisoformat(fdata['upload_date'])
        stmt = select(StoredFile).where(StoredFile.fuid == fuid)
        res = await session.execute(stmt)
        sf = res.scalar_one_or_none()
        if not sf:
            session.add(StoredFile(fuid=fuid, **fdata))
        else:
            for k, v in fdata.items(): setattr(sf, k, v)
        return True

async def db_get_file(fuid):
    async with get_session() as session:
        stmt = select(StoredFile).where(StoredFile.fuid == fuid)
        result = await session.execute(stmt)
        return _to_dict(result.scalar_one_or_none())

async def db_get_file_by_id(file_id):
    async with get_session() as session:
        stmt = select(StoredFile).where(StoredFile.file_id == file_id)
        result = await session.execute(stmt)
        return _to_dict(result.scalar_one_or_none())

async def db_del_file(fuid):
    async with get_session() as session:
        await session.execute(delete(StoredFile).where(StoredFile.fuid == fuid))
        return True

async def db_get_all_files(bot_id=None, user_id=None, limit=None):
    async with get_session() as session:
        stmt = select(StoredFile)
        if bot_id: stmt = stmt.where(StoredFile.bot_id == bot_id)
        if user_id: stmt = stmt.where(StoredFile.user_id == user_id)
        stmt = stmt.order_by(desc(StoredFile.upload_date))
        if limit: stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return {f.fuid: _to_dict(f) for f in result.scalars().all()}

async def db_search_files(bot_id, query, limit=20):
    async with get_session() as session:
        stmt = select(StoredFile).where(StoredFile.bot_id == bot_id, StoredFile.file_name.ilike(f'%{query}%')).limit(limit)
        result = await session.execute(stmt)
        return {f.fuid: _to_dict(f) for f in result.scalars().all()}

async def db_bump_file_access(fuid):
    async with get_session() as session:
        await session.execute(update(StoredFile).where(StoredFile.fuid == fuid).values(access_count=StoredFile.access_count + 1))

# --- BATCH FUNCTIONS ---

async def db_save_batch(bid, bdata):
    async with get_session() as session:
        if 'date' in bdata and isinstance(bdata['date'], str):
            bdata['date'] = datetime.datetime.fromisoformat(bdata['date'])
        stmt = select(Batch).where(Batch.bid == bid)
        res = await session.execute(stmt)
        if not res.scalar_one_or_none(): session.add(Batch(bid=bid, **bdata))
        else: await session.execute(update(Batch).where(Batch.bid == bid).values(**bdata))
        return True

async def db_get_batch(bid):
    async with get_session() as session:
        stmt = select(Batch).where(Batch.bid == bid)
        result = await session.execute(stmt)
        return _to_dict(result.scalar_one_or_none())

async def db_get_all_batches(bot_id=None, user_id=None):
    async with get_session() as session:
        stmt = select(Batch)
        if bot_id: stmt = stmt.where(Batch.bot_id == bot_id)
        if user_id: stmt = stmt.where(Batch.created_by == user_id)
        result = await session.execute(stmt)
        return {b.bid: _to_dict(b) for b in result.scalars().all()}

# --- DUAL POST FUNCTIONS ---

async def db_save_dual_post(post_id, pdata):
    async with get_session() as session:
        for k in ['created_at', 'last_accessed']:
            if k in pdata and isinstance(pdata[k], str):
                pdata[k] = datetime.datetime.fromisoformat(pdata[k])
        stmt = select(DualPost).where(DualPost.post_id == post_id)
        res = await session.execute(stmt)
        if not res.scalar_one_or_none(): session.add(DualPost(post_id=post_id, **pdata))
        else: await session.execute(update(DualPost).where(DualPost.post_id == post_id).values(**pdata))
        return True

async def db_get_dual_post(post_id):
    async with get_session() as session:
        stmt = select(DualPost).where(DualPost.post_id == post_id)
        result = await session.execute(stmt)
        return _to_dict(result.scalar_one_or_none())

async def db_get_all_dual_posts(bot_id=None, user_id=None):
    async with get_session() as session:
        stmt = select(DualPost)
        if bot_id: stmt = stmt.where(DualPost.bot_id == bot_id)
        if user_id: stmt = stmt.where(DualPost.created_by == user_id)
        result = await session.execute(stmt)
        return {dp.post_id: _to_dict(dp) for dp in result.scalars().all()}

async def db_del_dual_post(post_id):
    async with get_session() as session:
        await session.execute(delete(DualPost).where(DualPost.post_id == post_id))
        return True

async def db_bump_dual_access(post_id, tier):
    async with get_session() as session:
        field = f'access_{tier}'
        await session.execute(update(DualPost).where(DualPost.post_id == post_id).values(**{field: getattr(DualPost, field) + 1, 'access_total': DualPost.access_total + 1, 'last_accessed': datetime.datetime.now()}))

# --- PROTECTED LINKS ---

async def db_save_plink(lpid, pdata):
    async with get_session() as session:
        if 'created_at' in pdata and isinstance(pdata['created_at'], (int, float)):
            pdata['created_at'] = datetime.datetime.fromtimestamp(pdata['created_at'])
        stmt = select(ProtectedLink).where(ProtectedLink.lpid == lpid)
        res = await session.execute(stmt)
        if not res.scalar_one_or_none(): session.add(ProtectedLink(lpid=lpid, **pdata))
        else: await session.execute(update(ProtectedLink).where(ProtectedLink.lpid == lpid).values(**pdata))
        return True

async def db_get_plink(lpid):
    async with get_session() as session:
        stmt = select(ProtectedLink).where(ProtectedLink.lpid == lpid)
        result = await session.execute(stmt)
        return _to_dict(result.scalar_one_or_none())

async def db_get_all_plinks(bot_id=None):
    async with get_session() as session:
        stmt = select(ProtectedLink)
        if bot_id: stmt = stmt.where(ProtectedLink.bot_id == bot_id)
        result = await session.execute(stmt)
        return {pl.lpid: _to_dict(pl) for pl in result.scalars().all()}

async def db_del_plink(lpid):
    async with get_session() as session:
        await session.execute(delete(ProtectedLink).where(ProtectedLink.lpid == lpid))
        return True

# --- GLOBAL CONFIG ---

async def db_get_global_config():
    async with get_session() as session:
        result = await session.execute(select(GlobalConfig))
        return {c.key: c.value for c in result.scalars().all()}

async def db_update_global_config(key, value):
    async with get_session() as session:
        stmt = select(GlobalConfig).where(GlobalConfig.key == key)
        res = await session.execute(stmt)
        cfg = res.scalar_one_or_none()
        if not cfg: session.add(GlobalConfig(key=key, value=value))
        else: cfg.value = value

# --- PENDING REQUESTS ---

async def db_mark_join_request(channel_id, user_id):
    async with get_session() as session: session.add(PendingRequest(channel_id=channel_id, user_id=user_id))

async def db_clear_join_request(channel_id, user_id):
    async with get_session() as session: await session.execute(delete(PendingRequest).where(PendingRequest.channel_id == channel_id, PendingRequest.user_id == user_id))

async def db_get_all_pending_requests():
    async with get_session() as session:
        result = await session.execute(select(PendingRequest))
        res = {}
        for pr in result.scalars().all(): res.setdefault(pr.channel_id, {})[pr.user_id] = str(pr.timestamp)
        return res

# --- CACHE FUNCTIONS ---

async def db_add_to_cache(file_id, data):
    async with get_session() as session:
        if 'expires_at' in data and isinstance(data['expires_at'], str):
            data['expires_at'] = datetime.datetime.fromisoformat(data['expires_at'])
        stmt = select(FileCache).where(FileCache.file_id == file_id)
        res = await session.execute(stmt)
        if not res.scalar_one_or_none(): session.add(FileCache(file_id=file_id, **data))
        else: await session.execute(update(FileCache).where(FileCache.file_id == file_id).values(**data))

async def db_get_from_cache(file_id):
    async with get_session() as session:
        stmt = select(FileCache).where(FileCache.file_id == file_id)
        result = await session.execute(stmt)
        fc = result.scalar_one_or_none()
        if not fc: return None
        if fc.expires_at and fc.expires_at < datetime.datetime.now():
            await session.delete(fc)
            return None
        return _to_dict(fc)

async def db_clean_cache():
    async with get_session() as session:
        stmt = delete(FileCache).where(FileCache.expires_at < datetime.datetime.now())
        res = await session.execute(stmt)
        return res.rowcount
