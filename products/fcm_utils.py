import os
import sys
import time
import threading

try:
    import firebase_admin
    from firebase_admin import credentials, messaging, exceptions
    FIREBASE_AVAILABLE = True
except ImportError:
    firebase_admin = None
    credentials = None
    messaging = None
    exceptions = None
    FIREBASE_AVAILABLE = False

from .models import DeviceFCMToken, Conversation, Users, EndUser, SupplierExecutive, Supplier, Company

# ---------------------------------------------------------------------------
# Firebase Admin — initialise once at import time
# FIX #23: if key file missing, set FIREBASE_AVAILABLE=False so sends fail
#          loudly (logged) instead of silently.
# ---------------------------------------------------------------------------
KEY_PATHS = [
    os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json'),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'serviceAccountKey.json'),
]

if FIREBASE_AVAILABLE and not firebase_admin._apps:
    _initialized = False
    for kp in KEY_PATHS:
        if os.path.exists(kp):
            try:
                cred = credentials.Certificate(kp)
                firebase_admin.initialize_app(cred)
                print(f'[FCM] Firebase Admin initialized with {kp}')
                _initialized = True
                break
            except Exception as _e:
                print(f'[FCM] Warning initializing Firebase Admin: {_e}')
    if not _initialized:
        FIREBASE_AVAILABLE = False
        print('[FCM] ERROR: serviceAccountKey.json not found. FCM is DISABLED. '
              'Ensure the file exists at products/serviceAccountKey.json on the VPS.')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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
    """Return a deduplicated list of valid FCM tokens for the given user/role."""
    if not user_id:
        return []
    try:
        u_type = str(user_type).lower().strip()
        u_ids = [int(user_id)]
        target_types = [u_type]

        if u_type == 'company':
            target_types = ['company', 'user']
            company_user_ids = list(
                Users.objects.filter(companyid=int(user_id)).values_list('userid', flat=True)
            )
            u_ids.extend(company_user_ids)
            usr = Users.objects.filter(userid=int(user_id)).first()
            if usr and usr.companyid_id:
                u_ids.append(usr.companyid_id)

        elif u_type == 'supplier':
            # FIX #24: include 'supplieruser' type so supplier app tokens are found
            target_types = ['supplier', 'supplieruser', 'user']
            from .models import Supplieruser
            sup_user_ids = list(
                Supplieruser.objects.filter(supplierid=int(user_id)).values_list('supplieruserid', flat=True)
            )
            u_ids.extend(sup_user_ids)
            su = Supplieruser.objects.filter(supplieruserid=int(user_id)).first()
            if su and su.supplierid_id:
                u_ids.append(su.supplierid_id)

        tokens = list(DeviceFCMToken.objects.filter(
            user_id__in=list(set(u_ids)),
            user_type__in=target_types,
        ).values_list('fcm_token', flat=True))

        # FIX #10: only return tokens that look like real FCM tokens (>50 chars)
        valid = list(set(t.strip() for t in tokens if t and len(t.strip()) > 50))
        return valid
    except Exception as e:
        _safe_log(f'[FCM] Error fetching tokens for {user_type} #{user_id}: {e}')
        return []


# ---------------------------------------------------------------------------
# Core send — DATA-ONLY message
#
# FIX #8  — removed notification= block entirely.
#            When BOTH notification + data are sent, Android system shows the
#            FCM notification automatically AND the Flutter background handler
#            fires only when message.notification == null — so with both present
#            the background handler never fires and OEM-killed apps show nothing.
#            Data-only forces Flutter's _firebaseMessagingBackgroundHandler to
#            build and show the local notification via the correct channel.
#
# FIX #9  — removed deprecated click_action='FLUTTER_NOTIFICATION_CLICK'.
#            Routing is handled by onMessageOpenedApp / getInitialMessage via
#            the data payload.
#
# FIX #17 — added apns-priority:10 and apns-push-type:alert headers for
#            immediate delivery on iOS.
#
# FIX #14 — structured latency logging: token, title, latency_ms, message_id.
# ---------------------------------------------------------------------------
def send_push(fcm_token, title, body, data=None):
    if not FIREBASE_AVAILABLE:
        _safe_log('[FCM] send_push skipped — Firebase not initialized.')
        return None
    token_str = str(fcm_token or '').strip()
    if len(token_str) < 50:
        return None

    t0 = time.time()
    token_preview = token_str[:20]
    try:
        # Build data payload — FCM requires all values to be strings
        data_payload = {k: str(v) for k, v in (data or {}).items() if v is not None}
        # Always embed title/body in data so Flutter background handler can build notif
        data_payload['title'] = str(title or '')
        data_payload['body'] = str(body or '')

        message = messaging.Message(
            # No notification= block (data-only — see FIX #8 above)
            data=data_payload,
            android=messaging.AndroidConfig(
                priority='high',  # Wakes device from Doze / battery-kill
            ),
            apns=messaging.APNSConfig(
                headers={
                    'apns-priority': '10',       # FIX #17: immediate delivery
                    'apns-push-type': 'alert',   # FIX #17: required for iOS 13+
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='notification_sound.mp3',
                        badge=1,
                        content_available=True,
                    )
                ),
            ),
            token=token_str,
        )
        res = messaging.send(message)
        latency_ms = int((time.time() - t0) * 1000)
        _safe_log(
            f'[FCM] SENT token={token_preview}... title="{title}" '
            f'latency={latency_ms}ms msg_id={res}'
        )
        return res

    except Exception as e:
        latency_ms = int((time.time() - t0) * 1000)
        if exceptions and isinstance(e, exceptions.FirebaseError):
            err_msg = str(e).lower()
            if any(k in err_msg for k in ('not-registered', 'notregistered', 'invalid-registration-token')):
                _safe_log(
                    f'[FCM] Token {token_preview}... expired/invalid — removing from DB. '
                    f'latency={latency_ms}ms'
                )
                try:
                    DeviceFCMToken.objects.filter(fcm_token=token_str).delete()
                except Exception:
                    pass
            else:
                _safe_log(
                    f'[FCM] Firebase error token={token_preview}... '
                    f'latency={latency_ms}ms err={e}'
                )
            return None
        _safe_log(f'[FCM] Error token={token_preview}... latency={latency_ms}ms err={e}')
        return None


# ---------------------------------------------------------------------------
# FIX #1 + #4: send_push_to_user is now fire-and-forget.
#
# The Django view calls send_push_to_user() and returns the HTTP response
# immediately. A daemon thread fetches tokens and sends to all concurrently.
# This unblocks Gunicorn workers even if FCM is slow/down.
# ---------------------------------------------------------------------------
def _do_send_push_to_user(user_id, user_type, title, body, data):
    """Background worker: fetch tokens and send to each concurrently."""
    try:
        tokens = get_recipient_tokens(user_id, user_type)
        if not tokens:
            _safe_log(f'[FCM] No tokens for {user_type} #{user_id} — title="{title}"')
            return
        _safe_log(f'[FCM] Dispatching to {len(tokens)} token(s) for {user_type} #{user_id}')
        sub_threads = []
        for tok in tokens:
            t = threading.Thread(target=send_push, args=(tok, title, body, data), daemon=True)
            t.start()
            sub_threads.append(t)
        for t in sub_threads:
            t.join(timeout=10)
    except Exception as e:
        _safe_log(f'[FCM] _do_send_push_to_user error: {e}')


def send_push_to_user(user_id, user_type, title, body, data=None):
    """
    Fire-and-forget push notification sender.
    Returns immediately; actual FCM I/O runs in a daemon thread.
    """
    t = threading.Thread(
        target=_do_send_push_to_user,
        args=(user_id, user_type, title, body, data),
        daemon=True,
    )
    t.start()


# ===========================================================================
# 1. CHAT MESSAGE NOTIFICATION (TEXT, VOICE, IMAGE)
# Format: Title = Sender Name (TOP), Body = Message content (BELOW)
# ===========================================================================
def notify_chat_message(conversation, sender_type, text_content=None, has_audio=False, has_image=False):
    try:
        if not conversation:
            return

        import re
        preview = (text_content or '').strip()
        if preview.startswith('[reply:'):
            parts = preview.split('\n', 1)
            preview = parts[1].strip() if len(parts) > 1 else ''
        preview = re.sub(r'\[ref:#[0-9]+\]', '', preview).strip()

        if has_audio:
            msg_type = 'voice'
            body = 'Voice message'
        elif has_image:
            msg_type = 'image'
            body = 'Photo'
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
            sender_name = conversation.company.companyname if conversation.company else 'Store'
            title = sender_name
            base_data.update({'sender_name': sender_name, 'title_name': sender_name})
            if (conversation.conversation_type == 'executive' or conversation.executive_id) and conversation.executive_id:
                send_push_to_user(conversation.executive_id, 'executive', title, body, base_data)
            elif conversation.enduser_id:
                send_push_to_user(conversation.enduser_id, 'enduser', title, body, base_data)

        elif sender_type == 'enduser':
            sender_name = conversation.enduser.endusername if conversation.enduser else 'Customer'
            title = sender_name
            base_data.update({'sender_name': sender_name, 'title_name': sender_name})
            if conversation.company_id:
                send_push_to_user(conversation.company_id, 'company', title, body, base_data)

        elif sender_type == 'executive':
            sender_name = conversation.executive.executive_name if conversation.executive else 'Executive'
            title = sender_name
            base_data.update({'sender_name': sender_name, 'title_name': sender_name})
            if conversation.company_id:
                send_push_to_user(conversation.company_id, 'company', title, body, base_data)

        elif sender_type in ('supplier', 'manager'):
            sender_name = conversation.executive.executive_name if conversation.executive else 'Supplier'
            title = sender_name
            base_data.update({'sender_name': sender_name, 'title_name': sender_name})
            if conversation.company_id:
                send_push_to_user(conversation.company_id, 'company', title, body, base_data)

    except Exception as e:
        _safe_log(f'[FCM] notify_chat_message error: {e}')


# ===========================================================================
# 2. NEW ORDER NOTIFICATION
# ===========================================================================
def notify_new_order(conversation, cart_summary):
    try:
        if conversation.executive_id:
            company_name = conversation.company.companyname if conversation.company else 'Store'
            order_data = {
                'type': 'order',
                'conversation_id': str(conversation.id),
                'company_id': str(conversation.company_id),
                'executive_id': str(conversation.executive_id),
                'sender_name': company_name,
                'title_name': company_name,
                'sender_type': 'company',
            }
            send_push_to_user(
                conversation.executive_id, 'executive',
                company_name, 'Placed a new order\nTap to view details and accept.',
                order_data,
            )
            return

        if not conversation.company_id:
            return
        buyer_name = conversation.enduser.endusername if conversation.enduser else 'Customer'
        order_data = {
            'type': 'order',
            'conversation_id': str(conversation.id),
            'company_id': str(conversation.company_id),
            'enduser_id': str(conversation.enduser_id or ''),
            'sender_name': buyer_name,
            'title_name': buyer_name,
            'sender_type': 'enduser',
        }
        send_push_to_user(
            conversation.company_id, 'company',
            buyer_name, 'Placed a new order\nTap to view details and accept.',
            order_data,
        )
    except Exception as e:
        _safe_log(f'[FCM] notify_new_order error: {e}')


# ===========================================================================
# 3. ORDER STATUS NOTIFICATION
# ===========================================================================
def notify_order_status(conversation, status_val):
    try:
        if not conversation:
            return
        status_clean = str(status_val or '').strip().lower()
        notif_type = f'order_{status_clean}' if status_clean else 'order_status'
        body_map = {
            'accepted': 'Accepted your order\nThe store is preparing your invoice.',
            'declined': 'Declined your order.',
            'cancelled': 'Order was cancelled.',
            'confirmed': 'Order confirmed.',
        }
        body = body_map.get(status_clean, f'Order status updated: {status_clean}')

        if conversation.executive_id:
            exec_name = conversation.executive.executive_name if conversation.executive else 'Executive'
            status_data = {
                'type': notif_type,
                'conversation_id': str(conversation.id),
                'company_id': str(conversation.company_id or ''),
                'executive_id': str(conversation.executive_id),
                'sender_type': 'executive',
                'sender_name': exec_name,
                'title_name': exec_name,
                'order_status': status_clean,
            }
            if conversation.company_id:
                send_push_to_user(conversation.company_id, 'company', exec_name, body, status_data)
            return

        if not conversation.enduser_id:
            return
        company_name = conversation.company.companyname if conversation.company else 'Store'
        status_data = {
            'type': notif_type,
            'conversation_id': str(conversation.id),
            'company_id': str(conversation.company_id or ''),
            'enduser_id': str(conversation.enduser_id),
            'sender_type': 'company',
            'sender_name': company_name,
            'title_name': company_name,
            'order_status': status_clean,
        }
        send_push_to_user(conversation.enduser_id, 'enduser', company_name, body, status_data)
    except Exception as e:
        _safe_log(f'[FCM] notify_order_status error: {e}')


# ===========================================================================
# 4. BILL / INVOICE NOTIFICATION
# ===========================================================================
def notify_bill_sent(conversation, text_content=None, sender_type='company'):
    try:
        if not conversation:
            return
        import re
        raw_text = str(text_content or '')
        amt_match = re.search(r'([0-9]+(?:\.[0-9]+)?)', raw_text)
        amt_str = amt_match.group(1) if amt_match else ''
        body = (
            f'Order Accepted & Bill Sent: {amt_str} Tokens\nLock with tokens to confirm pickup.'
            if amt_str else
            'Order Accepted & Bill Ready\nLock with tokens to confirm pickup.'
        )

        if sender_type == 'company':
            company_name = conversation.company.companyname if conversation.company else 'Store'
            title = company_name
            bill_data = {
                'type': 'bill', 'is_bill': 'true',
                'conversation_id': str(conversation.id),
                'company_id': str(conversation.company_id or ''),
                'enduser_id': str(conversation.enduser_id or '') if conversation.enduser_id else '',
                'executive_id': str(conversation.executive_id or '') if conversation.executive_id else '',
                'sender_type': 'company', 'sender_name': company_name, 'title_name': company_name,
                'text_content': text_content or '',
                'amount': amt_str,  # Fix A: Flutter reads data['amount'] to show token amount
            }
            if conversation.executive_id:
                send_push_to_user(conversation.executive_id, 'executive', title, body, bill_data)
            elif conversation.enduser_id:
                send_push_to_user(conversation.enduser_id, 'enduser', title, body, bill_data)
        else:
            sender_name = conversation.executive.executive_name if conversation.executive else 'Supplier'
            title = sender_name
            bill_data = {
                'type': 'bill', 'is_bill': 'true',
                'conversation_id': str(conversation.id),
                'company_id': str(conversation.company_id or ''),
                'sender_type': str(sender_type), 'sender_name': sender_name, 'title_name': sender_name,
                'text_content': text_content or '',
                'amount': amt_str,  # Fix A: Flutter reads data['amount'] to show token amount
            }
            if conversation.company_id:
                send_push_to_user(conversation.company_id, 'company', title, body, bill_data)
    except Exception as e:
        _safe_log(f'[FCM] notify_bill_sent error: {e}')


# ===========================================================================
# 5. ORDER LOCKED
# ===========================================================================
def notify_order_locked(conversation, coins_locked):
    try:
        if not conversation or not conversation.company_id:
            return
        buyer_name = conversation.enduser.endusername if conversation.enduser else 'Customer'
        data = {
            'type': 'order_locked',
            'conversation_id': str(conversation.id),
            'company_id': str(conversation.company_id),
            'enduser_id': str(conversation.enduser_id or ''),
            'sender_type': 'enduser', 'sender_name': buyer_name, 'title_name': buyer_name,
            'coins_locked': str(coins_locked),
        }
        send_push_to_user(
            conversation.company_id, 'company',
            buyer_name,
            f'Order Locked ({coins_locked} Tokens)\nCustomer confirmed pickup guarantee.',
            data,
        )
    except Exception as e:
        _safe_log(f'[FCM] notify_order_locked error: {e}')


# ===========================================================================
# 6. ORDER PACKED
# ===========================================================================
def notify_order_packed(conversation):
    try:
        if not conversation or not conversation.enduser_id:
            return
        store_name = conversation.company.companyname if conversation.company else 'Store'
        data = {
            'type': 'order_packed',
            'conversation_id': str(conversation.id),
            'company_id': str(conversation.company_id or ''),
            'enduser_id': str(conversation.enduser_id),
            'sender_type': 'company', 'sender_name': store_name, 'title_name': store_name,
        }
        send_push_to_user(
            conversation.enduser_id, 'enduser',
            store_name,
            'Order Packed & Ready for Pickup\nPlease collect within 6 hours.',
            data,
        )
    except Exception as e:
        _safe_log(f'[FCM] notify_order_packed error: {e}')


# ===========================================================================
# 7. ORDER PICKED UP
# ===========================================================================
def notify_order_picked_up(conversation, coins_refunded=0):
    try:
        if not conversation or not conversation.enduser_id:
            return
        store_name = conversation.company.companyname if conversation.company else 'Store'
        body = (
            f'Order Picked Up Successfully\n{coins_refunded} Tokens refunded to your wallet.'
            if coins_refunded and int(coins_refunded) > 0
            else 'Order Picked Up Successfully\nThank you for shopping!'
        )
        data = {
            'type': 'order_picked_up',
            'conversation_id': str(conversation.id),
            'company_id': str(conversation.company_id or ''),
            'enduser_id': str(conversation.enduser_id),
            'sender_type': 'company', 'sender_name': store_name, 'title_name': store_name,
            'coins_refunded': str(coins_refunded),
        }
        send_push_to_user(conversation.enduser_id, 'enduser', store_name, body, data)
    except Exception as e:
        _safe_log(f'[FCM] notify_order_picked_up error: {e}')
