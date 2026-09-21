from datetime import date
from decimal import Decimal
import unittest

from src.mp_colppy.domain import normalize_row


def sample_row(**overrides):
    row = {
        "ID DE OPERACIÓN EN MERCADO PAGO": 160321104999,
        "TIPO DE OPERACIÓN": "Pago aprobado",
        "FECHA DE ORIGEN": "2026-05-26T15:15:48.000-04:00",
        "VALOR DE LA COMPRA": 190000,
        "MONTO NETO DE LA OPERACIÓN QUE IMPACTÓ TU DINERO": 184980.87,
        "PAGADOR": "Cliente de prueba",
        "TIPO DE IDENTIFICACIÓN DEL PAGADOR": "CUIT",
        "NÚMERO DE IDENTIFICACIÓN DEL PAGADOR": "20123456789",
        "BANCO DE ORIGEN": "Banco ejemplo",
        "MEDIO DE PAGO": "Dinero disponible",
        "NOMBRE DE LOCAL": "Local de prueba",
    }
    row.update(overrides)
    return row


class DomainTests(unittest.TestCase):
    def test_uses_gross_purchase_amount_and_clean_concept_from_spanish_headers(self):
        movement = normalize_row(sample_row(), "mayo.xlsx", 2)

        self.assertEqual(movement.date, date(2026, 5, 26))
        self.assertEqual(movement.amount, Decimal("190000.00"))
        self.assertEqual(movement.receipt, "MP-160321104999")
        self.assertEqual(
            movement.concept,
            "Local de prueba - Cliente de prueba - CUIT - 20123456789",
        )

    def test_same_source_id_is_distinct_for_refund(self):
        payment = normalize_row(sample_row(), "mayo.xlsx", 2)
        refund = normalize_row(
            sample_row(
                **{
                    "TIPO DE OPERACIÓN": "Devolución de dinero",
                    "VALOR DE LA COMPRA": -190000,
                    "MONTO NETO DE LA OPERACIÓN QUE IMPACTÓ TU DINERO": -184980.87,
                }
            ),
            "mayo.xlsx",
            3,
        )

        self.assertNotEqual(payment.key, refund.key)
        self.assertEqual(refund.receipt, "MP-160321104999-DEV")
        self.assertEqual(refund.amount, Decimal("-190000.00"))
        self.assertEqual(
            refund.concept,
            "Devolución de dinero - Local de prueba - Cliente de prueba - CUIT - 20123456789",
        )

    def test_keeps_exceptional_type_when_other_concept_fields_are_empty(self):
        for transaction_type in ("PAYOUTS", "Reclamo"):
            with self.subTest(transaction_type=transaction_type):
                movement = normalize_row(
                    sample_row(
                        **{
                            "TIPO DE OPERACIÓN": transaction_type,
                            "PAGADOR": "",
                            "TIPO DE IDENTIFICACIÓN DEL PAGADOR": "",
                            "NÚMERO DE IDENTIFICACIÓN DEL PAGADOR": "",
                            "NOMBRE DE LOCAL": "",
                        }
                    ),
                    "mayo.xlsx",
                    3,
                )
                self.assertEqual(movement.concept, transaction_type)

    def test_omits_empty_concept_parts_and_limits_length(self):
        movement = normalize_row(
            sample_row(
                **{
                    "PAGADOR": "X" * 300,
                    "TIPO DE IDENTIFICACIÓN DEL PAGADOR": "",
                    "NÚMERO DE IDENTIFICACIÓN DEL PAGADOR": "",
                    "BANCO DE ORIGEN": None,
                    "MEDIO DE PAGO": "Dato que no debe incluirse",
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
                "TRANSACTION_AMOUNT": -5100,
                "SETTLEMENT_NET_AMOUNT": -5000,
                "PAYER_NAME": "",
                "POI_BANK_NAME": "",
                "PAYMENT_METHOD": "Transferencia de dinero",
                "STORE_NAME": "",
            },
            "junio.xlsx",
            2,
        )

        self.assertEqual(movement.receipt, "MP-ABC-9-PAYOUT")
        self.assertEqual(movement.date, date(2026, 6, 1))
        self.assertEqual(movement.amount, Decimal("-5100.00"))
        self.assertEqual(movement.concept, "PAYOUTS")

    def test_rejects_report_without_gross_purchase_amount(self):
        with self.assertRaisesRegex(ValueError, "valor de la compra"):
            normalize_row(
                sample_row(**{"VALOR DE LA COMPRA": None}),
                "mayo.xlsx",
                8,
            )

    def test_rejects_missing_required_id(self):
        with self.assertRaisesRegex(ValueError, "ID de operación"):
            normalize_row(
                sample_row(**{"ID DE OPERACIÓN EN MERCADO PAGO": None}),
                "mayo.xlsx",
                9,
            )


if __name__ == "__main__":
    unittest.main()
