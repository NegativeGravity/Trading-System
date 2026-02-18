import sqlite3
import pandas as pd
from datetime import datetime

class TradingJournal:
    def __init__(self, db_name="trading_journal.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()


