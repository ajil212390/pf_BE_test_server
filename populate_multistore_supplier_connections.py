import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Company, Products, Supplier, Supplieruser, SupplierProduct

def create_multistore_connections():
    print("=" * 75)
    print("  CONNECTING ONBOARDED SUPPLIERS TO MULTIPLE STORES & POPULATING CATALOGS")
    print("=" * 75)

    # Fetch onboarded supplier users
    supplier_users = Supplieruser.objects.select_related('supplierid').all().order_by('supplieruserid')
    
    # Store connection maps for each onboarded supplier
    multi_connections = {
        # ABC Traders -> AN Gallery (1), Navas Bakers (2), AI Supermart (3)
        'abctraders': [1, 2, 3],
        # Malabar Flour & Bakery Goods -> Navas Bakers (2), AI Supermart (3), Western Mart (4)
        'malabarbakers': [2, 3, 4],
        # Kerala Grains & Pulses -> AI Supermart (3), Calvino Mart (6), Western Mart (4)
        'keralagrains': [3, 6, 4],
        # Metro Confectionery & Sweets -> Western Mart (4), Navas Bakers (2)
        'metrosweets': [4, 2],
        # GreenCare Household Hygiene -> Calvino Mart (6), AI Supermart (3)
        'greencare': [6, 3],
    }

    total_supp_created = 0
    total_sp_created = 0

    for su in supplier_users:
        uname = su.supplierusername
        base_supp = su.supplierid
        target_comp_ids = multi_connections.get(uname, [base_supp.companyid.companyid])

        print(f"\n  Supplier User: '{uname}' ({base_supp.suppliername})")

        for cid in target_comp_ids:
            comp = Company.objects.get(companyid=cid)
            
            # Check or create connected Supplier record for this store
            supp_record, created = Supplier.objects.get_or_create(
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
            
            if created:
                total_supp_created += 1
                print(f"    [NEW CONNECTION] Connected to Store: {comp.companyname} (Supplier ID #{supp_record.supplierid})")
            else:
                supp_record.isconnected = 1
                supp_record.save()
                print(f"    [EXISTING CONNECTION] Store: {comp.companyname} (Supplier ID #{supp_record.supplierid})")

            # Link products of this store to the supplier
            comp_prods = Products.objects.filter(companyid=comp)
            for p in comp_prods:
                wholesale_p = round(float(p.productprice) * 0.93, 2)
                # Link for store-specific supplier record
                sp, sp_created = SupplierProduct.objects.get_or_create(
                    supplier=supp_record,
                    product=p,
                    company=comp,
                    defaults={
                        'supplier_price': wholesale_p,
                        'is_active': True,
                    }
                )
                if sp_created:
                    total_sp_created += 1
                    print(f"      + Added Product: '{p.productname}' (Wholesale: Rs.{sp.supplier_price})")
                
                # Also ensure link exists for base_supp if different
                if base_supp != supp_record:
                    sp_base, sp_base_created = SupplierProduct.objects.get_or_create(
                        supplier=base_supp,
                        product=p,
                        company=comp,
                        defaults={
                            'supplier_price': wholesale_p,
                            'is_active': True,
                        }
                    )
                    if sp_base_created:
                        total_sp_created += 1
                        print(f"      + Added Base Supplier Link: '{p.productname}' for {base_supp.suppliername}")

    print("\n" + "=" * 75)
    print(f"  SUCCESSFULLY FINISHED MULTI-STORE CONNECTIVITY!")
    print(f"  - New Multi-Store Supplier Connections Created: {total_supp_created}")
    print(f"  - New Supplier Product Links Created: {total_sp_created}")
    print("=" * 75)

if __name__ == '__main__':
    create_multistore_connections()
