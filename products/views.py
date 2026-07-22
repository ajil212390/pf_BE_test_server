from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Products, Productcategory, Productunit, Company, Users
from .serializers import ProductSerializer, ProductCategorySerializer, ProductUnitSerializer
from django.core.files.storage import default_storage
import uuid
from rest_framework.decorators import action, api_view
import openpyxl
import csv
import io
from datetime import datetime, date

@api_view(['POST'])
def register_user(request):
    data = request.data
    try:
        # Create Company
        company_name = data.get('companyname')
        company_phone = data.get('companyphonenumber')
        
        company = None
        if company_name:
            company, _ = Company.objects.get_or_create(
                companyname=company_name,
                defaults={'companyphonenumber': company_phone}
            )

        # Create User
        user = Users.objects.create(
            username=data.get('username'),
            useremail=data.get('useremail'),
            userpassword=data.get('userpassword'),  # Warning: Storing plain text password for demo
            companyid=company
        )

        return Response({
            'message': 'Registration successful',
            'userid': user.userid,
            'username': user.username,
            'companyid': company.companyid if company else None
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login_user(request):
    data = request.data
    username = data.get('username')
    password = data.get('userpassword')

    try:
        user = Users.objects.get(username__iexact=username)
        if user.userpassword == password:
            company = user.companyid
            return Response({
                'message': 'Login successful',
                'userid': user.userid,
                'username': user.username,
                'useremail': user.useremail or '',
                'companyid': company.companyid if company else None,
                'companyname': company.companyname if company else '',
                'companyphonenumber': str(company.companyphonenumber) if company and company.companyphonenumber else '',
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)
    except Users.DoesNotExist:
        return Response({'error': 'Username not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def update_company(request):
    data = request.data
    user_id = data.get('userid')
    try:
        user = Users.objects.get(userid=user_id)
        company = user.companyid
        if company:
            if 'companyname' in data:
                company.companyname = data['companyname']
            if 'companyphonenumber' in data:
                company.companyphonenumber = data['companyphonenumber']
            company.save()
            return Response({'message': 'Company updated successfully'})
        else:
            return Response({'error': 'No company found for this user'}, status=status.HTTP_404_NOT_FOUND)
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def change_password(request):
    data = request.data
    user_id = data.get('userid')
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    try:
        user = Users.objects.get(userid=user_id)
        if user.userpassword != current_password:
            return Response({'error': 'Incorrect current password.'}, status=status.HTTP_400_BAD_REQUEST)
            
        user.userpassword = new_password
        user.save()
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
    except Users.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ─── ADMIN ENDPOINTS ────────────────────────────────────────────────────────

# Identifiers to exclude from all lists (the built-in super admin)
ADMIN_USERNAME   = 'admin'
ADMIN_COMPANY    = 'Admin HQ'

@api_view(['GET'])
def admin_overview(request):
    """Returns high-level counts – excludes the built-in admin account."""
    total_companies = Company.objects.exclude(companyname__iexact=ADMIN_COMPANY).count()
    total_users     = Users.objects.exclude(username__iexact=ADMIN_USERNAME).count()
    total_products  = Products.objects.count()
    return Response({
        'total_companies': total_companies,
        'total_users':     total_users,
        'total_products':  total_products,
    })

@api_view(['GET'])
def admin_companies(request):
    """Returns all companies except Admin HQ, with user & product counts."""
    companies = Company.objects.exclude(companyname__iexact=ADMIN_COMPANY)
    result = []
    for c in companies:
        user_count = Users.objects.filter(companyid=c).exclude(username__iexact=ADMIN_USERNAME).count()
        product_count = Products.objects.filter(companyid=c).count()
        result.append({
            'companyid':           c.companyid,
            'companyname':         c.companyname,
            'companyphonenumber':  str(c.companyphonenumber) if c.companyphonenumber else '',
            'user_count':          user_count,
            'product_count':       product_count,
        })
    return Response(result)

@api_view(['GET'])
def admin_users(request):
    """Returns all users except the built-in admin, with their company & product count."""
    users = (
        Users.objects
        .select_related('companyid')
        .exclude(username__iexact=ADMIN_USERNAME)
    )
    result = []
    for u in users:
        product_count = Products.objects.filter(userid=u).count()
        result.append({
            'userid':       u.userid,
            'username':     u.username,
            'useremail':    u.useremail or '',
            'companyname':  u.companyid.companyname if u.companyid else 'No Company',
            'product_count': product_count,
        })
    return Response(result)

@api_view(['GET'])
def admin_products(request):
    """Returns all products with the uploader and their company."""
    products = (
        Products.objects
        .select_related('userid', 'companyid', 'productcategoryid', 'productunitid')
        .all()
        .order_by('-productid')
    )
    result = []
    for p in products:
        result.append({
            'productid':    p.productid,
            'productname':  p.productname,
            'productprice': str(p.productprice),
            'category':     p.productcategoryid.productcategoryname if p.productcategoryid else '',
            'unit':         p.productunitid.productunitname if p.productunitid else '',
            'dateadded':    str(p.dateadded) if p.dateadded else '',
            'createdat':    p.createdat.strftime('%Y-%m-%d %H:%M') if p.createdat else '',
            'addtype':      p.addtype or 'Single',
            'uploaded_by':  p.userid.username if p.userid else 'Unknown',
            'userid':       p.userid.userid if p.userid else None,
            'company':      p.companyid.companyname if p.companyid else 'No Company',
        })
    return Response(result)

@api_view(['GET'])
def admin_user_products(request, user_id):
    """Returns all products for a specific user (for drill-down view)."""
    try:
        user = Users.objects.select_related('companyid').get(userid=user_id)
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    products = (
        Products.objects
        .select_related('productcategoryid', 'productunitid')
        .filter(userid=user)
        .order_by('-createdat', '-productid')
    )
    result = []
    for p in products:
        result.append({
            'productid':    p.productid,
            'productname':  p.productname,
            'productprice': str(p.productprice),
            'category':     p.productcategoryid.productcategoryname if p.productcategoryid else '',
            'unit':         p.productunitid.productunitname if p.productunitid else '',
            'dateadded':    str(p.dateadded) if p.dateadded else '',
            'createdat':    p.createdat.strftime('%Y-%m-%d %H:%M') if p.createdat else '',
            'addtype':      p.addtype or 'Single',
        })
    return Response({
        'username':   user.username,
        'useremail':  user.useremail or '',
        'company':    user.companyid.companyname if user.companyid else '',
        'total':      len(result),
        'products':   result,
    })

@api_view(['GET'])
def admin_company_products(request, company_id):
    """Returns all products for a specific company (for drill-down view)."""
    try:
        company = Company.objects.get(companyid=company_id)
    except Company.DoesNotExist:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)

    products = (
        Products.objects
        .select_related('productcategoryid', 'productunitid', 'userid')
        .filter(companyid=company)
        .order_by('-createdat', '-productid')
    )
    result = []
    for p in products:
        result.append({
            'productid':    p.productid,
            'productname':  p.productname,
            'productprice': str(p.productprice),
            'category':     p.productcategoryid.productcategoryname if p.productcategoryid else '',
            'unit':         p.productunitid.productunitname if p.productunitid else '',
            'dateadded':    str(p.dateadded) if p.dateadded else '',
            'createdat':    p.createdat.strftime('%Y-%m-%d %H:%M') if p.createdat else '',
            'addtype':      p.addtype or 'Single',
        })
    return Response({
        'companyname':   company.companyname,
        'companyphone':  str(company.companyphonenumber) if company.companyphonenumber else '',
        'total':      len(result),
        'products':   result,
    })

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def _handle_image_uploads(self, request, existing_images_str=''):
        files = request.FILES.getlist('productphotopath')
        retained_images = request.data.get('retained_images', '')
        
        saved_paths = []
        if retained_images:
            saved_paths.extend([img.strip() for img in retained_images.split(',') if img.strip()])
        
        for f in files:
            # Generate a unique filename to avoid overwrites
            filename = f"scaled_{uuid.uuid4().hex}_{f.name}"
            # Save file to media root
            file_name = default_storage.save(filename, f)
            saved_paths.append(file_name)
            
        return ','.join(saved_paths)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if 'productphotopath' in request.FILES:
            data['productphotopath'] = self._handle_image_uploads(request)
        data['addtype'] = 'Single'   # mark as single add
        
        user_id = data.get('userid')
        if user_id:
            try:
                user_obj = Users.objects.get(userid=user_id)
                if user_obj.companyid:
                    data['companyid'] = user_obj.companyid.companyid
            except Users.DoesNotExist:
                pass

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()
        
        if 'productphotopath' in request.FILES or 'retained_images' in request.data:
            data['productphotopath'] = self._handle_image_uploads(request, str(instance.productphotopath or ''))
            
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def preview_import(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
        
        file_obj = request.FILES['file']
        if not file_obj.name.endswith(('.xlsx', '.xls', '.csv')):
            return Response({'error': 'Invalid file format. Only Excel and CSV files are supported.'}, status=status.HTTP_400_BAD_REQUEST)
        
        preview_data = []
        try:
            if file_obj.name.endswith('.csv'):
                decoded_file = file_obj.read().decode('utf-8-sig').splitlines()
                reader = csv.reader(decoded_file)
                rows = list(reader)
                if not rows:
                    return Response({'error': 'Empty CSV file'}, status=status.HTTP_400_BAD_REQUEST)
                headers_raw = rows[0]
                data_rows = rows[1:]
            else:
                wb = openpyxl.load_workbook(file_obj, data_only=True)
                sheet = wb.active
                rows = list(sheet.iter_rows(values_only=True))
                if not rows:
                    return Response({'error': 'Empty Excel file'}, status=status.HTTP_400_BAD_REQUEST)
                headers_raw = rows[0]
                data_rows = rows[1:]
            
            headers = [str(h).strip().lower().replace(' ', '').replace('_', '') if h else f'col_{i}' for i, h in enumerate(headers_raw)]
            
            for row in data_rows:
                if not any(row):
                    continue
                
                row_data = dict(zip(headers, list(row) + [''] * (len(headers) - len(row))))
                
                name = row_data.get('name') or row_data.get('productname') or row_data.get('item') or row_data.get('itemname') or row_data.get('title')
                price = row_data.get('price') or row_data.get('productprice') or row_data.get('cost') or row_data.get('rate') or row_data.get('mrp')
                category_name = row_data.get('category') or row_data.get('productcategory') or row_data.get('group') or row_data.get('department')
                unit_name = row_data.get('unit') or row_data.get('productunit') or row_data.get('uom') or row_data.get('measure')
                date_val = row_data.get('date') or row_data.get('dateadded') or row_data.get('created') or row_data.get('added')
                
                if not name and len(row) > 0:
                    name = row[0]
                if price is None and len(row) > 1:
                    price = row[1]
                if not category_name and len(row) > 2:
                    category_name = row[2]
                if not unit_name and len(row) > 3:
                    unit_name = row[3]
                    
                if not name or price is None:
                    continue 
                    
                try:
                    price_str = str(price).replace(',', '').replace('₹', '').replace('$', '').strip()
                    price_val = float(price_str) if price_str else 0.0
                except ValueError:
                    price_val = 0.0

                preview_data.append({
                    'name': str(name).strip(),
                    'price': price_val,
                    'category': str(category_name).strip() if category_name and str(category_name).strip() != 'None' else '',
                    'unit': str(unit_name).strip() if unit_name and str(unit_name).strip() != 'None' else '',
                    'date': str(date_val).strip() if date_val and str(date_val).strip() != 'None' else '',
                })
                
            return Response({'preview': preview_data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def confirm_import(self, request):
        products_data = request.data.get('products', [])
        user_id = request.data.get('userid')   # sent by Flutter
        if not isinstance(products_data, list):
            return Response({'error': 'Expected a list of products'}, status=status.HTTP_400_BAD_REQUEST)

        # Resolve user object if userid provided
        user_obj = None
        company_obj = None
        if user_id:
            try:
                user_obj = Users.objects.get(userid=user_id)
                company_obj = user_obj.companyid
            except Users.DoesNotExist:
                pass

        imported_count = 0
        try:
            for item in products_data:
                name = item.get('name')
                price = item.get('price', 0.0)
                category_name = item.get('category')
                unit_name = item.get('unit')
                item_date = item.get('date')

                if not name:
                    continue

                category_id = None
                if category_name:
                    category, _ = Productcategory.objects.get_or_create(productcategoryname=str(category_name).strip())
                    category_id = category.productcategoryid

                unit_id = None
                if unit_name:
                    unit, _ = Productunit.objects.get_or_create(productunitname=str(unit_name).strip())
                    unit_id = unit.productunitid

                # Parse date if available, otherwise use today's date
                parsed_date = date.today()
                if item_date:
                    try:
                        parsed_date = datetime.strptime(str(item_date), '%Y-%m-%d').date()
                    except ValueError:
                        pass

                Products.objects.update_or_create(
                    productname=str(name).strip(),
                    defaults={
                        'productprice': price,
                        'productcategoryid_id': category_id,
                        'productunitid_id': unit_id,
                        'addtype': 'Bulk',
                        'userid': user_obj,
                        'companyid': company_obj,
                        'dateadded': parsed_date,
                    }
                )
                imported_count += 1

            return Response({'message': f'Successfully imported {imported_count} products'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = Productcategory.objects.all()
    serializer_class = ProductCategorySerializer

class ProductUnitViewSet(viewsets.ModelViewSet):
    queryset = Productunit.objects.all()
    serializer_class = ProductUnitSerializer
