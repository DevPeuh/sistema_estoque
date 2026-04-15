import logging
from typing import Any
from django.db import transaction
from rest_framework import serializers
from .models import Fornecedor, Compra, ItemCompra, ContaPagar

logger = logging.getLogger(__name__)

class FornecedorSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    def validate_razao_social(self, value):
        nome = (value or '').strip()
        if not nome:
            raise serializers.ValidationError('O nome do fornecedor é obrigatório.')
        return nome

    def validate_cnpj(self, value):
        digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
        if len(digits) not in (11, 14):
            raise serializers.ValidationError('CNPJ/CPF deve conter 11 ou 14 dígitos.')
        qs = Fornecedor.objects.filter(cnpj=digits, ativo=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Já existe fornecedor ativo com este CNPJ/CPF.')
        return digits

    def validate(self, attrs):
        attrs['razao_social'] = attrs.get('razao_social', getattr(self.instance, 'razao_social', '')).strip()
        attrs['contato_nome'] = (attrs.get('contato_nome') or attrs['razao_social']).strip()
        attrs['nome_fantasia'] = (attrs.get('nome_fantasia') or attrs['razao_social']).strip()
        attrs['endereco'] = (attrs.get('endereco') or 'Não informado').strip()
        telefone = attrs.get('telefone')
        if not telefone:
            raise serializers.ValidationError('Informe o telefone do fornecedor.')
        attrs['telefone'] = str(telefone).strip()
        email = attrs.get('email')
        attrs['email'] = str(email).strip() if email else None
        return attrs

    class Meta:
        model = Fornecedor
        fields = '__all__'

class ItemCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCompra
        fields = ['produto', 'quantidade', 'preco_unitario']

class CompraSerializer(serializers.ModelSerializer):
    itens = ItemCompraSerializer(many=True)
    fornecedor_nome = serializers.ReadOnlyField(source='fornecedor.razao_social')
    numero_nota_fiscal = serializers.CharField(required=False, allow_blank=True, allow_null=True, validators=[])

    class Meta:
        model = Compra
        fields = ['id', 'numero_nota_fiscal', 'fornecedor', 'fornecedor_nome', 'data_emissao', 'data_recebimento', 'valor_total', 'status_pagamento', 'data_vencimento', 'itens']

    def validate_numero_nota_fiscal(self, value):
        if value is None:
            return None
        numero = str(value).strip()
        if not numero:
            return None
        qs = Compra.objects.filter(numero_nota_fiscal=numero)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Já existe uma compra com este número de nota fiscal.')
        return numero

    def create(self, validated_data):
        itens_data = validated_data.pop('itens')
        if not validated_data['fornecedor'].ativo:
            raise serializers.ValidationError('Selecione um fornecedor ativo.')
        if not itens_data:
            raise serializers.ValidationError('Adicione pelo menos um item para registrar a compra.')
        if validated_data.get('status_pagamento') != 'pago' and not validated_data.get('data_vencimento'):
            raise serializers.ValidationError('Informe a data de vencimento para compras pendentes ou não pagas.')
        try:
            with transaction.atomic():
                compra = Compra.objects.create(**validated_data)
                valor_total_compra = 0
                for item_data in itens_data:
                    if not item_data['produto'].ativo:
                        raise serializers.ValidationError(f"O produto '{item_data['produto'].descricao}' está inativo.")
                    if item_data['quantidade'] <= 0:
                        raise serializers.ValidationError('Quantidade deve ser maior que zero.')
                    if item_data['preco_unitario'] <= 0:
                        raise serializers.ValidationError('Preço unitário deve ser maior que zero.')
                    item = ItemCompra.objects.create(compra=compra, **item_data)
                    valor_total_compra += item.subtotal
                if valor_total_compra <= 0:
                    raise serializers.ValidationError('Valor total da compra inválido.')
                compra.valor_total = valor_total_compra
                compra.save()
                return compra
        except Exception as exc:
            logger.exception('Falha ao registrar compra: %s', exc)
            raise

class ContaPagarSerializer(serializers.ModelSerializer):
    fornecedor_nome = serializers.ReadOnlyField(source='fornecedor.razao_social')

    def validate(self, attrs):
        status = attrs.get('status', getattr(self.instance, 'status', None))
        data_pagamento = attrs.get('data_pagamento', getattr(self.instance, 'data_pagamento', None))
        metodo_pagamento = attrs.get('metodo_pagamento', getattr(self.instance, 'metodo_pagamento', None))
        justificativa_status = attrs.get('justificativa_status', getattr(self.instance, 'justificativa_status', None))
        if status == 'pago':
            if not data_pagamento:
                raise serializers.ValidationError('Informe a data de pagamento para marcar como pago.')
            if not metodo_pagamento:
                raise serializers.ValidationError('Informe o método de pagamento para marcar como pago.')
        if status in ['pendente', 'atrasado'] and not justificativa_status:
            raise serializers.ValidationError('Informe uma justificativa ao marcar conta como não paga.')
        return attrs

    def update(self, instance, validated_data):
        with transaction.atomic():
            locked = ContaPagar.objects.select_for_update().get(pk=instance.pk)
            previous_status = locked.status
            updated = super().update(locked, validated_data)
            if previous_status != updated.status or validated_data.get('data_pagamento') or validated_data.get('metodo_pagamento'):
                historico = list[Any](updated.historico_pagamentos or [])
                historico.append({
                    'status': updated.status,
                    'data_pagamento': str(updated.data_pagamento) if updated.data_pagamento else None,
                    'metodo_pagamento': updated.metodo_pagamento,
                    'observacoes': updated.observacoes
                })
                updated.historico_pagamentos = historico
                updated.save(update_fields=['historico_pagamentos'])
            return updated

    class Meta:
        model = ContaPagar
        fields = [
            'id', 'compra', 'fornecedor', 'fornecedor_nome', 'valor', 'data_vencimento', 'status',
            'data_pagamento', 'metodo_pagamento', 'observacoes', 'justificativa_status',
            'historico_pagamentos'
        ]
