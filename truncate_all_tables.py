import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from django.db import connection

# Tables to truncate (FK-safe order: children first)
# EXCLUDED: enduser, productcategory
TABLES = [
    'supplier_order_item',
    'supplier_order',
    'executive_allocation',
    'supplier_executive',
    'supplier_manager',
    'chat_message',
    'conversation',
    'supplier_product',
    'customerbill',
    'supplierbill',
    'customer',
    'supplieruser',
    'supplier',
    'products',
    'users',
    'company',
    'companycategory',
    'productunit',
]


def truncate_all_except_enduser_and_productcategory():
    print("=" * 60)
    print("  TRUNCATE + RESTART IDENTITY")
    print("  EXCLUDED: enduser, productcategory")
    print("=" * 60)

    with connection.cursor() as cursor:
        for table in TABLES:
            sql = f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;'
            cursor.execute(sql)
            print(f"  [OK] TRUNCATED {table}")

    print("=" * 60)
    print("  Done! All sequences reset.")
    print("  enduser         --> NOT touched")
    print("  productcategory --> NOT touched")
    print("=" * 60)


if __name__ == '__main__':
    truncate_all_except_enduser_and_productcategory()
