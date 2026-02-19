import os
import sqlite3
import json
import zlib
from django.conf import settings


def get_db_path() -> str:
    media_dir = os.path.join(settings.BASE_DIR, 'media')
    os.makedirs(media_dir, exist_ok=True)
    return os.path.join(media_dir, 'chart_cache.sqlite3')


def save_chart_data(session_id: int, payload: dict) -> None:
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS chart_data
                        (
                            session_id
                            INTEGER
                            PRIMARY
                            KEY,
                            payload
                            BLOB
                        )''')

        compressed_data = zlib.compress(json.dumps(payload).encode('utf-8'), level=3)
        conn.execute('REPLACE INTO chart_data (session_id, payload) VALUES (?, ?)',
                     (session_id, compressed_data))


def load_chart_data(session_id: int) -> bytes:
    db_path = get_db_path()
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute('SELECT payload FROM chart_data WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            if row:
                return zlib.decompress(row[0])
    except sqlite3.OperationalError:
        pass

    return b'{"chart_data": [], "volume_data": [], "markers_data": []}'
