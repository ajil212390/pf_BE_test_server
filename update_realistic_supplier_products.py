import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import SupplierProduct, Supplier, Products, Company

def populate_realistic():
    print("=" * 75)
    print("  SETTING REALISTIC SUPPLIER_PRODUCT MAPPINGS")
    print("  - Multi-supplier test case ONLY in 'AN Gallery' (2-3 products)")
    print("  - All other stores/products mapped to distinct single suppliers")
    print("=" * 75)

    SupplierProduct.objects.all().delete()
    count = 0

    # 1. AN Gallery (Company 1)
    # Suppliers: ABC Traders (1), Global Electronics Supplies (2)
    s1 = Supplier.objects.get(supplierid=1)
    s2 = Supplier.objects.get(supplierid=2)
    c1_prods = Products.objects.filter(companyid=1).order_by('productid')

    # Earbuds & Cable get 2 suppliers (Multi-supplier test case for AN Gallery)
    for p in c1_prods:
        rp = float(p.productprice)
        if 'Earbuds' in p.productname or 'Cable' in p.productname:
            # Supplier 1
            sp1 = SupplierProduct.objects.create(supplier=s1, company=s1.companyid, product=p, supplier_price=round(rp * 0.95, 2), is_active=True)
            # Supplier 2 (different price for test)
            sp2 = SupplierProduct.objects.create(supplier=s2, company=s2.companyid, product=p, supplier_price=round(rp * 0.90, 2), is_active=True)
            count += 2
            print(f"  [Multi-Supplier Test] '{p.productname}' -> Supplied by BOTH {s1.suppliername} (Rs.{sp1.supplier_price}) and {s2.suppliername} (Rs.{sp2.supplier_price})")
        elif 'Speaker' in p.productname:
            sp = SupplierProduct.objects.create(supplier=s2, company=s2.companyid, product=p, supplier_price=round(rp * 0.92, 2), is_active=True)
            count += 1
            print(f"  [Single Supplier] '{p.productname}' -> Supplied by {s2.suppliername} (Rs.{sp.supplier_price})")
        else:
            sp = SupplierProduct.objects.create(supplier=s1, company=s1.companyid, product=p, supplier_price=round(rp * 0.95, 2), is_active=True)
            count += 1
            print(f"  [Single Supplier] '{p.productname}' -> Supplied by {s1.suppliername} (Rs.{sp.supplier_price})")

    # 2. Navas Bakers (Company 2)
    # Suppliers: Malabar Flour & Bakery Goods (3), Royal Dairy & Agro Industries (4)
    s3 = Supplier.objects.get(supplierid=3)
    s4 = Supplier.objects.get(supplierid=4)
    c2_prods = Products.objects.filter(companyid=2).order_by('productid')
    for p in c2_prods:
        rp = float(p.productprice)
        supp = s3 if ('Bread' in p.productname or 'Cake' in p.productname or 'Cookies' in p.productname) else s4
        sp = SupplierProduct.objects.create(supplier=supp, company=supp.companyid, product=p, supplier_price=round(rp * 0.95, 2), is_active=True)
        count += 1
        print(f"  [Single Supplier] '{p.productname}' -> Supplied by {supp.suppliername} (Rs.{sp.supplier_price})")

    # 3. AI Supermart (Company 3)
    # Suppliers: Kerala Grains & Pulses (5), Coastal Spice & Beverages (6)
    s5 = Supplier.objects.get(supplierid=5)
    s6 = Supplier.objects.get(supplierid=6)
    c3_prods = Products.objects.filter(companyid=3).order_by('productid')
    for p in c3_prods:
        rp = float(p.productprice)
        supp = s5 if ('Rice' in p.productname or 'Flour' in p.productname or 'Oil' in p.productname) else s6
        sp = SupplierProduct.objects.create(supplier=supp, company=supp.companyid, product=p, supplier_price=round(rp * 0.95, 2), is_active=True)
        count += 1
        print(f"  [Single Supplier] '{p.productname}' -> Supplied by {supp.suppliername} (Rs.{sp.supplier_price})")

    # 4. Western Mart (Company 4)
    # Suppliers: Metro Confectionery & Sweets (7), Supreme Personal Care (8)
    s7 = Supplier.objects.get(supplierid=7)
    s8 = Supplier.objects.get(supplierid=8)
    c4_prods = Products.objects.filter(companyid=4).order_by('productid')
    for p in c4_prods:
        rp = float(p.productprice)
        supp = s7 if ('Chocolate' in p.productname or 'Chips' in p.productname) else s8
        sp = SupplierProduct.objects.create(supplier=supp, company=supp.companyid, product=p, supplier_price=round(rp * 0.95, 2), is_active=True)
        count += 1
        print(f"  [Single Supplier] '{p.productname}' -> Supplied by {supp.suppliername} (Rs.{sp.supplier_price})")

    # 5. Calvino Mart (Company 6)
    # Suppliers: GreenCare Household Hygiene (9), Apex FMCG Merchants (10)
    s9 = Supplier.objects.get(supplierid=9)
    s10 = Supplier.objects.get(supplierid=10)
    c6_prods = Products.objects.filter(companyid=6).order_by('productid')
    for p in c6_prods:
        rp = float(p.productprice)
        supp = s10 if ('Milk' in p.productname or 'Ghee' in p.productname) else s9
        sp = SupplierProduct.objects.create(supplier=supp, company=supp.companyid, product=p, supplier_price=round(rp * 0.95, 2), is_active=True)
        count += 1
        print(f"  [Single Supplier] '{p.productname}' -> Supplied by {supp.suppliername} (Rs.{sp.supplier_price})")

    print("=" * 75)
    print(f"  FINISHED! Total SupplierProduct Mappings: {count}")
    print("=" * 75)

if __name__ == '__main__':
    populate_realistic()
