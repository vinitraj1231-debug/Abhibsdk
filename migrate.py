import os
import json
import asyncio
import datetime
from database import (
    init_db, get_session, User, Bot, StoredFile, Batch,
    DualPost, ProtectedLink, GlobalConfig, Admin, PendingRequest, FileCache
)

DB_FOLDER = 'database'
FILES_DB        = f'{DB_FOLDER}/files.json'
BATCH_DB        = f'{DB_FOLDER}/batches.json'
BOTS_DB         = f'{DB_FOLDER}/bots.json'
USERS_DB        = f'{DB_FOLDER}/users.json'
ADMINS_DB       = f'{DB_FOLDER}/admins.json'
FILE_CACHE_DB   = f'{DB_FOLDER}/file_cache.json'
CONFIG_DB       = f'{DB_FOLDER}/config.json'
PENDING_REQ_DB  = f'{DB_FOLDER}/pending_requests.json'
DUAL_POST_DB    = f'{DB_FOLDER}/dual_posts.json'
PLINKS_DB       = f'{DB_FOLDER}/protected_links.json'

def parse_date(date_str):
    if not date_str: return None
    try: return datetime.datetime.fromisoformat(date_str)
    except:
        try: return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
        except: return None

async def migrate():
    await init_db()
    print('Database initialized.')
    async with get_session() as session:
        if os.path.exists(ADMINS_DB):
            with open(ADMINS_DB, 'r') as f:
                data = json.load(f)
                for uid in data: session.add(Admin(user_id=int(uid)))
            print(f'Migrated {len(data)} admins.')
        if os.path.exists(CONFIG_DB):
            with open(CONFIG_DB, 'r') as f:
                data = json.load(f)
                for k, v in data.items(): session.add(GlobalConfig(key=k, value=v))
            print(f'Migrated {len(data)} config keys.')
        if os.path.exists(USERS_DB):
            with open(USERS_DB, 'r') as f:
                data = json.load(f)
                for k, v in data.items():
                    session.add(User(user_id=int(v['user_id']), bot_id=int(v['bot_id']), username=v.get('username'), name=v.get('name'), join_date=parse_date(v.get('join_date')), is_banned=v.get('is_banned', False), files_uploaded=v.get('files_uploaded', 0), batches_created=v.get('batches_created', 0), bots_cloned=v.get('bots_cloned', 0), is_premium=v.get('is_premium', False), refer_count=v.get('refer_count', 0), refer_rewards=v.get('refer_rewards', 0), last_active=parse_date(v.get('last_active')), pref_font=v.get('pref_font', 'smallcaps')))
            print(f'Migrated {len(data)} users.')
        if os.path.exists(BOTS_DB):
            with open(BOTS_DB, 'r') as f:
                data = json.load(f)
                for k, v in data.items():
                    session.add(Bot(bot_id=int(v['bot_id']), token=v['token'], bot_username=v.get('bot_username'), owner_id=v['owner_id'], owner_name=v.get('owner_name'), parent_bot_id=v.get('parent_bot_id'), created_on=parse_date(v.get('created_on')), is_active=v.get('is_active', True), custom_welcome=v.get('custom_welcome'), welcome_image=v.get('welcome_image'), auto_delete_time=v.get('auto_delete_time', 300), auto_approve=v.get('auto_approve', False), premium_price=v.get('premium_price', '500'), premium_contact=v.get('premium_contact', 'zolvid'), premium_qr=v.get('premium_qr'), auto_caption=v.get('auto_caption', True), connected_channel=v.get('connected_channel'), join_method=v.get('join_method', 'direct'), verify_link=v.get('verify_link'), update_channel=v.get('update_channel'), force_subs=v.get('force_subs', []), shortener_api=v.get('shortener_api'), shortener_url=v.get('shortener_url'), is_shortener_enabled=v.get('is_shortener_enabled', False), log_channel=v.get('log_channel'), secondary_admins=v.get('secondary_admins', [])))
            print(f'Migrated {len(data)} bots.')
        if os.path.exists(FILES_DB):
            with open(FILES_DB, 'r') as f:
                data = json.load(f)
                for k, v in data.items():
                    session.add(StoredFile(fuid=k, file_id=v.get('file_id'), file_name=v.get('file_name'), file_size=v.get('file_size', 0), caption=v.get('caption'), user_id=v.get('user_id'), bot_id=v.get('bot_id'), upload_date=parse_date(v.get('upload_date')), db_msg_id=v.get('db_msg_id'), access_count=v.get('access_count', 0), media_type=v.get('media_type'), custom_thumbnail=v.get('custom_thumbnail'), reply_markup=v.get('reply_markup'), password=v.get('password')))
            print(f'Migrated {len(data)} files.')
        if os.path.exists(BATCH_DB):
            with open(BATCH_DB, 'r') as f:
                data = json.load(f)
                for k, v in data.items():
                    session.add(Batch(bid=k, files=v.get('files', []), created_by=v.get('created_by'), bot_id=v.get('bot_id'), date=parse_date(v.get('date'))))
            print(f'Migrated {len(data)} batches.')
        if os.path.exists(DUAL_POST_DB):
            with open(DUAL_POST_DB, 'r') as f:
                data = json.load(f)
                for k, v in data.items():
                    session.add(DualPost(post_id=k, bot_id=v.get('bot_id'), created_by=v.get('created_by'), created_at=parse_date(v.get('created_at')), title=v.get('title'), free_files=v.get('free_files', []), pro_files=v.get('pro_files', []), description_free=v.get('description_free'), description_pro=v.get('description_pro'), access_free=v.get('access_free', 0), access_pro=v.get('access_pro', 0), access_total=v.get('access_total', 0), last_accessed=parse_date(v.get('last_accessed'))))
            print(f'Migrated {len(data)} dual posts.')
        if os.path.exists(PLINKS_DB):
            with open(PLINKS_DB, 'r') as f:
                data = json.load(f)
                for k, v in data.items():
                    session.add(ProtectedLink(lpid=k, bot_id=v.get('bot_id'), channel_id=v.get('channel_id'), title=v.get('title'), mode=v.get('mode'), created_by=v.get('created_by'), created_at=datetime.datetime.fromtimestamp(v.get('created_at')) if v.get('created_at') else None))
            print(f'Migrated {len(data)} protected links.')
        if os.path.exists(FILE_CACHE_DB):
            with open(FILE_CACHE_DB, 'r') as f:
                data = json.load(f)
                for k, v in data.items(): session.add(FileCache(file_id=k, message_id=v.get('message_id'), chat_id=v.get('chat_id'), bot_id=v.get('bot_id'), caption=v.get('caption'), expires_at=parse_date(v.get('expires_at'))))
            print(f'Migrated {len(data)} cache entries.')
        if os.path.exists(PENDING_REQ_DB):
            with open(PENDING_REQ_DB, 'r') as f:
                data = json.load(f)
                for cid, users in data.items():
                    if not isinstance(users, dict): continue
                    for uid, ts in users.items(): session.add(PendingRequest(channel_id=int(cid), user_id=int(uid), timestamp=parse_date(ts)))
            print(f'Migrated pending requests.')

if __name__ == '__main__':
    asyncio.run(migrate())
