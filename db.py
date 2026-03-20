"""
Database module for GrievTrack
Handles SQLite connection and schema initialization
"""

import sqlite3
from flask import g

DATABASE = 'grievtrack.db'


def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database with schema (idempotent)"""
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()

    # Table 1: complaints
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            complaint_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            citizen_id TEXT NOT NULL,
            current_status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Table 2: complaint_events
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaint_events (
            event_id TEXT PRIMARY KEY,
            complaint_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            remarks TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
        )
    ''')

    # Table 3: ledger_hashes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ledger_hashes (
            ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            complaint_id TEXT NOT NULL,
            event_hash TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')

    db.commit()
    db.close()
    print("Database initialized successfully")


if __name__ == '__main__':
    init_db()
