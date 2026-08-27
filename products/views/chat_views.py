from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers

from ..models import Conversation, ChatMessage


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
        cart_items = request.data.get('cart_items', [])  # List of dicts {name, qty, price}

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
