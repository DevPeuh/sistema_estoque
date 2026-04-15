from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Compra, ItemCompra, ContaPagar
from products.models import MovimentacaoEstoque

@receiver(post_save, sender=ItemCompra)
def atualizar_estoque_compra(sender, instance, created, **kwargs):
    if created:
        MovimentacaoEstoque.objects.create(
            produto=instance.produto,
            quantidade=instance.quantidade,
            tipo_movimento='entrada',
            descricao=f'Compra NF {instance.compra.numero_nota_fiscal}'
        )

@receiver(post_save, sender=Compra)
def criar_conta_pagar(sender, instance, created, **kwargs):
    if instance.status_pagamento in ['pendente', 'atrasado'] and instance.valor_total > 0:
        conta, created_conta = ContaPagar.objects.get_or_create(
            compra=instance,
            defaults={
                'fornecedor': instance.fornecedor,
                'valor': instance.valor_total,
                'data_vencimento': instance.data_vencimento,
                'status': 'atrasado' if instance.status_pagamento == 'atrasado' else 'pendente'
            }
        )
        if not created_conta:
            conta.fornecedor = instance.fornecedor
            conta.valor = instance.valor_total
            conta.data_vencimento = instance.data_vencimento
            conta.status = 'atrasado' if instance.status_pagamento == 'atrasado' else 'pendente'
            conta.save(update_fields=['fornecedor', 'valor', 'data_vencimento', 'status'])

@receiver(post_save, sender=ContaPagar)
def atualizar_status_compra(sender, instance, **kwargs):
    if instance.status == 'pago':
        compra = instance.compra
        if compra.status_pagamento != 'pago':
            compra.status_pagamento = 'pago'
            compra.save()
