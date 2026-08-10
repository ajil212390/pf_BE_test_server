import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.views import supplier_dashboard
from django.test import RequestFactory
from products.models import Supplieruser

factory = RequestFactory()

users = Supplieruser.objects.all()
for u in users:
    request = factory.get(f'/api/supplier/{u.supplieruserid}/dashboard/')
    response = supplier_dashboard(request, u.supplieruserid)
    if response.status_code == 500:
        print(f"User {u.supplieruserid} returned 500!")
        print(response.data)
    elif response.status_code == 200:
        bills = response.data['overview']['total_bills']
        if bills > 0:
            print(f"User {u.supplieruserid} returned 200 with {bills} bills!")
