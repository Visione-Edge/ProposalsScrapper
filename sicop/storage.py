"""Almacenamiento SQLite para licitaciones."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .client import Tender


class Storage:
    """Persiste licitaciones en SQLite para detectar nuevas."""

    def __init__(self, db_path: str | Path = "data/licitaciones.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tenders (
                cartel_no TEXT NOT NULL,
                cartel_seq TEXT NOT NULL,
                inst_cartel_no TEXT,
                name TEXT,
                institution_code TEXT,
                institution_name TEXT,
                procedure_type TEXT,
                status TEXT,
                registration_date TEXT,
                bid_start_date TEXT,
                bid_end_date TEXT,
                opening_date TEXT,
                executor_name TEXT,
                relevance TEXT DEFAULT 'no_relevante',
                matched_keywords TEXT DEFAULT '[]',
                first_seen TEXT DEFAULT (datetime('now', 'localtime')),
                last_seen TEXT DEFAULT (datetime('now', 'localtime')),
                raw_json TEXT,
                favorite INTEGER DEFAULT 0,
                not_interested INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                PRIMARY KEY (cartel_no, cartel_seq)
            );

            CREATE INDEX IF NOT EXISTS idx_relevance ON tenders(relevance);
            CREATE INDEX IF NOT EXISTS idx_institution ON tenders(institution_name);
            CREATE INDEX IF NOT EXISTS idx_reg_date ON tenders(registration_date);
        """)
        # Migrate existing databases that lack the new columns
        existing = {row[1] for row in self._conn.execute("PRAGMA table_info(tenders)")}
        for col, definition in [
            ("favorite", "INTEGER DEFAULT 0"),
            ("not_interested", "INTEGER DEFAULT 0"),
            ("notes", "TEXT DEFAULT ''"),
        ]:
            if col not in existing:
                self._conn.execute(f"ALTER TABLE tenders ADD COLUMN {col} {definition}")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_favorite ON tenders(favorite)")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Storage:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def get_known_ids(self) -> set[tuple[str, str]]:
        rows = self._conn.execute("SELECT cartel_no, cartel_seq FROM tenders").fetchall()
        return {(r["cartel_no"], r["cartel_seq"]) for r in rows}

    def upsert_tender(
        self,
        tender: Tender,
        relevance: str = "no_relevante",
        matched_keywords: list[str] | None = None,
    ) -> bool:
        """Inserta o actualiza una licitación. Retorna True si es nueva."""
        keywords_json = json.dumps(matched_keywords or [], ensure_ascii=False)
        raw_json = json.dumps(tender.raw, ensure_ascii=False, default=str)

        cursor = self._conn.execute(
            """
            INSERT INTO tenders (
                cartel_no, cartel_seq, inst_cartel_no, name,
                institution_code, institution_name, procedure_type,
                status, registration_date, bid_start_date, bid_end_date,
                opening_date, executor_name, relevance, matched_keywords, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cartel_no, cartel_seq) DO UPDATE SET
                status = excluded.status,
                last_seen = datetime('now', 'localtime'),
                bid_end_date = excluded.bid_end_date
            """,
            (
                tender.cartel_no, tender.cartel_seq, tender.inst_cartel_no,
                tender.name, tender.institution_code, tender.institution_name,
                tender.procedure_type, tender.status, tender.registration_date,
                tender.bid_start_date, tender.bid_end_date, tender.opening_date,
                tender.executor_name, relevance, keywords_json, raw_json,
            ),
        )
        self._conn.commit()
        return cursor.rowcount == 1 and cursor.lastrowid is not None

    def toggle_favorite(self, cartel_no: str, cartel_seq: str) -> bool:
        self._conn.execute(
            "UPDATE tenders SET favorite = CASE WHEN favorite=1 THEN 0 ELSE 1 END WHERE cartel_no=? AND cartel_seq=?",
            (cartel_no, cartel_seq),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT favorite FROM tenders WHERE cartel_no=? AND cartel_seq=?",
            (cartel_no, cartel_seq),
        ).fetchone()
        return bool(row["favorite"]) if row else False

    def toggle_not_interested(self, cartel_no: str, cartel_seq: str) -> bool:
        self._conn.execute(
            "UPDATE tenders SET not_interested = CASE WHEN not_interested=1 THEN 0 ELSE 1 END WHERE cartel_no=? AND cartel_seq=?",
            (cartel_no, cartel_seq),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT not_interested FROM tenders WHERE cartel_no=? AND cartel_seq=?",
            (cartel_no, cartel_seq),
        ).fetchone()
        return bool(row["not_interested"]) if row else False

    def save_notes(self, cartel_no: str, cartel_seq: str, notes: str) -> None:
        self._conn.execute(
            "UPDATE tenders SET notes=? WHERE cartel_no=? AND cartel_seq=?",
            (notes, cartel_no, cartel_seq),
        )
        self._conn.commit()

    def get_all_tenders(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM tenders ORDER BY registration_date DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("matched_keywords"), str):
                try:
                    d["matched_keywords"] = json.loads(d["matched_keywords"])
                except Exception:
                    d["matched_keywords"] = []
            result.append(d)
        return result

    def get_stats(self) -> dict:
        total = self._conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
        favorites = self._conn.execute("SELECT COUNT(*) FROM tenders WHERE favorite=1").fetchone()[0]
        by_relevance: dict = {}
        for row in self._conn.execute("SELECT relevance, COUNT(*) as cnt FROM tenders GROUP BY relevance"):
            by_relevance[row["relevance"]] = row["cnt"]
        by_institution: dict = {}
        for row in self._conn.execute(
            "SELECT institution_name, COUNT(*) as cnt FROM tenders GROUP BY institution_name ORDER BY cnt DESC LIMIT 20"
        ):
            by_institution[row["institution_name"]] = row["cnt"]
        return {
            "total": total,
            "favorites": favorites,
            "by_relevance": by_relevance,
            "by_institution": by_institution,
        }
