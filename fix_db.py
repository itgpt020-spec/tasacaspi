import sqlite3
from config import DB_PATH

def fix_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("Проверяю базу данных...")

    # 1. Найти всех user_id из cleanups, которых нет в users
    c.execute("SELECT DISTINCT user_id FROM cleanups")
    cleanup_users = c.fetchall()

    added = 0
    for (uid,) in cleanup_users:
        c.execute("SELECT 1 FROM users WHERE telegram_id = ?", (uid,))
        if not c.fetchone():
            c.execute("INSERT INTO users (telegram_id, username, first_name, group_name) VALUES (?, ?, ?, ?)",
                      (uid, None, "Волонтёр", "Индивидуально"))
            added += 1
            print(f"Добавлен пользователь ID={uid}")

    # 2. Пересчитать статистику для всех пользователей
    c.execute("SELECT telegram_id FROM users")
    users = c.fetchall()
    updated = 0
    for (uid,) in users:
        c.execute("SELECT COALESCE(SUM(weight_kg), 0) FROM cleanup_items ci JOIN cleanups c ON ci.cleanup_id = c.id WHERE c.user_id = ?", (uid,))
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM cleanups WHERE user_id = ?", (uid,))
        count = c.fetchone()[0]
        c.execute("UPDATE users SET total_kg = ?, cleanups_count = ? WHERE telegram_id = ?",
                  (total, count, uid))
        updated += 1

    conn.commit()
    conn.close()

    print(f"Готово! Добавлено {added} пользователей, обновлено {updated} записей.")
    print("Теперь перезапустите сайт (Ctrl+C, затем python webapp.py) и обновите страницу.")

if __name__ == "__main__":
    fix_database()
