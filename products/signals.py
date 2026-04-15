from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import MovimentacaoEstoque

@receiver(post_save, sender=MovimentacaoEstoque)
def update_product_inventory(sender, instance, created, **kwargs):
    if created:
        produto = instance.produto
        if instance.tipo_movimento == 'entrada':
            produto.estoque_atual += instance.quantidade
        elif instance.tipo_movimento == 'saida':
            produto.estoque_atual -= instance.quantidade
        elif instance.tipo_movimento == 'ajuste':
            # Para ajuste, assumimos que a quantidade informada é o novo total ou uma diferença?
            # Vamos assumir que é uma diferença (pode ser negativa para diminuir).
            produto.estoque_atual += instance.quantidade
        
        produto.save()
