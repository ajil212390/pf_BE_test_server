import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import SupplierExecutive, ExecutiveAllocation, SupplierOrder, SupplierOrderItem

def truncate_tables():
    print("Cleaning newly added tables...")
    
    items_deleted, _ = SupplierOrderItem.objects.all().delete()
    print(f"Deleted {items_deleted} SupplierOrderItem records.")
    
    orders_deleted, _ = SupplierOrder.objects.all().delete()
    print(f"Deleted {orders_deleted} SupplierOrder records.")
    
    alloc_deleted, _ = ExecutiveAllocation.objects.all().delete()
    print(f"Deleted {alloc_deleted} ExecutiveAllocation records.")
    
    exec_deleted, _ = SupplierExecutive.objects.all().delete()
    print(f"Deleted {exec_deleted} SupplierExecutive records.")
    
    print("All newly added tables have been successfully truncated!")

if __name__ == '__main__':
    truncate_tables()
