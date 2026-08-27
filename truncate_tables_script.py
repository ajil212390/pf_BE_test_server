import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from django.db import connection

# Tables to truncate in FK-safe order (children first)
# EXCLUDED (KEPT): company, enduser, users, companycategory, productcategory
TABLES_TO_TRUNCATE = [
    'supplier_order_item',
    'supplier_order',
    'executive_allocation',
    'supplier_executive',
    'supplier_manager',
    'supplier_product',
    'chat_message',
    'conversation',
    'customerbill',
    'supplierbill',
    'customer',
    'supplieruser',
    'supplier',
    'products',
    'productunit',
]

def run_truncation():
    print("=" * 60)
    print("  TRUNCATING TABLES (EXCEPT 5 KEPT TABLES)")
    print("  KEPT TABLES: company, enduser, users, companycategory, productcategory")
    print("=" * 60)

    with connection.cursor() as cursor:
        for table in TABLES_TO_TRUNCATE:
            try:
                sql = f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;'
                cursor.execute(sql)
                print(f"  [OK] Truncated {table}")
            except Exception as e:
                print(f"  [ERROR] Could not truncate {table}: {e}")

    print("=" * 60)
    print("  FINISHED TABLE TRUNCATION!")
    print("=" * 60)

if __name__ == '__main__':
    run_truncation()
