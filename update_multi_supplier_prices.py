import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import SupplierProduct, Supplier, Products, Company

def update_multi_supplier_prices():
    print("=" * 75)
    print("  UPDATING MULTI-SUPPLIER PRICING (SAME PRODUCT, DIFFERENT SUPPLIERS)")
    print("=" * 75)

    # Secondary suppliers get a 10% wholesale discount (vs 5% for primary suppliers)
    secondary_supplier_ids = [2, 4, 6, 8, 10]
    updated_count = 0

    for sp in SupplierProduct.objects.filter(supplier_id__in=secondary_supplier_ids):
        retail_p = float(sp.product.productprice)
        sp.supplier_price = round(retail_p * 0.90, 2)  # 10% discount
        sp.save()
        updated_count += 1

    print(f"\n  Successfully updated {updated_count} supplier product entries!")
    print("\n  [VERIFICATION] Multi-supplier comparison for identical products:")
    
    companies = Company.objects.filter(companyid__in=[1, 2, 3, 4, 6]).order_by('companyid')
    for comp in companies:
        print(f"\n  --- Store: {comp.companyname} ---")
        prods = Products.objects.filter(companyid=comp).order_by('productid')[:2] # sample 2 products per company
        for p in prods:
            sps = SupplierProduct.objects.filter(company=comp, product=p).select_related('supplier')
            print(f"   Product: '{p.productname}' (Retail Price: Rs.{p.productprice}):")
            for sp_item in sps:
                print(f"     -> Supplier: {sp_item.supplier.suppliername} (ID #{sp_item.supplier.supplierid}) | Supplier Wholesale Price: Rs.{sp_item.supplier_price}")

    print("=" * 75)

if __name__ == '__main__':
    update_multi_supplier_prices()
