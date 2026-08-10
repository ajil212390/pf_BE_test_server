import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import SupplierBill, Supplieruser

try:
    s = Supplieruser.objects.get(supplieruserid=11)
    print(s)
except Exception as e:
    print(e)
    
bills = SupplierBill.objects.all()
print('Total bills:', bills.count())
for b in bills:
    print(f"ID:{getattr(b, 'supplierbillid', '?')} No:{getattr(b, 'supplierbillnumber', '?')} Type:{getattr(b, 'supplierbilltype', '?')} Amt:{getattr(b, 'supplierbillamount', '?')} Paid:{getattr(b, 'paidamount', '?')}")
