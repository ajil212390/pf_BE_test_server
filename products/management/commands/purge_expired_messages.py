from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
import datetime
from products.models import ChatMessage, Conversation, Company

class Command(BaseCommand):
    help = 'Purges all 24-hour expired customer chat messages (including order receipts) and auto-forfeits expired 6-hour pickup orders'

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff_24h = now - datetime.timedelta(hours=24)

        # 1. Purge ALL customer chat messages older than 24 hours (including order receipts, bills, images, audio, text)
        # NOTE: B2B Supplier-Company Commitments are preserved and never touched.
        expired_chats = ChatMessage.objects.filter(
            Q(conversation__conversation_type='customer') | Q(conversation__enduser__isnull=False),
            timestamp__lt=cutoff_24h
        )

        chat_count = expired_chats.count()
        for msg in expired_chats:
            try:
                if msg.audio_file:
                    msg.audio_file.delete(save=False)
                if msg.image_file:
                    msg.image_file.delete(save=False)
            except Exception:
                pass

        expired_chats.delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully purged {chat_count} customer chat messages older than 24h (including order receipts). Commitments left intact.'))

        # 2. Auto-forfeit expired packed orders where 6-hour pickup window elapsed
        expired_packed = ChatMessage.objects.filter(
            order_status='packed',
            expires_at__isnull=False,
            expires_at__lte=now,
            is_coins_refunded=False
        )

        forfeit_count = 0
        for exp_msg in expired_packed:
            try:
                with transaction.atomic():
                    exp_msg = ChatMessage.objects.select_for_update().filter(id=exp_msg.id).first()
                    if exp_msg and exp_msg.order_status == 'packed':
                        coins = getattr(exp_msg, 'commitment_coins_locked', 0) or 0
                        if coins > 0:
                            conv = exp_msg.conversation
                            if conv and conv.company:
                                comp = Company.objects.select_for_update().filter(companyid=conv.company.companyid).first()
                                if comp:
                                    comp.coins_balance = (comp.coins_balance or 0) + coins
                                    comp.save(update_fields=['coins_balance'])
                        exp_msg.order_status = 'forfeited'
                        exp_msg.save(update_fields=['order_status'])
                        forfeit_count += 1
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(f'Successfully auto-forfeited {forfeit_count} orders where the 6-hour window elapsed.'))
