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
    return any(marker in normalized for marker in ['return', 'credit', 'debit', 'note', 'rtn'])


def _is_payment_entry(entry_type, bill_no=''):
    if entry_type:
        normalized = str(entry_type).strip().lower()
        if any(marker in normalized for marker in ['receipt', 'payment', 'rcpt', 'pay']):
            return True
    if bill_no:
        bn = str(bill_no).strip().lower()
        if bn.startswith('rcpt') or bn.startswith('pay') or 'rcpt-' in bn or 'pay-' in bn:
            return True
    return False


def _allocate_payments_to_bills(regular_bills, payment_bills):
    bill_payments_map = {b.pk: [] for b in regular_bills}
    sorted_bills = sorted(regular_bills, key=lambda b: (getattr(b, 'customerbilldate', None) or getattr(b, 'supplierbilldate', None), b.pk))
    sorted_payments = sorted(payment_bills, key=lambda p: (getattr(p, 'customerbilldate', None) or getattr(p, 'supplierbilldate', None), p.pk))
    
    bill_idx = 0
    cur_bill_capacity = float(getattr(sorted_bills[0], 'customerbillamount', None) or getattr(sorted_bills[0], 'supplierbillamount', None)) if sorted_bills else 0
    cur_bill_allocated = 0.0
    
    for p in sorted_payments:
        p_amt = float(getattr(p, 'customerbillamount', None) or getattr(p, 'supplierbillamount', None) or 0)
        while bill_idx < len(sorted_bills) - 1 and cur_bill_allocated + p_amt > cur_bill_capacity + 0.01:
            bill_idx += 1
            cur_bill_capacity = float(getattr(sorted_bills[bill_idx], 'customerbillamount', None) or getattr(sorted_bills[bill_idx], 'supplierbillamount', None))
            cur_bill_allocated = 0.0
        
        if bill_idx < len(sorted_bills):
            bill_payments_map[sorted_bills[bill_idx].pk].append(p)
            cur_bill_allocated += p_amt
            
    return bill_payments_map


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

    # 1. Categorize customer bills
    customer_regular_bills = []
    customer_note_bills = []
    customer_payment_bills = []
    for bill in customer_bills:
        b_type = getattr(bill, 'customerbilltype', None)
        b_no = getattr(bill, 'customerbillno', '')
        if _is_note_entry(b_type):
            customer_note_bills.append(bill)
        elif _is_payment_entry(b_type, b_no):
            customer_payment_bills.append(bill)
        else:
            customer_regular_bills.append(bill)

    # 2. Categorize supplier bills
    supplier_regular_bills = []
    supplier_note_bills = []
    supplier_payment_bills = []
    for bill in supplier_bills:
        b_type = getattr(bill, 'supplierbilltype', None)
        b_no = getattr(bill, 'supplierbillno', '')
        if _is_note_entry(b_type):
            supplier_note_bills.append(bill)
        elif _is_payment_entry(b_type, b_no):
            supplier_payment_bills.append(bill)
        else:
            supplier_regular_bills.append(bill)

    # 3. Build customer bill items with linked payments
    customer_bill_items = []
    for customer in customers:
        c_sales = [b for b in customer_regular_bills if b.customerid_id == customer.customerid]
        c_rcpts = [b for b in customer_payment_bills if b.customerid_id == customer.customerid]
        c_mapping = _allocate_payments_to_bills(c_sales, c_rcpts)

        for bill in c_sales:
            p_list = c_mapping.get(bill.pk, [])
            matched_payments = [{
                'payment_id': p.customerbillno or str(p.customerbillid),
                'bill_no': p.customerbillno or '',
                'date': str(p.customerbilldate) if p.customerbilldate else '',
                'amount': float(p.customerbillamount or 0),
                'type': p.customerbilltype or 'Receipt',
                'narration': p.narration or '',
            } for p in p_list]

            p_tot = sum(p['amount'] for p in matched_payments)
            amt = float(bill.customerbillamount or 0)
            bal = max(0.0, amt - p_tot)

            customer_bill_items.append({
                'id': bill.customerbillid,
                'customer_id': customer.customerid,
                'customer_name': customer.customername,
                'bill_no': bill.customerbillno or '',
                'date': str(bill.customerbilldate) if bill.customerbilldate else '',
                'due_date': str(bill.customerbillduedate) if bill.customerbillduedate else '',
                'amount': amt,
                'paid_amount': p_tot,
                'balance': bal,
                'narration': bill.narration or '',
                'type': bill.customerbilltype or 'Sales',
                'payments': matched_payments,
            })

    # 4. Customer note items (Returns / Credit Notes)
    customer_note_items = []
    for bill in customer_note_bills:
        customer_note_items.append({
            'id': bill.customerbillid,
            'customer_id': bill.customerid.customerid if getattr(bill, 'customerid', None) else None,
            'customer_name': bill.customerid.customername if getattr(bill, 'customerid', None) else '',
            'bill_no': bill.customerbillno or '',
            'date': str(bill.customerbilldate) if bill.customerbilldate else '',
            'due_date': str(bill.customerbillduedate) if bill.customerbillduedate else '',
            'amount': float(bill.customerbillamount or 0),
            'paid_amount': 0.0,
            'balance': float(bill.customerbillamount or 0),
            'narration': bill.narration or '',
            'type': bill.customerbilltype or 'Return',
        })

    # 5. Customer payment items (Receipts)
    customer_payment_items = []
    for bill in customer_payment_bills:
        customer_payment_items.append({
            'id': bill.customerbillid,
            'customer_id': bill.customerid.customerid if getattr(bill, 'customerid', None) else None,
            'customer_name': bill.customerid.customername if getattr(bill, 'customerid', None) else '',
            'bill_no': bill.customerbillno or '',
            'date': str(bill.customerbilldate) if bill.customerbilldate else '',
            'due_date': str(bill.customerbillduedate) if bill.customerbillduedate else '',
            'amount': float(bill.customerbillamount or 0),
            'paid_amount': float(bill.customerbillamount or 0),
            'balance': 0.0,
            'narration': bill.narration or '',
            'type': bill.customerbilltype or 'Receipt',
            'status': 'Paid',
        })

    # 6. Build supplier bill items with linked payments
    supplier_bill_items = []
    for supplier in suppliers:
        s_purchases = [b for b in supplier_regular_bills if b.supplierid_id == supplier.supplierid]
        s_pays = [b for b in supplier_payment_bills if b.supplierid_id == supplier.supplierid]
        s_mapping = _allocate_payments_to_bills(s_purchases, s_pays)

        for bill in s_purchases:
            p_list = s_mapping.get(bill.pk, [])
            matched_payments = [{
                'payment_id': p.supplierbillno or str(p.supplierbillid),
                'bill_no': p.supplierbillno or '',
                'date': str(p.supplierbilldate) if p.supplierbilldate else '',
                'amount': float(p.supplierbillamount or 0),
                'type': p.supplierbilltype or 'Payment',
                'narration': p.narration or '',
            } for p in p_list]

            p_tot = sum(p['amount'] for p in matched_payments)
            amt = float(bill.supplierbillamount or 0)
            bal = max(0.0, amt - p_tot)

            supplier_bill_items.append({
                'id': bill.supplierbillid,
                'supplier_id': supplier.supplierid,
                'supplier_name': supplier.suppliername,
                'bill_no': bill.supplierbillno or '',
                'date': str(bill.supplierbilldate) if bill.supplierbilldate else '',
                'due_date': str(bill.supplierbillduedate) if bill.supplierbillduedate else '',
                'amount': amt,
                'paid_amount': p_tot,
                'balance': bal,
                'narration': bill.narration or '',
                'type': bill.supplierbilltype or 'Purchase',
                'payments': matched_payments,
            })

    # 7. Supplier note items (Debit Notes)
    supplier_note_items = []
    for bill in supplier_note_bills:
        supplier_note_items.append({
            'id': bill.supplierbillid,
            'supplier_id': bill.supplierid.supplierid if getattr(bill, 'supplierid', None) else None,
            'supplier_name': bill.supplierid.suppliername if getattr(bill, 'supplierid', None) else '',
            'bill_no': bill.supplierbillno or '',
            'date': str(bill.supplierbilldate) if bill.supplierbilldate else '',
            'due_date': str(bill.supplierbillduedate) if bill.supplierbillduedate else '',
            'amount': float(bill.supplierbillamount or 0),
            'paid_amount': 0.0,
            'balance': float(bill.supplierbillamount or 0),
            'narration': bill.narration or '',
            'type': bill.supplierbilltype or 'Debit Note',
        })

    # 8. Supplier payment items (Payments)
    supplier_payment_items = []
    for bill in supplier_payment_bills:
        supplier_payment_items.append({
            'id': bill.supplierbillid,
            'supplier_id': bill.supplierid.supplierid if getattr(bill, 'supplierid', None) else None,
            'supplier_name': bill.supplierid.suppliername if getattr(bill, 'supplierid', None) else '',
            'bill_no': bill.supplierbillno or '',
            'date': str(bill.supplierbilldate) if bill.supplierbilldate else '',
            'due_date': str(bill.supplierbillduedate) if bill.supplierbillduedate else '',
            'amount': float(bill.supplierbillamount or 0),
            'paid_amount': float(bill.supplierbillamount or 0),
            'balance': 0.0,
            'narration': bill.narration or '',
            'type': bill.supplierbilltype or 'Payment',
            'status': 'Paid',
        })

    # 9. Customer list with individual financial totals
    customer_list = []
    for customer in customers:
        c_entry_bills = CustomerBill.objects.filter(customerid=customer)
        c_sales = [b for b in c_entry_bills if not _is_note_entry(b.customerbilltype) and not _is_payment_entry(b.customerbilltype, b.customerbillno)]
        c_notes = [b for b in c_entry_bills if _is_note_entry(b.customerbilltype)]
        c_pays = [b for b in c_entry_bills if _is_payment_entry(b.customerbilltype, b.customerbillno)]

        c_sales_amt = sum(float(b.customerbillamount or 0) for b in c_sales)
        c_notes_amt = sum(float(b.customerbillamount or 0) for b in c_notes)
        c_paid_amt = sum(float(b.customerbillamount or 0) for b in c_pays)
        c_outstanding = (c_sales_amt - c_notes_amt) - c_paid_amt

        customer_list.append({
            'id': customer.customerid,
            'name': customer.customername,
            'gst_number': customer.customergst or '',
            'phone': customer.customerphonenumber or '',
            'email': customer.customeremail or '',
            'address': customer.customeraddress or '',
            'bills_count': len(c_sales),
            'bills_amount': c_sales_amt,
            'credit_notes_count': len(c_notes),
            'credit_notes_amount': c_notes_amt,
            'paid_amount': c_paid_amt,
            'balance_amount': c_outstanding,
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

    # 10. Supplier list with individual financial totals
    supplier_list = []
    for supplier in suppliers:
        s_entry_bills = SupplierBill.objects.filter(supplierid=supplier)
        s_purchases = [b for b in s_entry_bills if not _is_note_entry(b.supplierbilltype) and not _is_payment_entry(b.supplierbilltype, b.supplierbillno)]
        s_notes = [b for b in s_entry_bills if _is_note_entry(b.supplierbilltype)]
        s_pays = [b for b in s_entry_bills if _is_payment_entry(b.supplierbilltype, b.supplierbillno)]

        s_purchases_amt = sum(float(b.supplierbillamount or 0) for b in s_purchases)
        s_notes_amt = sum(float(b.supplierbillamount or 0) for b in s_notes)
        s_paid_amt = sum(float(b.supplierbillamount or 0) for b in s_pays)
        s_outstanding = (s_purchases_amt - s_notes_amt) - s_paid_amt

        supplier_list.append({
            'id': supplier.supplierid,
            'name': supplier.suppliername,
            'gst_number': supplier.suppliergst or '',
            'phone': supplier.supplierphonenumber or '',
            'email': supplier.supplieremail or '',
            'address': supplier.supplieraddress or '',
            'location_coordinates': getattr(supplier, 'location_coordinates', None),
            'isconnected': getattr(supplier, 'isconnected', 1),
            'bills_count': len(s_purchases),
            'bills_amount': s_purchases_amt,
            'debit_notes_count': len(s_notes),
            'debit_notes_amount': s_notes_amt,
            'paid_amount': s_paid_amt,
            'balance_amount': s_outstanding,
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
        'companyid': company.companyid,
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
