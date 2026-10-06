from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers

from ..models import CoinTransaction, Conversation, ChatMessage, SupplierExecutive, Supplier, Company, Users, DeviceFCMToken, EndUser, SupplierOrder, SupplierOrderItem, SupplierProduct, Products
from ..fcm_utils import notify_chat_message, notify_new_order, notify_order_status, notify_bill_sent



def _resolve_company_id(company_id):
    if not company_id:
        return company_id
    try:
        cid = int(company_id)
    except (ValueError, TypeError):
        return company_id
    if Company.objects.filter(companyid=cid).exists():
        return cid
    user = Users.objects.filter(userid=cid).select_related('companyid').first()
    if user and user.companyid:
        return user.companyid.companyid
    return cid




def _is_company_buyer(request, enduser_id):
    if request.user.role != "company" or not request.user.company_id:
        return False
    company = Company.objects.filter(companyid=request.user.company_id).first()
    enduser = EndUser.objects.filter(endsuerid=enduser_id).first()
    if not company or not enduser:
        return False
    allowed_names = {
        company.companyname.strip().casefold(),
        (company.companyname + " (Store)").strip().casefold(),
    }
    return enduser.endusername.strip().casefold() in allowed_names


def _can_access_enduser(request, enduser_id):
    if request.user.role == "admin":
        return True
    if request.user.role == "enduser":
        return request.user.user_id == enduser_id
    return _is_company_buyer(request, enduser_id)


def _can_access_conversation(request, conversation):
    role = request.user.role
    if role == "admin":
        return True
    if role == "company":
        return (
            conversation.company_id == request.user.company_id
            or _is_company_buyer(request, conversation.enduser_id)
        )
    if role == "enduser":
        return conversation.enduser_id == request.user.user_id
    if role == "executive":
        return conversation.executive_id == request.user.executive_id
    if role == "manager":
        return bool(conversation.executive_id) and SupplierExecutive.objects.filter(
            executiveid=conversation.executive_id,
            manager_id=request.user.manager_id,
        ).exists()
    if role == "supplier":
        return bool(conversation.executive_id) and SupplierExecutive.objects.filter(
            executiveid=conversation.executive_id,
        ).filter(
            Q(supplier_user_id=request.user.supplier_user_id)
            | Q(manager__supplier_user_id=request.user.supplier_user_id)
        ).exists()
    return False

# ==================== CHAT API VIEWS ====================

@api_view(['GET'])
def get_company_conversations(request, company_id):
    """
    Returns retail customer conversations for a store.
    Excludes executive/supplier conversations so customers are never mixed up.
    """
    try:
        company_id = _resolve_company_id(company_id)
        conversations = Conversation.objects.filter(
            company_id=company_id,
            enduser__isnull=False
        ).select_related('enduser').order_by('-updated_at')

        result = []
        for conv in conversations:
            if not conv.enduser:
                continue
            last_message = conv.messages.order_by('-timestamp').first()
            unread_count = conv.messages.filter(sender_type='enduser', is_read=False).count()
            enduser_ph = str(getattr(conv.enduser, 'enduserphone', '') or "").strip()
            result.append({
                'conversation_id': conv.id,
                'enduser_id': conv.enduser.endsuerid,
                'enduser_name': conv.enduser.endusername,
                'enduser_phone': enduser_ph,
                'phone': enduser_ph,
                'updated_at': conv.updated_at,
                'last_message': last_message.text_content if last_message else None,
                'last_message_sender': last_message.sender_type if last_message else None,
                'is_read': last_message.is_read if last_message else True,
                'has_unread': unread_count > 0,
                'unread_count': unread_count,
                'has_audio': bool(last_message.audio_file) if last_message else False,
                'conversation_type': 'customer',
            })
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_company_executive_conversations(request, company_id):
    """
    Returns supplier executive conversations for a store.
    Strictly returns the conversation with the CURRENTLY ALLOCATED executive for each connected supplier.
    """
    try:
        from ..models import ExecutiveAllocation
        company_id = _resolve_company_id(company_id)
        
        # 1. Connected suppliers for this store
        store_suppliers = list(Supplier.objects.filter(companyid=company_id))
        store_supplier_phones = {s.supplierphonenumber for s in store_suppliers if s.supplierphonenumber}
        store_supplier_names = {s.suppliername.strip().lower() for s in store_suppliers if s.suppliername}

        # 2. Get active executive allocations for this company
        allocations = ExecutiveAllocation.objects.filter(company_id=company_id).select_related(
            'executive', 'executive__supplier_user', 'executive__manager', 'executive__manager__supplier_user'
        )

        allocated_exec_ids = set()
        for alloc in allocations:
            if alloc.executive:
                allocated_exec_ids.add(alloc.executive.executiveid)
                Conversation.objects.get_or_create(
                    company_id=company_id,
                    executive=alloc.executive,
                    defaults={'conversation_type': 'executive'}
                )

        # 3. Query conversations for this company
        # We exclusively prioritize currently allocated executives
        conversations = Conversation.objects.filter(
            company_id=company_id,
            executive__isnull=False
        ).select_related(
            'executive', 'executive__supplier_user', 'executive__manager', 'executive__manager__supplier_user'
        ).order_by('-updated_at')

        result = []
        for conv in conversations:
            if not conv.executive:
                continue
            ex = conv.executive
            
            # If there are allocations for this store, only include currently allocated executives (unless conversation has messages)
            is_allocated = ex.executiveid in allocated_exec_ids
            last_message = conv.messages.order_by('-timestamp').first()
            if not is_allocated and last_message is None:
                continue

            unread_count = conv.messages.filter(sender_type='executive', is_read=False).count()
            su = ex.supplier_user or (ex.manager.supplier_user if ex.manager else None)
            supp_name = 'Supplier'
            supp_id = None
            comp_supp = None

            if su:
                supp_name = su.suppliername or 'Supplier'
                if su.supplieruserphone:
                    comp_supp = Supplier.objects.filter(companyid=company_id, supplierphonenumber=su.supplieruserphone).first()
                if not comp_supp and supp_name:
                    comp_supp = Supplier.objects.filter(companyid=company_id, suppliername__iexact=supp_name).first()
                if comp_supp:
                    supp_id = comp_supp.supplierid
                    supp_name = comp_supp.suppliername
                else:
                    supp_id = su.supplierid_id or su.supplieruserid

            exec_ph = str(getattr(ex, 'executive_phone', '') or "").strip()
            coords = getattr(comp_supp, 'location_coordinates', None) or (getattr(su, 'location_coordinates', None) if su else None)
            result.append({
                'conversation_id': conv.id,
                'executive_id': ex.executiveid,
                'executive_name': ex.executive_name,
                'executive_phone': exec_ph,
                'phone': exec_ph,
                'location_coordinates': coords,
                'is_allocated': is_allocated,
                'supplier_id': supp_id,
                'supplier_name': supp_name,
                'company_name': supp_name,
                'updated_at': conv.updated_at,
                'last_message': last_message.text_content if last_message else None,
                'last_message_sender': last_message.sender_type if last_message else None,
                'is_read': last_message.is_read if last_message else True,
                'has_unread': unread_count > 0,
                'unread_count': unread_count,
                'has_audio': bool(last_message.audio_file) if last_message else False,
                'conversation_type': 'executive',
            })

        # Deduplicate by supplier, giving HIGHEST PRIORITY to currently allocated executives!
        result.sort(
            key=lambda x: (
                1 if x.get('is_allocated') else 0,
                1 if (x['last_message'] or x['has_audio']) else 0,
                x['updated_at']
            ),
            reverse=True
        )

        seen_supp_ids = set()
        seen_supp_names = set()
        deduped = []
        for item in result:
            sid = item.get('supplier_id')
            sname = (item.get('supplier_name') or '').strip().lower()
            if sid and sid in seen_supp_ids:
                continue
            if sname and sname in seen_supp_names:
                continue
            if sid:
                seen_supp_ids.add(sid)
            if sname:
                seen_supp_names.add(sname)
            deduped.append(item)

        return Response(deduped)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_enduser_conversations(request, enduser_id):
    """
    Returns store conversations for a retail customer (enduser).
    """
    try:
        conversations = Conversation.objects.filter(
            enduser_id=enduser_id
        ).select_related('company').order_by('-updated_at')

        result = []
        for conv in conversations:
            if not conv.company:
                continue
            last_message = conv.messages.order_by('-timestamp').first()
            unread_count = conv.messages.filter(sender_type='company', is_read=False).count()
            comp_ph = str(getattr(conv.company, 'companyphonenumber', '') or "").strip()
            comp_ph = str(getattr(conv.company, 'companyphonenumber', '') or "").strip()
            result.append({
                'conversation_id': conv.id,
                'company_id': conv.company.companyid,
                'company_name': conv.company.companyname,
                'company_phone': comp_ph,
                'phone': comp_ph,
                'company_phone': comp_ph,
                'phone': comp_ph,
                'updated_at': conv.updated_at,
                'last_message': last_message.text_content if last_message else None,
                'last_message_sender': last_message.sender_type if last_message else None,
                'is_read': last_message.is_read if last_message else True,
                'has_unread': unread_count > 0,
                'unread_count': unread_count,
                'has_audio': bool(last_message.audio_file) if last_message else False,
                'conversation_type': 'customer',
            })
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_executive_conversations(request, executive_id):
    """
    Returns store conversations for a supplier executive.
    Strictly includes companies currently allocated to this executive.
    """
    try:
        from ..models import ExecutiveAllocation
        # Ensure conversations exist for all companies allocated to this executive
        allocations = ExecutiveAllocation.objects.filter(executive_id=executive_id).select_related('company')
        allocated_company_ids = set()
        for alloc in allocations:
            if alloc.company:
                allocated_company_ids.add(alloc.company.companyid)
                Conversation.objects.get_or_create(
                    company=alloc.company,
                    executive_id=executive_id,
                    defaults={'conversation_type': 'executive'}
                )

        conversations = Conversation.objects.filter(
            executive_id=executive_id,
            company_id__in=allocated_company_ids
        ).select_related('company').order_by('-updated_at')

        result = []
        for conv in conversations:
            if not conv.company:
                continue
            
            last_message = conv.messages.order_by('-timestamp').first()
            unread_count = conv.messages.filter(sender_type='company', is_read=False).count()
            result.append({
                'conversation_id': conv.id,
                'company_id': conv.company.companyid,
                'company_name': conv.company.companyname,
                'updated_at': conv.updated_at,
                'last_message': last_message.text_content if last_message else None,
                'last_message_sender': last_message.sender_type if last_message else None,
                'is_read': last_message.is_read if last_message else True,
                'has_unread': unread_count > 0,
                'unread_count': unread_count,
                'has_audio': bool(last_message.audio_file) if last_message else False,
                'conversation_type': 'executive',
            })
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_conversation_messages(request, conversation_id):
    """
    Fetches all messages in a conversation and marks incoming messages as read.
    """
    try:
        sender_type = (request.GET.get('sender_type') or '').strip().lower()
        if sender_type in ['supplier', 'manager'] or request.GET.get('is_supervisor') == 'true':
            ChatMessage.objects.filter(
                conversation_id=conversation_id,
                is_read=False
            ).update(is_read=True)
        elif sender_type == 'company':
            ChatMessage.objects.filter(
                conversation_id=conversation_id
            ).exclude(sender_type='company').filter(is_read=False).update(is_read=True)
        elif sender_type:
            ChatMessage.objects.filter(
                conversation_id=conversation_id,
                sender_type='company',
                is_read=False
            ).update(is_read=True)

        messages = ChatMessage.objects.filter(conversation_id=conversation_id).order_by('timestamp')
        result = []
        for msg in messages:
            result.append({
                'id': msg.id,
                'sender_type': msg.sender_type,
                'text_content': msg.text_content,
                'audio_url': request.build_absolute_uri(msg.audio_file.url) if msg.audio_file else None,
                'image_url': request.build_absolute_uri(msg.image_file.url) if msg.image_file else None,
                'duration': msg.duration,
                'waveform': msg.waveform,
                'is_read': msg.is_read,
                'timestamp': msg.timestamp,
                'order_status': msg.order_status,
                'commitment_coins_locked': getattr(msg, 'commitment_coins_locked', 0) or 0,
                'is_customer_confirmed': getattr(msg, 'is_customer_confirmed', False) or False,
                'is_coins_refunded': getattr(msg, 'is_coins_refunded', False) or False,
                'is_pack_confirmed': getattr(msg, 'is_pack_confirmed', False) or False,
                'pack_confirmed_at': msg.pack_confirmed_at.isoformat() if getattr(msg, 'pack_confirmed_at', None) else None,
                'expires_at': msg.expires_at.isoformat() if getattr(msg, 'expires_at', None) else None,
            })
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=inline_serializer(
        name="SendMessageRequest",
        fields={
            "company_id": serializers.IntegerField(),
            "enduser_id": serializers.IntegerField(required=False),
            "executive_id": serializers.IntegerField(required=False),
            "sender_type": serializers.CharField(),
            "text_content": serializers.CharField(required=False),
            "audio_file": serializers.FileField(required=False),
        }
    ),
    responses={200: OpenApiResponse(description="Message sent"), 400: OpenApiResponse(description="Bad request")}
)
@api_view(['POST'])
def send_message(request):
    """
    Sends a message in either a customer conversation or executive conversation.
    """
    try:
        company_id = _resolve_company_id(request.data.get('company_id'))
        enduser_id = request.data.get('enduser_id')
        executive_id = request.data.get('executive_id')
        sender_type = request.data.get('sender_type')
        text_content = request.data.get('text_content', '')
        audio_file = request.FILES.get('audio_file')
        image_file = request.FILES.get('image_file') or request.FILES.get('image')
        duration = request.data.get('duration')
        waveform = request.data.get('waveform')
        conversation_id = request.data.get('conversation_id')

        conversation = None
        if conversation_id:
            conversation = Conversation.objects.filter(id=conversation_id).first()

        if not conversation:
            if executive_id or sender_type == 'executive':
                exec_id = int(executive_id) if executive_id else int(enduser_id)
                conversation, _ = Conversation.objects.get_or_create(
                    company_id=company_id,
                    executive_id=exec_id,
                    defaults={'conversation_type': 'executive'}
                )
            else:
                conversation, _ = Conversation.objects.get_or_create(
                    company_id=company_id,
                    enduser_id=int(enduser_id),
                    defaults={'conversation_type': 'customer'}
                )

        parsed_duration = None
        if duration is not None and str(duration).strip() != '':
            try:
                parsed_duration = int(float(str(duration).strip()))
            except (ValueError, TypeError):
                parsed_duration = None

        msg = ChatMessage.objects.create(
            conversation=conversation,
            sender_type=sender_type,
            text_content=text_content or '',
            audio_file=audio_file,
            image_file=image_file,
            duration=parsed_duration,
            waveform=waveform
        )

        conversation.updated_at = msg.timestamp
        conversation.save()

        # Trigger Push Notification
        try:
            raw_text = (text_content or '').strip()
            is_bill = 'order bill' in raw_text.lower() or '🧾' in raw_text or '[ref:#' in raw_text
            if is_bill:
                notify_bill_sent(conversation, raw_text)
            else:
                notify_chat_message(
                    conversation=conversation,
                    sender_type=sender_type,
                    text_content=text_content,
                    has_audio=bool(audio_file),
                    has_image=bool(image_file)
                )
        except Exception as _fcm_err:
            print(f"[FCM] Error notifying in send_message: {_fcm_err}")

        return Response({
            'success': True,
            'message_id': msg.id,
            'conversation_id': conversation.id,
            'timestamp': msg.timestamp,
            'audio_url': request.build_absolute_uri(msg.audio_file.url) if msg.audio_file else None,
            'image_url': request.build_absolute_uri(msg.image_file.url) if msg.image_file else None,
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
def get_or_create_company_buyer_profile(request):
    """
    Returns or creates a dedicated EndUser buyer account for a company.
    This allows a company to switch to Product Finder and place orders or chat with other companies
    without mixing with their company dashboard seller messages or using a random enduser account.
    """
    try:
        raw_company_id = request.data.get('company_id')
        company_name = (request.data.get('company_name') or '').strip()
        company = None

        if raw_company_id:
            resolved_id = _resolve_company_id(raw_company_id)
            if resolved_id:
                try:
                    company = Company.objects.get(companyid=resolved_id)
                except Company.DoesNotExist:
                    company = None

        if not company and company_name:
            company = Company.objects.filter(companyname__iexact=company_name).first()

        target_name = company.companyname if company else company_name
        if not target_name:
            return Response({'error': 'Company ID or name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Look for existing EndUser matching company name exactly
        enduser = EndUser.objects.filter(endusername__iexact=target_name).first()
        if not enduser:
            enduser = EndUser.objects.filter(endusername__iexact=f"{target_name} (Store)").first()

        # 2. If not found, create one
        if not enduser:
            candidate_name = target_name
            if EndUser.objects.filter(endusername__iexact=candidate_name).exists():
                candidate_name = f"{target_name} (Store)"
            phone_str = None
            if company and company.companyphonenumber:
                phone_str = str(company.companyphonenumber)
            enduser = EndUser.objects.create(
                endusername=candidate_name,
                enduserpassword='1234',
                enduserphone=phone_str,
            )

        return Response({
            'success': True,
            'enduser_id': enduser.endsuerid,
            'enduser_name': enduser.endusername,
            'enduser_phone': enduser.enduserphone or '',
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def send_order_message(request):
    try:
        company_id = _resolve_company_id(request.data.get('company_id'))
        enduser_id = request.data.get('enduser_id')
        executive_id = request.data.get('executive_id')
        conversation_id = request.data.get('conversation_id')
        buyer_company_id = _resolve_company_id(request.data.get('buyer_company_id'))
        cart_items = request.data.get('cart_items', [])
        sender_type_param = (request.data.get('sender_type') or '').strip().lower()

        conversation = None
        if conversation_id and int(conversation_id) > 0:
            conversation = Conversation.objects.filter(id=int(conversation_id)).first()

        if not conversation and executive_id:
            conversation = Conversation.objects.filter(
                company_id=company_id,
                executive_id=executive_id
            ).first()
            if not conversation:
                conversation = Conversation.objects.create(
                    company_id=company_id,
                    executive_id=executive_id,
                    conversation_type='executive'
                )

        if not conversation:
            # If order is placed by a company buyer, ensure we map to the company's dedicated EndUser account
            if buyer_company_id:
                try:
                    buyer_comp = Company.objects.get(companyid=buyer_company_id)
                    buyer_enduser = EndUser.objects.filter(endusername__iexact=buyer_comp.companyname).first()
                    if not buyer_enduser:
                        buyer_enduser = EndUser.objects.filter(endusername__iexact=f"{buyer_comp.companyname} (Store)").first()
                    if not buyer_enduser:
                        candidate_name = buyer_comp.companyname
                        if EndUser.objects.filter(endusername__iexact=candidate_name).exists():
                            candidate_name = f"{buyer_comp.companyname} (Store)"
                        buyer_enduser = EndUser.objects.create(
                            endusername=candidate_name,
                            enduserpassword='1234',
                            enduserphone=str(buyer_comp.companyphonenumber) if buyer_comp.companyphonenumber else None,
                        )
                    enduser_id = buyer_enduser.endsuerid
                except Exception as e:
                    print(f"[send_order_message] Error resolving buyer company {buyer_company_id}: {e}")

            conversation, created = Conversation.objects.get_or_create(
                company_id=company_id,
                enduser_id=enduser_id,
                defaults={'conversation_type': 'customer'}
            )

        note = (request.data.get('note') or '').strip()
        order_text = chr(0x1F6CD) + chr(0xFE0F) + ' New Order\n\n'
        for item in cart_items:
            qty = item.get('qty', 1)
            name = item.get('name', 'Product')
            order_text += chr(0x2022) + f" {name} (x{qty})\n"
        if note:
            order_text += f"\n\U0001F4DD Note: {note}\n"

        # If this is an executive conversation, create real SupplierOrder so it appears in:
        # 1. Executive's "My Orders" screen
        # 2. Supplier Manager's "Field Orders" tab
        # 3. Supplier Dashboard's Field Orders list
        created_supplier_order = None
        if conversation.executive_id or executive_id:
            try:
                executive = conversation.executive if conversation.executive else SupplierExecutive.objects.filter(executiveid=executive_id).first()
                company = conversation.company if conversation.company else Company.objects.filter(companyid=company_id).first()
                supplier = None

                supp_user = executive.supplier_user or (executive.manager.supplier_user if executive and executive.manager else None)
                if supp_user and company:
                    supp_q = Q(companyid=company)
                    filter_q = Q(supplierphonenumber=supp_user.supplieruserphone)
                    if getattr(supp_user, 'supplierusergst', None):
                        filter_q |= Q(suppliergst=supp_user.supplierusergst)
                    if getattr(supp_user, 'supplierusergstnumber', None):
                        filter_q |= Q(suppliergst=supp_user.supplierusergstnumber)
                    if supp_user.supplierusername:
                        filter_q |= Q(suppliername__iexact=supp_user.supplierusername)
                    supplier = Supplier.objects.filter(supp_q & filter_q).first()

                if not supplier and supp_user and company:
                    supplier = Supplier.objects.create(
                        companyid=company,
                        suppliername=supp_user.supplierusername,
                        supplierphonenumber=supp_user.supplieruserphone,
                        suppliergst=getattr(supp_user, 'supplierusergst', '') or getattr(supp_user, 'supplierusergstnumber', '') or '',
                        supplieraddress=getattr(supp_user, 'supplieruseraddress', '') or '',
                        location_coordinates=getattr(supp_user, 'location_coordinates', None),
                    )

                if not supplier and company:
                    supplier = Supplier.objects.filter(companyid=company).first()

                if supplier and executive and company:
                    created_supplier_order = SupplierOrder.objects.create(
                        company=company,
                        supplier=supplier,
                        executive=executive,
                        total_amount=0,
                        status='Pending',
                    )

                    for item in cart_items:
                        pid = item.get('product_id')
                        qty = int(item.get('qty', 1))
                        product = Products.objects.filter(productid=pid).first()
                        if not product and pid:
                            product = Products.objects.filter(id=pid).first()
                        if product:
                            supp_prod = SupplierProduct.objects.filter(company=company, supplier=supplier, product=product).first()
                            SupplierOrderItem.objects.create(
                                order=created_supplier_order,
                                product=product,
                                supplier_product=supp_prod,
                                quantity=qty,
                                price_at_order=0,
                            )
            except Exception as _so_err:
                print(f"[send_order_message] Error creating SupplierOrder: {_so_err}")

        if created_supplier_order:
            order_text += f"\n[ref:#{created_supplier_order.order_id}]"

        effective_sender_type = sender_type_param or ('company' if conversation.executive_id else 'enduser')
        msg = ChatMessage.objects.create(
            conversation=conversation,
            sender_type=effective_sender_type,
            text_content=order_text,
            order_status='pending'
        )
        conversation.updated_at = msg.timestamp
        conversation.save()

        # Trigger Push Notification
        try:
            summary = ", ".join([f"{it.get('qty', 1)}x {it.get('name')}" for it in cart_items])
            notify_new_order(conversation, summary)
        except Exception as _fcm_err:
            print(f"[FCM] Error notifying on order: {_fcm_err}")

        return Response({'success': True, 'message': 'Order sent as chat message.', 'conversation_id': conversation.id, 'message_id': msg.id})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_message(request, message_id):
    try:
        sender_type = (request.GET.get('sender_type') or request.data.get('sender_type') or '').strip().lower()
        if sender_type == 'executive' or request.GET.get('is_executive') == 'true':
            return Response({'error': 'Supplier executives are not permitted to delete sent messages.'}, status=status.HTTP_403_FORBIDDEN)
        msg = ChatMessage.objects.get(id=message_id)
        if sender_type == 'executive' or msg.sender_type == 'executive':
            return Response({'error': 'Supplier executives are not permitted to delete sent messages.'}, status=status.HTTP_403_FORBIDDEN)
        if msg.conversation and msg.conversation.executive_id and msg.sender_type == 'executive':
            return Response({'error': 'Supplier executives are not permitted to delete sent messages.'}, status=status.HTTP_403_FORBIDDEN)
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

        # Sync SupplierOrder if linked to executive
        if msg.conversation and msg.conversation.executive_id:
            try:
                target_status = 'Approved' if status_val == 'accepted' else ('Declined' if status_val == 'declined' else str(status_val).capitalize())
                ref_match = re.search(r'\[ref:#(\d+)\]', msg.text_content or '')
                if ref_match:
                    so_id = int(ref_match.group(1))
                    SupplierOrder.objects.filter(order_id=so_id).update(status=target_status)
                else:
                    so = SupplierOrder.objects.filter(
                        company_id=msg.conversation.company_id,
                        executive_id=msg.conversation.executive_id
                    ).order_by('-created_at').first()
                    if so:
                        so.status = target_status
                        so.save()
            except Exception as _so_sync:
                print(f"[update_order_status] Error syncing SupplierOrder: {_so_sync}")

        # Trigger Push Notification
        try:
            notify_order_status(msg.conversation, status_val)
        except Exception as _fcm_err:
            print(f"[FCM] Error notifying on order status: {_fcm_err}")
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
            conversation__conversation_type='customer'
        ).filter(
            Q(text_content__contains='New Order') | Q(text_content__startswith='\U0001f6cd\ufe0f') | Q(text_content__startswith='\U0001f6d2')
        ).exclude(
            Q(text_content__contains='Order Bill') | Q(text_content__contains='\U0001f9fe')
                ).select_related('conversation__company').order_by('-timestamp')

        orders = []
        for msg in messages:
            comp_ph = str(getattr(msg.conversation.company, 'companyphonenumber', '') or "").strip() if msg.conversation.company else ''
            orders.append({
                'id': msg.id,
                'company_name': msg.conversation.company.companyname,
                'company_phone': comp_ph,
                'phone': comp_ph,
                'text_content': msg.text_content,
                'timestamp': msg.timestamp,
                'order_status': msg.order_status,
                'company_id': msg.conversation.company.companyid,
                'conversation_id': msg.conversation_id,
            })

        return Response(orders)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_company_orders(request, company_id):
    try:
        company_id = _resolve_company_id(company_id)
        messages = ChatMessage.objects.filter(
            conversation__company_id=company_id,
            conversation__conversation_type='customer'
        ).filter(
            Q(text_content__contains='New Order') | Q(text_content__startswith='\U0001f6cd\ufe0f') | Q(text_content__startswith='\U0001f6d2')
        ).exclude(
            Q(text_content__contains='Order Bill') | Q(text_content__contains='\U0001f9fe')
                ).select_related('conversation__enduser').order_by('-timestamp')

        orders = []
        for msg in messages:
            enduser_ph = str(getattr(msg.conversation.enduser, 'enduserphone', '') or "").strip() if msg.conversation.enduser else ''
            orders.append({
                'id': msg.id,
                'enduser_name': msg.conversation.enduser.endusername if msg.conversation.enduser else 'Customer',
                'enduser_phone': enduser_ph,
                'phone': enduser_ph,
                'text_content': msg.text_content,
                'timestamp': msg.timestamp,
                'order_status': msg.order_status,
                'enduser_id': msg.conversation.enduser.endsuerid if msg.conversation.enduser else None,
                'conversation_id': msg.conversation_id,
                'company_id': company_id,
            })

        return Response(orders)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def update_fcm_token(request):
    """
    Endpoint to store or update the FCM device token for any user role.
    """
    try:
        fcm_token = request.data.get('fcm_token')
        user_id = request.data.get('user_id')
        user_type = (request.data.get('user_type') or '').lower().strip()

        if not fcm_token or not user_id:
            return Response({'error': 'fcm_token and user_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        uid = int(user_id)
        token_str = str(fcm_token).strip()

        # Remove token from other users so multi-account testing on the same device does not route wrong notifications
        DeviceFCMToken.objects.filter(fcm_token=token_str).exclude(user_id=uid, user_type=user_type).delete()

        DeviceFCMToken.objects.update_or_create(
            user_id=uid,
            user_type=user_type,
            defaults={'fcm_token': token_str}
        )

        if user_type == 'company':
            u = Users.objects.filter(userid=uid).first()
            if u and u.companyid_id and u.companyid_id != uid:
                DeviceFCMToken.objects.update_or_create(
                    user_id=u.companyid_id,
                    user_type='company',
                    defaults={'fcm_token': token_str}
                )
            for cu in Users.objects.filter(companyid=uid):
                if cu.userid != uid:
                    DeviceFCMToken.objects.update_or_create(
                        user_id=cu.userid,
                        user_type='company',
                        defaults={'fcm_token': token_str}
                    )

        return Response({'success': True, 'message': f'FCM token registered for {user_type} #{user_id}'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_conversation_details(request, conversation_id=0):
    try:
        conv = None
        if conversation_id and int(conversation_id) > 0:
            conv = Conversation.objects.select_related('company', 'enduser', 'executive').filter(id=int(conversation_id)).first()

        comp_id = request.GET.get('company_id')
        enduser_id = request.GET.get('enduser_id')
        exec_id = request.GET.get('executive_id')

        comp_phone = ''
        enduser_phone = ''
        exec_phone = ''
        comp_name = ''
        enduser_name = ''
        exec_name = ''

        if conv:
            if conv.company:
                comp_phone = str(getattr(conv.company, 'companyphonenumber', '') or "").strip()
                comp_name = conv.company.companyname or ''
            if conv.enduser:
                enduser_phone = str(getattr(conv.enduser, 'enduserphone', '') or "").strip()
                enduser_name = conv.enduser.endusername or ''
            if conv.executive:
                exec_phone = str(getattr(conv.executive, 'executive_phone', '') or "").strip()
                exec_name = conv.executive.executive_name or ''

        if not comp_phone and comp_id:
            c = Company.objects.filter(companyid=comp_id).first()
            if c:
                comp_phone = str(getattr(c, 'companyphonenumber', '') or "").strip()
                comp_name = c.companyname or ''

        if not enduser_phone and enduser_id:
            eu = EndUser.objects.filter(endsuerid=enduser_id).first()
            if eu:
                enduser_phone = str(getattr(eu, 'enduserphone', '') or "").strip()
                enduser_name = eu.endusername or ''

        if not exec_phone and exec_id:
            se = SupplierExecutive.objects.filter(executiveid=exec_id).first()
            if se:
                exec_phone = str(getattr(se, 'executive_phone', '') or "").strip()
                exec_name = se.executive_name or ''

        supp_id = None
        if conv and conv.executive:
            ex = conv.executive
            supp_id = ex.supplier_user_id or (ex.manager.supplier_user_id if ex.manager else None)
        elif exec_id:
            se = SupplierExecutive.objects.filter(executiveid=exec_id).first()
            if se:
                supp_id = se.supplier_user_id or (se.manager.supplier_user_id if se.manager else None)

        return Response({
            'conversation_id': conv.id if conv else int(conversation_id or 0),
            'company_phone': comp_phone,
            'company_name': comp_name,
            'enduser_phone': enduser_phone,
            'enduser_name': enduser_name,
            'executive_phone': exec_phone,
            'executive_name': exec_name,
            'supplier_id': supp_id,
            'conversation_type': conv.conversation_type if conv else ('executive' if exec_id else 'customer'),
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
def get_supplier_monitored_conversations(request, supplier_user_id):
    """
    Returns all executive-to-company conversations under this supplier for supervisory monitoring.
    """
    try:
        from ..models import SupplierExecutive
        executives = SupplierExecutive.objects.filter(
            Q(supplier_user_id=supplier_user_id) | Q(manager__supplier_user_id=supplier_user_id)
        ).select_related('manager')

        exec_ids = list(executives.values_list('executiveid', flat=True))

        conversations = Conversation.objects.filter(
            executive_id__in=exec_ids
        ).select_related('company', 'executive', 'executive__manager').order_by('-updated_at')

        result = []
        for conv in conversations:
            if not conv.company or not conv.executive:
                continue
            last_message = conv.messages.order_by('-timestamp').first()
            unread_count = conv.messages.filter(is_read=False).count()
            has_audio = (last_message.audio_file is not None and bool(last_message.audio_file)) if last_message else False
            
            exec_obj = conv.executive
            mgr_name = exec_obj.manager.manager_name if (exec_obj and exec_obj.manager) else ''

            result.append({
                'conversation_id': conv.id,
                'company_id': conv.company.companyid,
                'company_name': conv.company.companyname,
                'company_phone': str(getattr(conv.company, 'companyphonenumber', '') or ''),
                'executive_id': exec_obj.executiveid,
                'executive_name': exec_obj.executive_name,
                'executive_phone': str(getattr(exec_obj, 'executive_phone', '') or ''),
                'manager_name': mgr_name,
                'updated_at': conv.updated_at.isoformat() if conv.updated_at else None,
                'last_message': last_message.text_content if last_message else None,
                'last_message_sender': last_message.sender_type if last_message else None,
                'has_audio': has_audio,
                'is_read': last_message.is_read if last_message else True,
                'unread_count': unread_count,
            })
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_manager_monitored_conversations(request, manager_id):
    """
    Returns all executive-to-company conversations under this manager for supervisory monitoring.
    """
    try:
        from ..models import SupplierExecutive
        executives = SupplierExecutive.objects.filter(manager_id=manager_id).select_related('manager')
        exec_ids = list(executives.values_list('executiveid', flat=True))

        conversations = Conversation.objects.filter(
            executive_id__in=exec_ids
        ).select_related('company', 'executive', 'executive__manager').order_by('-updated_at')

        result = []
        for conv in conversations:
            if not conv.company or not conv.executive:
                continue
            last_message = conv.messages.order_by('-timestamp').first()
            unread_count = conv.messages.filter(is_read=False).count()
            has_audio = (last_message.audio_file is not None and bool(last_message.audio_file)) if last_message else False

            exec_obj = conv.executive
            result.append({
                'conversation_id': conv.id,
                'company_id': conv.company.companyid,
                'company_name': conv.company.companyname,
                'company_phone': str(getattr(conv.company, 'companyphonenumber', '') or ''),
                'executive_id': exec_obj.executiveid,
                'executive_name': exec_obj.executive_name,
                'executive_phone': str(getattr(exec_obj, 'executive_phone', '') or ''),
                'manager_name': exec_obj.manager.manager_name if exec_obj.manager else '',
                'updated_at': conv.updated_at.isoformat() if conv.updated_at else None,
                'last_message': last_message.text_content if last_message else None,
                'last_message_sender': last_message.sender_type if last_message else None,
                'has_audio': has_audio,
                'is_read': last_message.is_read if last_message else True,
                'unread_count': unread_count,
            })
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def update_supplier_order_status(request, order_id):
    try:
        status_val = request.data.get('status') or 'Approved'
        order = SupplierOrder.objects.get(order_id=order_id)
        order.status = status_val.capitalize()
        order.save()

        # Also sync chat message if there's a matching message with [ref:#order_id]
        chat_status = 'accepted' if status_val.lower() in ['approved', 'accepted'] else ('declined' if status_val.lower() == 'declined' else status_val.lower())
        ChatMessage.objects.filter(text_content__contains=f'[ref:#{order_id}]').update(order_status=chat_status)

        try:
            conv = Conversation.objects.filter(company=order.company, executive=order.executive).first()
            if conv:
                notify_order_status(conv, chat_status)
        except Exception as _nerr:
            pass

        return Response({'success': True, 'message': f'Order status updated to {order.status}'})
    except SupplierOrder.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE', 'POST'])
def delete_supplier_order(request, order_id):
    try:
        sender_type = (request.GET.get('sender_type') or request.data.get('sender_type') or '').strip().lower()
        if sender_type == 'executive' or request.GET.get('is_executive') == 'true':
            return Response({'error': 'Supplier executives are not permitted to delete orders.'}, status=status.HTTP_403_FORBIDDEN)
        order = SupplierOrder.objects.filter(order_id=order_id).first()
        if order:
            SupplierOrderItem.objects.filter(order=order).delete()
            ChatMessage.objects.filter(text_content__contains=f'[ref:#{order_id}]').delete()
            order.delete()
            return Response({'success': True, 'message': 'Order deleted completely.'})
        cm = ChatMessage.objects.filter(id=order_id).first()
        if cm:
            cm.delete()
            return Response({'success': True, 'message': 'Order message deleted completely.'})
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

from ..api_auth import RoleTokenAuthentication

@api_view(['GET'])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_company_wallet(request, company_id):
    """
    Returns the company's Dual Wallet: Standard Tokens (B2C) and Premium Tokens (B2B).
    """
    try:
        if request.user.role != 'company' or request.user.company_id != company_id:
            if request.user.role != 'admin':
                return Response({'error': 'Not authorized for this wallet.'}, status=status.HTTP_403_FORBIDDEN)
        company = Company.objects.filter(companyid=company_id).first()
        if not company:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
        standard = company.coins_balance or 0
        premium = getattr(company, 'premium_tokens_balance', 500) or 0
        return Response({
            'company_id': company.companyid,
            'company_name': company.companyname,
            'coins_balance': standard,
            'standard_tokens': standard,
            'standard_tokens_balance': standard,
            'premium_tokens': premium,
            'premium_tokens_balance': premium,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def recharge_company_premium_wallet(request, company_id):
    """
    Simulated B2B Premium Token recharge for companies.
    Tiers: ₹100 -> 1,000, ₹250 -> 2,500, ₹500 -> 5,000 Premium Tokens.
    """
    try:
        if request.user.role not in ['company', 'admin'] or (request.user.role == 'company' and request.user.company_id != company_id):
            return Response({'error': 'Not authorized for this wallet.'}, status=status.HTTP_403_FORBIDDEN)
        amount = int(request.data.get('amount') or 0)
        if amount <= 0:
            return Response({'error': 'Invalid recharge amount.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            company = Company.objects.select_for_update().filter(companyid=company_id).first()
            if not company:
                return Response({'error': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)
            curr = getattr(company, 'premium_tokens_balance', 0) or 0
            company.premium_tokens_balance = curr + amount
            company.save(update_fields=['premium_tokens_balance'])
            return Response({
                'success': True,
                'premium_tokens_balance': company.premium_tokens_balance,
                'coins_balance': company.premium_tokens_balance,
                'added_amount': amount,
                'message': f'Successfully recharged {amount} Premium Tokens!'
            })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def recharge_company_wallet(request, company_id):
    try:
        if request.user.role not in ['company', 'admin'] or (request.user.role == 'company' and request.user.company_id != company_id):
            return Response({'error': 'Not authorized for this wallet.'}, status=status.HTTP_403_FORBIDDEN)
        amount = int(request.data.get('amount') or 0)
        if amount <= 0:
            return Response({'error': 'Invalid recharge amount.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            company = Company.objects.select_for_update().filter(companyid=company_id).first()
            if not company:
                return Response({'error': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)
            company.coins_balance = (company.coins_balance or 0) + amount
            company.save(update_fields=['coins_balance'])
            return Response({
                'success': True,
                'coins_balance': company.coins_balance,
                'added_amount': amount,
                'message': f'Successfully recharged {amount} Frontlly Tokens!'
            })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def deduct_company_wallet(request, company_id):
    try:
        if request.user.role != 'company' or request.user.company_id != company_id:
            return Response({'error': 'Not authorized for this wallet.'}, status=status.HTTP_403_FORBIDDEN)
        amount = int(request.data.get('amount') or 0)
        reason = request.data.get('reason') or 'Coin deduction'
        if amount <= 0:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            company = Company.objects.select_for_update().filter(companyid=company_id).first()
            if not company:
                return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
            curr = company.coins_balance or 0
            if curr < amount:
                return Response({
                    'success': False,
                    'error': f'Insufficient Frontlly Coins. Required: {amount}, Available: {curr}',
                    'coins_balance': curr
                }, status=status.HTTP_400_BAD_REQUEST)
            company.coins_balance = curr - amount
            company.save()
            return Response({
                'success': True,
                'coins_balance': company.coins_balance,
                'deducted_amount': amount,
                'reason': reason
            })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_supplier_wallet(request, supplier_id):
    """
    Returns supplier's Premium Token balance.
    """
    try:
        supplier = Supplier.objects.filter(supplierid=supplier_id).first()
        if not supplier:
            su = Supplieruser.objects.filter(supplieruserid=supplier_id).first()
            if su and su.supplierid:
                supplier = Supplier.objects.filter(supplierid=su.supplierid).first()
        balance = getattr(supplier, 'premium_tokens_balance', 0) if supplier else 0
        return Response({
            'success': True,
            'supplier_id': supplier_id,
            'coins_balance': balance,
            'premium_tokens_balance': balance,
            'premium_tokens': balance,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def recharge_supplier_wallet(request, supplier_id):
    """
    Simulated recharge for suppliers.
    """
    try:
        amount = int(request.data.get('amount') or 0)
        if amount <= 0:
            return Response({'error': 'Invalid recharge amount'}, status=status.HTTP_400_BAD_REQUEST)
        supplier = Supplier.objects.filter(supplierid=supplier_id).first()
        if not supplier:
            su = Supplieruser.objects.filter(supplieruserid=supplier_id).first()
            if su and su.supplierid:
                supplier = Supplier.objects.filter(supplierid=su.supplierid).first()
        if not supplier:
            return Response({'error': 'Supplier not found'}, status=status.HTTP_404_NOT_FOUND)
        curr = getattr(supplier, 'premium_tokens_balance', 0) or 0
        supplier.premium_tokens_balance = curr + amount
        supplier.save(update_fields=['premium_tokens_balance'])
        return Response({
            'success': True,
            'premium_tokens_balance': supplier.premium_tokens_balance,
            'coins_balance': supplier.premium_tokens_balance,
            'added_amount': amount,
            'message': f'Successfully recharged {amount} Premium Tokens!'
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def deduct_supplier_wallet(request, supplier_id):
    return _supplier_wallet_unavailable()


@api_view(["GET"])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_enduser_wallet(request, enduser_id):
    """Returns enduser coin balance."""
    try:
        enduser = EndUser.objects.filter(endsuerid=enduser_id).first()
        if not enduser:
            return Response({"error": "EndUser not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "enduser_id": enduser.endsuerid,
            "enduser_name": enduser.endusername,
            "coins_balance": enduser.coins_balance or 0,
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def recharge_enduser_wallet(request, enduser_id):
    """Recharge enduser wallet with coins."""
    try:
        enduser = EndUser.objects.filter(endsuerid=enduser_id).first()
        if not enduser:
            return Response({"error": "EndUser not found"}, status=status.HTTP_404_NOT_FOUND)
        amount = int(request.data.get("amount", 0))
        if amount <= 0:
            return Response({"error": "Amount must be positive"}, status=status.HTTP_400_BAD_REQUEST)
        enduser.coins_balance = (enduser.coins_balance or 0) + amount
        enduser.save()
        return Response({
            "success": True,
            "enduser_id": enduser.endsuerid,
            "coins_balance": enduser.coins_balance,
            "recharged": amount,
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def confirm_order_bill(request, message_id=None, conversation_id=None):
    """
    Confirm the bill for an order in a conversation.
    Deducts commitment tokens from EndUser and deposits them directly into Company normal tokens (coins_balance).
    """
    try:
        target_id = message_id or conversation_id or request.data.get("message_id")
        msg = ChatMessage.objects.filter(id=target_id).first()
        if not msg and target_id:
            msg = ChatMessage.objects.filter(conversation_id=target_id).order_by("-id").first()
        if not msg:
            return Response({"error": "Order message not found"}, status=status.HTTP_404_NOT_FOUND)

        conv = msg.conversation
        if not conv:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

        if not _can_access_conversation(request, conv):
            return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        try:
            required_coins = int(request.data.get("required_coins", 200))
        except (ValueError, TypeError):
            required_coins = 200
        if required_coins < 0:
            required_coins = 200

        with transaction.atomic():
            # Update ChatMessage status and locked tokens
            msg.order_status = "confirmed"
            msg.is_customer_confirmed = True
            msg.commitment_coins_locked = required_coins
            msg.save(update_fields=["order_status", "is_customer_confirmed", "commitment_coins_locked"])

            enduser_balance = 0
            enduser = conv.enduser
            if enduser:
                enduser = EndUser.objects.select_for_update().filter(endsuerid=enduser.endsuerid).first()
                if enduser:
                    curr = enduser.coins_balance or 0
                    enduser.coins_balance = max(0, curr - required_coins)
                    enduser.save(update_fields=["coins_balance"])
                    enduser_balance = enduser.coins_balance

                    # Record transaction
                    try:
                        CoinTransaction.objects.create(
                            end_user=enduser,
                            amount=-required_coins,
                            transaction_type="order_lock",
                            reference_order_id=msg.id,
                            note=f"Locked for pickup order #{msg.id}",
                        )
                    except Exception:
                        pass

            # Credit to company normal tokens (coins_balance)
            company_balance = 0
            company = conv.company
            if company:
                company = Company.objects.select_for_update().filter(companyid=company.companyid).first()
                if company:
                    company.coins_balance = (company.coins_balance or 0) + required_coins
                    company.save(update_fields=["coins_balance"])
                    company_balance = company.coins_balance

        return Response({
            "success": True,
            "message_id": msg.id,
            "conversation_id": conv.id,
            "order_status": "confirmed",
            "is_customer_confirmed": True,
            "coins_locked": required_coins,
            "coins_balance": enduser_balance,
            "company_coins_balance": company_balance,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def complete_order_delivery(request, message_id=None, conversation_id=None):
    """Mark an order as delivered."""
    try:
        target_id = message_id or conversation_id or request.data.get("message_id")
        msg = ChatMessage.objects.filter(id=target_id).first()
        if not msg and target_id:
            msg = ChatMessage.objects.filter(conversation_id=target_id).order_by("-id").first()
        if not msg:
            return Response({"error": "Order message not found"}, status=status.HTTP_404_NOT_FOUND)
        conv = msg.conversation
        if not conv:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
        if not _can_access_conversation(request, conv):
            return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        msg.order_status = "delivered"
        msg.is_coins_refunded = True
        msg.save(update_fields=["order_status", "is_coins_refunded"])

        if conv.enduser:
            try:
                EndUser.objects.filter(endsuerid=conv.enduser.endsuerid).update(
                    completed_orders_count=models.F("completed_orders_count") + 1
                )
            except Exception:
                pass

        return Response({
            "success": True,
            "message_id": msg.id,
            "conversation_id": conv.id,
            "order_status": "delivered",
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def toggle_trusted_customer(request, conversation_id=None, enduser_id=None):
    """Toggle trusted status of a customer in a conversation."""
    try:
        conv = None
        if conversation_id:
            conv = Conversation.objects.filter(id=conversation_id).first()
        elif enduser_id:
            conv = Conversation.objects.filter(enduser_id=enduser_id).first()
        if not conv:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
        current = getattr(conv, "trusted_customer", False) or False
        conv.trusted_customer = not current
        conv.save()
        return Response({"success": True, "trusted_customer": conv.trusted_customer})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def forfeit_order_coins(request, message_id=None, order_id=None):
    """Forfeit coins associated with an order."""
    try:
        target_id = message_id or order_id or request.data.get("message_id")
        msg = ChatMessage.objects.filter(id=target_id).first()
        if msg:
            msg.order_status = "forfeited"
            coins = getattr(msg, "commitment_coins_locked", 0) or 0
            msg.save(update_fields=["order_status"])
            return Response({"success": True, "forfeited_coins": coins})

        order = SupplierOrder.objects.filter(id=target_id).first()
        if order:
            coins = getattr(order, "coins_deducted", 0) or 0
            if coins > 0:
                order.coins_deducted = 0
                order.save()
            return Response({"success": True, "forfeited_coins": coins})
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([RoleTokenAuthentication])
@permission_classes([IsAuthenticated])
def company_pack_order(request, message_id=None, conversation_id=None):
    """Mark order as packed by company."""
    try:
        from django.utils import timezone
        import datetime

        target_id = message_id or conversation_id or request.data.get("message_id")
        msg = ChatMessage.objects.filter(id=target_id).first()
        if not msg and target_id:
            msg = ChatMessage.objects.filter(conversation_id=target_id).order_by("-id").first()
        if not msg:
            return Response({"error": "Order message not found"}, status=status.HTTP_404_NOT_FOUND)

        conv = msg.conversation
        if not conv:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

        if not _can_access_conversation(request, conv):
            return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        msg.order_status = "packed"
        msg.is_pack_confirmed = True
        msg.pack_confirmed_at = timezone.now()
        msg.expires_at = timezone.now() + datetime.timedelta(hours=6)
        msg.save(update_fields=["order_status", "is_pack_confirmed", "pack_confirmed_at", "expires_at"])

        return Response({
            "success": True,
            "message_id": msg.id,
            "conversation_id": conv.id,
            "order_status": "packed",
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
