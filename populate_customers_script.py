import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Company, Customer

def seed_customers():
    print("=" * 60)
    print("  SEEDING CUSTOMERS INTO DATABASE")
    print("=" * 60)

    customers_data = [
        # Company 1: AN Gallery
        {
            'company_id': 1,
            'name': 'Rahul Nair',
            'phone': '9847112233',
            'email': 'rahul.nair@gmail.com',
            'address': 'Door No 45/12, Panampilly Nagar, Ernakulam',
            'pincode': '682036',
            'gst': '32ABCDE1111A1Z1',
            'pan': 'ABCDE1111A',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('1250.00'),
        },
        {
            'company_id': 1,
            'name': 'Priya Suresh',
            'phone': '9847223344',
            'email': 'priya.suresh@outlook.com',
            'address': 'Flat 3B, Sky Towers, Kakkanad, Kochi',
            'pincode': '682030',
            'gst': '32ABCDE2222B1Z2',
            'pan': 'ABCDE2222B',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('450.00'),
        },
        {
            'company_id': 1,
            'name': 'Apex Retailers & Mart',
            'phone': '9847334455',
            'email': 'contact@apexretailers.in',
            'address': 'Building 12, MG Road, Ernakulam',
            'pincode': '682016',
            'gst': '32ABCDE3333C1Z3',
            'pan': 'ABCDE3333C',
            'state': 'Kerala',
            'opening_bal': Decimal('5000.00'),
            'current_bal': Decimal('12400.00'),
        },
        {
            'company_id': 1,
            'name': 'Ananya Krishna',
            'phone': '9847445566',
            'email': 'ananya.k@yahoo.com',
            'address': 'Hill View Apartments, Palarivattom, Kochi',
            'pincode': '682025',
            'gst': '32ABCDE4444D1Z4',
            'pan': 'ABCDE4444D',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('0.00'),
        },

        # Company 2: Navas Bakers
        {
            'company_id': 2,
            'name': 'Malabar Cafe & Treats',
            'phone': '9847556677',
            'email': 'malabarcafe@gmail.com',
            'address': 'SM Street, Kozhikode',
            'pincode': '673001',
            'gst': '32ABCDE5555E1Z5',
            'pan': 'ABCDE5555E',
            'state': 'Kerala',
            'opening_bal': Decimal('1000.00'),
            'current_bal': Decimal('3200.00'),
        },
        {
            'company_id': 2,
            'name': 'Fasalu Rahman',
            'phone': '9847667788',
            'email': 'fasalu.r@gmail.com',
            'address': 'Beach Road, Calicut',
            'pincode': '673032',
            'gst': '32ABCDE6666F1Z6',
            'pan': 'ABCDE6666F',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('150.00'),
        },
        {
            'company_id': 2,
            'name': 'Royal Sweet Palace',
            'phone': '9847778899',
            'email': 'orders@royalsweets.com',
            'address': 'Mavoor Road, Kozhikode',
            'pincode': '673004',
            'gst': '32ABCDE7777G1Z7',
            'pan': 'ABCDE7777G',
            'state': 'Kerala',
            'opening_bal': Decimal('2000.00'),
            'current_bal': Decimal('6800.00'),
        },

        # Company 3: AI Supermart
        {
            'company_id': 3,
            'name': 'Siddharth Varma',
            'phone': '9847889900',
            'email': 'sid.varma@gmail.com',
            'address': 'Vyttila, Ernakulam',
            'pincode': '682019',
            'gst': '32ABCDE8888H1Z8',
            'pan': 'ABCDE8888H',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('890.00'),
        },
        {
            'company_id': 3,
            'name': 'Grand Hypermarket',
            'phone': '9847990011',
            'email': 'billing@grandhyper.in',
            'address': 'NH Bypass, Edappally, Kochi',
            'pincode': '682024',
            'gst': '32ABCDE9999I1Z9',
            'pan': 'ABCDE9999I',
            'state': 'Kerala',
            'opening_bal': Decimal('10000.00'),
            'current_bal': Decimal('25000.00'),
        },

        # Company 4: Western Mart
        {
            'company_id': 4,
            'name': 'Deepak Joseph',
            'phone': '9847001122',
            'email': 'deepak.j@gmail.com',
            'address': 'Kaloor Kadavanthra Road, Kochi',
            'pincode': '682017',
            'gst': '32ABCDE1010J1Z0',
            'pan': 'ABCDE1010J',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('520.00'),
        },
        {
            'company_id': 4,
            'name': 'City Corner Store',
            'phone': '9847113355',
            'email': 'citycorner@gmail.com',
            'address': 'Thevara, Kochi',
            'pincode': '682013',
            'gst': '32ABCDE2020K1Z1',
            'pan': 'ABCDE2020K',
            'state': 'Kerala',
            'opening_bal': Decimal('1500.00'),
            'current_bal': Decimal('4200.00'),
        },

        # Company 6: Calvino Mart
        {
            'company_id': 6,
            'name': 'Gautam Nambiar',
            'phone': '9847224466',
            'email': 'gautam.n@gmail.com',
            'address': 'Fort Kochi, Kochi',
            'pincode': '682001',
            'gst': '32ABCDE3030L1Z2',
            'pan': 'ABCDE3030L',
            'state': 'Kerala',
            'opening_bal': Decimal('0.00'),
            'current_bal': Decimal('750.00'),
        },
        {
            'company_id': 6,
            'name': 'Metro Provisions',
            'phone': '9847335577',
            'email': 'metro.prov@gmail.com',
            'address': 'Mattancherry, Kochi',
            'pincode': '682002',
            'gst': '32ABCDE4040M1Z3',
            'pan': 'ABCDE4040M',
            'state': 'Kerala',
            'opening_bal': Decimal('2500.00'),
            'current_bal': Decimal('5600.00'),
        }
    ]

    inserted_count = 0
    for data in customers_data:
        try:
            company = Company.objects.get(companyid=data['company_id'])
        except Company.DoesNotExist:
            print(f"[SKIP] Company ID {data['company_id']} not found.")
            continue

        # Check if customer already exists for this company
        existing = Customer.objects.filter(customername=data['name'], companyid=company).first()
        if existing:
            print(f"[EXISTS] Customer '{data['name']}' already exists for {company.companyname} (ID: {existing.customerid})")
        else:
            customer = Customer.objects.create(
                customername=data['name'],
                customerphonenumber=data['phone'],
                customeraddress=data['address'],
                customeremail=data['email'],
                customercurrentbal=data['current_bal'],
                customeropeningbal=data['opening_bal'],
                customerpincode=data['pincode'],
                customergst=data['gst'],
                customerstate=data['state'],
                customerpanno=data['pan'],
                companyid=company
            )
            print(f"[CREATED] Customer ID {customer.customerid}: '{customer.customername}' -> {company.companyname}")
            inserted_count += 1

    print("\n" + "=" * 60)
    print(f"  SUCCESSFULLY INSERTED {inserted_count} NEW CUSTOMERS!")
    print(f"  TOTAL CUSTOMERS IN DB: {Customer.objects.count()}")
    print("=" * 60)

if __name__ == '__main__':
    seed_customers()
