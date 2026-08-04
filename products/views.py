from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Products, Productcategory, Productunit, Company, Users, Customer, Supplier, CustomerBill, SupplierBill, EndUser, Supplieruser
from .serializers import ProductSerializer, ProductCategorySerializer, ProductUnitSerializer
from django.core.files.storage import default_storage
import uuid
from rest_framework.decorators import action, api_view
import openpyxl
import csv
import io
from datetime import datetime, date
from django.db.models import Sum

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


@api_view(['POST'])
def login_supplier(request):
    data = request.data
    username = data.get('supplierusername') or data.get('username')
    password = data.get('supplieruserpassword') or data.get('password')

    if not username or not password:
        return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        supplier_user = Supplieruser.objects.get(supplierusername__iexact=username)
        if supplier_user.supplieruserpassword == password:
            return Response({
                'message': 'Login successful',
                'supplieruserid': supplier_user.supplieruserid,
                'suppliername': supplier_user.suppliername or '',
                'supplierusername': supplier_user.supplierusername,
                'supplieruseremail': supplier_user.supplieruseremail or '',
                'supplieruserphone': supplier_user.supplieruserphone or '',
                'supplierusergstnumber': supplier_user.supplierusergstnumber or '',
                'supplieruseraddress': supplier_user.supplieruseraddress or '',
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)
    except Supplieruser.DoesNotExist:
        return Response({'error': 'Username not found.'}, status=status.HTTP_404_NOT_FOUND)


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
            'name': supplier.suppliername,
            'phone': supplier.supplieruserphone,
            'gst_number': supplier.supplierusergstnumber,
            'email': supplier.supplieruseremail,
            'address': supplier.supplieruseraddress,
        }, status=status.HTTP_200_OK)
    
    return Response({'message': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

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
        }, status=status.HTTP_200_OK)
    
    return Response({'message': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def onboard_supplier(request):
    data = request.data
    try:
        phone = data.get('phone')
        username = data.get('username')
        
        if phone and Supplieruser.objects.filter(supplieruserphone=phone).exists():
            return Response({'error': 'Supplier with this phone already exists'}, status=status.HTTP_400_BAD_REQUEST)
            
        if username and Supplieruser.objects.filter(supplierusername=username).exists():
            return Response({'error': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)
            
        supplier = Supplieruser.objects.create(
            suppliername=data.get('name'),
            supplierusername=username,
            supplieruserpassword=data.get('password'),
            supplieruserphone=phone,
            supplieruseremail=data.get('email'),
            supplierusergstnumber=data.get('gst_number'),
            supplieruseraddress=data.get('address')
        )
        
        return Response({
            'success': True,
            'supplier_id': supplier.supplieruserid,
            'username': supplier.supplierusername,
            'password': supplier.supplieruserpassword,
            'message': 'Successfully onboarded the supplier'
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
