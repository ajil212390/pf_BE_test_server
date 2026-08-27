import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Company, Users, Productcategory, Productunit, Products
from django.db import connection

def seed_units_and_products():
    print("=" * 60)
    print("  SEEDING PRODUCT UNITS & 25 PRODUCTS FOR 5 COMPANIES")
    print("=" * 60)

    # 1. Clear existing products to ensure clean seed
    Products.objects.all().delete()

    # 2. Seed Product Units if empty
    units_data = ['Pcs', 'Kg', 'Litre', 'Packet', 'Box']
    unit_map = {}
    for u_name in units_data:
        unit_obj, created = Productunit.objects.get_or_create(productunitname=u_name)
        unit_map[u_name] = unit_obj
        print(f"  Unit: {u_name} (ID: {unit_obj.productunitid})")

    # Fetch Categories map by name substring
    cats = {c.productcategoryname.lower(): c for c in Productcategory.objects.all()}

    def get_cat(name_sub):
        for k, v in cats.items():
            if name_sub.lower() in k:
                return v
        return list(cats.values())[0]

    # 3. Product definitions (5 per company)
    products_to_create = [
        # Company 1: AN Gallery (companyid: 1, userid: 1) - Electronics & Stationary
        {'companyid': 1, 'userid': 1, 'name': 'Wireless Earbuds Pro', 'cat': 'Electronics', 'unit': 'Pcs', 'price': 1999.00},
        {'companyid': 1, 'userid': 1, 'name': 'Fast Charging Cable Type-C', 'cat': 'Electronics', 'unit': 'Pcs', 'price': 299.00},
        {'companyid': 1, 'userid': 1, 'name': 'Bluetooth Mini Speaker', 'cat': 'Electronics', 'unit': 'Pcs', 'price': 899.00},
        {'companyid': 1, 'userid': 1, 'name': 'Executive Leather Notebook', 'cat': 'Stationary', 'unit': 'Pcs', 'price': 350.00},
        {'companyid': 1, 'userid': 1, 'name': 'Ergonomic Gel Pen Set (Pack of 5)', 'cat': 'Stationary', 'unit': 'Box', 'price': 150.00},

        # Company 2: Navas Bakers (companyid: 2, userid: 2) - Bakery & Sweets
        {'companyid': 2, 'userid': 2, 'name': 'Fresh Milk Bread 400g', 'cat': 'Bakery', 'unit': 'Packet', 'price': 45.00},
        {'companyid': 2, 'userid': 2, 'name': 'Butter Chocolate Cake 500g', 'cat': 'Bakery', 'unit': 'Pcs', 'price': 350.00},
        {'companyid': 2, 'userid': 2, 'name': 'Choco Chip Cookies 250g', 'cat': 'Bakery', 'unit': 'Box', 'price': 120.00},
        {'companyid': 2, 'userid': 2, 'name': 'Vanilla Muffin (Pack of 4)', 'cat': 'Bakery', 'unit': 'Box', 'price': 80.00},
        {'companyid': 2, 'userid': 2, 'name': 'Crispy Butter Croissant', 'cat': 'Bakery', 'unit': 'Pcs', 'price': 65.00},

        # Company 3: AI Supermart (companyid: 3, userid: 3) - Groceries & Beverages
        {'companyid': 3, 'userid': 3, 'name': 'Premium Basmati Rice 5kg', 'cat': 'Grains', 'unit': 'Kg', 'price': 480.00},
        {'companyid': 3, 'userid': 3, 'name': 'Refined Sunflower Oil 1L', 'cat': 'Oils', 'unit': 'Litre', 'price': 145.00},
        {'companyid': 3, 'userid': 3, 'name': 'Natural Green Tea 250g', 'cat': 'Beverages', 'unit': 'Box', 'price': 210.00},
        {'companyid': 3, 'userid': 3, 'name': 'Organic Wheat Flour (Atta) 5kg', 'cat': 'Groceries', 'unit': 'Kg', 'price': 260.00},
        {'companyid': 3, 'userid': 3, 'name': 'Instant Filter Coffee Powder 200g', 'cat': 'Beverages', 'unit': 'Packet', 'price': 175.00},

        # Company 4: Western Mart (companyid: 4, userid: 4) - Packets, Personal Care & Chocolates
        {'companyid': 4, 'userid': 4, 'name': 'Dark Chocolate Bar 100g', 'cat': 'Chocolates', 'unit': 'Pcs', 'price': 99.00},
        {'companyid': 4, 'userid': 4, 'name': 'Almond & Raisin Chocolate 150g', 'cat': 'Chocolates', 'unit': 'Pcs', 'price': 149.00},
        {'companyid': 4, 'userid': 4, 'name': 'Moisturizing Body Wash 250ml', 'cat': 'Personal Care', 'unit': 'Pcs', 'price': 225.00},
        {'companyid': 4, 'userid': 4, 'name': 'Herbal Shampoo 300ml', 'cat': 'Personal Care', 'unit': 'Pcs', 'price': 195.00},
        {'companyid': 4, 'userid': 4, 'name': 'Potato Chips Cream & Onion 100g', 'cat': 'Packets', 'unit': 'Packet', 'price': 40.00},

        # Company 5: Calvino Mart (companyid: 6, userid: 5) - Dairy, Household & Home Care
        {'companyid': 6, 'userid': 5, 'name': 'Fresh Farm Cow Milk 1L', 'cat': 'Dairy', 'unit': 'Litre', 'price': 56.00},
        {'companyid': 6, 'userid': 5, 'name': 'Pure Cow Ghee 500ml', 'cat': 'Dairy', 'unit': 'Litre', 'price': 340.00},
        {'companyid': 6, 'userid': 5, 'name': 'Antibacterial Dishwash Gel 500ml', 'cat': 'Household', 'unit': 'Pcs', 'price': 115.00},
        {'companyid': 6, 'userid': 5, 'name': 'Multi-Surface Liquid Cleaner 1L', 'cat': 'Home Care', 'unit': 'Litre', 'price': 185.00},
        {'companyid': 6, 'userid': 5, 'name': 'Fabric Softener & Conditioner 1L', 'cat': 'Home Care', 'unit': 'Litre', 'price': 210.00},
    ]

    created_count = 0
    today = date.today()
    for item in products_to_create:
        comp = Company.objects.get(companyid=item['companyid'])
        usr = Users.objects.get(userid=item['userid'])
        cat_obj = get_cat(item['cat'])
        unit_obj = unit_map[item['unit']]

        prod = Products.objects.create(
            productname=item['name'],
            productcategoryid=cat_obj,
            productunitid=unit_obj,
            productprice=item['price'],
            dateadded=today,
            userid=usr,
            companyid=comp,
            addtype='Single'
        )
        created_count += 1
        print(f"  [{created_count}/25] Created: '{prod.productname}' (Rs. {prod.productprice}) -> Company: {comp.companyname}")

    print("=" * 60)
    print(f"  SUCCESSFULLY CREATED {created_count} PRODUCTS ACROSS 5 COMPANIES!")
    print("=" * 60)

if __name__ == '__main__':
    seed_units_and_products()
