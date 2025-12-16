import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from messages import Transcript, message_from_dict


DB_FILE = Path(__file__).parent.parent / "data" / "chat_history.db"

def initialize_database():
    """Initializes the database and creates the users and transcripts tables if they don't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Create transcripts table with user_id and summary
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                problem_type TEXT NOT NULL,
                transcript TEXT NOT NULL,
                summary TEXT,
                scores TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
        _ensure_scores_column(cursor)
        
        # Create default admin user if it doesn't exist
        _create_default_admin(cursor)
        conn.commit()

def _ensure_scores_column(cursor):
    """Add scores column to transcripts if it doesn't exist (idempotent)."""
    cursor.execute("PRAGMA table_info(transcripts)")
    columns = [row[1] for row in cursor.fetchall()]
    if "scores" not in columns:
        cursor.execute("ALTER TABLE transcripts ADD COLUMN scores TEXT")
        cursor.connection.commit()

def _create_default_admin(cursor):
    """Create a default admin user if no users exist."""
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # Default admin: username='admin', password='admin' (change this in production!)
        password_hash = hashlib.sha256("admin".encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users (username, password_hash, is_admin)
            VALUES (?, ?, ?)
        """, ("admin", password_hash, 1))

def create_user(username: str, password: str, is_admin: bool = False) -> Optional[int]:
    """Creates a new user and returns the user ID, or None if username already exists."""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, is_admin)
                VALUES (?, ?, ?)
            """, (username, password_hash, 1 if is_admin else 0))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates a user and returns user info if successful, None otherwise."""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, is_admin FROM users
            WHERE username = ? AND password_hash = ?
        """, (username, password_hash))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Gets user information by username."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, is_admin FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def save_transcript(
    user_id: int,
    session_id: str,
    problem_type: str,
    transcript: Transcript,
    summary: Optional[str] = None,
    scores: Optional[list[dict]] = None,
):
    """Saves a chat transcript with user_id, summary, and optional scores."""
    timestamp = datetime.now().isoformat()
    transcript_json = json.dumps(transcript.serialize())
    scores_json = json.dumps(scores) if scores is not None else None
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transcripts (user_id, session_id, timestamp, problem_type, transcript, summary, scores)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, session_id, timestamp, problem_type, transcript_json, summary, scores_json))
        conn.commit()

def get_user_sessions(user_id: int) -> List[Dict[str, Any]]:
    """Retrieves all sessions for a specific user."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, timestamp, problem_type, summary, scores
            FROM transcripts
            WHERE user_id = ?
            ORDER BY timestamp DESC
        """, (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_all_sessions_for_admin() -> List[Dict[str, Any]]:
    """Retrieves all sessions for admin view, including username."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.session_id, t.timestamp, t.problem_type, t.summary, t.scores,
                   u.username
            FROM transcripts t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.timestamp DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_transcript_by_id(transcript_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a specific transcript by its ID. If user_id is provided, only returns if it belongs to that user."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT t.*, u.username
                FROM transcripts t
                JOIN users u ON t.user_id = u.id
                WHERE t.id = ? AND t.user_id = ?
            """, (transcript_id, user_id))
        else:
            cursor.execute("""
                SELECT t.*, u.username
                FROM transcripts t
                JOIN users u ON t.user_id = u.id
                WHERE t.id = ?
            """, (transcript_id,))
        row = cursor.fetchone()
        if row:
            transcript_data = dict(row)
            # Also deserialize the transcript content into a Transcript object
            transcript_json = json.loads(transcript_data['transcript'])
            messages = [message_from_dict(msg) for msg in transcript_json]
            transcript_data['transcript_obj'] = Transcript(messages)
            # Deserialize scores if present
            raw_scores = transcript_data.get("scores")
            if raw_scores:
                try:
                    transcript_data["scores_obj"] = json.loads(raw_scores)
                except (json.JSONDecodeError, TypeError):
                    transcript_data["scores_obj"] = None
            return transcript_data
        return None
