import os
import sys
import hashlib
import json
from datetime import datetime

# Add parent directory to path so we can import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, get_db_conn

def hash_password(password: str) -> str:
    salt = "election_prediction_salt_12983"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def seed():
    print("Initializing database tables...")
    init_db()
    
    with get_db_conn() as conn:
        cursor = conn.cursor()
        
        # Check if already seeded
        cursor.execute("SELECT COUNT(*) FROM users WHERE Email = 'admin@electionpredict.com';")
        if cursor.fetchone()[0] > 0:
            print("Database already seeded.")
            return

        print("Seeding parties (Karnataka)...")
        parties = [
            ("BJP", "Bharatiya Janata Party", "lotus", "#FF9933"),
            ("INC", "Indian National Congress", "hand", "#19AAED"),
            ("JD(S)", "Janata Dal (Secular)", "woman_farmer", "#006400"),
            ("Others", "Others / Independent", "globe", "#777777")
        ]
        cursor.executemany("INSERT OR IGNORE INTO parties (PartyID, PartyName, Symbol, Color) VALUES (?, ?, ?, ?);", parties)

        print("Seeding users...")
        users = [
            ("System Administrator", "admin@electionpredict.com", hash_password("admin123"), "Admin"),
            ("Lead Analyst", "analyst@electionpredict.com", hash_password("analyst123"), "Analyst")
        ]
        cursor.executemany("INSERT INTO users (Name, Email, PasswordHash, Role) VALUES (?, ?, ?, ?);", users)

        print("Seeding candidates (Karnataka)...")
        candidates = [
            ("B.Y. Vijayendra", "BJP", "Karnataka", "Bengaluru Rural"),
            ("D.K. Shivakumar", "INC", "Karnataka", "Bengaluru Central"),
            ("Siddaramaiah", "INC", "Karnataka", "Mysuru"),
            ("H.D. Kumaraswamy", "JD(S)", "Karnataka", "Mandya"),
            ("Prahlad Joshi", "BJP", "Karnataka", "Dharwad"),
            ("Shobha Karandlaje", "BJP", "Karnataka", "Udupi-Chikkamagaluru"),
            ("D.V. Sadananda Gowda", "BJP", "Karnataka", "Bengaluru North"),
            ("Veerappa Moily", "INC", "Karnataka", "Chikkaballapur")
        ]
        cursor.executemany("INSERT INTO candidates (Name, PartyID, State, Constituency) VALUES (?, ?, ?, ?);", candidates)

        print("Seeding Karnataka historical results...")
        historical = [
            # 2014 Karnataka Lok Sabha results
            (2014, "Karnataka", "BJP", 0.430, 17),
            (2014, "Karnataka", "INC", 0.410, 9),
            (2014, "Karnataka", "JD(S)", 0.112, 2),
            (2014, "Karnataka", "Others", 0.048, 0),
            
            # 2019 Karnataka Lok Sabha results
            (2019, "Karnataka", "BJP", 0.514, 25),
            (2019, "Karnataka", "INC", 0.325, 1),
            (2019, "Karnataka", "JD(S)", 0.097, 1),
            (2019, "Karnataka", "Others", 0.064, 1),
            
            # 2024 Karnataka Lok Sabha results
            (2024, "Karnataka", "BJP", 0.461, 17),
            (2024, "Karnataka", "INC", 0.454, 9),
            (2024, "Karnataka", "JD(S)", 0.056, 2),
            (2024, "Karnataka", "Others", 0.029, 0),

            # Region-wise 2024 results
            (2024, "Bengaluru", "BJP", 0.550, 4),
            (2024, "Bengaluru", "INC", 0.400, 0),
            (2024, "Bengaluru", "JD(S)", 0.020, 0),
            (2024, "Bengaluru", "Others", 0.030, 0),

            (2024, "Old Mysore", "BJP", 0.250, 1),
            (2024, "Old Mysore", "INC", 0.480, 4),
            (2024, "Old Mysore", "JD(S)", 0.220, 2),
            (2024, "Old Mysore", "Others", 0.050, 0),

            (2024, "Coastal Karnataka", "BJP", 0.600, 3),
            (2024, "Coastal Karnataka", "INC", 0.350, 0),
            (2024, "Coastal Karnataka", "JD(S)", 0.010, 0),
            (2024, "Coastal Karnataka", "Others", 0.040, 0),

            (2024, "Kittur Karnataka", "BJP", 0.520, 4),
            (2024, "Kittur Karnataka", "INC", 0.430, 2),
            (2024, "Kittur Karnataka", "JD(S)", 0.010, 0),
            (2024, "Kittur Karnataka", "Others", 0.040, 0),

            (2024, "Kalyana Karnataka", "BJP", 0.450, 2),
            (2024, "Kalyana Karnataka", "INC", 0.500, 3),
            (2024, "Kalyana Karnataka", "JD(S)", 0.010, 0),
            (2024, "Kalyana Karnataka", "Others", 0.040, 0),

            (2024, "Central Karnataka", "BJP", 0.540, 3),
            (2024, "Central Karnataka", "INC", 0.420, 0),
            (2024, "Central Karnataka", "JD(S)", 0.010, 0),
            (2024, "Central Karnataka", "Others", 0.030, 0),
        ]
        cursor.executemany("INSERT INTO historical_results (Year, State, PartyID, VoteShare, SeatsWon) VALUES (?, ?, ?, ?, ?);", historical)

        print("Seeding social media popularity data...")
        # Create social_popularity table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_popularity (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                PartyID TEXT NOT NULL,
                Platform TEXT NOT NULL,
                Score REAL NOT NULL,
                UpdatedAt TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        social_data = [
            ("BJP", "Twitter", 48.0),
            ("BJP", "Instagram", 44.0),
            ("BJP", "YouTube", 46.0),
            ("INC", "Twitter", 42.0),
            ("INC", "Instagram", 46.0),
            ("INC", "YouTube", 44.0),
            ("JD(S)", "Twitter", 7.0),
            ("JD(S)", "Instagram", 6.0),
            ("JD(S)", "YouTube", 8.0),
            ("Others", "Twitter", 3.0),
            ("Others", "Instagram", 4.0),
            ("Others", "YouTube", 2.0),
        ]
        cursor.executemany("INSERT INTO social_popularity (PartyID, Platform, Score) VALUES (?, ?, ?);", social_data)

        print("Seeding opinion polls (Karnataka)...")
        polls = [
            (
                "Karnataka Insights",
                "2026-05-20",
                12000,
                json.dumps({"BJP": 0.46, "INC": 0.44, "JD(S)": 0.07, "Others": 0.03})
            ),
            (
                "Lokniti-CSDS",
                "2026-06-01",
                8000,
                json.dumps({"BJP": 0.45, "INC": 0.45, "JD(S)": 0.06, "Others": 0.04})
            ),
            (
                "C-Voter Karnataka",
                "2026-06-05",
                10000,
                json.dumps({"BJP": 0.47, "INC": 0.43, "JD(S)": 0.07, "Others": 0.03})
            )
        ]
        cursor.executemany("INSERT INTO polls (Agency, Date, SampleSize, PartyVoteShare) VALUES (?, ?, ?, ?);", polls)
        
        conn.commit()
        print("Database seeded successfully with Karnataka data via sqlite3!")

if __name__ == "__main__":
    seed()
