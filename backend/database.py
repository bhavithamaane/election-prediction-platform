import os
import sqlite3
import json
from contextlib import contextmanager

# Determine database path in the backend directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "election.db")

@contextmanager
def get_db_conn():
    """
    Context manager that yields a sqlite3 connection.
    Sets row_factory to sqlite3.Row for dict-like column access.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """
    Initializes database tables using built-in sqlite3.
    """
    with get_db_conn() as conn:
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # 1. Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Email TEXT UNIQUE NOT NULL,
            PasswordHash TEXT NOT NULL,
            Role TEXT DEFAULT 'User'
        );
        """)
        
        # 2. Parties table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS parties (
            PartyID TEXT PRIMARY KEY,
            PartyName TEXT NOT NULL,
            Symbol TEXT,
            Color TEXT
        );
        """)
        
        # 3. Candidates table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            CandidateID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            PartyID TEXT NOT NULL,
            State TEXT NOT NULL,
            Constituency TEXT NOT NULL,
            FOREIGN KEY (PartyID) REFERENCES parties(PartyID) ON DELETE CASCADE
        );
        """)
        
        # 4. Polls table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            PollID INTEGER PRIMARY KEY AUTOINCREMENT,
            Agency TEXT NOT NULL,
            Date TEXT NOT NULL,
            SampleSize INTEGER NOT NULL,
            PartyVoteShare TEXT NOT NULL -- JSON string of party shares
        );
        """)
        
        # 5. Predictions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            PredictionID INTEGER PRIMARY KEY AUTOINCREMENT,
            State TEXT DEFAULT 'National',
            PartyID TEXT NOT NULL,
            PredictedSeats INTEGER NOT NULL,
            Confidence REAL NOT NULL,
            Date TEXT NOT NULL,
            FOREIGN KEY (PartyID) REFERENCES parties(PartyID)
        );
        """)
        
        # 6. Historical Results table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_results (
            ResultID INTEGER PRIMARY KEY AUTOINCREMENT,
            Year INTEGER NOT NULL,
            State TEXT NOT NULL,
            PartyID TEXT NOT NULL,
            VoteShare REAL NOT NULL,
            SeatsWon INTEGER NOT NULL,
            FOREIGN KEY (PartyID) REFERENCES parties(PartyID)
        );
        """)
        
        conn.commit()
        print("Database schemas initialized successfully via sqlite3.")

# Database helper to convert row to dict
def row_to_dict(row):
    if row is None:
        return None
    return dict(row)
