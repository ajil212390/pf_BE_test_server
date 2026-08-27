import os
import django
from decimal import Decimal
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Company, Products, Productcategory, Productunit, Supplier, SupplierProduct, Users

def add_products():
    navas_company = Company.objects.get(companyid=2)
    navas_user = Users.objects.filter(companyid=navas_company).first()
    
    # Get categories and units
    bakery_cat = Productcategory.objects.filter(productcategoryname__icontains='Bakery').first()
    if not bakery_cat:
        bakery_cat = Productcategory.objects.first()
        
    dairy_cat = Productcategory.objects.filter(productcategoryname__icontains='Dairy').first()
    if not dairy_cat:
        dairy_cat = bakery_cat

    pkt_unit = Productunit.objects.filter(productunitname__icontains='Packet').first()
    if not pkt_unit:
        pkt_unit = Productunit.objects.first()
        
    pcs_unit = Productunit.objects.filter(productunitname__icontains='Pcs').first() or pkt_unit
    box_unit = Productunit.objects.filter(productunitname__icontains='Box').first() or pkt_unit

    # Suppliers for Navas Bakers
    supp_malabar = Supplier.objects.get(supplierid=3) # Malabar Flour & Bakery Goods
    supp_royal = Supplier.objects.get(supplierid=4)   # Royal Dairy & Agro Industries
    supp_abc = Supplier.objects.get(supplierid=1)     # ABC Traders

    new_products_data = [
        {
            "name": "Butter Cream Cake 500g",
            "category": bakery_cat,
            "unit": pcs_unit,
            "price": Decimal("280.00"),
            "suppliers": [
                (supp_malabar, Decimal("240.00")),
                (supp_abc, Decimal("235.00")),
            ]
        },
        {
            "name": "Butter Cookies 250g",
            "category": bakery_cat,
            "unit": pkt_unit,
            "price": Decimal("120.00"),
            "suppliers": [
                (supp_malabar, Decimal("100.00")),
            ]
        },
        {
            "name": "Fresh Paneer 200g",
            "category": dairy_cat,
            "unit": pkt_unit,
            "price": Decimal("95.00"),
            "suppliers": [
                (supp_royal, Decimal("80.00")),
                (supp_abc, Decimal("78.00")),
            ]
        },
        {
            "name": "Chocolate Muffin (Pack of 4)",
            "category": bakery_cat,
            "unit": box_unit,
            "price": Decimal("160.00"),
            "suppliers": [
                (supp_malabar, Decimal("135.00")),
            ]
        },
        {
            "name": "Whole Wheat Bread 400g",
            "category": bakery_cat,
            "unit": pkt_unit,
            "price": Decimal("50.00"),
            "suppliers": [
                (supp_malabar, Decimal("42.00")),
                (supp_royal, Decimal("43.50")),
            ]
        }
    ]

    added_prods = []
    for item in new_products_data:
        prod, created = Products.objects.get_or_create(
            productname=item["name"],
            companyid=navas_company,
            defaults={
                'productcategoryid': item["category"],
                'productunitid': item["unit"],
                'productprice': item["price"],
                'userid': navas_user,
                'dateadded': datetime.date.today(),
                'addtype': 'Single'
            }
        )
        if not created:
            prod.productprice = item["price"]
            prod.productcategoryid = item["category"]
            prod.productunitid = item["unit"]
            prod.save()

        # Add SupplierProduct records
        for supplier_obj, supp_price in item["suppliers"]:
            sp, _ = SupplierProduct.objects.get_or_create(
                company=navas_company,
                supplier=supplier_obj,
                product=prod,
                defaults={
                    'supplier_price': supp_price,
                    'is_active': True
                }
            )
            sp.supplier_price = supp_price
            sp.is_active = True
            sp.save()

        added_prods.append(prod)

    print(f"Successfully added/updated {len(added_prods)} products for Navas Bakers (Company ID #2):")
    for p in added_prods:
        sps = SupplierProduct.objects.filter(company=navas_company, product=p)
        supp_details = ", ".join([f"{sp.supplier.suppliername} @ Rs.{sp.supplier_price}" for sp in sps])
        print(f"  - Prod #{p.productid}: '{p.productname}' | Retail Price: Rs.{p.productprice} | Suppliers: {supp_details}")

if __name__ == '__main__':
    add_products()
