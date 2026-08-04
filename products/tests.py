from decimal import Decimal
from django.test import SimpleTestCase
from .views import _build_financial_summary, _is_note_entry, _rollup_account_rows


class FinancialSummaryTests(SimpleTestCase):
    def test_build_financial_summary_formats_values(self):
        summary = _build_financial_summary(
            total_count=3,
            bill_count=4,
            bill_amount=Decimal('1250.50'),
            note_count=2,
            note_amount=Decimal('500.25'),
            paid_amount=Decimal('1000.00'),
            balance_amount=Decimal('250.50'),
        )

        self.assertEqual(summary['count'], 3)
        self.assertEqual(summary['bills_count'], 4)
        self.assertEqual(summary['bills_amount'], 1250.5)
        self.assertEqual(summary['notes_count'], 2)
        self.assertEqual(summary['notes_amount'], 500.25)
        self.assertEqual(summary['paid_amount'], 1000.0)
        self.assertEqual(summary['balance_amount'], 250.5)

    def test_rollup_account_rows_sums_each_account_balance(self):
        rows = [
            {
                'bills_count': 2,
                'bills_amount': 1450.0,
                'credit_notes_count': 1,
                'credit_notes_amount': 200.0,
                'paid_amount': 1000.0,
                'balance_amount': 1250.0,
            },
            {
                'bills_count': 2,
                'bills_amount': 2800.0,
                'credit_notes_count': 1,
                'credit_notes_amount': 300.0,
                'paid_amount': 1500.0,
                'balance_amount': 2000.0,
            },
        ]

        summary = _rollup_account_rows(rows)

        self.assertEqual(summary['bills_count'], 4)
        self.assertEqual(summary['bills_amount'], 4250.0)
        self.assertEqual(summary['notes_count'], 2)
        self.assertEqual(summary['notes_amount'], 500.0)
        self.assertEqual(summary['paid_amount'], 2500.0)
        self.assertEqual(summary['balance_amount'], 3250.0)

    def test_return_type_is_treated_as_note(self):
        self.assertTrue(_is_note_entry('Return'))
        self.assertTrue(_is_note_entry('Sales Return'))
        self.assertTrue(_is_note_entry('Credit Note'))
        self.assertFalse(_is_note_entry('Sales'))
        self.assertFalse(_is_note_entry('Purchase'))
