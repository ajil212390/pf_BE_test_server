# On-Field Bill Due Date Extension API Views and FCM Push Notifications
import random
import logging
from datetime import timedelta
from django.db import transaction, connection
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from ..fcm_utils import send_push_to_user, _safe_log
from ..models import SupplierBill, Commitment, Company, Supplier

logger = logging.getLogger(__name__)

def generate_4_digit_otp() -> str:
    return str(random.SystemRandom().randint(1000, 9999))

@api_view(['POST'])
@permission_classes([AllowAny])
def request_extension_otp_view(request):
    data = request.data
    try:
        company_id = int(data.get('company_id', 0))
        supplier_id = int(data.get('supplier_id', 0))
        bill_id = int(data.get('bill_id', 0))
        bill_no = str(data.get('bill_no', '')).strip()
        new_due_date_str = str(data.get('new_due_date', '')).strip()
        extension_days = int(data.get('extension_days', 7))
        token_cost = int(data.get('token_cost', 0))
    except (ValueError, TypeError) as e:
        return Response({'success': False, 'error': f'Invalid parameter: {e}'}, status=status.HTTP_400_BAD_REQUEST)

    if not company_id or not (bill_id or bill_no) or not new_due_date_str:
        return Response({'success': False, 'error': 'company_id, bill_id, and new_due_date are required'}, status=status.HTTP_400_BAD_REQUEST)

    bill = None
    if bill_id:
        bill = SupplierBill.objects.select_related('supplierid').filter(supplierbillid=bill_id).first()
    if not bill and bill_no:
        bill = SupplierBill.objects.select_related('supplierid').filter(supplierbillno=bill_no).order_by('-supplierbillid').first()

    if not bill:
        return Response({'success': False, 'error': f'Bill #{bill_no or bill_id} not found in database'}, status=status.HTTP_404_NOT_FOUND)

    effective_bill_id = bill.supplierbillid
    effective_bill_no = bill.supplierbillno
    effective_company_id = company_id or (bill.supplierid.companyid_id if bill.supplierid else 0)
    effective_supplier_id = supplier_id or bill.supplierid_id

    # Calculate live extension count and escalating token fee
    # 1st extension (count=0): 10%, 2nd extension (count=1): 11%, 3rd (count=2): 12%, etc.
    existing_commitments_count = Commitment.objects.filter(
        bill_no=effective_bill_no,
        company_id=effective_company_id,
        supplier_id=effective_supplier_id
    ).count()

    bill_amt = float(bill.supplierbillamount or 0)
    fee_rate_percent = 10 + existing_commitments_count
    fee_rate = fee_rate_percent / 100.0
    calculated_cost = int(round(bill_amt * fee_rate))
    final_token_cost = calculated_cost if calculated_cost > 0 else (token_cost if token_cost > 0 else 45)

    otp_code = generate_4_digit_otp()
    now = timezone.now()
    expires_at = now + timedelta(minutes=5)

    with connection.cursor() as cursor:
        cursor.execute(
            'UPDATE due_date_extension_otp SET is_used = 1 WHERE company_id = %s AND bill_id = %s AND is_used = 0',
            [effective_company_id, effective_bill_id]
        )
        cursor.execute(
            '''
            INSERT INTO due_date_extension_otp 
            (company_id, supplier_id, bill_id, bill_no, otp_code, new_due_date, extension_days, token_cost, created_at, expires_at, is_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            ''',
            [effective_company_id, effective_supplier_id, effective_bill_id, effective_bill_no, otp_code, new_due_date_str, extension_days, final_token_cost, now, expires_at]
        )

    _safe_log(f'[Extension OTP] Generated OTP {otp_code} for Bill #{effective_bill_no} (Company: {effective_company_id}, Fee: {final_token_cost} tokens, Rate: {fee_rate_percent}%, Count: {existing_commitments_count})')

    notif_title = f'Approval OTP ({fee_rate_percent}%)'
    notif_body = f'OTP: {otp_code} for Bill #{effective_bill_no} (+{extension_days} Days). Cost: {final_token_cost} tokens ({fee_rate_percent}%).'
    notif_data = {
        'type': 'due_extension_otp',
        'otp': str(otp_code),
        'bill_id': str(effective_bill_id),
        'bill_no': str(effective_bill_no),
        'extension_days': str(extension_days),
        'new_due_date': str(new_due_date_str),
        'token_cost': str(final_token_cost),
        'fee_percent': str(fee_rate_percent),
        'extension_count': str(existing_commitments_count),
        'expires_in': '300',
    }

    try:
        send_push_to_user(
            user_id=effective_company_id,
            user_type='company',
            title=notif_title,
            body=notif_body,
            data=notif_data
        )
    except Exception as e:
        _safe_log(f'[FCM Extension OTP Error] {e}')

    return Response({
        'success': True,
        'message': 'OTP sent to Store Owner app',
        'bill_id': effective_bill_id,
        'bill_no': effective_bill_no,
        'expires_in': 300,
        'otp': otp_code,
        'token_cost': final_token_cost,
        'extension_count': existing_commitments_count,
        'fee_percent': fee_rate_percent,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_and_extend_view(request):
    data = request.data
    try:
        company_id = int(data.get('company_id', 0))
        supplier_id = int(data.get('supplier_id', 0))
        bill_id = int(data.get('bill_id', 0))
        bill_no = str(data.get('bill_no', '')).strip()
        otp_code = str(data.get('otp_code', '')).strip()
        new_due_date_str = str(data.get('new_due_date', '')).strip()
        extension_days = int(data.get('extension_days', 7))
        token_cost = int(data.get('token_cost', 0))
        executive_id = data.get('executive_id')
    except (ValueError, TypeError) as e:
        return Response({'success': False, 'error': f'Invalid parameter: {e}'}, status=status.HTTP_400_BAD_REQUEST)

    if not company_id or not (bill_id or bill_no) or not otp_code or not new_due_date_str:
        return Response({'success': False, 'error': 'company_id, bill_id, otp_code, and new_due_date are required'}, status=status.HTTP_400_BAD_REQUEST)

    bill = None
    if bill_id:
        bill = SupplierBill.objects.select_related('supplierid').filter(supplierbillid=bill_id).first()
    if not bill and bill_no:
        bill = SupplierBill.objects.select_related('supplierid').filter(supplierbillno=bill_no).order_by('-supplierbillid').first()

    if not bill:
        return Response({'success': False, 'error': f'Bill #{bill_no or bill_id} not found in database'}, status=status.HTTP_404_NOT_FOUND)

    effective_bill_id = bill.supplierbillid
    effective_bill_no = bill.supplierbillno
    effective_company_id = company_id or (bill.supplierid.companyid_id if bill.supplierid else 0)
    effective_supplier_id = supplier_id or bill.supplierid_id
    previous_due_date = str(bill.supplierbillduedate or bill.supplierbilldate or '')

    now = timezone.now()

    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT id, otp_code, expires_at, is_used, token_cost, extension_days, new_due_date
            FROM due_date_extension_otp
            WHERE company_id = %s AND bill_id = %s AND otp_code = %s
            ORDER BY id DESC LIMIT 1
            ''',
            [effective_company_id, effective_bill_id, otp_code]
        )
        row = cursor.fetchone()
        if not row:
            return Response({'success': False, 'error': 'Invalid OTP entered. Please verify with Store Owner.'}, status=status.HTTP_400_BAD_REQUEST)

        otp_id = row[0]
        expires_at = row[2]
        is_used = bool(row[3])
        recorded_cost = row[4] if (row[4] is not None and row[4] > 0) else token_cost

        if is_used:
            return Response({'success': False, 'error': 'This OTP has already been used.'}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())

        if now > expires_at:
            return Response({'success': False, 'error': 'This OTP has expired (5 min limit). Please request a new code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check company balance before charging
        cursor.execute(
            'SELECT COALESCE(premium_tokens_balance, 0) FROM company WHERE companyid = %s',
            [effective_company_id]
        )
        comp_row = cursor.fetchone()
        comp_balance = comp_row[0] if (comp_row and comp_row[0] is not None) else 0

        if recorded_cost > 0 and comp_balance < recorded_cost:
            return Response({
                'success': False,
                'error': f'Company has insufficient Premium Tokens. Required: {recorded_cost}, Available: {comp_balance}',
                'premium_tokens_balance': comp_balance,
                'required': recorded_cost,
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Invalidate OTP
                cursor.execute('UPDATE due_date_extension_otp SET is_used = 1 WHERE id = %s', [otp_id])

                # 2. Update Bill Due Date
                cursor.execute('UPDATE supplierbill SET supplierbillduedate = %s WHERE supplierbillid = %s', [new_due_date_str, effective_bill_id])

                # 3. Log Extension into Commitment Table
                narration = f'Extended by +{extension_days} days via Field Executive #{executive_id or "Field"} (Fee: {recorded_cost} tokens)'
                cursor.execute(
                    '''
                    INSERT INTO commitment 
                    (bill_no, supplierbillid, company_id, supplier_id, previous_due_date, new_due_date, bill_due_date, extension_days, narration, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    [effective_bill_no, effective_bill_id, effective_company_id, effective_supplier_id, previous_due_date, new_due_date_str, new_due_date_str, extension_days, narration, now, now]
                )

                # 4. Atomically DEDUCT tokens from Company Wallet
                if recorded_cost > 0 and effective_company_id:
                    cursor.execute(
                        '''
                        UPDATE company 
                        SET premium_tokens_balance = GREATEST(0, COALESCE(premium_tokens_balance, 0) - %s)
                        WHERE companyid = %s
                        ''',
                        [recorded_cost, effective_company_id]
                    )

                # 5. Atomically CREDIT tokens to Supplier Wallet
                if recorded_cost > 0 and effective_supplier_id:
                    cursor.execute(
                        '''
                        UPDATE supplier 
                        SET premium_tokens_balance = COALESCE(premium_tokens_balance, 0) + %s
                        WHERE supplierid = %s
                        ''',
                        [recorded_cost, effective_supplier_id]
                    )
                    cursor.execute(
                        '''
                        UPDATE supplieruser 
                        SET premium_tokens_balance = COALESCE(premium_tokens_balance, 0) + %s
                        WHERE supplierid = %s OR supplieruserid = %s
                        ''',
                        [recorded_cost, effective_supplier_id, effective_supplier_id]
                    )

                # Query updated balances inside atomic transaction
                cursor.execute('SELECT COALESCE(premium_tokens_balance, 0) FROM company WHERE companyid = %s', [effective_company_id])
                comp_bal_row = cursor.fetchone()
                updated_company_balance = comp_bal_row[0] if comp_bal_row else 0

                cursor.execute('SELECT COALESCE(premium_tokens_balance, 0) FROM supplier WHERE supplierid = %s', [effective_supplier_id])
                sup_bal_row = cursor.fetchone()
                updated_supplier_balance = sup_bal_row[0] if sup_bal_row else 0

                # 6. Record transaction in premium_token_transaction
                note_text = (
                    f'Bill #{effective_bill_no} extended by {extension_days} days to {new_due_date_str}'
                    if recorded_cost > 0
                    else f'Bill #{effective_bill_no} extended by {extension_days} days (0 tokens, waived)'
                )
                cursor.execute(
                    '''
                    INSERT INTO premium_token_transaction 
                    (company_id, supplier_id, supplier_user_id, bill_no, bill_id, amount, transaction_type, company_balance_after, supplier_balance_after, extension_days, executive_id, note, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    [
                        effective_company_id,
                        effective_supplier_id,
                        effective_supplier_id,
                        effective_bill_no,
                        effective_bill_id,
                        recorded_cost,
                        'due_date_extension',
                        updated_company_balance,
                        updated_supplier_balance,
                        extension_days,
                        executive_id,
                        note_text,
                        now
                    ]
                )

        except Exception as e:
            logger.error(f'[Extension Error] {e}', exc_info=True)
            return Response({'success': False, 'error': f'Failed to update bill due date: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    _safe_log(f'[Extension Confirmed] Bill #{effective_bill_no} extended to {new_due_date_str}. Fee: {recorded_cost} tokens transferred from Company {effective_company_id} to Supplier {effective_supplier_id}.')

    # Push Notification to Company Store Owner
    try:
        send_push_to_user(
            user_id=effective_company_id,
            user_type='company',
            title='Due Date Extended',
            body=f'Bill #{effective_bill_no} extended to {new_due_date_str}. {recorded_cost} tokens transferred to supplier. Balance: {updated_company_balance}',
            data={
                'type': 'due_extension_success',
                'bill_id': str(effective_bill_id),
                'bill_no': str(effective_bill_no),
                'new_due_date': str(new_due_date_str),
                'token_cost': str(recorded_cost),
                'company_tokens': str(updated_company_balance),
                'supplier_tokens': str(updated_supplier_balance),
            }
        )
    except Exception as e:
        _safe_log(f'[FCM Confirm Company Error] {e}')

    # Push Notification to Supplier
    try:
        send_push_to_user(
            user_id=effective_supplier_id,
            user_type='supplier',
            title='Token Credited for Extension',
            body=f'+{recorded_cost} tokens received for Bill #{effective_bill_no} extension. Balance: {updated_supplier_balance}',
            data={
                'type': 'supplier_token_credited',
                'bill_no': str(effective_bill_no),
                'token_cost': str(recorded_cost),
                'supplier_tokens': str(updated_supplier_balance),
            }
        )
    except Exception as e:
        _safe_log(f'[FCM Confirm Supplier Error] {e}')

    return Response({
        'success': True,
        'message': f'Due date extended to {new_due_date_str}',
        'bill_id': effective_bill_id,
        'bill_no': effective_bill_no,
        'new_due_date': new_due_date_str,
        'extension_days': extension_days,
        'token_cost': recorded_cost,
        'company_premium_tokens_balance': updated_company_balance,
        'supplier_premium_tokens_balance': updated_supplier_balance,
    }, status=status.HTTP_200_OK)
