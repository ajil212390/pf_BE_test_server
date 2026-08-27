import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import SupplierProduct, Supplier, Products, Company

def populate():
    print("=" * 70)
    print("  POPULATING SUPPLIER_PRODUCT TABLE WITH NEW PRODUCTS & SUPPLIERS")
    print("=" * 70)

    SupplierProduct.objects.all().delete()
    count = 0

    suppliers = Supplier.objects.select_related('companyid').all().order_by('supplierid')
    for supp in suppliers:
        comp = supp.companyid
        prods = Products.objects.filter(companyid=comp).order_by('productid')
        print(f"\n  Supplier: {supp.suppliername} (ID: {supp.supplierid}) -> Connected Store: {comp.companyname}")
        for p in prods:
            wholesale_price = round(float(p.productprice) * 0.95, 2)
            sp = SupplierProduct.objects.create(
                supplier=supp,
                company=comp,
                product=p,
                supplier_price=wholesale_price,
                is_active=True
            )
            count += 1
            print(f"    - SpID #{sp.id}: Product '{p.productname}' (Retail: Rs.{p.productprice} -> Supplier Price: Rs.{sp.supplier_price})")

    print("=" * 70)
    print(f"  SUCCESSFULLY POPULATED {count} SUPPLIER PRODUCT ENTRIES!")
    print("=" * 70)

if __name__ == '__main__':
    populate()
