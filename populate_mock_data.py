import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalog_project.settings')
django.setup()

from products.models import Company, Supplier, Products, SupplierProduct

def populate_mock_data():
    # Fetch a company
    company = Company.objects.first()
    if not company:
        print("No company found. Creating a mock company.")
        company = Company.objects.create(companyname="Test Company")

    # Fetch or create some products
    products = Products.objects.filter(companyid=company)[:5]
    if not products.exists():
        print("No products found for the company. Creating mock products.")
        product_list = []
        for i in range(3):
            p = Products.objects.create(
                productname=f"Mock Product {i+1}", 
                productprice=10.00 + i, 
                companyid=company
            )
            product_list.append(p)
        products = product_list

    # Fetch or create a supplier
    supplier = Supplier.objects.filter(companyid=company).first()
    if not supplier:
        print("No supplier found for the company. Creating a mock supplier.")
        supplier = Supplier.objects.create(suppliername="Mock Supplier", companyid=company)
        
    print(f"Using Company: {company.companyname}")
    print(f"Using Supplier: {supplier.suppliername}")
    
    for product in products:
        supplier_product, created = SupplierProduct.objects.get_or_create(
            company=company,
            supplier=supplier,
            product=product,
            defaults={'is_active': True}
            # supplier_price is null by default now
        )
        if created:
            print(f"Created SupplierProduct mapping for {product.productname}")
        else:
            print(f"SupplierProduct mapping already exists for {product.productname}")

if __name__ == '__main__':
    populate_mock_data()
