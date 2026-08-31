import os
import django
from decimal import Decimal
from datetime import date
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Supplier

def seed_supplier_bills():
    print("=" * 70)
    print("  SEEDING SUPPLIER BILLS ACROSS ALL COMPANIES")
    print("=" * 70)

    cursor = connection.cursor()

    # Sync PostgreSQL sequence for sid
    cursor.execute("""
        SELECT setval('supplierbill_sid_seq', (SELECT COALESCE(MAX(sid), 1) FROM supplierbill));
    """)
    cursor.execute("SELECT COALESCE(MAX(supplierbillid), 1) FROM supplierbill")
    current_bill_id = cursor.fetchone()[0]

    def get_prefix(name):
        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0].upper()}{parts[1][0].upper()}"
        elif len(name) >= 2:
            return name[:2].upper()
        return "SB"

    suppliers = Supplier.objects.select_related('companyid').all().order_by('companyid', 'supplierid')
    inserted_rows = 0

    for supplier in suppliers:
        # Check existing bills for this supplier
        cursor.execute("SELECT COUNT(*) FROM supplierbill WHERE supplierid = %s", [supplier.supplierid])
        existing_count = cursor.fetchone()[0]
        if existing_count > 0:
            print(f"[SKIP] Supplier ID {supplier.supplierid} ('{supplier.suppliername}') already has {existing_count} bills.")
            continue

        prefix = get_prefix(supplier.suppliername)
        sid_str = str(supplier.supplierid)

        print(f"\n--> Generating bills for Supplier ID {supplier.supplierid}: {supplier.suppliername} ({supplier.companyid.companyname})")

        # -------------------------------------------------------------
        # PURCHASE INVOICE 1 (Purchase + 2 Payments)
        # -------------------------------------------------------------
        current_bill_id += 1
        inv1_id = current_bill_id
        inv1_no = f"{prefix}{sid_str}-001"
        inv1_date = date(2026, 8, 4)
        inv1_duedate = date(2026, 9, 4)
        inv1_amount = Decimal('2400.00')

        # Insert Purchase Bill 1
        cursor.execute("""
            INSERT INTO supplierbill (supplierbillid, supplierid, supplierbillno, supplierbilldate, supplierbillduedate, supplierbillamount, paidamount, balance, narration, supplierbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [inv1_id, supplier.supplierid, inv1_no, inv1_date, inv1_duedate, inv1_amount, Decimal('0.00'), Decimal('0.00'), 'purchase invoice', 'purchase'])
        inserted_rows += 1
        print(f"    [+ PURCHASE] bill_id: {inv1_id} | no: {inv1_no} | amount: Rs.{inv1_amount}")

        # Insert Payment 1 for Purchase 1 (shares SAME supplierbillid)
        p1_no = f"{prefix}{sid_str}R-001"
        p1_date = date(2026, 8, 9)
        p1_amount = Decimal('1000.00')
        cursor.execute("""
            INSERT INTO supplierbill (supplierbillid, supplierid, supplierbillno, supplierbilldate, supplierbillduedate, supplierbillamount, paidamount, balance, narration, supplierbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [inv1_id, supplier.supplierid, p1_no, p1_date, inv1_duedate, p1_amount, Decimal('0.00'), Decimal('0.00'), 'bank transfer installment 1', 'payment'])
        inserted_rows += 1
        print(f"    [+ PAYMENT] bill_id: {inv1_id} | no: {p1_no} | amount: Rs.{p1_amount}")

        # Insert Payment 2 for Purchase 1 (shares SAME supplierbillid)
        p2_no = f"{prefix}{sid_str}R-002"
        p2_date = date(2026, 8, 14)
        p2_amount = Decimal('1400.00')
        cursor.execute("""
            INSERT INTO supplierbill (supplierbillid, supplierid, supplierbillno, supplierbilldate, supplierbillduedate, supplierbillamount, paidamount, balance, narration, supplierbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [inv1_id, supplier.supplierid, p2_no, p2_date, inv1_duedate, p2_amount, Decimal('0.00'), Decimal('0.00'), 'full payment settlement', 'payment'])
        inserted_rows += 1
        print(f"    [+ PAYMENT] bill_id: {inv1_id} | no: {p2_no} | amount: Rs.{p2_amount}")

        # -------------------------------------------------------------
        # DEBIT NOTE / PURCHASE RETURN
        # -------------------------------------------------------------
        current_bill_id += 1
        rtn_id = current_bill_id
        rtn_no = f"{prefix}{sid_str}RTN-001"
        rtn_date = date(2026, 8, 17)
        rtn_amount = Decimal('400.00')
        cursor.execute("""
            INSERT INTO supplierbill (supplierbillid, supplierid, supplierbillno, supplierbilldate, supplierbillduedate, supplierbillamount, paidamount, balance, narration, supplierbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [rtn_id, supplier.supplierid, rtn_no, rtn_date, None, rtn_amount, Decimal('0.00'), Decimal('0.00'), 'damaged stock return / debit note', 'debit note'])
        inserted_rows += 1
        print(f"    [+ DEBIT NOTE] bill_id: {rtn_id} | no: {rtn_no} | amount: Rs.{rtn_amount}")

        # -------------------------------------------------------------
        # PURCHASE INVOICE 2 (Purchase + 1 Payment)
        # -------------------------------------------------------------
        current_bill_id += 1
        inv2_id = current_bill_id
        inv2_no = f"{prefix}{sid_str}-002"
        inv2_date = date(2026, 8, 21)
        inv2_duedate = date(2026, 9, 21)
        inv2_amount = Decimal('4800.00')

        # Insert Purchase Bill 2
        cursor.execute("""
            INSERT INTO supplierbill (supplierbillid, supplierid, supplierbillno, supplierbilldate, supplierbillduedate, supplierbillamount, paidamount, balance, narration, supplierbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [inv2_id, supplier.supplierid, inv2_no, inv2_date, inv2_duedate, inv2_amount, Decimal('0.00'), Decimal('0.00'), 'bulk stock purchase order', 'purchase'])
        inserted_rows += 1
        print(f"    [+ PURCHASE] bill_id: {inv2_id} | no: {inv2_no} | amount: Rs.{inv2_amount}")

        # Insert Payment for Purchase 2 (shares SAME supplierbillid)
        p3_no = f"{prefix}{sid_str}R-003"
        p3_date = date(2026, 8, 27)
        p3_amount = Decimal('2500.00')
        cursor.execute("""
            INSERT INTO supplierbill (supplierbillid, supplierid, supplierbillno, supplierbilldate, supplierbillduedate, supplierbillamount, paidamount, balance, narration, supplierbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [inv2_id, supplier.supplierid, p3_no, p3_date, inv2_duedate, p3_amount, Decimal('0.00'), Decimal('0.00'), 'advance payment against invoice', 'payment'])
        inserted_rows += 1
        print(f"    [+ PAYMENT] bill_id: {inv2_id} | no: {p3_no} | amount: Rs.{p3_amount}")

    print("\n" + "=" * 70)
    print(f"  SUCCESSFULLY INSERTED {inserted_rows} SUPPLIER BILL / PAYMENT / DEBIT NOTE ROWS!")
    cursor.execute("SELECT COUNT(*) FROM supplierbill")
    total_in_db = cursor.fetchone()[0]
    print(f"  TOTAL SUPPLIER BILLS IN DATABASE: {total_in_db}")
    print("=" * 70)

if __name__ == '__main__':
    seed_supplier_bills()
