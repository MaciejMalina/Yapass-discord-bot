import sqlite3
import logging

logger = logging.getLogger('discord_bot')

class DatabaseManager:
    def __init__(self, db_path='bot_data.db'):
        self.db_path = db_path
        self.init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS todo 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, item TEXT, user TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS participants 
                     (message_id INTEGER, user_id INTEGER, username TEXT, event_name TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS sent_reminders 
                     (event_id TEXT, sent_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS finance 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, payer TEXT, amount REAL, description TEXT, date TEXT)''')
        conn.commit()
        conn.close()
        logger.info("Baza danych została zsynchronizowana.")

    def add_todo(self, category, item, user):
        conn = self._connect(); c = conn.cursor()
        c.execute("INSERT INTO todo (category, item, user) VALUES (?, ?, ?)", (category, item, user))
        conn.commit(); conn.close()

    def get_all_todo(self):
        conn = self._connect(); c = conn.cursor()
        c.execute("SELECT category, item, user FROM todo ORDER BY category ASC")
        rows = c.fetchall(); conn.close()
        return rows
