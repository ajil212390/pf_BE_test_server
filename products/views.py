from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Products, Productcategory, Productunit, Company, Users, Customer, Supplier, CustomerBill, SupplierBill, EndUser, Supplieruser, Companycategory, Conversation, ChatMessage, SupplierExecutive, ExecutiveAllocation, SupplierOrder, SupplierOrderItem
from .serializers import ProductSerializer, ProductCategorySerializer, ProductUnitSerializer, CompanySerializer, CompanyCategorySerializer
from django.core.files.storage import default_storage
import uuid
from rest_framework.decorators import action, api_view
import openpyxl
import csv
import io
from datetime import datetime, date
from django.db.models import Q, Sum
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes, inline_serializer
from rest_framework import serializers

@extend_schema(
    request=inline_serializer(
        name="RegisterEndUserRequest",
        fields={
            "endusername": serializers.CharField(),
            "enduserpassword": serializers.CharField(),
            "enduseremail": serializers.EmailField(required=False),
            "enduserphone": serializers.CharField(required=False),
        }
    ),
    responses={201: OpenApiResponse(description="Registration successful"), 400: OpenApiResponse(description="Bad request")}
)
@api_view(['POST'])
def register_enduser(request):
    data = request.data
    try:
        if EndUser.objects.filter(endusername__iexact=data.get('endusername')).exists():
            return Response({'error': 'Username already taken.'}, status=status.HTTP_400_BAD_REQUEST)

        enduser = EndUser.objects.create(
            endusername=data.get('endusername'),
            enduserpassword=data.get('enduserpassword'),  # plain text, matching your existing pattern
            enduseremail=data.get('enduseremail'),
            enduserphone=data.get('enduserphone'),
        )
        return Response({
            'message': 'Registration successful',
            'enduserid': enduser.endsuerid,
            'endusername': enduser.endusername,
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=inline_serializer(
        name="LoginSupplierRequest",
        fields={
            "supplierusername": serializers.CharField(required=False),
            "supplieruserphone": serializers.CharField(required=False),
            "supplieruserpassword": serializers.CharField(),
        }
    ),
    responses={200: OpenApiResponse(description="Login successful"), 400: OpenApiResponse(description="Bad request"), 401: OpenApiResponse(description="Unauthorized"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['POST'])
def login_supplier(request):
    data = request.data
    username_or_phone = data.get('supplierusername') or data.get('username') or data.get('supplieruserphone') or data.get('phone')
    password = data.get('supplieruserpassword') or data.get('password')

    if not username_or_phone or not password:
        return Response({'error': 'Username (or phone) and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        supplier_user = Supplieruser.objects.filter(
            Q(supplierusername__iexact=username_or_phone) |
            Q(supplieruserphone__iexact=username_or_phone)
        ).first()

        if not supplier_user:
            return Response({'error': 'Username or phone not found.'}, status=status.HTTP_404_NOT_FOUND)

        if supplier_user.supplieruserpassword == password:
            return Response({
                'message': 'Login successful',
                'supplieruserid': supplier_user.supplieruserid,
                'supplierid': supplier_user.supplierid_id,
                'suppliername': supplier_user.suppliername or '',
                'supplierusername': supplier_user.supplierusername,
                'supplieruseremail': supplier_user.supplieruseremail or '',
                'supplieruserphone': supplier_user.supplieruserphone or '',
                'supplierusergstnumber': supplier_user.supplierusergstnumber or '',
                'supplieruseraddress': supplier_user.supplieruseraddress or '',
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=inline_serializer(
        name="LoginEndUserRequest",
        fields={
            "endusername": serializers.CharField(),
            "enduserpassword": serializers.CharField(),
        }
    ),
    responses={200: OpenApiResponse(description="Login successful"), 401: OpenApiResponse(description="Unauthorized"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['POST'])
def login_enduser(request):
    data = request.data
    username = data.get('endusername')
    password = data.get('enduserpassword')

    try:
        enduser = EndUser.objects.get(endusername__iexact=username)
        if enduser.enduserpassword == password:
            return Response({
                'message': 'Login successful',
                'enduserid': enduser.endsuerid,
                'endusername': enduser.endusername,
                'enduseremail': enduser.enduseremail or '',
                'enduserphone': enduser.enduserphone or '',
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)
    except EndUser.DoesNotExist:
        return Response({'error': 'Username not found.'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(
    request=inline_serializer(
        name="RegisterUserRequest",
        fields={
            "companyname": serializers.CharField(required=False),
            "companyphonenumber": serializers.CharField(required=False),
            "username": serializers.CharField(),
            "useremail": serializers.EmailField(required=False),
            "userpassword": serializers.CharField(),
        }
    ),
    responses={201: OpenApiResponse(description="Registration successful"), 400: OpenApiResponse(description="Bad request")}
)
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

@extend_schema(
    request=inline_serializer(
        name="LoginUserRequest",
        fields={
            "username": serializers.CharField(),
            "userpassword": serializers.CharField(),
        }
    ),
    responses={200: OpenApiResponse(description="Login successful"), 401: OpenApiResponse(description="Unauthorized"), 404: OpenApiResponse(description="Not found")}
)
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

@extend_schema(
    request=inline_serializer(
        name="UpdateCompanyRequest",
        fields={
            "userid": serializers.IntegerField(),
            "companyname": serializers.CharField(required=False),
            "companyphonenumber": serializers.CharField(required=False),
        }
    ),
    responses={200: OpenApiResponse(description="Company updated successfully"), 400: OpenApiResponse(description="Bad request"), 404: OpenApiResponse(description="Not found")}
)
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

@extend_schema(
    request=inline_serializer(
        name="ChangePasswordRequest",
        fields={
            "userid": serializers.IntegerField(),
            "current_password": serializers.CharField(),
            "new_password": serializers.CharField(),
        }
    ),
    responses={200: OpenApiResponse(description="Password changed successfully"), 400: OpenApiResponse(description="Bad request"), 404: OpenApiResponse(description="Not found")}
)
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

def _currency_value(value):
    if value is None:
        return 0.0
    return float(Decimal(str(value)).quantize(Decimal('0.01')))


def _build_financial_summary(total_count, bill_count, bill_amount, note_count, note_amount, paid_amount, balance_amount):
    return {
        'count': total_count,
        'bills_count': bill_count,
        'bills_amount': _currency_value(bill_amount),
        'notes_count': note_count,
        'notes_amount': _currency_value(note_amount),
        'paid_amount': _currency_value(paid_amount),
        'balance_amount': _currency_value(balance_amount),
    }


def _rollup_account_rows(rows):
    bill_count = sum(int(row.get('bills_count') or 0) for row in rows)
    bills_amount = sum(float(row.get('bills_amount') or 0.0) for row in rows)
    note_count = sum(int(row.get('credit_notes_count') or row.get('debit_notes_count') or 0) for row in rows)
    notes_amount = sum(float(row.get('credit_notes_amount') or row.get('debit_notes_amount') or 0.0) for row in rows)
    paid_amount = sum(float(row.get('paid_amount') or 0.0) for row in rows)
    balance_amount = sum(float(row.get('balance_amount') or 0.0) for row in rows)
    return {
        'bills_count': bill_count,
        'bills_amount': _currency_value(bills_amount),
        'notes_count': note_count,
        'notes_amount': _currency_value(notes_amount),
        'paid_amount': _currency_value(paid_amount),
        'balance_amount': _currency_value(balance_amount),
    }


def _net_outstanding(balance_amount, note_amount):
    balance_amount = balance_amount or Decimal('0.00')
    note_amount = note_amount or Decimal('0.00')
    return balance_amount - note_amount


def _is_note_entry(entry_type):
    if not entry_type:
        return False
    normalized = str(entry_type).strip().lower()
    return any(marker in normalized for marker in ['return', 'credit', 'debit', 'note'])


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
def admin_user_customer_supplier_overview(request, user_id):
    """Returns customer and supplier overview totals for the company's dashboard."""
    try:
        user = Users.objects.select_related('companyid').get(userid=user_id)
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    company = user.companyid
    if company is None:
        empty_summary = _build_financial_summary(0, 0, Decimal('0.00'), 0, Decimal('0.00'), Decimal('0.00'), Decimal('0.00'))
        return Response({
            'company': '',
            'totalCustomers': 0,
            'totalSuppliers': 0,
            'customers': empty_summary,
            'suppliers': empty_summary,
        })

    customers = Customer.objects.filter(companyid=company)
    suppliers = Supplier.objects.filter(companyid=company)

    customer_bills = CustomerBill.objects.filter(customerid__companyid=company)
    supplier_bills = SupplierBill.objects.filter(supplierid__companyid=company)

    customer_note_types = ('Credit Note', 'Credit Notes', 'Credit', 'CreditNote', 'CN', 'Return', 'Sales Return')
    supplier_note_types = ('Debit Note', 'Debit Notes', 'Debit', 'DebitNote', 'DN', 'Return', 'Purchase Return')

    customer_note_bills = []
    customer_regular_bills = []
    for bill in customer_bills:
        if _is_note_entry(getattr(bill, 'customerbilltype', None)):
            customer_note_bills.append(bill)
        else:
            customer_regular_bills.append(bill)

    supplier_note_bills = []
    supplier_regular_bills = []
    for bill in supplier_bills:
        if _is_note_entry(getattr(bill, 'supplierbilltype', None)):
            supplier_note_bills.append(bill)
        else:
            supplier_regular_bills.append(bill)

    customer_regular_bill_ids = [bill.customerbillid for bill in customer_regular_bills]
    customer_note_bill_ids = [bill.customerbillid for bill in customer_note_bills]
    supplier_regular_bill_ids = [bill.supplierbillid for bill in supplier_regular_bills]
    supplier_note_bill_ids = [bill.supplierbillid for bill in supplier_note_bills]

    customer_regular_bills_qs = customer_bills.filter(customerbillid__in=customer_regular_bill_ids)
    customer_note_bills_qs = customer_bills.filter(customerbillid__in=customer_note_bill_ids)
    supplier_regular_bills_qs = supplier_bills.filter(supplierbillid__in=supplier_regular_bill_ids)
    supplier_note_bills_qs = supplier_bills.filter(supplierbillid__in=supplier_note_bill_ids)

    customer_bills_amount = customer_regular_bills_qs.aggregate(total=Sum('customerbillamount'))['total'] or Decimal('0.00')
    customer_paid_amount = customer_regular_bills_qs.aggregate(total=Sum('paidamount'))['total'] or Decimal('0.00')
    customer_balance_amount = customer_regular_bills_qs.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
    customer_notes_amount = customer_note_bills_qs.aggregate(total=Sum('customerbillamount'))['total'] or Decimal('0.00')
    customer_outstanding_amount = _net_outstanding(customer_balance_amount, customer_notes_amount)

    supplier_bills_amount = supplier_regular_bills_qs.aggregate(total=Sum('supplierbillamount'))['total'] or Decimal('0.00')
    supplier_paid_amount = supplier_regular_bills_qs.aggregate(total=Sum('paidamount'))['total'] or Decimal('0.00')
    supplier_balance_amount = supplier_regular_bills_qs.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
    supplier_notes_amount = supplier_note_bills_qs.aggregate(total=Sum('supplierbillamount'))['total'] or Decimal('0.00')
    supplier_outstanding_amount = _net_outstanding(supplier_balance_amount, supplier_notes_amount)

    customer_bill_items = []
    customer_note_items = []
    customer_payment_items = []
    for bill in customer_regular_bills:
        item = {
            'id': bill.customerbillid,
            'customer_id': bill.customerid.customerid if getattr(bill, 'customerid', None) else None,
            'customer_name': bill.customerid.customername if getattr(bill, 'customerid', None) else '',
            'bill_no': bill.customerbillno or '',
            'date': str(bill.customerbilldate) if bill.customerbilldate else '',
            'due_date': str(bill.customerbillduedate) if bill.customerbillduedate else '',
            'amount': float(bill.customerbillamount or 0),
            'paid_amount': float(bill.paidamount or 0),
            'balance': float(bill.balance or 0),
            'narration': bill.narration or '',
            'type': bill.customerbilltype or '',
        }
        customer_bill_items.append(item)
        if item['paid_amount'] > 0:
            customer_payment_items.append({**item, 'status': 'Paid' if item['balance'] <= 0 else 'Partially Paid'})

    for bill in customer_note_bills:
        customer_note_items.append({
            'id': bill.customerbillid,
            'customer_id': bill.customerid.customerid if getattr(bill, 'customerid', None) else None,
            'customer_name': bill.customerid.customername if getattr(bill, 'customerid', None) else '',
            'bill_no': bill.customerbillno or '',
            'date': str(bill.customerbilldate) if bill.customerbilldate else '',
            'due_date': str(bill.customerbillduedate) if bill.customerbillduedate else '',
            'amount': float(bill.customerbillamount or 0),
            'paid_amount': float(bill.paidamount or 0),
            'balance': float(bill.balance or 0),
            'narration': bill.narration or '',
            'type': bill.customerbilltype or '',
        })

    supplier_bill_items = []
    supplier_note_items = []
    supplier_payment_items = []
    for bill in supplier_regular_bills:
        item = {
            'id': bill.supplierbillid,
            'supplier_id': bill.supplierid.supplierid if getattr(bill, 'supplierid', None) else None,
            'supplier_name': bill.supplierid.suppliername if getattr(bill, 'supplierid', None) else '',
            'bill_no': bill.supplierbillno or '',
            'date': str(bill.supplierbilldate) if bill.supplierbilldate else '',
            'due_date': str(bill.supplierbillduedate) if bill.supplierbillduedate else '',
            'amount': float(bill.supplierbillamount or 0),
            'paid_amount': float(bill.paidamount or 0),
            'balance': float(bill.balance or 0),
            'narration': bill.narration or '',
            'type': bill.supplierbilltype or '',
        }
        supplier_bill_items.append(item)
        if item['paid_amount'] > 0:
            supplier_payment_items.append({**item, 'status': 'Paid' if item['balance'] <= 0 else 'Partially Paid'})

    for bill in supplier_note_bills:
        supplier_note_items.append({
            'id': bill.supplierbillid,
            'supplier_id': bill.supplierid.supplierid if getattr(bill, 'supplierid', None) else None,
            'supplier_name': bill.supplierid.suppliername if getattr(bill, 'supplierid', None) else '',
            'bill_no': bill.supplierbillno or '',
            'date': str(bill.supplierbilldate) if bill.supplierbilldate else '',
            'due_date': str(bill.supplierbillduedate) if bill.supplierbillduedate else '',
            'amount': float(bill.supplierbillamount or 0),
            'paid_amount': float(bill.paidamount or 0),
            'balance': float(bill.balance or 0),
            'narration': bill.narration or '',
            'type': bill.supplierbilltype or '',
        })

    customer_list = []
    for customer in customers:
        customer_entry_bills = CustomerBill.objects.filter(customerid=customer)
        customer_entry_note_bills = [bill for bill in customer_entry_bills if _is_note_entry(getattr(bill, 'customerbilltype', None))]
        customer_entry_regular_bills = [bill for bill in customer_entry_bills if not _is_note_entry(getattr(bill, 'customerbilltype', None))]
        customer_entry_bills_amount = sum(float(b.customerbillamount or 0) for b in customer_entry_regular_bills)
        customer_entry_notes_amount = sum(float(b.customerbillamount or 0) for b in customer_entry_note_bills)
        customer_entry_paid_amount = sum(float(b.paidamount or 0) for b in customer_entry_regular_bills)
        customer_entry_balance_amount = sum(float(b.balance or 0) for b in customer_entry_regular_bills)
        customer_entry_outstanding_amount = customer_entry_balance_amount - customer_entry_notes_amount
        customer_list.append({
            'id': customer.customerid,
            'name': customer.customername,
            'gst_number': customer.customergst or '',
            'phone': customer.customerphonenumber or '',
            'email': customer.customeremail or '',
            'address': customer.customeraddress or '',
            'bills_count': len(customer_entry_regular_bills),
            'bills_amount': customer_entry_bills_amount,
            'credit_notes_count': len(customer_entry_note_bills),
            'credit_notes_amount': customer_entry_notes_amount,
            'paid_amount': customer_entry_paid_amount,
            'balance_amount': customer_entry_outstanding_amount,
        })

    customer_summary = _build_financial_summary(
        total_count=customers.count(),
        bill_count=sum(int(item['bills_count']) for item in customer_list),
        bill_amount=sum(float(item['bills_amount']) for item in customer_list),
        note_count=sum(int(item['credit_notes_count']) for item in customer_list),
        note_amount=sum(float(item['credit_notes_amount']) for item in customer_list),
        paid_amount=sum(float(item['paid_amount']) for item in customer_list),
        balance_amount=sum(float(item['balance_amount']) for item in customer_list),
    )

    supplier_list = []
    for supplier in suppliers:
        supplier_entry_bills = SupplierBill.objects.filter(supplierid=supplier)
        supplier_entry_note_bills = [bill for bill in supplier_entry_bills if _is_note_entry(getattr(bill, 'supplierbilltype', None))]
        supplier_entry_regular_bills = [bill for bill in supplier_entry_bills if not _is_note_entry(getattr(bill, 'supplierbilltype', None))]
        supplier_entry_bills_amount = sum(float(b.supplierbillamount or 0) for b in supplier_entry_regular_bills)
        supplier_entry_notes_amount = sum(float(b.supplierbillamount or 0) for b in supplier_entry_note_bills)
        supplier_entry_paid_amount = sum(float(b.paidamount or 0) for b in supplier_entry_regular_bills)
        supplier_entry_balance_amount = sum(float(b.balance or 0) for b in supplier_entry_regular_bills)
        supplier_entry_outstanding_amount = supplier_entry_balance_amount - supplier_entry_notes_amount
        supplier_list.append({
            'id': supplier.supplierid,
            'name': supplier.suppliername,
            'gst_number': supplier.suppliergst or '',
            'phone': supplier.supplierphonenumber or '',
            'email': supplier.supplieremail or '',
            'address': supplier.supplieraddress or '',
            'bills_count': len(supplier_entry_regular_bills),
            'bills_amount': supplier_entry_bills_amount,
            'debit_notes_count': len(supplier_entry_note_bills),
            'debit_notes_amount': supplier_entry_notes_amount,
            'paid_amount': supplier_entry_paid_amount,
            'balance_amount': supplier_entry_outstanding_amount,
        })

    supplier_summary = _build_financial_summary(
        total_count=suppliers.count(),
        bill_count=sum(int(item['bills_count']) for item in supplier_list),
        bill_amount=sum(float(item['bills_amount']) for item in supplier_list),
        note_count=sum(int(item['debit_notes_count']) for item in supplier_list),
        note_amount=sum(float(item['debit_notes_amount']) for item in supplier_list),
        paid_amount=sum(float(item['paid_amount']) for item in supplier_list),
        balance_amount=sum(float(item['balance_amount']) for item in supplier_list),
    )

    return Response({
        'company': company.companyname,
        'totalCustomers': customer_summary['count'],
        'totalSuppliers': supplier_summary['count'],
        'customers': customer_summary,
        'customer_list': customer_list,
        'customer_bills': customer_bill_items,
        'customer_notes': customer_note_items,
        'customer_payments': customer_payment_items,
        'suppliers': supplier_summary,
        'supplier_list': supplier_list,
        'supplier_bills': supplier_bill_items,
        'supplier_notes': supplier_note_items,
        'supplier_payments': supplier_payment_items,
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

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

class CompanyCategoryViewSet(viewsets.ModelViewSet):
    queryset = Companycategory.objects.all()
    serializer_class = CompanyCategorySerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get('companyid')
        if company_id:
            queryset = queryset.filter(companyid=company_id)
        return queryset

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
        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
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
        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
        
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

@extend_schema(
    parameters=[
        OpenApiParameter(name="phone", description="Supplier Phone Number", required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name="gstn", description="Supplier GST Number", required=False, type=OpenApiTypes.STR),
    ],
    responses={200: OpenApiResponse(description="Supplier found"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['GET'])
def search_supplier_globally(request):
    phone = request.GET.get('phone')
    gstn = request.GET.get('gstn')
    
    supplier = None
    if phone:
        supplier = Supplieruser.objects.filter(supplieruserphone=phone).first()
    elif gstn:
        supplier = Supplieruser.objects.filter(supplierusergstnumber=gstn).first()
        
    if supplier:
        return Response({
            'id': supplier.supplieruserid,
            'supplier_id': supplier.supplierid_id,
            'name': supplier.suppliername,
            'phone': supplier.supplieruserphone,
            'gst_number': supplier.supplierusergstnumber,
            'email': supplier.supplieruseremail,
            'address': supplier.supplieruseraddress,
        }, status=status.HTTP_200_OK)
    
    return Response({'message': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(
    parameters=[
        OpenApiParameter(name="phone", description="Supplier Phone Number", required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name="gstn", description="Supplier GST Number", required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name="company_id", description="Company ID", required=False, type=OpenApiTypes.INT),
        OpenApiParameter(name="user_id", description="User ID", required=False, type=OpenApiTypes.INT),
    ],
    responses={200: OpenApiResponse(description="Supplier found"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['GET'])
def search_local_supplier(request):
    phone = request.GET.get('phone')
    gstn = request.GET.get('gstn')
    
    supplier = None
    if phone:
        supplier = Supplier.objects.filter(supplierphonenumber=phone).first()
    elif gstn:
        supplier = Supplier.objects.filter(suppliergst=gstn).first()
        
    if supplier:
        return Response({
            'id': supplier.supplierid,
            'name': supplier.suppliername,
            'phone': supplier.supplierphonenumber,
            'gst_number': supplier.suppliergst,
            'email': supplier.supplieremail,
            'address': supplier.supplieraddress,
            'isconnected': bool(supplier.isconnected),
        }, status=status.HTTP_200_OK)
    
    return Response({'message': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(
    request=inline_serializer(
        name="ConnectSupplierRequest",
        fields={
            "supplieruserid": serializers.IntegerField(required=False),
            "supplier_user_id": serializers.IntegerField(required=False),
            "supplier_id": serializers.IntegerField(required=False),
            "userid": serializers.IntegerField(required=False),
            "user_id": serializers.IntegerField(required=False),
            "company_user_id": serializers.IntegerField(required=False),
        }
    ),
    responses={200: OpenApiResponse(description="Supplier connected successfully"), 400: OpenApiResponse(description="Bad request"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['POST'])
def connect_supplier(request):
    data = request.data
    supplier_user_id = data.get('supplieruserid') or data.get('supplier_user_id') or data.get('supplier_id')
    company_user_id = data.get('userid') or data.get('user_id') or data.get('company_user_id')

    if not supplier_user_id or not company_user_id:
        return Response({'error': 'supplieruserid and userid are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        supplier_user = Supplieruser.objects.get(supplieruserid=supplier_user_id)
    except Supplieruser.DoesNotExist:
        return Response({'error': 'Supplier user not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        company_user = Users.objects.select_related('companyid').get(userid=company_user_id)
    except Users.DoesNotExist:
        return Response({'error': 'Company user not found.'}, status=status.HTTP_404_NOT_FOUND)

    company = company_user.companyid
    if company is None:
        return Response({'error': 'Company not found for this user.'}, status=status.HTTP_404_NOT_FOUND)

    local_supplier = None
    phone = supplier_user.supplieruserphone
    gst = supplier_user.supplierusergstnumber

    if phone:
        local_supplier = Supplier.objects.filter(companyid=company, supplierphonenumber=phone).first()
    if not local_supplier and gst:
        local_supplier = Supplier.objects.filter(companyid=company, suppliergst=gst).first()

    if not local_supplier:
        local_supplier = Supplier.objects.create(
            suppliername=supplier_user.suppliername or '',
            supplierphonenumber=phone,
            supplieraddress=supplier_user.supplieruseraddress,
            supplieremail=supplier_user.supplieruseremail,
            suppliergst=gst,
            isconnected=1,
            companyid=company
        )
    else:
        updated = False
        if not local_supplier.isconnected:
            local_supplier.isconnected = 1
            updated = True
        if supplier_user.suppliername and supplier_user.suppliername != local_supplier.suppliername:
            local_supplier.suppliername = supplier_user.suppliername
            updated = True
        if supplier_user.supplieruseraddress and supplier_user.supplieruseraddress != local_supplier.supplieraddress:
            local_supplier.supplieraddress = supplier_user.supplieruseraddress
            updated = True
        if supplier_user.supplieruseremail and supplier_user.supplieruseremail != local_supplier.supplieremail:
            local_supplier.supplieremail = supplier_user.supplieruseremail
            updated = True
        if supplier_user.supplierusergstnumber and supplier_user.supplierusergstnumber != local_supplier.suppliergst:
            local_supplier.suppliergst = supplier_user.supplierusergstnumber
            updated = True
        if updated:
            local_supplier.save()

    # Link the SupplierUser to the local Supplier via FK
    if supplier_user.supplierid_id != local_supplier.supplierid:
        supplier_user.supplierid = local_supplier
        supplier_user.save(update_fields=['supplierid'])

    return Response({
        'success': True,
        'message': 'Supplier connected successfully.',
        'supplier_id': local_supplier.supplierid,
        'supplier_user_id': supplier_user.supplieruserid,
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def supplier_bills(request, supplier_user_id):
    try:
        supplier_user = Supplieruser.objects.get(supplieruserid=supplier_user_id)
    except Supplieruser.DoesNotExist:
        return Response({'error': 'Supplier user not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Find ALL matching supplier records across companies
    # 1. By exact FK if exists
    suppliers_q = Q()
    if supplier_user.supplierid_id:
        suppliers_q |= Q(supplierid=supplier_user.supplierid_id)
    # 2. By phone number
    if supplier_user.supplieruserphone:
        suppliers_q |= Q(supplierphonenumber=supplier_user.supplieruserphone)
    # 3. By GST number
    if supplier_user.supplierusergstnumber:
        suppliers_q |= Q(suppliergst=supplier_user.supplierusergstnumber)
        
    suppliers = Supplier.objects.filter(suppliers_q).distinct() if suppliers_q else Supplier.objects.none()

    bills = (
        SupplierBill.objects
        .select_related('supplierid__companyid')
        .filter(supplierid__in=suppliers)
        .order_by('-supplierbilldate', '-supplierbillid')
    )

    try:
        result = []
        for bill in bills:
            company = bill.supplierid.companyid if getattr(bill, 'supplierid', None) else None
            result.append({
                'id': bill.supplierbillid,
                'supplier_id': bill.supplierid.supplierid if getattr(bill, 'supplierid', None) else None,
                'supplier_name': bill.supplierid.suppliername if getattr(bill, 'supplierid', None) else '',
                'bill_no': bill.supplierbillno or '',
                'date': str(bill.supplierbilldate) if bill.supplierbilldate else '',
                'amount': float(bill.supplierbillamount or 0),
                'paid_amount': float(bill.paidamount or 0),
                'balance': float(bill.balance or 0),
                'type': bill.supplierbilltype or '',
                'narration': bill.narration or '',
                'company_id': company.companyid if company else None,
                'company_name': company.companyname if company else '',
                'company_phone': str(company.companyphonenumber) if company and company.companyphonenumber else '',
                'company_email': '',
                'company_gst': '',
                'company_address': '',
            })

        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def supplier_dashboard(request, supplier_user_id):
    try:
        supplier_user = Supplieruser.objects.get(supplieruserid=supplier_user_id)
    except Supplieruser.DoesNotExist:
        return Response({'error': 'Supplier user not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Find ALL matching supplier records across companies
    suppliers_q = Q()
    if supplier_user.supplierid_id:
        suppliers_q |= Q(supplierid=supplier_user.supplierid_id)
    if supplier_user.supplieruserphone:
        suppliers_q |= Q(supplierphonenumber=supplier_user.supplieruserphone)
    if supplier_user.supplierusergstnumber:
        suppliers_q |= Q(suppliergst=supplier_user.supplierusergstnumber)
        
    suppliers = Supplier.objects.select_related('companyid').filter(suppliers_q).distinct() if suppliers_q else Supplier.objects.none()

    companies_data = []
    total_bills = 0
    total_paid = 0.0
    total_balance = 0.0
    total_amount = 0.0
    total_debit_notes_count = 0
    total_debit_notes_amount = 0.0

    for supplier in suppliers:
        company = supplier.companyid
        if not company:
            continue
            
        bills = SupplierBill.objects.filter(supplierid=supplier)
        
        comp_bills_count = 0
        comp_amount = 0.0
        comp_paid = 0.0
        comp_balance = 0.0
        comp_debit_notes = 0
        comp_debit_amount = 0.0
        
        main_bills = []
        payment_bills = []
        for bill in bills:
            bill_type = (bill.supplierbilltype or '').lower()
            bill_no = (bill.supplierbillno or '').lower()
            if 'receipt' in bill_type or 'payment' in bill_type or 'payments' in bill_type or bill_no.startswith('rcpt') or 'rcpt-' in bill_no or bill_no.startswith('pay') or 'pay-' in bill_no:
                payment_bills.append(bill)
            else:
                main_bills.append(bill)
                
        for bill in main_bills:
            amount = float(bill.supplierbillamount or 0)
            paid = float(bill.paidamount or 0)
            bal = float(bill.balance or 0)
            
            bill_type = (bill.supplierbilltype or '').lower()
            if 'return' in bill_type or 'credit' in bill_type or 'refund' in bill_type or bill.supplierbilltype == 'Debit Note':
                comp_debit_notes += 1
                comp_debit_amount += amount
                total_debit_notes_count += 1
                total_debit_notes_amount += amount
                continue
                
            matched_payments_sum = 0.0
            bill_no = (bill.supplierbillno or '').strip().lower()
            bill_id = str(bill.supplierbillid or '').strip().lower()
            
            for p in payment_bills:
                p_type = (p.supplierbilltype or '').lower()
                p_no = (p.supplierbillno or '').lower()
                p_ref = (getattr(p, 'reference', '') or '').lower()
                p_against = (getattr(p, 'against', '') or '').lower()
                
                refs = [
                    p_ref, p_against, p_no, str(p.supplierbillid or '').lower()
                ]
                
                is_match = False
                if bill_no and bill_no in refs:
                    is_match = True
                elif bill_id and bill_id in refs:
                    is_match = True
                elif bill_no and bill_no in p_no:
                    is_match = True
                    
                if is_match:
                    p_amt = float(p.supplierbillamount or p.paidamount or 0)
                    matched_payments_sum += p_amt
            
            actual_paid = matched_payments_sum if matched_payments_sum > 0 else paid
            
            comp_bills_count += 1
            comp_amount += amount
            comp_paid += actual_paid
            comp_balance += amount - actual_paid
            
            total_bills += 1
            total_amount += amount
            total_paid += actual_paid
            total_balance += amount - actual_paid

        companies_data.append({
            'company_id': company.companyid,
            'company_name': company.companyname or '',
            'company_phone': company.companyphonenumber or '',
            'company_email': '',
            'company_address': '',
            'supplier_id': supplier.supplierid,
            'is_connected': supplier.isconnected,
            'summary': {
                'bills_count': comp_bills_count,
                'total_amount': comp_amount,
                'paid_amount': comp_paid,
                'balance': comp_balance,
                'debit_notes_count': comp_debit_notes,
                'debit_notes_amount': comp_debit_amount,
            }
        })

    executive_count = SupplierExecutive.objects.filter(manager_id=supplier_user_id).count()
    field_orders_count = SupplierOrder.objects.filter(executive__manager_id=supplier_user_id).count()

    return Response({
        'overview': {
            'total_companies': len(companies_data),
            'total_bills': total_bills,
            'total_amount': total_amount,
            'total_paid': total_paid,
            'total_balance': total_balance,
            'total_debit_notes': total_debit_notes_count,
            'total_debit_amount': total_debit_notes_amount,
            'executive_count': executive_count,
            'field_orders_count': field_orders_count,
        },
        'companies': companies_data
    }, status=status.HTTP_200_OK)

@extend_schema(
    request=inline_serializer(
        name="OnboardSupplierRequest",
        fields={
            "phone": serializers.CharField(required=False),
            "username": serializers.CharField(required=False),
            "userid": serializers.IntegerField(required=False),
            "user_id": serializers.IntegerField(required=False),
            "companyid": serializers.IntegerField(required=False),
            "company_id": serializers.IntegerField(required=False),
        }
    ),
    responses={201: OpenApiResponse(description="Supplier onboarded successfully"), 400: OpenApiResponse(description="Bad request"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['POST'])
def onboard_supplier(request):
    data = request.data
    try:
        phone = data.get('phone')
        username = data.get('username')
        # determine company context (accept either userid or companyid)
        company = None
        user_id = data.get('userid') or data.get('user_id')
        company_id = data.get('companyid') or data.get('company_id')
        if user_id:
            try:
                user_obj = Users.objects.select_related('companyid').get(userid=user_id)
                company = user_obj.companyid
            except Users.DoesNotExist:
                company = None
        elif company_id:
            try:
                company = Company.objects.get(companyid=company_id)
            except Company.DoesNotExist:
                company = None

        with transaction.atomic():
            if phone and Supplieruser.objects.filter(supplieruserphone=phone).exists():
                return Response({'error': 'Supplier with this phone already exists'}, status=status.HTTP_400_BAD_REQUEST)

            if username and Supplieruser.objects.filter(supplierusername=username).exists():
                return Response({'error': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)

            supplier_user = Supplieruser.objects.create(
                suppliername=data.get('name'),
                supplierusername=username,
                supplieruserpassword=data.get('password'),
                supplieruserphone=phone,
                supplieruseremail=data.get('email'),
                supplierusergstnumber=data.get('gst_number'),
                supplieruseraddress=data.get('address')
            )

            # If company context is provided, ensure a local Supplier entry exists for that company
            if company:
                gst = data.get('gst_number')
                # prefer matching by phone, then GST, then by name
                local_supplier = None
                if phone:
                    local_supplier = Supplier.objects.filter(companyid=company, supplierphonenumber=phone).first()
                if not local_supplier and gst:
                    local_supplier = Supplier.objects.filter(companyid=company, suppliergst=gst).first()
                if not local_supplier:
                    local_supplier = Supplier.objects.create(
                        suppliername=data.get('name') or supplier_user.suppliername,
                        supplierphonenumber=phone,
                        supplieraddress=data.get('address'),
                        supplieremail=data.get('email'),
                        suppliergst=gst,
                        isconnected=1,
                        companyid=company
                    )
                else:
                    # Mark existing local supplier as connected
                    if not local_supplier.isconnected:
                        local_supplier.isconnected = 1
                        local_supplier.save(update_fields=['isconnected'])
                # Link the SupplierUser to the local Supplier via FK
                supplier_user.supplierid = local_supplier
                supplier_user.save(update_fields=['supplierid'])

        resp = {
            'success': True,
            'id': supplier_user.supplieruserid,
            'supplier_user_id': supplier_user.supplieruserid,
            'supplier_id': supplier_user.supplierid_id,
            'username': supplier_user.supplierusername,
            'password': supplier_user.supplieruserpassword or '',
            'message': 'Successfully onboarded the supplier'
        }

        return Response(resp, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# ==================== CHAT API VIEWS ====================

@api_view(['GET'])
def get_company_conversations(request, company_id):
    try:
        conversations = Conversation.objects.filter(company_id=company_id).select_related('enduser').order_by('-updated_at')
        result = []
        for conv in conversations:
            last_message = conv.messages.order_by('-timestamp').first()
            has_unread = conv.messages.filter(sender_type='enduser', is_read=False).exists()
            result.append({
                'conversation_id': conv.id,
                'enduser_id': conv.enduser.endsuerid,
                'enduser_name': conv.enduser.endusername,
                'updated_at': conv.updated_at,
                'last_message': last_message.text_content if last_message else None,
                'last_message_sender': last_message.sender_type if last_message else None,
                'is_read': last_message.is_read if last_message else True,
                'has_unread': has_unread,
                'has_audio': bool(last_message.audio_file) if last_message else False,
            })
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_enduser_conversations(request, enduser_id):
    try:
        conversations = Conversation.objects.filter(enduser_id=enduser_id).select_related('company').order_by('-updated_at')
        result = []
        for conv in conversations:
            last_message = conv.messages.order_by('-timestamp').first()
            result.append({
                'conversation_id': conv.id,
                'company_id': conv.company.companyid,
                'company_name': conv.company.companyname,
                'updated_at': conv.updated_at,
                'last_message': last_message.text_content if last_message else None,
                'last_message_sender': last_message.sender_type if last_message else None,
                'is_read': last_message.is_read if last_message else True,
                'has_audio': bool(last_message.audio_file) if last_message else False,
            })
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_conversation_messages(request, conversation_id):
    try:
        sender_type = request.GET.get('sender_type')
        if sender_type:
            opposite_sender = 'enduser' if sender_type == 'company' else 'company'
            ChatMessage.objects.filter(conversation_id=conversation_id, sender_type=opposite_sender, is_read=False).update(is_read=True)
        messages = ChatMessage.objects.filter(conversation_id=conversation_id).order_by('timestamp')
        result = []
        for msg in messages:
            result.append({
                'id': msg.id,
                'sender_type': msg.sender_type,
                'text_content': msg.text_content,
                'audio_url': msg.audio_file.url if msg.audio_file else None,
                'duration': msg.duration,
                'waveform': msg.waveform,
                'is_read': msg.is_read,
                'timestamp': msg.timestamp,
                'order_status': msg.order_status,
            })
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=inline_serializer(
        name="SendMessageRequest",
        fields={
            "company_id": serializers.IntegerField(),
            "enduser_id": serializers.IntegerField(),
            "sender_type": serializers.CharField(),
            "text_content": serializers.CharField(required=False),
            "audio_file": serializers.FileField(required=False),
        }
    ),
    responses={200: OpenApiResponse(description="Message sent"), 400: OpenApiResponse(description="Bad request")}
)
@api_view(['POST'])
def send_message(request):
    try:
        company_id = request.data.get('company_id')
        enduser_id = request.data.get('enduser_id')
        sender_type = request.data.get('sender_type')
        text_content = request.data.get('text_content', '')
        audio_file = request.FILES.get('audio_file')
        duration = request.data.get('duration')
        waveform = request.data.get('waveform')

        conversation, created = Conversation.objects.get_or_create(
            company_id=company_id,
            enduser_id=enduser_id
        )

        msg = ChatMessage.objects.create(
            conversation=conversation,
            sender_type=sender_type,
            text_content=text_content,
            audio_file=audio_file,
            duration=int(duration) if duration else None,
            waveform=waveform
        )

        conversation.updated_at = msg.timestamp
        conversation.save()

        return Response({
            'success': True,
            'message_id': msg.id,
            'conversation_id': conversation.id,
            'timestamp': msg.timestamp,
            'audio_url': msg.audio_file.url if msg.audio_file else None,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=inline_serializer(
        name="SendOrderMessageRequest",
        fields={
            "company_id": serializers.IntegerField(),
            "enduser_id": serializers.IntegerField(),
            "cart_items": serializers.ListField(
                child=inline_serializer(
                    name="CartItem",
                    fields={
                        "name": serializers.CharField(),
                        "qty": serializers.IntegerField(default=1),
                        "price": serializers.FloatField(required=False),
                    }
                )
            ),
        }
    ),
    responses={200: OpenApiResponse(description="Order sent"), 400: OpenApiResponse(description="Bad request")}
)
@api_view(['POST'])
def send_order_message(request):
    try:
        company_id = request.data.get('company_id')
        enduser_id = request.data.get('enduser_id')
        cart_items = request.data.get('cart_items', []) # List of dicts {name, qty, price}
        
        conversation, created = Conversation.objects.get_or_create(
            company_id=company_id,
            enduser_id=enduser_id
        )

        order_text = "🛍️ New Order\n\n"
        for item in cart_items:
            qty = item.get('qty', 1)
            order_text += f"• {item.get('name')} (x{qty})\n"

        msg = ChatMessage.objects.create(
            conversation=conversation,
            sender_type='enduser',
            text_content=order_text
        )

        conversation.updated_at = msg.timestamp
        conversation.save()

        return Response({'success': True, 'message': 'Order sent as chat message.'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_message(request, message_id):
    try:
        msg = ChatMessage.objects.get(id=message_id)
        msg.delete()
        return Response({'success': True, 'message': 'Message deleted completely.'})
    except ChatMessage.DoesNotExist:
        return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=inline_serializer(
        name="UpdateOrderStatusRequest",
        fields={
            "status": serializers.CharField(),
        }
    ),
    responses={200: OpenApiResponse(description="Order status updated"), 400: OpenApiResponse(description="Bad request"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['POST'])
def update_order_status(request, message_id):
    try:
        status_val = request.data.get('status')
        msg = ChatMessage.objects.get(id=message_id)
        msg.order_status = status_val
        msg.save()
        return Response({'success': True, 'message': f'Order status updated to {status_val}'})
    except ChatMessage.DoesNotExist:
        return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=inline_serializer(
        name="DeleteConversationsRequest",
        fields={
            "conversation_ids": serializers.ListField(child=serializers.IntegerField()),
        }
    ),
    responses={200: OpenApiResponse(description="Conversations deleted"), 400: OpenApiResponse(description="Bad request")}
)
@api_view(['POST'])
def delete_conversations(request):
    try:
        conversation_ids = request.data.get('conversation_ids', [])
        if not conversation_ids:
            return Response({'error': 'No conversation IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        Conversation.objects.filter(id__in=conversation_ids).delete()
        return Response({'success': True, 'message': 'Conversations deleted successfully.'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_enduser_orders(request, enduser_id):
    try:
        messages = ChatMessage.objects.filter(
            conversation__enduser_id=enduser_id,
            text_content__startswith='🛍️ New Order'
        ).select_related('conversation__company').order_by('-timestamp')
        
        orders = []
        for msg in messages:
            orders.append({
                'id': msg.id,
                'company_name': msg.conversation.company.companyname,
                'text_content': msg.text_content,
                'timestamp': msg.timestamp,
                'order_status': msg.order_status,
                'company_id': msg.conversation.company.companyid,
            })
        
        return Response(orders)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_company_orders(request, company_id):
    try:
        messages = ChatMessage.objects.filter(
            conversation__company_id=company_id,
            text_content__startswith='🛍️ New Order'
        ).select_related('conversation__enduser').order_by('-timestamp')
        
        orders = []
        for msg in messages:
            orders.append({
                'id': msg.id,
                'enduser_name': msg.conversation.enduser.username,
                'text_content': msg.text_content,
                'timestamp': msg.timestamp,
                'order_status': msg.order_status,
                'enduser_id': msg.conversation.enduser.userid,
            })
        
        return Response(orders)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# ─── SUPPLIER EXECUTIVE ENDPOINTS ──────────────────────────────────────────

@api_view(['POST'])
def register_supplier_executive(request):
    data = request.data
    manager_id = data.get('manager_id')
    name = data.get('executive_name')
    username = data.get('executive_username')
    password = data.get('executive_password')
    phone = data.get('executive_phone')

    try:
        manager = Supplieruser.objects.get(supplieruserid=manager_id)
        
        if SupplierExecutive.objects.filter(executive_username__iexact=username).exists():
            return Response({'error': 'Username already taken.'}, status=status.HTTP_400_BAD_REQUEST)

        exec_obj = SupplierExecutive.objects.create(
            manager=manager,
            executive_name=name,
            executive_username=username,
            executive_password=password,
            executive_phone=phone
        )
        return Response({'message': 'Executive registered successfully', 'executive_id': exec_obj.executiveid}, status=status.HTTP_201_CREATED)
    except Supplieruser.DoesNotExist:
        return Response({'error': 'Manager not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login_supplier_executive(request):
    data = request.data
    username = data.get('username')
    password = data.get('password')

    try:
        executive = SupplierExecutive.objects.get(executive_username__iexact=username)
        if executive.executive_password == password:
            return Response({
                'message': 'Login successful',
                'executive_id': executive.executiveid,
                'executive_name': executive.executive_name,
                'manager_id': executive.manager_id,
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)
    except SupplierExecutive.DoesNotExist:
        return Response({'error': 'Username not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_supplier_executives(request, manager_id):
    try:
        executives = SupplierExecutive.objects.filter(manager_id=manager_id).order_by('-created_at')
        result = []
        for ex in executives:
            alloc_count = ExecutiveAllocation.objects.filter(executive=ex).count()
            result.append({
                'executive_id': ex.executiveid,
                'name': ex.executive_name,
                'username': ex.executive_username,
                'phone': ex.executive_phone,
                'allocated_companies': alloc_count,
            })
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def allocate_company_to_executive(request):
    data = request.data
    executive_id = data.get('executive_id')
    company_ids = data.get('company_ids', [])

    try:
        executive = SupplierExecutive.objects.get(executiveid=executive_id)
        ExecutiveAllocation.objects.filter(executive=executive).delete()
        for cid in company_ids:
            company = Company.objects.get(companyid=cid)
            ExecutiveAllocation.objects.create(executive=executive, company=company)
            
        return Response({'message': 'Companies allocated successfully'}, status=status.HTTP_200_OK)
    except SupplierExecutive.DoesNotExist:
        return Response({'error': 'Executive not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Company.DoesNotExist:
        return Response({'error': 'One or more companies not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_allocated_companies(request, executive_id):
    try:
        allocations = ExecutiveAllocation.objects.filter(executive_id=executive_id).select_related('company')
        result = []
        for alloc in allocations:
            c = alloc.company
            result.append({
                'company_id': c.companyid,
                'company_name': c.companyname,
                'company_phone': c.companyphonenumber,
                'address': c.companyaddress,
                'allocated_at': alloc.allocated_at,
            })
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def place_executive_order(request):
    data = request.data
    executive_id = data.get('executive_id')
    company_id = data.get('company_id')
    supplier_id = data.get('supplier_id')
    items = data.get('items', [])
    lat = data.get('latitude')
    lng = data.get('longitude')

    try:
        executive = SupplierExecutive.objects.get(executiveid=executive_id)
        company = Company.objects.get(companyid=company_id)

        supplier = None
        if executive.manager and executive.manager.supplierid:
            supplier = executive.manager.supplierid
        elif supplier_id:
            supplier = Supplier.objects.filter(supplierid=supplier_id).first()

        if not supplier:
            supplier = Supplier.objects.first()

        total_amount = sum(float(item.get('price', 0)) * int(item.get('quantity', 0)) for item in items)

        order = SupplierOrder.objects.create(
            company=company,
            supplier=supplier,
            executive=executive,
            total_amount=total_amount,
            gps_latitude=lat,
            gps_longitude=lng
        )

        for item in items:
            product_id = item.get('product_id')
            product = Products.objects.get(productid=product_id)
            SupplierOrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.get('quantity', 1),
                price_at_order=item.get('price', 0)
            )

        return Response({'message': 'Order placed successfully', 'order_id': order.order_id}, status=status.HTTP_201_CREATED)
    except Exception as e:
        print("ERROR in place_executive_order:", str(e))
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


import math

def calculate_distance_meters(lat1, lon1, lat2, lon2):
    try:
        R = 6371000  # Earth's radius in meters
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dLon / 2) * math.sin(dLon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except Exception:
        return None

def parse_lat_lng(location_str):
    if not location_str:
        return None, None
    try:
        parts = str(location_str).split(',')
        if len(parts) >= 2:
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            return lat, lng
    except Exception:
        pass
    return None, None

@api_view(['GET'])
def get_supplier_manager_orders(request, manager_id):
    try:
        orders = SupplierOrder.objects.filter(executive__manager_id=manager_id).select_related('company', 'executive').order_by('-created_at')
        result = []
        for o in orders:
            items = SupplierOrderItem.objects.filter(order=o).select_related('product')
            item_list = []
            for item in items:
                item_list.append({
                    'product_name': item.product.productname,
                    'quantity': item.quantity,
                    'price': float(item.price_at_order),
                })

            exec_lat = float(o.gps_latitude) if o.gps_latitude is not None else None
            exec_lng = float(o.gps_longitude) if o.gps_longitude is not None else None

            comp_lat, comp_lng = parse_lat_lng(o.company.companylocation)

            is_verified = False
            distance_meters = None

            if exec_lat is not None and exec_lng is not None:
                if comp_lat is not None and comp_lng is not None:
                    dist = calculate_distance_meters(exec_lat, exec_lng, comp_lat, comp_lng)
                    if dist is not None:
                        distance_meters = round(dist, 1)
                        is_verified = bool(dist <= 500.0)
                else:
                    # If company coordinates are not explicitly set in DB,
                    # treat GPS presence as verified (with distance unknown)
                    is_verified = True

            result.append({
                'order_id': o.order_id,
                'company_name': o.company.companyname,
                'executive_name': o.executive.executive_name if o.executive else 'N/A',
                'total_amount': float(o.total_amount),
                'status': o.status,
                'gps_latitude': exec_lat,
                'gps_longitude': exec_lng,
                'company_latitude': comp_lat,
                'company_longitude': comp_lng,
                'distance_meters': distance_meters,
                'is_location_verified': is_verified,
                'created_at': o.created_at,
                'items': item_list,
            })
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_connected_companies_for_manager(request, manager_id):
    try:
        supplier_user = Supplieruser.objects.get(supplieruserid=manager_id)
        suppliers_q = Q()
        if supplier_user.supplierid_id:
            suppliers_q |= Q(supplierid=supplier_user.supplierid_id)
        if supplier_user.supplieruserphone:
            suppliers_q |= Q(supplierphonenumber=supplier_user.supplieruserphone)
        if supplier_user.supplierusergstnumber:
            suppliers_q |= Q(suppliergst=supplier_user.supplierusergstnumber)

        suppliers = Supplier.objects.select_related('companyid').filter(suppliers_q).distinct() if suppliers_q else Supplier.objects.none()

        result = []
        seen_ids = set()
        for s in suppliers:
            c = s.companyid
            if c and c.companyid not in seen_ids:
                seen_ids.add(c.companyid)
                result.append({
                    'companyid': c.companyid,
                    'companyname': c.companyname,
                    'companyphonenumber': c.companyphonenumber,
                    'companylocation': c.companylocation,
                    'companyaddress': c.companyaddress,
                })

        if not result:
            all_comps = Company.objects.all()
            for c in all_comps:
                result.append({
                    'companyid': c.companyid,
                    'companyname': c.companyname,
                    'companyphonenumber': c.companyphonenumber,
                    'companylocation': c.companylocation,
                    'companyaddress': c.companyaddress,
                })

        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_executive_orders(request, executive_id):
    try:
        orders = SupplierOrder.objects.filter(executive_id=executive_id).select_related('company').order_by('-created_at')
        result = []
        for o in orders:
            items = SupplierOrderItem.objects.filter(order=o).select_related('product')
            item_list = []
            for item in items:
                item_list.append({
                    'product_name': item.product.productname,
                    'quantity': item.quantity,
                    'price': float(item.price_at_order),
                })

            exec_lat = float(o.gps_latitude) if o.gps_latitude is not None else None
            exec_lng = float(o.gps_longitude) if o.gps_longitude is not None else None

            comp_lat, comp_lng = parse_lat_lng(o.company.companylocation)
            is_verified = False
            distance_meters = None
            if exec_lat is not None and exec_lng is not None:
                if comp_lat is not None and comp_lng is not None:
                    dist = calculate_distance_meters(exec_lat, exec_lng, comp_lat, comp_lng)
                    if dist is not None:
                        distance_meters = round(dist, 1)
                        is_verified = bool(dist <= 500.0)
                else:
                    is_verified = True

            result.append({
                'order_id': o.order_id,
                'company_name': o.company.companyname,
                'total_amount': float(o.total_amount),
                'status': o.status,
                'gps_latitude': exec_lat,
                'gps_longitude': exec_lng,
                'distance_meters': distance_meters,
                'is_location_verified': is_verified,
                'created_at': o.created_at,
                'items': item_list,
            })
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



