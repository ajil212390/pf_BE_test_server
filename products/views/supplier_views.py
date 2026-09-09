from ..serializers import CommitmentSerializer
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes, inline_serializer
from rest_framework import serializers

from ..models import Commitment, Supplier, Supplieruser, SupplierBill, Company, Users, SupplierOrder, SupplierExecutive


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
            'location_coordinates': getattr(supplier, 'location_coordinates', None),
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
            'location_coordinates': getattr(supplier, 'location_coordinates', None),
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

    company = None
    try:
        company_user = Users.objects.select_related('companyid').get(userid=company_user_id)
        company = company_user.companyid
    except Users.DoesNotExist:
        company = Company.objects.filter(companyid=company_user_id).first()

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
            companyid=company,
            location_coordinates=getattr(supplier_user, 'location_coordinates', None)
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
        su_coords = getattr(supplier_user, 'location_coordinates', None)
        if su_coords and getattr(local_supplier, 'location_coordinates', None) != su_coords:
            local_supplier.location_coordinates = su_coords
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
    suppliers_q = Q()
    if supplier_user.supplierid_id:
        suppliers_q |= Q(supplierid=supplier_user.supplierid_id)
    if supplier_user.supplieruserphone:
        suppliers_q |= Q(supplierphonenumber=supplier_user.supplieruserphone)
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
        # Pre-fetch latest commitments for all bills
        bill_nos = [b.supplierbillno for b in bills if b.supplierbillno]
        latest_commitments = {}
        if bill_nos:
            commits = Commitment.objects.filter(bill_no__in=bill_nos).order_by('created_at')
            for c in commits:
                latest_commitments[c.bill_no] = c.new_due_date or (str(c.bill_due_date) if c.bill_due_date else '')

        result = []
        for bill in bills:
            company = bill.supplierid.companyid if getattr(bill, 'supplierid', None) else None
            b_no = bill.supplierbillno or ''
            due_date = latest_commitments.get(b_no) or (str(bill.supplierbillduedate) if bill.supplierbillduedate else '')

            result.append({
                'id': bill.supplierbillid,
                'supplier_id': bill.supplierid.supplierid if getattr(bill, 'supplierid', None) else None,
                'supplier_name': bill.supplierid.suppliername if getattr(bill, 'supplierid', None) else '',
                'bill_no': b_no,
                'date': str(bill.supplierbilldate) if bill.supplierbilldate else '',
                'due_date': due_date,
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

                refs = [p_ref, p_against, p_no, str(p.supplierbillid or '').lower()]

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
                company = Company.objects.filter(companyid=user_id).first()
        elif company_id:
            try:
                company = Company.objects.get(companyid=company_id)
            except Company.DoesNotExist:
                user_obj = Users.objects.filter(userid=company_id).select_related('companyid').first()
                company = user_obj.companyid if user_obj else None

        with transaction.atomic():
            if phone and Supplieruser.objects.filter(supplieruserphone=phone).exists():
                return Response({'error': 'Supplier with this phone already exists'}, status=status.HTTP_400_BAD_REQUEST)

            if username and Supplieruser.objects.filter(supplierusername=username).exists():
                return Response({'error': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)

            supplier_user = Supplieruser.objects.create(
                suppliername=data.get('suppliername') or data.get('name'),
                supplierusername=username,
                supplieruserpassword=data.get('password'),
                supplieruserphone=phone,
                supplieruseremail=data.get('email'),
                supplierusergstnumber=data.get('gst_number'),
                supplieruseraddress=data.get('address'),
                location_coordinates=data.get('location_coordinates')
            )

            # If company context is provided, ensure a local Supplier entry exists for that company
            if company:
                gst = data.get('gst_number')
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
                        companyid=company,
                        location_coordinates=data.get('location_coordinates')
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
            'supplierid': supplier_user.supplierid_id,
            'supplier_id': supplier_user.supplierid_id,
            'username': supplier_user.supplierusername,
            'password': supplier_user.supplieruserpassword or '',
            'message': 'Successfully onboarded the supplier'
        }

        return Response(resp, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def bill_commitments_view(request, bill_no=None):
    if request.method == 'POST':
        data = request.data
        b_no = data.get('bill_no') or bill_no
        if not b_no:
            return Response({'error': 'bill_no is required'}, status=status.HTTP_400_BAD_REQUEST)

        new_due = data.get('new_due_date') or ''
        prev_due = data.get('previous_due_date') or ''
        try:
            ext_days = int(data.get('extension_days') or 0)
        except Exception:
            ext_days = 0
        narration = data.get('narration') or ''
        bill_id = data.get('bill_id')
        company_id = data.get('company_id')
        supplier_id = data.get('supplier_id')

        # Automatically resolve missing IDs from existing SupplierBill and Supplier table
        try:
            sb = SupplierBill.objects.filter(supplierbillno=b_no).select_related('supplierid').first()
            if sb:
                if not bill_id:
                    bill_id = sb.supplierbillid
                if not supplier_id and sb.supplierid:
                    supplier_id = getattr(sb.supplierid, 'supplierid', None)
                if not company_id and sb.supplierid:
                    company_id = getattr(sb.supplierid, 'companyid_id', None)
                    if not company_id and hasattr(sb.supplierid, 'companyid'):
                        company_id = getattr(sb.supplierid.companyid, 'companyid', None)
        except Exception:
            pass

        due_date_val = None
        try:
            from datetime import datetime
            due_date_val = datetime.strptime(new_due.strip(), '%Y-%m-%d').date()
        except Exception:
            pass

        commitment = Commitment.objects.create(
            bill_no=b_no,
            bill_id=bill_id,
            company_id=company_id,
            supplier_id=supplier_id,
            previous_due_date=prev_due,
            new_due_date=new_due,
            bill_due_date=due_date_val,
            extension_days=ext_days,
            narration=narration,
        )

        try:
            if due_date_val:
                SupplierBill.objects.filter(supplierbillno=b_no).update(supplierbillduedate=due_date_val)
        except Exception:
            pass

        serializer = CommitmentSerializer(commitment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    elif request.method == 'GET':
        b_no = bill_no or request.GET.get('bill_no')
        if not b_no:
            return Response({'error': 'bill_no is required'}, status=status.HTTP_400_BAD_REQUEST)

        commitments = Commitment.objects.filter(bill_no=b_no).order_by('-created_at')
        serializer = CommitmentSerializer(commitments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
