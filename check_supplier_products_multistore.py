import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import SupplierProduct, Supplier, Products, Company

def check():
    s = Supplier.objects.get(supplierid=1)
    print(f"Base Supplier #1: {s.suppliername} (GST: {s.suppliergst})")
    
    matching_suppliers = Supplier.objects.filter(suppliergst=s.suppliergst)
    matching_ids = list(matching_suppliers.values_list('supplierid', flat=True))
    print(f"Matching Supplier IDs across stores: {matching_ids}")

    for supp in matching_suppliers:
        print(f"  Supplier Record ID #{supp.supplierid} -> Store: {supp.companyid.companyname} (Company ID #{supp.companyid.companyid})")

    for cid in [1, 2, 3]:
        comp = Company.objects.get(companyid=cid)
        sps = SupplierProduct.objects.filter(supplier_id__in=matching_ids, company_id=cid, is_active=True).select_related('product', 'supplier')
        print(f"\n  Store: '{comp.companyname}' (Company ID #{cid}) -> Products found: {sps.count()}")
        for sp in sps:
            print(f"    - Product: '{sp.product.productname}' | Supplier: '{sp.supplier.suppliername}' (SuppID #{sp.supplier.supplierid}) | Supplier Price: Rs.{sp.supplier_price}")

if __name__ == '__main__':
    check()
