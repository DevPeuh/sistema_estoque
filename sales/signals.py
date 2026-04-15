from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Venda, ItemVenda, ContaReceber
from products.models import MovimentacaoEstoque
from django.utils import timezone

@receiver(post_save, sender=ItemVenda)
def atualizar_estoque_venda(sender, instance, created, **kwargs):
    if created:
        MovimentacaoEstoque.objects.create(
            produto=instance.produto,
            quantidade=instance.quantidade,
            tipo_movimento='saida',
            descricao=f'Venda #{instance.venda.id}'
        )

@receiver(post_save, sender=Venda)
def criar_conta_receber(sender, instance, created, **kwargs):
    if instance.status_pagamento in ['pendente', 'atrasado'] and instance.valor_total > 0:
        vencimento = instance.data_vencimento or (instance.data_venda + timezone.timedelta(days=30))
        conta, created_conta = ContaReceber.objects.get_or_create(
            venda=instance,
            defaults={
                'cliente': instance.cliente,
                'valor': instance.valor_total,
                'data_vencimento': vencimento,
                'status': 'atrasado' if instance.status_pagamento == 'atrasado' else 'pendente'
            }
        )
        if not created_conta:
            conta.cliente = instance.cliente
            conta.valor = instance.valor_total
            conta.data_vencimento = vencimento
            conta.status = 'atrasado' if instance.status_pagamento == 'atrasado' else 'pendente'
            conta.save(update_fields=['cliente', 'valor', 'data_vencimento', 'status'])

@receiver(post_save, sender=ContaReceber)
def atualizar_status_venda(sender, instance, **kwargs):
    if instance.status == 'pago':
        venda = instance.venda
        if venda.status_pagamento != 'pago':
            venda.status_pagamento = 'pago'
            venda.save()
