import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Company, Users, EndUser, Supplier, Supplieruser, Productcategory, Products, SupplierProduct, SupplierManager, SupplierExecutive, ExecutiveAllocation

def generate_markdown():
    lines = []
    lines.append("# Product Catalog & B2B Supply Chain System Documentation")
    lines.append("")
    lines.append("> [!NOTE]")
    lines.append("> This document provides a complete technical overview of the system architecture, database schema, entity relationships, user credentials, store directories, multi-store supplier connections, field managers/executives, store allocations, and executive order-taking catalogs.")
    lines.append("")

    # Section 1: System Overview
    lines.append("## 1. System Overview & Technology Stack")
    lines.append("- **Backend Framework**: Django 5.1 / Python 3.13")
    lines.append("- **Database**: PostgreSQL (`mydb` on `localhost:5432`)")
    lines.append("- **Frontend App**: Flutter 3.x (`d:\\app1\\lib`)")
    lines.append("- **Core Capabilities**: Multi-tenant B2B Product Catalog, Multi-Store Supplier Connections, Field Executive Beat Plan & Take Order Management, Real-time Customer Billing & Orders.")
    lines.append("")

    # Section 2: Database Schema & Entity Relationships
    lines.append("---")
    lines.append("## 2. Database Schema & Relational Structure")
    lines.append("")
    lines.append("### Primary Database Tables & Foreign Key Dependencies")
    lines.append("")
    lines.append("| Table Name | Primary Key | Description & Foreign Keys |")
    lines.append("|---|---|---|")
    lines.append("| `company` | `companyid` | Stores retail stores/companies. Linked to `companycategory` (`categoryid`). |")
    lines.append("| `users` | `userid` | Store Manager / Company login accounts. Linked to `company` (`companyid`). |")
    lines.append("| `enduser` | `endsuerid` | End-customer accounts for chat/ordering. |")
    lines.append("| `companycategory` | `categoryid` | Categories for retail stores (e.g. Grocery, Bakery, Supermarket). |")
    lines.append("| `productcategory` | `productcategoryid` | Categories for products (e.g. Dairy, Bakery, Electronics, Beverages). |")
    lines.append("| `productunit` | `productunitid` | Measurement units (e.g. Pcs, Kg, Litre, Packet, Box). |")
    lines.append("| `products` | `productid` | Product catalog items. Linked to `company` (`companyid`), `users` (`userid`), `productcategory` (`productcategoryid`), `productunit` (`productunitid`). |")
    lines.append("| `supplier` | `supplierid` | B2B Supplier records associated with specific stores (`companyid`). |")
    lines.append("| `supplieruser` | `supplieruserid` | Onboarded Supplier login accounts. Linked to base `supplier` (`supplierid`). |")
    lines.append("| `supplier_product` | `id` | Maps products offered by specific suppliers to companies (`supplierid`, `companyid`, `productid`). |")
    lines.append("| `supplier_manager` | `manager_id` | Field sales managers for suppliers. Linked to `supplieruser` (`supplier_user_id`). |")
    lines.append("| `supplier_executive` | `executiveid` | Sales executives under a supplier manager. Linked to `supplier_manager` (`manager_id`). |")
    lines.append("| `executive_allocation` | `allocation_id` | Allocates sales executives to visit specific stores (`executive_id`, `company_id`). |")
    lines.append("| `supplier_order` | `order_id` | Orders placed by executives or stores. Linked to `companyid`, `supplierid`, `executive_id`. |")
    lines.append("| `supplier_order_item` | `item_id` | Items within a supplier order. Linked to `order_id`, `productid`. |")
    lines.append("")

    # Section 3: System Login Credentials
    lines.append("---")
    lines.append("## 3. System Login Credentials Directory")
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append("> All user account passwords across the system have been standardly set to **`1234`**.")
    lines.append("")
    lines.append("### A. Company / Store Accounts (`users` Table)")
    lines.append("| User ID | Username | Password | Company Name | Company ID |")
    lines.append("|---|---|---|---|---|")
    for u in Users.objects.select_related('companyid').all().order_by('userid'):
        comp_name = u.companyid.companyname if u.companyid else 'N/A'
        comp_id = u.companyid.companyid if u.companyid else 'N/A'
        lines.append(f"| #{u.userid} | `{u.username}` | `{u.userpassword}` | {comp_name} | #{comp_id} |")
    lines.append("")

    lines.append("### B. Onboarded Supplier Accounts (`supplieruser` Table)")
    lines.append("| Supplier User ID | Supplier Name | Username | Password | Phone | GST Number |")
    lines.append("|---|---|---|---|---|---|")
    for su in Supplieruser.objects.all().order_by('supplieruserid'):
        lines.append(f"| #{su.supplieruserid} | {su.suppliername} | `{su.supplierusername}` | `{su.supplieruserpassword}` | {su.supplieruserphone} | `{su.supplierusergstnumber}` |")
    lines.append("")

    lines.append("### C. Supplier Field Managers (`supplier_manager` Table)")
    lines.append("| Manager ID | Manager Name | Username | Password | Phone | Assigned Area | Supplier Company |")
    lines.append("|---|---|---|---|---|---|---|")
    for sm in SupplierManager.objects.select_related('supplier_user').all().order_by('manager_id'):
        supp_name = sm.supplier_user.suppliername if sm.supplier_user else 'N/A'
        lines.append(f"| #{sm.manager_id} | **{sm.manager_name}** | `{sm.manager_username}` | `{sm.manager_password}` | {sm.manager_phone or 'N/A'} | {sm.manager_area or 'N/A'} | {supp_name} |")
    lines.append("")

    lines.append("### D. Supplier Sales Executives (`supplier_executive` Table)")
    lines.append("| Executive ID | Executive Name | Username | Password | Phone | Reporting Manager | Supplier Company |")
    lines.append("|---|---|---|---|---|---|---|")
    for se in SupplierExecutive.objects.select_related('manager', 'supplier_user').all().order_by('executiveid'):
        mgr_name = se.manager.manager_name if se.manager else 'N/A'
        supp_name = se.supplier_user.suppliername if se.supplier_user else (se.manager.supplier_user.suppliername if se.manager and se.manager.supplier_user else 'N/A')
        lines.append(f"| #{se.executiveid} | **{se.executive_name}** | `{se.executive_username}` | `{se.executive_password}` | {se.executive_phone or 'N/A'} | {mgr_name} | {supp_name} |")
    lines.append("")

    lines.append("### E. End-User Accounts (`enduser` Table)")
    lines.append("| End-User ID | Username | Password | Phone | Email |")
    lines.append("|---|---|---|---|---|")
    for eu in EndUser.objects.all().order_by('endsuerid'):
        lines.append(f"| #{eu.endsuerid} | `{eu.endusername}` | `{eu.enduserpassword}` | {eu.enduserphone or 'N/A'} | {eu.enduseremail or 'N/A'} |")
    lines.append("")

    # Section 4: Store Directory
    lines.append("---")
    lines.append("## 4. Retail Stores Directory & Connected Suppliers")
    lines.append("")
    for comp in Company.objects.filter(companyid__in=[1, 2, 3, 4, 6]).order_by('companyid'):
        supps = Supplier.objects.filter(companyid=comp, isconnected=1)
        supp_names = sorted(list(set([s.suppliername for s in supps])))
        cat_name = comp.categoryid.categoryname if comp.categoryid else 'General'
        lines.append(f"### Store #{comp.companyid}: **{comp.companyname}**")
        lines.append(f"- **Category**: {cat_name}")
        lines.append(f"- **Address**: {comp.companyaddress or 'N/A'}")
        lines.append(f"- **Phone**: {comp.companyphonenumber or 'N/A'}")
        lines.append(f"- **Connected Onboarded Suppliers**: {', '.join(supp_names) if supp_names else 'None'}")
        lines.append("")

    # Section 5: Supplier Directory & Multi-Store Connections
    lines.append("---")
    lines.append("## 5. Suppliers Directory & Multi-Store Connections")
    lines.append("")
    lines.append("An onboarded supplier can be connected to **multiple retail stores**. When an executive under a supplier logs in, they can visit and take orders across all connected stores:")
    lines.append("")
    
    su_list = Supplieruser.objects.all().order_by('supplieruserid')
    for su in su_list:
        matching_supps = Supplier.objects.filter(suppliergst=su.supplierusergstnumber, isconnected=1)
        connected_stores = [f"{s.companyid.companyname} (SuppID #{s.supplierid})" for s in matching_supps]
        lines.append(f"### Supplier: **{su.suppliername}** (`{su.supplierusername}`)")
        lines.append(f"- **Supplier User ID**: #{su.supplieruserid}")
        lines.append(f"- **Login Credentials**: Username: `{su.supplierusername}` | Password: `{su.supplieruserpassword}`")
        lines.append(f"- **GST Number**: `{su.supplierusergstnumber}`")
        lines.append(f"- **Phone**: {su.supplieruserphone}")
        lines.append(f"- **Address**: {su.supplieruseraddress}")
        lines.append(f"- **Connected Retail Stores**: {', '.join(connected_stores)}")
        lines.append("")

    # Section 6: Executive Allocations & Take-Order Matrix
    lines.append("---")
    lines.append("## 6. Executive Beat Plan & Take-Order Matrix (No Pricing)")
    lines.append("")
    lines.append("When a Sales Executive logs into the Flutter app, their Beat Plan displays all allocated stores. Tapping **Take Order** for any allocated store displays the products offered by their supplier for that specific store:")
    lines.append("")

    executives = SupplierExecutive.objects.select_related('manager', 'supplier_user').all().order_by('executiveid')
    for se in executives:
        supp_user = se.supplier_user or (se.manager.supplier_user if se.manager else None)
        supp_name = supp_user.suppliername if supp_user else 'N/A'
        lines.append(f"### Sales Executive: **{se.executive_name}** (`{se.executive_username}`)")
        lines.append(f"- **Executive ID**: #{se.executiveid}")
        lines.append(f"- **Login Credentials**: Username: `{se.executive_username}` | Password: `{se.executive_password}`")
        lines.append(f"- **Supplier Organization**: {supp_name}")
        lines.append(f"- **Reporting Manager**: {se.manager.manager_name if se.manager else 'N/A'}")
        lines.append("")

        allocations = ExecutiveAllocation.objects.filter(executive=se).select_related('company')
        lines.append("#### Allocated Stores & Available Products for Order Taking:")
        for alloc in allocations:
            comp = alloc.company
            lines.append(f"##### Store: **{comp.companyname}** (Company ID #{comp.companyid})")
            lines.append("| Product ID | Product Name | Category | Unit | Supplying Supplier |")
            lines.append("|---|---|---|---|---|")
            
            # Find products for this company linked to this supplier
            matching_supp_ids = list(Supplier.objects.filter(suppliergst=supp_user.supplierusergstnumber).values_list('supplierid', flat=True)) if supp_user else [se.supplier_user_id]
            sps = SupplierProduct.objects.filter(company=comp, supplier_id__in=matching_supp_ids, is_active=True).select_related('product')
            
            for sp in sps:
                cat_name = sp.product.productcategoryid.productcategoryname if sp.product.productcategoryid else 'General'
                unit_name = sp.product.productunitid.productunitname if sp.product.productunitid else 'Pcs'
                lines.append(f"| #{sp.product.productid} | **{sp.product.productname}** | {cat_name} | {unit_name} | {supp_name} |")
            lines.append("")

    # Section 7: Complete Store Catalogs & Product Supplier Mappings
    lines.append("---")
    lines.append("## 7. Complete Store Catalogs & Product Supplier Mappings (No Pricing)")
    lines.append("")
    lines.append("Below is the complete breakdown of every store's product catalog and all suppliers offering each product:")
    lines.append("")

    companies = Company.objects.filter(companyid__in=[1, 2, 3, 4, 6]).order_by('companyid')
    for comp in companies:
        lines.append(f"### Store: **{comp.companyname}** (Company ID #{comp.companyid})")
        lines.append("")
        lines.append("| Product ID | Product Name | Category | Unit | Supplying Suppliers | Setup Type |")
        lines.append("|---|---|---|---|---|---|")
        prods = Products.objects.filter(companyid=comp).select_related('productcategoryid', 'productunitid').order_by('productid')
        for p in prods:
            sps = SupplierProduct.objects.filter(company=comp, product=p, is_active=True).select_related('supplier')
            supp_names = sorted(list(set([sp.supplier.suppliername for sp in sps])))
            is_multi = len(supp_names) > 1
            stype = "**Multi-Supplier Test**" if is_multi else "Single Supplier"
            cat_name = p.productcategoryid.productcategoryname if p.productcategoryid else 'General'
            unit_name = p.productunitid.productunitname if p.productunitid else 'Pcs'
            lines.append(f"| #{p.productid} | **{p.productname}** | {cat_name} | {unit_name} | {', '.join(supp_names)} | {stype} |")
        lines.append("")

    content = "\n".join(lines)

    # Save to workspace documentation file
    doc_path = r"d:\app001\product_catalog_api\system_structure_and_data_map.md"
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Save to artifacts directory
    artifact_path = r"C:\Users\AJIL\.gemini\antigravity-ide\brain\25f467ea-d785-4b38-bd07-2f025333c5b9\system_structure_and_data_map.md"
    with open(artifact_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Successfully generated updated Markdown document at:\n - {doc_path}\n - {artifact_path}")

if __name__ == '__main__':
    generate_markdown()
