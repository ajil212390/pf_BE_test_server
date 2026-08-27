import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Company, Products, SupplierProduct

def dump_tables():
    companies = Company.objects.filter(companyid__in=[1, 2, 3, 4, 6]).order_by('companyid')
    for comp in companies:
        print(f"\n### Store: {comp.companyname} (Company ID #{comp.companyid})")
        print("| Product Name | Category | Retail Price | Supplier Name | Wholesale Supplier Price | Type |")
        print("|---|---|---|---|---|---|")
        prods = Products.objects.filter(companyid=comp).select_related('productcategoryid').order_by('productid')
        for p in prods:
            sps = SupplierProduct.objects.filter(company=comp, product=p).select_related('supplier')
            is_multi = len(sps) > 1
            for sp in sps:
                stype = "**Multi-Supplier**" if is_multi else "Single Supplier"
                cat_name = p.productcategoryid.productcategoryname if p.productcategoryid else 'General'
                print(f"| {p.productname} | {cat_name} | Rs. {p.productprice} | {sp.supplier.suppliername} | Rs. {sp.supplier_price} | {stype} |")

if __name__ == '__main__':
    dump_tables()
