from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers

from ..models import Conversation, ChatMessage, SupplierExecutive, Supplier, Company, Users


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
            result.append({
                'conversation_id': conv.id,
                'enduser_id': conv.enduser.endsuerid,
                'enduser_name': conv.enduser.endusername,
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

            result.append({
                'conversation_id': conv.id,
                'executive_id': ex.executiveid,
                'executive_name': ex.executive_name,
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
        sender_type = request.GET.get('sender_type')
        if sender_type:
            if sender_type == 'company':
                ChatMessage.objects.filter(
                    conversation_id=conversation_id
                ).exclude(sender_type='company').filter(is_read=False).update(is_read=True)
            else:
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
def send_order_message(request):
    try:
        company_id = _resolve_company_id(request.data.get('company_id'))
        enduser_id = request.data.get('enduser_id')
        cart_items = request.data.get('cart_items', [])

        conversation, created = Conversation.objects.get_or_create(
            company_id=company_id,
            enduser_id=enduser_id,
            defaults={'conversation_type': 'customer'}
        )

        note = (request.data.get('note') or '').strip()
        order_text = "🛍️ New Order\n\n"
        for item in cart_items:
            qty = item.get('qty', 1)
            order_text += f"• {item.get('name')} (x{qty})\n"
        if note:
            order_text += f"\n📝 Note: {note}\n"

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
            conversation__conversation_type='customer',
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
            conversation__conversation_type='customer',
            text_content__startswith='🛍️ New Order'
        ).select_related('conversation__enduser').order_by('-timestamp')

        orders = []
        for msg in messages:
            orders.append({
                'id': msg.id,
                'enduser_name': msg.conversation.enduser.endusername if msg.conversation.enduser else 'Customer',
                'text_content': msg.text_content,
                'timestamp': msg.timestamp,
                'order_status': msg.order_status,
                'enduser_id': msg.conversation.enduser.endsuerid if msg.conversation.enduser else None,
                'conversation_id': msg.conversation_id,
            })

        return Response(orders)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
