import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Company, Products, Supplier, Supplieruser, SupplierProduct

def seed_all():
    print("=" * 80)
    print("  SEEDING PRODUCTS FOR ALL 5 ONBOARDED SUPPLIERS ACROSS ALL CONNECTED STORES")
    print("=" * 80)

    # 1. Map onboarded suppliers to connected stores
    supplier_connections = {
        'abctraders': [1, 2, 3],        # AN Gallery, Navas Bakers, AI Supermart
        'malabarbakers': [2, 3, 4],     # Navas Bakers, AI Supermart, Western Mart
        'keralagrains': [3, 6, 4],      # AI Supermart, Calvino Mart, Western Mart
        'metrosweets': [4, 2, 1],       # Western Mart, Navas Bakers, AN Gallery
        'greencare': [6, 3, 1],         # Calvino Mart, AI Supermart, AN Gallery
    }

    supplier_users = Supplieruser.objects.select_related('supplierid').all().order_by('supplieruserid')
    total_sp_created = 0

    for su in supplier_users:
        uname = su.supplierusername
        base_supp = su.supplierid
        target_comp_ids = supplier_connections.get(uname, [base_supp.companyid.companyid])

        # Get all Supplier model records matching this supplier's GST or name
        all_supp_records = list(Supplier.objects.filter(suppliergst=base_supp.suppliergst))
        if base_supp not in all_supp_records:
            all_supp_records.append(base_supp)

        print(f"\n==========================================================================")
        print(f"  SUPPLIER: '{base_supp.suppliername}' (Username: '{uname}' | Base SuppID #{base_supp.supplierid})")
        print(f"==========================================================================")

        for cid in target_comp_ids:
            comp = Company.objects.get(companyid=cid)
            
            # Find store-specific supplier record or use base_supp
            store_supp = next((s for s in all_supp_records if s.companyid_id == cid), None)
            if not store_supp:
                store_supp, created = Supplier.objects.get_or_create(
                    companyid=comp,
                    suppliergst=base_supp.suppliergst,
                    defaults={
                        'suppliername': base_supp.suppliername,
                        'supplierphonenumber': base_supp.supplierphonenumber,
                        'supplieremail': base_supp.supplieremail,
                        'supplieraddress': base_supp.supplieraddress,
                        'supplierpincode': base_supp.supplierpincode,
                        'supplierpanno': base_supp.supplierpanno,
                        'supplierstate': base_supp.supplierstate,
                        'isconnected': 1,
                        'suppliercurrentbal': 0.00,
                        'supplieropeningbal': 0.00,
                    }
                )
                all_supp_records.append(store_supp)

            store_supp.isconnected = 1
            store_supp.save()

            # Get products for this store (4 to 5 products)
            prods = list(Products.objects.filter(companyid=comp).order_by('productid')[:5])
            print(f"  -> Connected Store: '{comp.companyname}' (CompID #{cid}) | Linking {len(prods)} products:")

            for p in prods:
                wholesale_p = round(float(p.productprice) * 0.92, 2)
                
                # Link for store-specific supplier record
                sp1, c1 = SupplierProduct.objects.get_or_create(
                    supplier=store_supp,
                    product=p,
                    company=comp,
                    defaults={'supplier_price': wholesale_p, 'is_active': True}
                )
                if c1: total_sp_created += 1

                # Link for base supplier record as well
                if base_supp != store_supp:
                    sp2, c2 = SupplierProduct.objects.get_or_create(
                        supplier=base_supp,
                        product=p,
                        company=comp,
                        defaults={'supplier_price': wholesale_p, 'is_active': True}
                    )
                    if c2: total_sp_created += 1

                print(f"     • '{p.productname}' (Retail: Rs.{p.productprice} -> Wholesale: Rs.{wholesale_p})")

    print("\n" + "=" * 80)
    print(f"  ALL 5 ONBOARDED SUPPLIERS FULLY POPULATED!")
    print(f"  Total New SupplierProduct Links Created: {total_sp_created}")
    print("=" * 80)

if __name__ == '__main__':
    seed_all()
