import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import SupplierProduct

products = SupplierProduct.objects.select_related('company', 'supplier', 'product').all()

print("| ID | Company Name (ID) | Product Name (ID) | Supplier Name (ID) | Supplier Price | Is Active |")
print("|---|---|---|---|---|---|")
for sp in products:
    print(f"| {sp.id} | {sp.company.companyname} ({sp.company.companyid}) | {sp.product.productname} ({sp.product.productid}) | {sp.supplier.suppliername} ({sp.supplier.supplierid}) | {sp.supplier_price} | {sp.is_active} |")
