import sqlite3
from datetime import datetime
from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users ("
              "telegram_id INTEGER PRIMARY KEY,"
              "username TEXT,"
              "first_name TEXT,"
              "last_name TEXT,"
              "group_name TEXT DEFAULT 'Индивидуально',"
              "total_kg REAL DEFAULT 0,"
              "cleanups_count INTEGER DEFAULT 0,"
              "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
              ")")

    c.execute("CREATE TABLE IF NOT EXISTS cleanups ("
              "id INTEGER PRIMARY KEY AUTOINCREMENT,"
              "user_id INTEGER,"
              "latitude REAL,"
              "longitude REAL,"
              "location_name TEXT,"
              "photo_file_id TEXT,"
              "status TEXT DEFAULT 'cleaned',"
              "cleanup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
              "notes TEXT"
              ")")

    c.execute("CREATE TABLE IF NOT EXISTS cleanup_items ("
              "id INTEGER PRIMARY KEY AUTOINCREMENT,"
              "cleanup_id INTEGER,"
              "trash_type TEXT,"
              "weight_kg REAL DEFAULT 0,"
              "bags_count INTEGER DEFAULT 0"
              ")")

    c.execute("CREATE TABLE IF NOT EXISTS trash_spots ("
              "id INTEGER PRIMARY KEY AUTOINCREMENT,"
              "user_id INTEGER,"
              "latitude REAL,"
              "longitude REAL,"
              "description TEXT,"
              "photo_file_id TEXT,"
              "status TEXT DEFAULT 'active',"
              "reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
              ")")

    conn.commit()
    conn.close()


def add_user(telegram_id, username, first_name, last_name=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name) "
              "VALUES (?, ?, ?, ?)", (telegram_id, username, first_name, last_name))
    conn.commit()
    conn.close()


def add_cleanup(user_id, lat, lon, location_name, photo_file_id, notes=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO cleanups (user_id, latitude, longitude, location_name, photo_file_id, notes) "
              "VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, lat, lon, location_name, photo_file_id, notes))
    cleanup_id = c.lastrowid
    conn.commit()
    conn.close()
    return cleanup_id


def add_cleanup_item(cleanup_id, trash_type, weight_kg, bags_count):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO cleanup_items (cleanup_id, trash_type, weight_kg, bags_count) "
              "VALUES (?, ?, ?, ?)",
              (cleanup_id, trash_type, weight_kg, bags_count))
    conn.commit()
    conn.close()


def add_trash_spot(user_id, lat, lon, description, photo_file_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO trash_spots (user_id, latitude, longitude, description, photo_file_id) "
              "VALUES (?, ?, ?, ?, ?)",
              (user_id, lat, lon, description, photo_file_id))
    conn.commit()
    conn.close()


def update_user_stats(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT SUM(weight_kg) FROM cleanup_items ci "
              "JOIN cleanups c ON ci.cleanup_id = c.id "
              "WHERE c.user_id = ?", (user_id,))
    total = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM cleanups WHERE user_id = ?", (user_id,))
    count = c.fetchone()[0]
    c.execute("UPDATE users SET total_kg = ?, cleanups_count = ? WHERE telegram_id = ?",
              (total, count, user_id))
    conn.commit()
    conn.close()


def get_cleanups():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, latitude, longitude, location_name, cleanup_date FROM cleanups ORDER BY cleanup_date DESC")
    rows = c.fetchall()
    result = []
    for row in rows:
        cid, uid, lat, lon, loc, dt = row
        c.execute("SELECT first_name, username FROM users WHERE telegram_id = ?", (uid,))
        user = c.fetchone()
        if user:
            fname, uname = user
        else:
            fname, uname = "Аноним", ""
        c.execute("SELECT COALESCE(SUM(weight_kg), 0), COALESCE(SUM(bags_count), 0) FROM cleanup_items WHERE cleanup_id = ?", (cid,))
        w, b = c.fetchone()
        result.append((cid, uid, lat, lon, loc, dt, fname, uname, w, b))
    conn.close()
    return result


def get_trash_spots():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, latitude, longitude, description, reported_at, photo_file_id FROM trash_spots WHERE status = 'active' ORDER BY reported_at DESC")
    rows = c.fetchall()
    result = []
    for row in rows:
        sid, uid, lat, lon, desc, dt, photo = row
        c.execute("SELECT first_name FROM users WHERE telegram_id = ?", (uid,))
        user = c.fetchone()
        fname = user[0] if user else "Аноним"
        result.append((lat, lon, desc, dt, fname, photo))
    conn.close()
    return result


def get_leaderboard(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT telegram_id, first_name, username, group_name FROM users")
    users = c.fetchall()
    result = []
    for uid, fname, uname, gname in users:
        c.execute("SELECT COALESCE(SUM(weight_kg), 0) FROM cleanup_items ci JOIN cleanups c ON ci.cleanup_id = c.id WHERE c.user_id = ?", (uid,))
        total = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM cleanups WHERE user_id = ?", (uid,))
        count = c.fetchone()[0]
        if total > 0:
            result.append((fname, uname, total, count, gname))
    result.sort(key=lambda x: x[2], reverse=True)
    conn.close()
    return result[:limit]


def get_group_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT telegram_id, group_name FROM users")
    users = c.fetchall()
    groups = {}
    for uid, gname in users:
        if gname not in groups:
            groups[gname] = {"members": 0, "kg": 0, "cleanups": 0}
        c.execute("SELECT COALESCE(SUM(weight_kg), 0) FROM cleanup_items ci JOIN cleanups c ON ci.cleanup_id = c.id WHERE c.user_id = ?", (uid,))
        total = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM cleanups WHERE user_id = ?", (uid,))
        count = c.fetchone()[0]
        if total > 0:
            groups[gname]["members"] += 1
            groups[gname]["kg"] += total
            groups[gname]["cleanups"] += count
    result = [(g, d["members"], d["kg"], d["cleanups"]) for g, d in groups.items() if d["kg"] > 0]
    result.sort(key=lambda x: x[2], reverse=True)
    conn.close()
    return result


def get_stats_by_type():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT trash_type, SUM(weight_kg), SUM(bags_count) FROM cleanup_items GROUP BY trash_type")
    rows = c.fetchall()
    conn.close()
    return rows


def get_monthly_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT strftime('%Y-%m', cleanup_date) as month, COALESCE(SUM(ci.weight_kg), 0), COUNT(DISTINCT c.id) FROM cleanups c LEFT JOIN cleanup_items ci ON ci.cleanup_id = c.id GROUP BY month ORDER BY month DESC")
    rows = c.fetchall()
    conn.close()
    return rows
