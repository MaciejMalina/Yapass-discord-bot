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
        conn = self._connect(); c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS todo 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, item TEXT, user TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS participants 
                     (message_id INTEGER, user_id INTEGER, username TEXT, event_name TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS sent_reminders 
                     (event_id TEXT, sent_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS finance 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, payer TEXT, amount REAL, description TEXT, date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS debts 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              debtor_id INTEGER, debtor_name TEXT, 
              creditor_id INTEGER, creditor_name TEXT, 
              amount REAL, description TEXT)''')
        conn.commit()
        conn.close()
        logger.info("Baza danych zsynchronizowana.")