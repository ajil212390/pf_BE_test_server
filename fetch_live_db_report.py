import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import (
    Company, Supplier, Supplieruser, SupplierManager, 
    SupplierExecutive, ExecutiveAllocation, Products, 
    SupplierProduct, SupplierOrder, SupplierOrderItem
)
from django.db import connection

def fetch_live_report():
    print(f"=== LIVE POSTGRESQL DATABASE REPORT ===")
    print(f"Database Engine: {connection.settings_dict['ENGINE']}")
    print(f"Database Name: {connection.settings_dict['NAME']}")
    print(f"Host: {connection.settings_dict['HOST']}:{connection.settings_dict['PORT']}\n")

    print("### 1. RETAIL STORES / COMPANIES")
    companies = Company.objects.all().order_by('companyid')
    print(f"Total Companies: {companies.count()}")
    for c in companies:
        cat_name = c.categoryid.categoryname if c.categoryid else 'None'
        print(f"- ID #{c.companyid} | Name: {c.companyname} | Phone: {c.companyphonenumber} | Category: {cat_name} | Location: {c.companylocation}")
    print()

    print("### 2. SUPPLIERS")
    suppliers = Supplier.objects.select_related('companyid').all().order_by('supplierid')
    print(f"Total Suppliers: {suppliers.count()}")
    for s in suppliers:
        comp_name = s.companyid.companyname if s.companyid else 'Unlinked'
        print(f"- Supplier ID #{s.supplierid} | Name: {s.suppliername} | Store: {comp_name} (ID #{s.companyid.companyid}) | GST: {s.suppliergst} | Connected: {s.isconnected}")
    print()

    print("### 3. SUPPLIER SALES EXECUTIVES & ALLOCATIONS")
    executives = SupplierExecutive.objects.select_related('manager', 'supplier_user').all().order_by('executiveid')
    print(f"Total Executives: {executives.count()}")
    for ex in executives:
        mgr_name = ex.manager.manager_name if ex.manager else 'None'
        supp_user_name = ex.supplier_user.suppliername if ex.supplier_user else 'None'
        allocations = ExecutiveAllocation.objects.filter(executive=ex).select_related('company')
        allocated_stores = [f"{a.company.companyname} (ID #{a.company.companyid})" for a in allocations]
        print(f"- Executive #{ex.executiveid}: {ex.executive_name} (Username: {ex.executive_username}) | Manager: {mgr_name} | Supplier: {supp_user_name}")
        print(f"  Allocated Stores ({len(allocated_stores)}): {', '.join(allocated_stores) if allocated_stores else 'None'}")
    print()

    print("### 4. PRODUCTS & SUPPLIER PRICING BY STORE")
    for comp in companies:
        print(f"\n#### Store: {comp.companyname} (Company ID #{comp.companyid})")
        prods = Products.objects.filter(companyid=comp).select_related('productcategoryid', 'productunitid').order_by('productid')
        if not prods.exists():
            print("  (No products listed for this store)")
            continue
        for p in prods:
            cat = p.productcategoryid.productcategoryname if p.productcategoryid else 'General'
            unit = p.productunitid.productunitname if p.productunitid else 'Unit'
            sps = SupplierProduct.objects.filter(company=comp, product=p).select_related('supplier')
            supp_info = []
            for sp in sps:
                supp_info.append(f"{sp.supplier.suppliername} [SuppID #{sp.supplier.supplierid}] @ Rs.{sp.supplier_price}")
            
            supp_str = " | ".join(supp_info) if supp_info else "No Supplier Linked"
            print(f"- Prod #{p.productid}: {p.productname} | Cat: {cat} | Unit: {unit} | Retail Price: Rs.{p.productprice} | Suppliers: {supp_str}")

    print("\n### 5. ORDERS")
    orders = SupplierOrder.objects.select_related('company', 'supplier', 'executive').all().order_by('-order_id')
    print(f"Total Supplier Orders: {orders.count()}")
    for o in orders:
        exec_name = o.executive.executive_name if o.executive else 'Direct / Self'
        print(f"- Order #{o.order_id} | Store: {o.company.companyname} | Supplier: {o.supplier.suppliername} | Exec: {exec_name} | Total: Rs.{o.total_amount} | Status: {o.status}")
        items = SupplierOrderItem.objects.filter(order=o).select_related('product')
        for item in items:
            print(f"   * {item.product.productname} x {item.quantity} @ Rs.{item.price_at_order} each")

if __name__ == '__main__':
    fetch_live_report()
