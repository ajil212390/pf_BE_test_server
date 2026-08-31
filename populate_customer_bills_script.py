import os
import django
from decimal import Decimal
from datetime import date, timedelta
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Company, Customer

def seed_customers_and_bills():
    print("=" * 70)
    print("  SEEDING CUSTOMERS & BILLS ACROSS ALL COMPANIES")
    print("=" * 70)

    # 1. Ensure at least 4 customers for every company
    additional_customers = [
        # Company 3: AI Supermart
        {
            'company_id': 3,
            'name': 'Kiran Raj',
            'phone': '9847551122',
            'email': 'kiran.raj@gmail.com',
            'address': 'MG Road, Ernakulam',
            'pincode': '682011',
            'gst': '32ABCDE5050N1Z4',
            'pan': 'ABCDE5050N',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('600.00'),
        },
        {
            'company_id': 3,
            'name': 'Archana Mohan',
            'phone': '9847662233',
            'email': 'archana.m@gmail.com',
            'address': 'Kakkanad, Kochi',
            'pincode': '682030',
            'gst': '32ABCDE6060O1Z5',
            'pan': 'ABCDE6060O',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('0.00'),
        },

        # Company 4: Western Mart
        {
            'company_id': 4,
            'name': 'Arun Kumar',
            'phone': '9847773344',
            'email': 'arun.k@gmail.com',
            'address': 'Palarivattom, Kochi',
            'pincode': '682025',
            'gst': '32ABCDE7070P1Z6',
            'pan': 'ABCDE7070P',
            'state': 'Kerala',
            'opening_bal': Decimal('500.00'),
            'current_bal': Decimal('1800.00'),
        },

        # Company 6: Calvino Mart
        {
            'company_id': 6,
            'name': 'Suresh Babu',
            'phone': '9847884455',
            'email': 'suresh.b@gmail.com',
            'address': 'Mattancherry, Kochi',
            'pincode': '682002',
            'gst': '32ABCDE8080Q1Z7',
            'pan': 'ABCDE8080Q',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('950.00'),
        },
        {
            'company_id': 6,
            'name': 'Nikhil Das',
            'phone': '9847995566',
            'email': 'nikhil.das@gmail.com',
            'address': 'Fort Kochi, Kochi',
            'pincode': '682001',
            'gst': '32ABCDE9090R1Z8',
            'pan': 'ABCDE9090R',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('0.00'),
        },
    ]

    for data in additional_customers:
        try:
            company = Company.objects.get(companyid=data['company_id'])
            cust, created = Customer.objects.get_or_create(
                customername=data['name'],
                companyid=company,
                defaults={
                    'customerphonenumber': data['phone'],
                    'customeraddress': data['address'],
                    'customeremail': data['email'],
                    'customercurrentbal': data['current_bal'],
                    'customeropeningbal': data['opening_bal'],
                    'customerpincode': data['pincode'],
                    'customergst': data['gst'],
                    'customerstate': data['state'],
                    'customerpanno': data['pan'],
                }
            )
            if created:
                print(f"[CREATED CUSTOMER] ID {cust.customerid}: '{cust.customername}' -> {company.companyname}")
            else:
                print(f"[EXISTS CUSTOMER] ID {cust.customerid}: '{cust.customername}' -> {company.companyname}")
        except Exception as e:
            print(f"[ERROR CREATING CUSTOMER] {data['name']}: {e}")

    # 2. Add Customer Bills for customers
    cursor = connection.cursor()
    # Sync PostgreSQL sequence for cid
    cursor.execute("""
        SELECT setval('customerbill_cid_seq', (SELECT COALESCE(MAX(cid), 1) FROM customerbill));
    """)
    cursor.execute("SELECT COALESCE(MAX(customerbillid), 1) FROM customerbill")
    current_bill_id = cursor.fetchone()[0]

    # Map initials/prefix for each customer
    def get_prefix(name):
        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0].upper()}{parts[1][0].upper()}"
        elif len(name) >= 2:
            return name[:2].upper()
        return "CB"

    # All customers
    all_customers = Customer.objects.select_related('companyid').all().order_by('companyid', 'customerid')

    inserted_bill_rows = 0

    for customer in all_customers:
        # Check if customer already has bills
        cursor.execute("SELECT COUNT(*) FROM customerbill WHERE customerid = %s", [customer.customerid])
        existing_bill_count = cursor.fetchone()[0]
        if existing_bill_count > 0:
            print(f"[SKIP BILLS] Customer ID {customer.customerid} ('{customer.customername}') already has {existing_bill_count} bills.")
            continue

        prefix = get_prefix(customer.customername)
        cid_str = str(customer.customerid)

        print(f"\n--> Generating bills for Customer ID {customer.customerid}: {customer.customername} ({customer.companyid.companyname})")

        # -------------------------------------------------------------
        # INVOICE 1 (Sales + Receipts)
        # -------------------------------------------------------------
        current_bill_id += 1
        inv1_bill_id = current_bill_id
        inv1_no = f"{prefix}{cid_str}-001"
        inv1_date = date(2026, 8, 5)
        inv1_duedate = date(2026, 9, 5)
        inv1_amount = Decimal('1800.00')

        # Insert Sales Bill 1
        cursor.execute("""
            INSERT INTO customerbill (customerbillid, customerid, customerbillno, customerbilldate, customerbillduedate, customerbillamount, paidamount, balance, narration, customerbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [inv1_bill_id, customer.customerid, inv1_no, inv1_date, inv1_duedate, inv1_amount, Decimal('0.00'), Decimal('0.00'), 'sales invoice', 'sales'])
        inserted_bill_rows += 1
        print(f"    [+ SALES] bill_id: {inv1_bill_id} | no: {inv1_no} | amount: Rs.{inv1_amount}")

        # Insert Receipt 1 for Invoice 1 (shares SAME customerbillid)
        r1_no = f"{prefix}{cid_str}R-001"
        r1_date = date(2026, 8, 10)
        r1_amount = Decimal('800.00')
        cursor.execute("""
            INSERT INTO customerbill (customerbillid, customerid, customerbillno, customerbilldate, customerbillduedate, customerbillamount, paidamount, balance, narration, customerbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [inv1_bill_id, customer.customerid, r1_no, r1_date, inv1_duedate, r1_amount, Decimal('0.00'), Decimal('0.00'), 'part receipt', 'receipt'])
        inserted_bill_rows += 1
        print(f"    [+ RECEIPT] bill_id: {inv1_bill_id} | no: {r1_no} | amount: Rs.{r1_amount}")

        # Insert Receipt 2 for Invoice 1 (shares SAME customerbillid)
        r2_no = f"{prefix}{cid_str}R-002"
        r2_date = date(2026, 8, 15)
        r2_amount = Decimal('1000.00')
        cursor.execute("""
            INSERT INTO customerbill (customerbillid, customerid, customerbillno, customerbilldate, customerbillduedate, customerbillamount, paidamount, balance, narration, customerbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [inv1_bill_id, customer.customerid, r2_no, r2_date, inv1_duedate, r2_amount, Decimal('0.00'), Decimal('0.00'), 'full payment settlement', 'receipt'])
        inserted_bill_rows += 1
        print(f"    [+ RECEIPT] bill_id: {inv1_bill_id} | no: {r2_no} | amount: Rs.{r2_amount}")

        # -------------------------------------------------------------
        # RETURN / CREDIT NOTE
        # -------------------------------------------------------------
        current_bill_id += 1
        rtn_bill_id = current_bill_id
        rtn_no = f"{prefix}{cid_str}RTN-001"
        rtn_date = date(2026, 8, 18)
        rtn_amount = Decimal('300.00')
        cursor.execute("""
            INSERT INTO customerbill (customerbillid, customerid, customerbillno, customerbilldate, customerbillduedate, customerbillamount, paidamount, balance, narration, customerbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [rtn_bill_id, customer.customerid, rtn_no, rtn_date, None, rtn_amount, Decimal('0.00'), Decimal('0.00'), 'goods return / damage credit note', 'return'])
        inserted_bill_rows += 1
        print(f"    [+ RETURN] bill_id: {rtn_bill_id} | no: {rtn_no} | amount: Rs.{rtn_amount}")

        # -------------------------------------------------------------
        # INVOICE 2 (Sales + Receipt)
        # -------------------------------------------------------------
        current_bill_id += 1
        inv2_bill_id = current_bill_id
        inv2_no = f"{prefix}{cid_str}-002"
        inv2_date = date(2026, 8, 22)
        inv2_duedate = date(2026, 9, 22)
        inv2_amount = Decimal('3500.00')

        # Insert Sales Bill 2
        cursor.execute("""
            INSERT INTO customerbill (customerbillid, customerid, customerbillno, customerbilldate, customerbillduedate, customerbillamount, paidamount, balance, narration, customerbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [inv2_bill_id, customer.customerid, inv2_no, inv2_date, inv2_duedate, inv2_amount, Decimal('0.00'), Decimal('0.00'), 'sales invoice bulk order', 'sales'])
        inserted_bill_rows += 1
        print(f"    [+ SALES] bill_id: {inv2_bill_id} | no: {inv2_no} | amount: Rs.{inv2_amount}")

        # Insert Receipt for Invoice 2 (shares SAME customerbillid)
        r3_no = f"{prefix}{cid_str}R-003"
        r3_date = date(2026, 8, 26)
        r3_amount = Decimal('2000.00')
        cursor.execute("""
            INSERT INTO customerbill (customerbillid, customerid, customerbillno, customerbilldate, customerbillduedate, customerbillamount, paidamount, balance, narration, customerbilltype)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [inv2_bill_id, customer.customerid, r3_no, r3_date, inv2_duedate, r3_amount, Decimal('0.00'), Decimal('0.00'), 'partial advance payment', 'receipt'])
        inserted_bill_rows += 1
        print(f"    [+ RECEIPT] bill_id: {inv2_bill_id} | no: {r3_no} | amount: Rs.{r3_amount}")

    print("\n" + "=" * 70)
    print(f"  SUCCESSFULLY INSERTED {inserted_bill_rows} BILL / RECEIPT / RETURN ROWS!")
    cursor.execute("SELECT COUNT(*) FROM customerbill")
    total_in_db = cursor.fetchone()[0]
    print(f"  TOTAL CUSTOMER BILLS IN DATABASE: {total_in_db}")
    print("=" * 70)

if __name__ == '__main__':
    seed_customers_and_bills()
