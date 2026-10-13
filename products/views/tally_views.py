import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, OpenApiTypes, inline_serializer
from products.models import (
    Company, Users, Companycategory, Supplier, SupplierBill,
    Customer, CustomerBill, Products, Productcategory, Productunit, EndUser
)

logger = logging.getLogger(__name__)

def parse_tally_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    for fmt in ('%Y-%m-%d', '%Y%m%d', '%d-%b-%Y', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    return None

@extend_schema(
    summary="List Company Categories",
    description="Returns all company categories available for Tally registration. No authentication required.",
    responses={200: OpenApiResponse(description="List of categories with categoryid and categoryname")},
    tags=["Tally Sync"]
)
@api_view(['GET'])
@permission_classes([AllowAny])
def tally_categories_view(request):
    cats = Companycategory.objects.all().values('categoryid', 'categoryname')
    return Response({'status': 'success', 'categories': list(cats)}, status=200)

@extend_schema(
    summary="Register Company (Tally)",
    description="Registers a new company and user account from Tally ERP. No authentication required.",
    request=inline_serializer(
        name="TallyRegisterCompanyRequest",
        fields={
            "company_name": serializers.CharField(help_text="Company name (required)"),
            "company_phone": serializers.CharField(help_text="Company phone number (required)"),
            "username": serializers.CharField(help_text="Login username (required)"),
            "password": serializers.CharField(help_text="Login password (required)"),
            "company_address": serializers.CharField(required=False, help_text="Company address"),
            "company_location": serializers.CharField(required=False, help_text="Company location"),
            "category_id": serializers.IntegerField(required=False, help_text="Company category ID from /tally/categories/"),
        }
    ),
    responses={
        201: OpenApiResponse(description="Company registered successfully — returns company_id, username"),
        400: OpenApiResponse(description="Missing required fields or username taken"),
        500: OpenApiResponse(description="Internal server error"),
    },
    tags=["Tally Sync"]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def tally_register_company_view(request):
    company_name = str(request.data.get('company_name', '')).strip()
    company_phone_raw = str(request.data.get('company_phone', '')).strip()
    company_address = str(request.data.get('company_address', '')).strip()
    company_location = str(request.data.get('company_location', '')).strip()
    category_id = request.data.get('category_id')
    username = str(request.data.get('username', '')).strip()
    password = str(request.data.get('password', '')).strip()

    if not company_name or not company_phone_raw or not username or not password:
        return Response({'status': 'error', 'message': 'Missing required fields'}, status=400)

    try:
        phone_int = int(''.join(filter(str.isdigit, company_phone_raw)))
    except ValueError:
        return Response({'status': 'error', 'message': 'Valid phone number is required'}, status=400)

    if Users.objects.filter(username__iexact=username).exists():
        return Response({'status': 'error', 'message': f'Username "{username}" is already taken'}, status=400)

    category = None
    if category_id:
        category = Companycategory.objects.filter(categoryid=category_id).first()
    if not category:
        category = Companycategory.objects.first()

    try:
        with transaction.atomic():
            company = Company.objects.create(
                companyname=company_name,
                companyphonenumber=phone_int,
                companyaddress=company_address or 'Kerala, India',
                companylocation=company_location or 'Kerala, India',
                categoryid=category,
                coins_balance=0,
                premium_tokens_balance=0
            )

            user = Users.objects.create(
                username=username,
                useremail=f"{username}@frontlly.com",
                userpassword=make_password(password),
                companyid=company
            )

        return Response({
            'status': 'success',
            'company_id': company.companyid,
            'company_name': company.companyname,
            'company_phone': str(company.companyphonenumber),
            'username': user.username,
            'message': 'Company registered successfully'
        }, status=201)

    except Exception as e:
        logger.error(f"Error registering company: {e}")
        return Response({'status': 'error', 'message': str(e)}, status=500)

@extend_schema(
    summary="Login Company (Tally)",
    description="Authenticates a company user from Tally ERP and returns company details. No authentication required.",
    request=inline_serializer(
        name="TallyLoginCompanyRequest",
        fields={
            "username": serializers.CharField(help_text="Login username"),
            "password": serializers.CharField(help_text="Login password"),
        }
    ),
    responses={
        200: OpenApiResponse(description="Login successful — returns company_id, company_name, company_phone"),
        400: OpenApiResponse(description="Missing fields or no company linked"),
        401: OpenApiResponse(description="Invalid username or password"),
    },
    tags=["Tally Sync"]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def tally_login_company_view(request):
    username = str(request.data.get('username', '')).strip()
    password = str(request.data.get('password', '')).strip()

    if not username or not password:
        return Response({'status': 'error', 'message': 'Username and password required'}, status=400)

    user = Users.objects.filter(username__iexact=username).select_related('companyid').first()
    if not user or not check_password(password, user.userpassword):
        return Response({'status': 'error', 'message': 'Invalid username or password'}, status=401)

    company = user.companyid
    if not company:
        return Response({'status': 'error', 'message': 'No company linked to this user'}, status=400)

    return Response({
        'status': 'success',
        'company_id': company.companyid,
        'company_name': company.companyname,
        'company_phone': str(company.companyphonenumber),
        'username': user.username,
        'message': 'Logged in successfully'
    }, status=200)

@extend_schema(
    summary="Test Tally Connection",
    description="Verifies that a Tally ERP client can reach this server and validates the company credentials.",
    request=inline_serializer(
        name="TallyTestConnectionRequest",
        fields={
            "company_id": serializers.IntegerField(help_text="Company ID to verify (required)"),
            "company_phone": serializers.CharField(required=False, help_text="Optional phone to verify against DB"),
        }
    ),
    responses={
        200: OpenApiResponse(description="Connection successful"),
        400: OpenApiResponse(description="company_id missing"),
        401: OpenApiResponse(description="Phone verification failed"),
        404: OpenApiResponse(description="Company not found"),
    },
    tags=["Tally Sync"]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def tally_test_connection_view(request):
    company_id = request.data.get('company_id')
    company_phone = request.data.get('company_phone')
    
    if not company_id:
        return Response({'status': 'error', 'message': 'company_id is required'}, status=400)
        
    try:
        company = Company.objects.get(companyid=company_id)
        if company_phone and str(company.companyphonenumber) != str(company_phone):
            return Response({'status': 'error', 'message': 'Invalid company phone verification'}, status=401)
            
        return Response({
            'status': 'success',
            'company_id': company.companyid,
            'company_name': company.companyname,
            'message': 'Connected successfully to Frontlly'
        }, status=200)
    except Company.DoesNotExist:
        return Response({'status': 'error', 'message': 'Company not found'}, status=404)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)

@extend_schema(
    summary="Sync Bills from Tally",
    description=(
        "Bulk-syncs supplier bills, customer bills, and products from Tally ERP.\n\n"
        "- **bills**: List of supplier/purchase bill objects\n"
        "- **customer_bills**: List of customer/sales bill objects\n"
        "- **products**: List of stock item objects\n\n"
        "Each bill object supports: party_name, bill_no, bill_date, due_date, "
        "original_amount, pending_balance, party_gst, party_phone, party_address, bill_type, narration."
    ),
    request=inline_serializer(
        name="TallySyncBillsRequest",
        fields={
            "company_id": serializers.IntegerField(help_text="Company ID (required)"),
            "company_phone": serializers.CharField(required=False, help_text="Company phone for verification"),
            "bills": serializers.ListField(
                child=serializers.DictField(),
                required=False,
                help_text="List of supplier bill objects from Tally"
            ),
            "customer_bills": serializers.ListField(
                child=serializers.DictField(),
                required=False,
                help_text="List of customer bill objects from Tally"
            ),
            "products": serializers.ListField(
                child=serializers.DictField(),
                required=False,
                help_text="List of stock item/product objects from Tally"
            ),
        }
    ),
    responses={
        200: OpenApiResponse(description="Sync result with counts of created/updated records"),
        400: OpenApiResponse(description="company_id missing"),
        401: OpenApiResponse(description="Phone verification failed"),
        404: OpenApiResponse(description="Company not found"),
    },
    tags=["Tally Sync"]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def tally_sync_bills_view(request):
    company_id = request.data.get('company_id')
    company_phone = request.data.get('company_phone')
    supplier_bills = request.data.get('bills') or request.data.get('supplier_bills', [])
    customer_bills = request.data.get('customer_bills', [])
    products_data = request.data.get('products', [])
    
    if not company_id:
        return Response({'status': 'error', 'message': 'company_id is required'}, status=400)
        
    try:
        company = Company.objects.get(companyid=company_id)
        if company_phone and str(company.companyphonenumber) != str(company_phone):
            return Response({'status': 'error', 'message': 'Unauthorized company phone verification'}, status=401)
    except Company.DoesNotExist:
        return Response({'status': 'error', 'message': 'Company not found'}, status=404)

    created_bills = 0
    updated_bills = 0
    created_suppliers = 0
    matched_existing_suppliers = 0

    created_cust_bills = 0
    created_customers = 0
    created_products = 0
    errors = []

    # 1. PROCESS SUPPLIERS & SUPPLIER BILLS / DEBIT NOTES
    if isinstance(supplier_bills, list):
        for item in supplier_bills:
            party_name = str(item.get('party_name', '')).strip()
            bill_no = str(item.get('bill_no', '')).strip()
            if not party_name or not bill_no:
                continue

            party_gst = str(item.get('party_gst', '')).strip()
            party_phone = str(item.get('party_phone', '')).strip()
            raw_bill_date = item.get('bill_date')
            raw_due_date = item.get('due_date')

            try:
                orig_amount = Decimal(str(item.get('original_amount', 0) or 0))
            except Exception:
                orig_amount = Decimal('0.00')

            try:
                pending_balance = Decimal(str(item.get('pending_balance', orig_amount) or 0))
            except Exception:
                pending_balance = orig_amount

            paid_amount = max(Decimal('0.00'), orig_amount - pending_balance)
            bill_date = parse_tally_date(raw_bill_date) or timezone.now().date()
            due_date = parse_tally_date(raw_due_date) or (bill_date + timedelta(days=30))
            bill_type = str(item.get('bill_type', 'Bill')).strip() or 'Bill'
            narration = str(item.get('narration', '')).strip() or f'Synced from Tally on {timezone.now().strftime("%Y-%m-%d %H:%M")}'

            try:
                with transaction.atomic():
                    # Check this company first
                    supplier = None
                    if party_gst:
                        supplier = Supplier.objects.filter(companyid=company, suppliergst__iexact=party_gst).first()
                    if not supplier and party_phone:
                        supplier = Supplier.objects.filter(companyid=company, supplierphonenumber=party_phone).first()
                    if not supplier:
                        supplier = Supplier.objects.filter(companyid=company, suppliername__iexact=party_name).first()

                    if not supplier:
                        # Global Platform Match (Match existing supplier across ANY company by GST or Phone)
                        global_match = None
                        if party_gst:
                            global_match = Supplier.objects.filter(suppliergst__iexact=party_gst).first()
                        if not global_match and party_phone:
                            global_match = Supplier.objects.filter(supplierphonenumber=party_phone).first()

                        if global_match:
                            # Auto-connected to verified platform supplier!
                            supplier = Supplier.objects.create(
                                companyid=company,
                                suppliername=global_match.suppliername,
                                suppliergst=global_match.suppliergst or party_gst,
                                supplierphonenumber=global_match.supplierphonenumber or party_phone,
                                supplieraddress=global_match.supplieraddress or str(item.get('party_address', '')).strip(),
                                supplieropeningbal=Decimal(str(item.get('party_opening_bal', 0) or 0)),
                                suppliercurrentbal=Decimal(str(item.get('party_current_bal', pending_balance) or pending_balance)),
                                isconnected=True,
                                coins_balance=0,
                                premium_tokens_balance=0
                            )
                            matched_existing_suppliers += 1
                        else:
                            # Brand new supplier
                            supplier = Supplier.objects.create(
                                companyid=company,
                                suppliername=party_name,
                                suppliergst=party_gst,
                                supplierphonenumber=party_phone,
                                supplieraddress=str(item.get('party_address', '')).strip(),
                                supplieropeningbal=Decimal(str(item.get('party_opening_bal', 0) or 0)),
                                suppliercurrentbal=Decimal(str(item.get('party_current_bal', pending_balance) or pending_balance)),
                                isconnected=False,
                                coins_balance=0,
                                premium_tokens_balance=0
                            )
                            created_suppliers += 1
                    else:
                        dirty = False
                        if party_gst and (not supplier.suppliergst or supplier.suppliergst != party_gst):
                            supplier.suppliergst = party_gst
                            dirty = True
                        if party_phone and (not supplier.supplierphonenumber or supplier.supplierphonenumber != party_phone):
                            supplier.supplierphonenumber = party_phone
                            dirty = True
                        party_addr = str(item.get('party_address', '')).strip()
                        if party_addr and not supplier.supplieraddress:
                            supplier.supplieraddress = party_addr
                            dirty = True
                        party_state = str(item.get('party_state', '')).strip()
                        if party_state and not supplier.supplierstate:
                            supplier.supplierstate = party_state
                            dirty = True
                        if dirty:
                            supplier.save()

                    bill_obj, created = SupplierBill.objects.update_or_create(
                        supplierid=supplier,
                        supplierbillno=bill_no,
                        defaults={
                            'supplierbilldate': bill_date,
                            'supplierbillduedate': due_date,
                            'supplierbillamount': orig_amount,
                            'paidamount': paid_amount,
                            'balance': pending_balance,
                            'supplierbilltype': bill_type,
                            'narration': narration
                        }
                    )
                    if created:
                        created_bills += 1
                    else:
                        updated_bills += 1
            except Exception as e:
                errors.append({'bill_no': bill_no, 'error': str(e)})

    # 2. PROCESS CUSTOMERS (SUNDRY DEBTORS) & CUSTOMER BILLS / CREDIT NOTES
    if isinstance(customer_bills, list):
        for item in customer_bills:
            cust_name = str(item.get('party_name', '')).strip()
            bill_no = str(item.get('bill_no', '')).strip()
            if not cust_name or not bill_no:
                continue

            cust_phone = str(item.get('party_phone', '')).strip()
            cust_gst = str(item.get('party_gst', '')).strip()
            cust_address = str(item.get('party_address', '')).strip()
            raw_bill_date = item.get('bill_date')
            raw_due_date = item.get('due_date')

            try:
                orig_amount = Decimal(str(item.get('original_amount', 0) or 0))
                pending_balance = Decimal(str(item.get('pending_balance', orig_amount) or 0))
            except Exception:
                orig_amount = Decimal('0.00')
                pending_balance = Decimal('0.00')

            paid_amount = max(Decimal('0.00'), orig_amount - pending_balance)
            bill_date = parse_tally_date(raw_bill_date) or timezone.now().date()
            due_date = parse_tally_date(raw_due_date) or (bill_date + timedelta(days=30))
            bill_type = str(item.get('bill_type', 'Sales')).strip() or 'Sales'
            narration = str(item.get('narration', '')).strip() or f'Synced from Tally'

            try:
                with transaction.atomic():
                    customer = None
                    if cust_phone:
                        customer = Customer.objects.filter(companyid=company, customerphonenumber=cust_phone).first()
                    if not customer:
                        customer = Customer.objects.filter(companyid=company, customername__iexact=cust_name).first()

                    if not customer:
                        customer = Customer.objects.create(
                            companyid=company,
                            customername=cust_name,
                            customerphonenumber=cust_phone,
                            customergst=cust_gst,
                            customeraddress=cust_address,
                            customeremail='',
                            customeropeningbal=Decimal('0.00'),
                            customercurrentbal=pending_balance,
                            customerpincode='',
                            customerstate=str(item.get('party_state', 'Kerala')).strip() or 'Kerala',
                            customerpanno=''
                        )
                        created_customers += 1
                    else:
                        dirty = False
                        if cust_phone and (not customer.customerphonenumber or customer.customerphonenumber != cust_phone):
                            customer.customerphonenumber = cust_phone
                            dirty = True
                        if cust_gst and (not customer.customergst or customer.customergst != cust_gst):
                            customer.customergst = cust_gst
                            dirty = True
                        if cust_address and not customer.customeraddress:
                            customer.customeraddress = cust_address
                            dirty = True
                        if dirty:
                            customer.save()

                    CustomerBill.objects.update_or_create(
                        customerid=customer,
                        customerbillno=bill_no,
                        defaults={
                            'customerbilldate': bill_date,
                            'customerbillduedate': due_date,
                            'customerbillamount': orig_amount,
                            'paidamount': paid_amount,
                            'balance': pending_balance,
                            'customerbilltype': bill_type,
                            'narration': narration
                        }
                    )
                    created_cust_bills += 1
            except Exception as e:
                errors.append({'customer_bill_no': bill_no, 'error': str(e)})

    # 3. PROCESS PRODUCTS (STOCK ITEMS)
    if isinstance(products_data, list):
        cat_default = Productcategory.objects.first()
        unit_default = Productunit.objects.first()
        admin_user = Users.objects.filter(companyid=company).first()

        for p in products_data:
            p_name = str(p.get('name', '')).strip()
            if not p_name:
                continue

            try:
                price = Decimal(str(p.get('price', 0) or 0))
            except Exception:
                price = Decimal('0.00')

            try:
                Products.objects.update_or_create(
                    companyid=company,
                    productname=p_name,
                    defaults={
                        'productcategoryid': cat_default,
                        'productunitid': unit_default,
                        'productprice': price,
                        'dateadded': timezone.now().date(),
                        'userid': admin_user,
                        'addtype': 'Tally'
                    }
                )
                created_products += 1
            except Exception as e:
                errors.append({'product': p_name, 'error': str(e)})

    return Response({
        'status': 'success',
        'company_id': company.companyid,
        'company_name': company.companyname,
        'created_supplier_bills': created_bills,
        'updated_supplier_bills': updated_bills,
        'created_suppliers': created_suppliers,
        'matched_existing_suppliers': matched_existing_suppliers,
        'created_customers': created_customers,
        'created_customer_bills': created_cust_bills,
        'created_products': created_products,
        'errors': errors
    }, status=200)
