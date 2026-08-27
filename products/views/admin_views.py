from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum, Q

from ..models import Company, Users, Products, Customer, Supplier, CustomerBill, SupplierBill


# ─── ADMIN ENDPOINTS ────────────────────────────────────────────────────────

# Identifiers to exclude from all lists (the built-in super admin)
ADMIN_USERNAME = 'admin'
ADMIN_COMPANY  = 'Admin HQ'


# ─── Financial helper functions ─────────────────────────────────────────────

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


# ─── Admin view functions ────────────────────────────────────────────────────

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
        product_count = Products.objects.filter(Q(companyid=u.companyid) | Q(userid=u)).count() if u.companyid else Products.objects.filter(userid=u).count()
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
    """Returns all products for a specific user or user's company (for drill-down view / dashboard)."""
    try:
        user = Users.objects.select_related('companyid').get(userid=user_id)
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if user.companyid:
        products = (
            Products.objects
            .select_related('productcategoryid', 'productunitid', 'companyid')
            .filter(Q(companyid=user.companyid) | Q(userid=user))
            .order_by('-createdat', '-productid')
        )
    else:
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
            'companyid':    p.companyid.companyid if p.companyid else None,
            'companyname':  p.companyid.companyname if p.companyid else '',
            'userid':       p.userid.userid if p.userid else None,
        })
    return Response({
        'username':   user.username,
        'useremail':  user.useremail or '',
        'company':    user.companyid.companyname if user.companyid else '',
        'companyid':  user.companyid.companyid if user.companyid else None,
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
