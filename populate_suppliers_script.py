import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Company, Products, Supplier, Supplieruser, SupplierProduct
from django.db import connection

def seed_suppliers_and_users():
    print("=" * 60)
    print("  SEEDING 10 SUPPLIERS, 5 ONBOARDED SUPPLIER USERS, AND SUPPLIER PRODUCTS")
    print("=" * 60)

    # Clear existing supplier data
    SupplierProduct.objects.all().delete()
    Supplieruser.objects.all().delete()
    Supplier.objects.all().delete()

    suppliers_data = [
        # Company 1: AN Gallery (companyid: 1)
        {
            'companyid': 1,
            'name': 'ABC Traders',
            'phone': '9876543210',
            'email': 'abc@traders.com',
            'address': 'MG Road, Ernakulam',
            'pincode': '682001',
            'gst': '32ABCDE1234F1Z1',
            'pan': 'ABCDE1234F',
            'state': 'Kerala',
            'onboard': True,
            'username': 'abctraders',
            'password': '1234'
        },
        {
            'companyid': 1,
            'name': 'Global Electronics Supplies',
            'phone': '9876543211',
            'email': 'global@electronics.com',
            'address': 'Marine Drive, Kochi',
            'pincode': '682002',
            'gst': '32ABCDE1234F1Z2',
            'pan': 'ABCDE1234G',
            'state': 'Kerala',
            'onboard': False
        },

        # Company 2: Navas Bakers (companyid: 2)
        {
            'companyid': 2,
            'name': 'Malabar Flour & Bakery Goods',
            'phone': '9876543212',
            'email': 'malabar@bakerysupplier.com',
            'address': 'Moyinkutty Vaidyar Street, Kozhikode',
            'pincode': '673001',
            'gst': '32ABCDE1234F1Z3',
            'pan': 'ABCDE1234H',
            'state': 'Kerala',
            'onboard': True,
            'username': 'malabarbakers',
            'password': '1234'
        },
        {
            'companyid': 2,
            'name': 'Royal Dairy & Agro Industries',
            'phone': '9876543213',
            'email': 'royaldairy@agro.com',
            'address': 'Palayam Market, Kozhikode',
            'pincode': '673002',
            'gst': '32ABCDE1234F1Z4',
            'pan': 'ABCDE1234I',
            'state': 'Kerala',
            'onboard': False
        },

        # Company 3: AI Supermart (companyid: 3)
        {
            'companyid': 3,
            'name': 'Kerala Grains & Pulses Wholesale',
            'phone': '9876543214',
            'email': 'keralagrains@wholesale.com',
            'address': 'Swaraj Round, Thrissur',
            'pincode': '680001',
            'gst': '32ABCDE1234F1Z5',
            'pan': 'ABCDE1234J',
            'state': 'Kerala',
            'onboard': True,
            'username': 'keralagrains',
            'password': '1234'
        },
        {
            'companyid': 3,
            'name': 'Coastal Spice & Beverages',
            'phone': '9876543215',
            'email': 'coastal@spices.com',
            'address': 'Rice Bazaar, Thrissur',
            'pincode': '680002',
            'gst': '32ABCDE1234F1Z6',
            'pan': 'ABCDE1234K',
            'state': 'Kerala',
            'onboard': False
        },

        # Company 4: Western Mart (companyid: 4)
        {
            'companyid': 4,
            'name': 'Metro Confectionery & Sweets',
            'phone': '9876543216',
            'email': 'metro@sweets.com',
            'address': 'Statue Junction, Thiruvananthapuram',
            'pincode': '695001',
            'gst': '32ABCDE1234F1Z7',
            'pan': 'ABCDE1234L',
            'state': 'Kerala',
            'onboard': True,
            'username': 'metrosweets',
            'password': '1234'
        },
        {
            'companyid': 4,
            'name': 'Supreme Personal Care Distributors',
            'phone': '9876543217',
            'email': 'supreme@personalcare.com',
            'address': 'East Fort, Thiruvananthapuram',
            'pincode': '695002',
            'gst': '32ABCDE1234F1Z8',
            'pan': 'ABCDE1234M',
            'state': 'Kerala',
            'onboard': False
        },

        # Company 5: Calvino Mart (companyid: 6)
        {
            'companyid': 6,
            'name': 'GreenCare Household Hygiene',
            'phone': '9876543218',
            'email': 'greencare@hygiene.com',
            'address': 'KK Road, Kottayam',
            'pincode': '686001',
            'gst': '32ABCDE1234F1Z9',
            'pan': 'ABCDE1234N',
            'state': 'Kerala',
            'onboard': True,
            'username': 'greencare',
            'password': '1234'
        },
        {
            'companyid': 6,
            'name': 'Apex FMCG Merchants',
            'phone': '9876543219',
            'email': 'apexfmcg@merchants.com',
            'address': 'Baker Junction, Kottayam',
            'pincode': '686002',
            'gst': '32ABCDE1234F1ZA',
            'pan': 'ABCDE1234O',
            'state': 'Kerala',
            'onboard': False
        },
    ]

    supplier_count = 0
    onboarded_count = 0
    sp_count = 0

    for s_data in suppliers_data:
        comp = Company.objects.get(companyid=s_data['companyid'])
        is_conn = 1 if s_data['onboard'] else 0

        supp = Supplier.objects.create(
            companyid=comp,
            suppliername=s_data['name'],
            supplierphonenumber=s_data['phone'],
            supplieremail=s_data['email'],
            supplieraddress=s_data['address'],
            supplierpincode=s_data['pincode'],
            suppliergst=s_data['gst'],
            supplierpanno=s_data['pan'],
            supplierstate=s_data['state'],
            isconnected=is_conn,
            suppliercurrentbal=0.00,
            supplieropeningbal=0.00
        )
        supplier_count += 1
        print(f"  [{supplier_count}/10] Supplier Created: '{supp.suppliername}' for Company: {comp.companyname}")

        # If onboarded, create Supplieruser record
        if s_data['onboard']:
            s_user = Supplieruser.objects.create(
                supplierid=supp,
                suppliername=supp.suppliername[:25],
                supplierusername=s_data['username'][:25],
                supplieruserphone=supp.supplierphonenumber[:20],
                supplieruseremail=supp.supplieremail[:30],
                supplierusergstnumber=supp.suppliergst[:50],
                supplieruseraddress=supp.supplieraddress[:100],
                supplieruserpassword=s_data['password'][:100]
            )
            onboarded_count += 1
            print(f"       -> Onboarded Supplier User: username='{s_user.supplierusername}' (ID: {s_user.supplieruserid})")

        # Link supplier products for this company's products
        comp_products = Products.objects.filter(companyid=comp)
        for prod in comp_products:
            sp, created = SupplierProduct.objects.get_or_create(
                supplier=supp,
                product=prod,
                company=comp,
                defaults={
                    'supplier_price': prod.productprice,
                    'is_active': True
                }
            )
            sp_count += 1

    print("=" * 60)
    print(f"  FINISHED SEEDING!")
    print(f"  - Total Suppliers: {supplier_count}")
    print(f"  - Onboarded Supplier Users: {onboarded_count}")
    print(f"  - Supplier Product Links: {sp_count}")
    print("=" * 60)

if __name__ == '__main__':
    seed_suppliers_and_users()
