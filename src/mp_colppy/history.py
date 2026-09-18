from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Iterable, Iterator, Sequence

from .domain import Movement


class HistoryRepository:
    def __init__(self, db_path: str | Path, backup_dir: str | Path):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    source_files TEXT NOT NULL,
                    export_path TEXT NOT NULL,
                    confirmed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS movements (
                    movement_key TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    movement_date TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    concept TEXT NOT NULL,
                    receipt TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    source_row INTEGER NOT NULL,
                    batch_id INTEGER NOT NULL,
                    imported_at TEXT NOT NULL,
                    FOREIGN KEY(batch_id) REFERENCES batches(id)
                );

                CREATE INDEX IF NOT EXISTS idx_movements_source_id ON movements(source_id);
                CREATE INDEX IF NOT EXISTS idx_movements_date ON movements(movement_date);
                """
            )

    def imported_keys(self, keys: Iterable[str]) -> set[str]:
        key_list = list(dict.fromkeys(keys))
        if not key_list:
            return set()
        found: set[str] = set()
        with self._connection() as connection:
            for start in range(0, len(key_list), 800):
                chunk = key_list[start : start + 800]
                placeholders = ",".join("?" for _ in chunk)
                query = f"SELECT movement_key FROM movements WHERE movement_key IN ({placeholders})"
                found.update(row[0] for row in connection.execute(query, chunk))
        return found

    def movement_count(self) -> int:
        with self._connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM movements").fetchone()[0])

    def backup(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        destination = self.backup_dir / f"historial-{timestamp}.db"
        if not self.db_path.exists():
            self._initialize()
        shutil.copy2(self.db_path, destination)
        return destination

    def confirm_batch(
        self,
        mode: str,
        source_files: Sequence[str],
        movements: Sequence[Movement],
        export_path: str | Path,
    ) -> int:
        if not movements:
            raise ValueError("No hay movimientos nuevos para confirmar")
        if self.movement_count() > 0:
            self.backup()
        confirmed_at = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO batches(mode, source_files, export_path, confirmed_at) VALUES (?, ?, ?, ?)",
                (mode, json.dumps(list(source_files), ensure_ascii=False), str(export_path), confirmed_at),
            )
            batch_id = int(cursor.lastrowid)
            connection.executemany(
                """
                INSERT OR IGNORE INTO movements(
                    movement_key, source_id, movement_date, occurred_at,
                    transaction_type, amount, concept, receipt,
                    source_file, source_row, batch_id, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.key,
                        item.source_id,
                        item.date.isoformat(),
                        item.occurred_at,
                        item.transaction_type,
                        format(item.amount, ".2f"),
                        item.concept,
                        item.receipt,
                        item.source_file,
                        item.row_number,
                        batch_id,
                        confirmed_at,
                    )
                    for item in movements
                ],
            )
        return batch_id
