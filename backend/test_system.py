import asyncio, sys, selectors, httpx
sys.stdout.reconfigure(encoding='utf-8')
if sys.platform == 'win32':
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)
sys.path.insert(0, '.')
from sqlalchemy import text
from app.database import engine
from app.services.encryption_service import decrypt
import pathlib, os

DATA_DIR = pathlib.Path(os.getenv('DATA_DIR', '../data'))
PROJECT_ID = '1739b6d5-3ecc-488e-9a18-c5d19bbd5680'


async def full_test():
    print('=== 1. BACKEND DB CHECK ===')
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT video_key_enc, video_provider, video_model FROM api_keys LIMIT 1'))
        row = r.fetchone()
        api_key = decrypt(row[0])
        print(f'  API Key: {api_key[:8]}... | provider={row[1]} | model={row[2]}')

        sql = text("""
            SELECT v.id, v.status, v.file_path, sc.scene_no 
            FROM videos v
            JOIN scenes sc ON sc.id=v.scene_id 
            JOIN scripts s ON s.id=sc.script_id
            JOIN episodes e ON e.id=s.episode_id
            WHERE e.project_id=:pid AND v.status='done'
        """)
        r2 = await conn.execute(sql, {'pid': PROJECT_ID})
        rows = r2.fetchall()
        print(f'  Videos done in project: {len(rows)}')
        for v in rows:
            exists = (DATA_DIR / v[2]).exists() if v[2] else False
            status = 'FILE_EXISTS' if exists else 'FILE_MISSING'
            print(f'  Scene {v[3]} | {status} | {v[2]}')

    print()
    print('=== 2. Z.AI API SUBMIT TEST ===')
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': 'cogvideox-3',
        'prompt': 'A cute cartoon dog playing in a park',
        'duration': 5,
        'size': '720x1280',
        'quality': 'speed',
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post('https://api.z.ai/api/paas/v4/videos/generations', json=payload, headers=headers)

    print(f'  Submit HTTP: {resp.status_code}')
    if resp.status_code == 200:
        task_id = resp.json().get('id', '')
        task_status = resp.json().get('task_status', '')
        print(f'  Task ID: {task_id}')
        print(f'  Initial status: {task_status}')

        print()
        print('=== 3. Z.AI POLL /async-result TEST ===')
        poll_headers = {'Authorization': f'Bearer {api_key}'}
        async with httpx.AsyncClient(timeout=10) as client:
            r2 = await client.get(
                f'https://api.z.ai/api/paas/v4/async-result/{task_id}',
                headers=poll_headers,
            )
        print(f'  Poll HTTP: {r2.status_code}')
        if r2.status_code == 200:
            poll_status = r2.json().get('task_status', '?')
            print(f'  Poll task_status: {poll_status}')
            print()
            print('  [ALL OK] Backend + Z.AI endpoint deu hoat dong chinh xac!')
        else:
            print(f'  [FAIL] Poll endpoint loi: {r2.text[:200]}')
    else:
        print(f'  [FAIL] Submit loi: {resp.text[:200]}')

    print()
    print('=== 4. FILE SERVER TEST ===')
    for v in rows:
        if v[2]:
            p = DATA_DIR / v[2]
            size = p.stat().st_size / 1024 if p.exists() else 0
            print(f'  Video file: {p.name} ({size:.0f} KB)')


if sys.platform == 'win32':
    loop.run_until_complete(full_test())
else:
    asyncio.run(full_test())
