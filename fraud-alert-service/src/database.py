import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "fraud_alerts.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db(db_path: Path | None = None):
    conn = get_connection(db_path or DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    with db(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          TEXT PRIMARY KEY,
                amount      REAL NOT NULL,
                merchant_name TEXT NOT NULL,
                merchant_category TEXT NOT NULL,
                location    TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                card_id     TEXT NOT NULL,
                account_id  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id              TEXT PRIMARY KEY,
                transaction_id  TEXT NOT NULL UNIQUE,
                risk_score      REAL NOT NULL,
                risk_level      TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pending',
                analyst_id      TEXT,
                contains_pii    INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                status_history  TEXT NOT NULL,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            )
        """)
