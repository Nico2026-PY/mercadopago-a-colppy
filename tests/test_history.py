from datetime import date
from decimal import Decimal
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from src.mp_colppy.domain import Movement
from src.mp_colppy.history import HistoryRepository


def movement(key="k1", source_id="1", amount="10.00"):
    return Movement(
        key=key,
        source_id=source_id,
        date=date(2026, 9, 1),
        occurred_at="2026-09-01T10:00:00-03:00",
        transaction_type="Pago aprobado",
        amount=Decimal(amount),
        concept="Pago aprobado - Ana",
        receipt=source_id,
        source_file="diario.xlsx",
        row_number=2,
        raw={},
    )


class HistoryTests(unittest.TestCase):
    def test_repository_closes_every_database_connection(self):
        class TrackingRepository(HistoryRepository):
            def __init__(self, *args, **kwargs):
                self.connections = []
                super().__init__(*args, **kwargs)

            def _connect(self):
                connection = super()._connect()
                self.connections.append(connection)
                return connection

        with TemporaryDirectory() as temp:
            repo = TrackingRepository(Path(temp) / "historial.db", Path(temp) / "respaldos")
            repo.movement_count()

            for connection in repo.connections:
                with self.assertRaises(sqlite3.ProgrammingError):
                    connection.execute("SELECT 1")

    def test_confirms_batch_and_returns_imported_keys(self):
        with TemporaryDirectory() as temp:
            repo = HistoryRepository(Path(temp) / "datos" / "historial.db", Path(temp) / "respaldos")
            batch_id = repo.confirm_batch("Diario", ["diario.xlsx"], [movement()], "salida.xlsx")

            self.assertGreater(batch_id, 0)
            self.assertEqual(repo.imported_keys(["k1", "otra"]), {"k1"})
            self.assertEqual(repo.movement_count(), 1)

    def test_confirming_same_key_twice_does_not_duplicate_history(self):
        with TemporaryDirectory() as temp:
            repo = HistoryRepository(Path(temp) / "historial.db", Path(temp) / "respaldos")
            repo.confirm_batch("Diario", ["uno.xlsx"], [movement()], "uno.xlsx")
            repo.confirm_batch("Mensual", ["mes.xlsx"], [movement()], "mes.xlsx")

            self.assertEqual(repo.movement_count(), 1)

    def test_backup_copies_existing_database(self):
        with TemporaryDirectory() as temp:
            repo = HistoryRepository(Path(temp) / "historial.db", Path(temp) / "respaldos")
            repo.confirm_batch("Diario", ["uno.xlsx"], [movement()], "uno.xlsx")

            backup = repo.backup()

            self.assertTrue(backup.exists())
            self.assertGreater(backup.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
