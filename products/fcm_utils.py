import os
import sys
import firebase_admin
from firebase_admin import credentials, messaging, exceptions
from .models import DeviceFCMToken, Conversation, Users, EndUser, SupplierExecutive, Supplier, Company

# Initialize Firebase Admin once
KEY_PATHS = [
    os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json'),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'serviceAccountKey.json'),
]

if not firebase_admin._apps:
    for kp in KEY_PATHS:
        if os.path.exists(kp):
            try:
                cred = credentials.Certificate(kp)
                firebase_admin.initialize_app(cred)
                print(f"[FCM] Firebase Admin initialized with {kp}")
                break
            except Exception as e:
                print(f"[FCM] Warning initializing Firebase Admin: {e}")

def _safe_log(msg):
    try:
        sys.stdout.buffer.write((str(msg) + '\n').encode('utf-8'))
        sys.stdout.buffer.flush()
    except Exception:
        try:
            print(str(msg).encode('ascii', 'replace').decode('ascii'))
        except Exception:
            pass

def get_recipient_tokens(user_id, user_type):
    if not user_id:
        return []
    try:
        u_type = str(user_type).lower().strip()
        u_ids = [int(user_id)]

        if u_type == 'company':
            company_user_ids = list(Users.objects.filter(companyid=int(user_id)).values_list('userid', flat=True))
            u_ids.extend(company_user_ids)
            usr = Users.objects.filter(userid=int(user_id)).first()
            if usr and usr.companyid_id:
                u_ids.append(usr.companyid_id)

        tokens = list(DeviceFCMToken.objects.filter(
            user_id__in=list(set(u_ids)),
            user_type=u_type
        ).values_list('fcm_token', flat=True))

        return list(set(t.strip() for t in tokens if t and t.strip()))
    except Exception as e:
        _safe_log(f"[FCM] Error fetching tokens: {e}")
        return []

def send_push(fcm_token, title, body, data=None):
    if not fcm_token or str(fcm_token).strip() == '':
        return None
    try:
        data_payload = {k: str(v) for k, v in (data or {}).items() if v is not None}
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data_payload,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='notification_sound',
                    channel_id='custom_sound_channel_v2',
                    click_action='FLUTTER_NOTIFICATION_CLICK',
                ),
            ),
            token=str(fcm_token).strip(),
        )
        res = messaging.send(message)
        _safe_log(f"[FCM] Successfully sent push to {str(fcm_token)[:20]}...: {title} -> {body[:30]}")
        return res
    except exceptions.FirebaseError as fe:
        err_msg = str(fe)
        if 'not-registered' in err_msg.lower() or 'notregistered' in err_msg.lower():
            _safe_log(f"[FCM] Token {str(fcm_token)[:20]}... expired/unregistered. Removing from DB.")
            try:
                DeviceFCMToken.objects.filter(fcm_token=str(fcm_token).strip()).delete()
            except Exception:
                pass
        else:
            _safe_log(f"[FCM] Firebase error sending push: {fe}")
        return None
    except Exception as e:
        _safe_log(f"[FCM] Error sending push: {e}")
        return None

def send_push_to_user(user_id, user_type, title, body, data=None):
    tokens = get_recipient_tokens(user_id, user_type)
    if not tokens:
        _safe_log(f"[FCM] No tokens found for {user_type} #{user_id}")
    for tok in tokens:
        send_push(tok, title, body, data)

# 1. CHAT MESSAGE NOTIFICATION (TEXT, VOICE, IMAGE)
# Format: Title = Name of Sender (TOP), Body = Message Content (BELOW)
def notify_chat_message(conversation, sender_type, text_content=None, has_audio=False, has_image=False):
    try:
        if not conversation:
            return

        preview = (text_content or '').strip()
        if preview.startswith('[reply:'):
            parts = preview.split('\n', 1)
            if len(parts) > 1:
                preview = parts[1].strip()

        import re
        preview = re.sub(r'\[ref:#[0-9]+\]', '', preview).strip()

        # Determine message body below title
        if has_audio:
            msg_type = 'voice'
            body = 'ðŸŽ¤ Voice message'
        elif has_image:
            msg_type = 'image'
            body = 'ðŸ“· Photo'
        else:
            msg_type = 'chat'
            body = preview if preview else 'Sent a message'

        if len(body) > 120:
            body = body[:117] + '...'

        base_data = {
            'type': msg_type,
            'conversation_id': str(conversation.id),
            'company_id': str(conversation.company_id or ''),
            'enduser_id': str(conversation.enduser_id or '') if conversation.enduser_id else '',
            'executive_id': str(conversation.executive_id or '') if conversation.executive_id else '',
            'sender_type': str(sender_type),
            'is_voice': 'true' if has_audio else 'false',
            'is_image': 'true' if has_image else 'false',
            'is_bill': 'false',
            'text_content': preview,
        }

        if sender_type == 'company':
            # Sender is store/company -> Receiver is enduser or executive
            sender_name = conversation.company.companyname if conversation.company else 'Store'
            title = sender_name # SENDER NAME ON TOP
            base_data['sender_name'] = sender_name
            base_data['title_name'] = sender_name

            if (conversation.conversation_type == 'executive' or conversation.executive_id) and conversation.executive_id:
                send_push_to_user(
                    user_id=conversation.executive_id,
                    user_type='executive',
                    title=title,
                    body=body,
                    data=base_data
                )
            elif conversation.enduser_id:
                send_push_to_user(
                    user_id=conversation.enduser_id,
                    user_type='enduser',
                    title=title,
                    body=body,
                    data=base_data
                )

        elif sender_type == 'enduser':
            # Sender is customer -> Receiver is company
            sender_name = conversation.enduser.endusername if conversation.enduser else 'Customer'
            title = sender_name # SENDER NAME ON TOP
            base_data['sender_name'] = sender_name
            base_data['title_name'] = sender_name

            if conversation.company_id:
                send_push_to_user(
                    user_id=conversation.company_id,
                    user_type='company',
                    title=title,
                    body=body,
                    data=base_data
                )

        elif sender_type == 'executive':
            # Sender is executive -> Receiver is company
            sender_name = conversation.executive.executive_name if conversation.executive else 'Executive'
            title = sender_name # SENDER NAME ON TOP
            base_data['sender_name'] = sender_name
            base_data['title_name'] = sender_name

            if conversation.company_id:
                send_push_to_user(
                    user_id=conversation.company_id,
                    user_type='company',
                    title=title,
                    body=body,
                    data=base_data
                )
    except Exception as e:
        _safe_log(f"[FCM] notify_chat_message error: {e}")

# 2. ORDER NOTIFICATION
# Format: Title = Buyer Name (TOP), Body = Order notice (BELOW)
def notify_new_order(conversation, cart_summary):
    try:
        buyer_name = conversation.enduser.endusername if conversation.enduser else 'Customer'
        company_id = conversation.company_id
        if company_id:
            title = buyer_name # BUYER NAME ON TOP
            order_body = "ðŸ›ï¸ Placed a new order\nTap to view details and accept."
            order_data = {
                'type': 'order',
                'conversation_id': str(conversation.id),
                'company_id': str(company_id),
                'enduser_id': str(conversation.enduser_id or ''),
                'sender_name': buyer_name,
                'title_name': buyer_name,
                'sender_type': 'enduser',
            }
            send_push_to_user(
                user_id=company_id,
                user_type='company',
                title=title,
                body=order_body,
                data=order_data
            )
    except Exception as e:
        _safe_log(f"[FCM] notify_new_order error: {e}")

# 3. ORDER STATUS NOTIFICATION
# Format: Title = Company Name (TOP), Body = Status (BELOW)
def notify_order_status(conversation, status_val):
    try:
        if not conversation or not conversation.enduser_id:
            return
        company_name = conversation.company.companyname if conversation.company else 'Store'
        title = company_name # COMPANY NAME ON TOP
        status_clean = str(status_val).lower().strip()
        if status_clean == 'accepted':
            body = "âœ… Accepted your order\nThe store is preparing your invoice."
            notif_type = 'order_accepted'
        elif status_clean == 'declined':
            body = "âŒ Declined your order"
            notif_type = 'order_declined'
        elif status_clean == 'cancelled':
            body = "âš ï¸ Order was cancelled"
            notif_type = 'order_cancelled'
        else:
            body = f"ðŸ“¦ Order {status_val.capitalize()}"
            notif_type = 'order_status'

        status_data = {
            'type': notif_type,
            'conversation_id': str(conversation.id),
            'company_id': str(conversation.company_id or ''),
            'enduser_id': str(conversation.enduser_id or ''),
            'sender_type': 'company',
            'sender_name': company_name,
            'title_name': company_name,
            'order_status': status_clean,
        }

        send_push_to_user(
            user_id=conversation.enduser_id,
            user_type='enduser',
            title=title,
            body=body,
            data=status_data
        )
    except Exception as e:
        _safe_log(f"[FCM] notify_order_status error: {e}")

# 4. BILL / INVOICE NOTIFICATION
# Format: Title = Company Name (TOP), Body = Invoice Notice (BELOW)
def notify_bill_sent(conversation, text_content=None):
    try:
        if not conversation:
            return
        company_name = conversation.company.companyname if conversation.company else 'Store'
        title = company_name # COMPANY NAME ON TOP
        body = "ðŸ§¾ Order Invoice & Bill Ready\nTap to view details."

        bill_data = {
            'type': 'bill',
            'is_bill': 'true',
            'conversation_id': str(conversation.id),
            'company_id': str(conversation.company_id or ''),
            'enduser_id': str(conversation.enduser_id or '') if conversation.enduser_id else '',
            'executive_id': str(conversation.executive_id or '') if conversation.executive_id else '',
            'sender_type': 'company',
            'sender_name': company_name,
            'title_name': company_name,
            'text_content': text_content or '',
        }

        if (conversation.conversation_type == 'executive' or conversation.executive_id) and conversation.executive_id:
            send_push_to_user(
                user_id=conversation.executive_id,
                user_type='executive',
                title=title,
                body=body,
                data=bill_data
            )
        elif conversation.enduser_id:
            send_push_to_user(
                user_id=conversation.enduser_id,
                user_type='enduser',
                title=title,
                body=body,
                data=bill_data
            )
    except Exception as e:
        _safe_log(f"[FCM] notify_bill_sent error: {e}")

