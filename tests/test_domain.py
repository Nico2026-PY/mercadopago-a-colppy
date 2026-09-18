from datetime import date
from decimal import Decimal
import unittest

from src.mp_colppy.domain import normalize_row


def sample_row(**overrides):
    row = {
        "ID DE OPERACIÓN EN MERCADO PAGO": 160321104999,
        "TIPO DE OPERACIÓN": "Pago aprobado",
        "FECHA DE ORIGEN": "2026-05-26T15:15:48.000-04:00",
        "MONTO NETO DE LA OPERACIÓN QUE IMPACTÓ TU DINERO": 184980.87,
        "PAGADOR": "Cliente de prueba",
        "BANCO DE ORIGEN": "Banco ejemplo",
        "MEDIO DE PAGO": "Dinero disponible",
        "NOMBRE DE LOCAL": "Local de prueba",
    }
    row.update(overrides)
    return row


class DomainTests(unittest.TestCase):
    def test_creates_colppy_fields_from_spanish_headers(self):
        movement = normalize_row(sample_row(), "mayo.xlsx", 2)

        self.assertEqual(movement.date, date(2026, 5, 26))
        self.assertEqual(movement.amount, Decimal("184980.87"))
        self.assertEqual(movement.receipt, "160321104999")
        self.assertEqual(
            movement.concept,
            "Pago aprobado - Cliente de prueba - Banco ejemplo - Dinero disponible - Local de prueba",
        )

    def test_same_source_id_is_distinct_for_refund(self):
        payment = normalize_row(sample_row(), "mayo.xlsx", 2)
        refund = normalize_row(
            sample_row(
                **{
                    "TIPO DE OPERACIÓN": "Devolución de dinero",
                    "MONTO NETO DE LA OPERACIÓN QUE IMPACTÓ TU DINERO": -184980.87,
                }
            ),
            "mayo.xlsx",
            3,
        )

        self.assertNotEqual(payment.key, refund.key)
        self.assertEqual(refund.receipt, "160321104999-DEV")
        self.assertEqual(refund.amount, Decimal("-184980.87"))

    def test_omits_empty_concept_parts_and_limits_length(self):
        movement = normalize_row(
            sample_row(
                **{
                    "PAGADOR": "",
                    "BANCO DE ORIGEN": None,
                    "MEDIO DE PAGO": "X" * 300,
                    "NOMBRE DE LOCAL": None,
                }
            ),
            "mayo.xlsx",
            4,
        )

        self.assertFalse("None" in movement.concept)
        self.assertFalse(" -  - " in movement.concept)
        self.assertEqual(len(movement.concept), 255)

    def test_accepts_technical_column_codes(self):
        movement = normalize_row(
            {
                "SOURCE_ID": "ABC-9",
                "TRANSACTION_TYPE": "PAYOUTS",
                "TRANSACTION_DATE": "2026-06-01T09:30:00-03:00",
                "SETTLEMENT_NET_AMOUNT": -5000,
                "PAYER_NAME": "",
                "POI_BANK_NAME": "",
                "PAYMENT_METHOD": "Transferencia de dinero",
                "STORE_NAME": "",
            },
            "junio.xlsx",
            2,
        )

        self.assertEqual(movement.receipt, "ABC-9-PAYOUT")
        self.assertEqual(movement.date, date(2026, 6, 1))

    def test_rejects_missing_required_id(self):
        with self.assertRaisesRegex(ValueError, "ID de operación"):
            normalize_row(
                sample_row(**{"ID DE OPERACIÓN EN MERCADO PAGO": None}),
                "mayo.xlsx",
                9,
            )


if __name__ == "__main__":
    unittest.main()
