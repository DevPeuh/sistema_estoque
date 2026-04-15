# Sistema de Gestão Comercial - Loja de Materiais de Construção

Este é um sistema completo para gestão de estoque, compras, vendas e dashboard administrativo, desenvolvido com Django e Django REST Framework.

## Funcionalidades
- **Autenticação JWT**: Login seguro com tokens.
- **Gestão de Produtos**: Cadastro completo com SKU e imagens.
- **Controle de Estoque**: Atualização automática via signals.
- **Gestão de Compras**: Registro de NFs e contas a pagar.
- **Gestão de Vendas**: Registro de saídas e contas a receber.
- **Dashboard**: KPIs em tempo real.
- **Relatórios**: Exportação para PDF e Excel.

## Instalação

1. Clone o repositório.
2. Crie um ambiente virtual: `python -m venv .venv`
3. Ative o ambiente virtual.
4. Instale as dependências: `pip install -r requirements.txt`
5. Configure as variáveis de ambiente (`DATABASE_URL`, `SECRET_KEY`, etc.).
6. Execute as migrações: `python manage.py migrate`
7. Crie um superusuário: `python manage.py createsuperuser`
8. Inicie o servidor: `python manage.py runserver`

## API Endpoints
- `/api/token/`: Obter token JWT.
- `/api/categorias/`: CRUD de categorias.
- `/api/produtos/`: CRUD de produtos.
- `/api/compras/compras/`: CRUD de compras.
- `/api/vendas/vendas/`: CRUD de vendas.
- `/api/dashboard/stats/`: KPIs do sistema.
- `/api/reports/inventory/excel/`: Exportar estoque para Excel.
- `/api/reports/sales/pdf/`: Exportar vendas para PDF.

## Deploy
Configurado para deploy no Railway com PostgreSQL.

## Backup
Script `backup_db.py` configurado para ser executado via GitHub Actions.

## Testes
O sistema possui testes unitários e de integração integrados ao fluxo de desenvolvimento:
- **Testes Unitários**: Localizados em `products/tests.py`, validam modelos e labels.
- **Testes de Integração**: Arquivos `tests_integration.py` e `tests_unittest.py` fornecem cobertura para API e fluxos de negócio.
- **Verificação API**: `test_api.py` permite testes rápidos via `requests`.
- **Labels Amigáveis**: O Django Admin foi customizado para exibir labels intuitivos (ex: "Nome do Produto" em vez de "SKU").

Para executar os testes nativos:
```bash
python manage.py test
```

## Changelog - 13/03/2026

- **FIX**: Corrigido erro `Cannot read properties of undefined` nas telas de Produtos, Vendas e Compras. A API agora retorna listas diretas em vez de objetos paginados, e o frontend foi ajustado para lidar com dados potencialmente nulos.
- **FEAT**: Implementado formulário completo para **Registrar Compra**, permitindo a adição dinâmica de múltiplos itens e atualização automática do estoque após o registro.
- **FEAT**: Adicionado campo **Quantidade Inicial** no formulário de cadastro de produto, permitindo que o estoque seja inicializado no momento da criação.
- **FEAT**: Implementado formulário completo para **Nova Venda**, substituindo a mensagem de "em desenvolvimento" por uma interface funcional que atualiza o estoque em tempo real.
- **FEAT**: Implementado suporte básico **Offline** com fila de sincronização automática via LocalStorage.
- **FEAT**: Adicionado escaneamento de **Código de Barras** via câmera e máscara de formatação automática no cadastro de produtos.
- **FEAT**: Implementado fluxo de **Venda Fiado** (Contas a Receber) com data de vencimento configurável e atualização automática de status.
- **FEAT**: Implementado fluxo de **Compra a Prazo** (Contas a Pagar) integrado ao módulo de compras.
- **UX**: Adicionado debounce de 1s em botões de ação e confirmação via modal para remoção de itens.
- **SECURITY**: Bloqueio de exclusão de produtos que possuam histórico de vendas ou compras vinculados (Integridade Referencial).
- **TEST**: Suíte de testes expandida para cobrir fluxos de pagamento, vencimento e bloqueio de deleção.

## Manual do Usuário - Venda a Prazo (Fiado)

1. Vá para a tela de **Vendas** e clique em **Nova Venda**.
2. Selecione o cliente e os produtos.
3. No campo **Status do Pagamento**, selecione **Pendente** ou **Não Pago**.
4. Um novo campo **Data de Vencimento** aparecerá. Informe a data acordada com o cliente.
5. Ao registrar a venda, o sistema gerará automaticamente uma **Conta a Receber** vinculada a este cliente.
6. Quando o cliente realizar o pagamento, vá ao módulo financeiro (ou via Admin) e altere o status da conta para **Pago**.
7. O sistema atualizará automaticamente o status da venda original para **Pago**.
- **VALIDATION**: Adicionada validação de estoque no backend para impedir vendas de produtos com quantidade insuficiente, prevenindo estoque negativo.
- **TEST**: Adicionados testes de integração para as novas funcionalidades, cobrindo a criação de produtos com estoque inicial, registro de compras e vendas, validação de estoque e o CRUD de clientes.

## Changelog - 18/03/2026 (Correções Críticas)

- **FIX (UI/UX)**: Corrigida a remoção de itens nos modais de venda e compra com confirmação funcional sem perda do formulário.
- **FIX (Compras)**: Corrigido cálculo de total de compra que estava sendo salvo como `0,00` em cenários com múltiplos itens.
- **FIX (Vendas)**: Corrigido envio de itens no frontend para evitar falha de registro ao usar índices dinâmicos.
- **FIX (Pagamentos)**: Alinhados os status de pagamento entre frontend e backend (`pago`, `pendente`, `atrasado`).
- **FIX (Contas)**: Ajustada geração de contas a pagar/receber para usar valor total final da operação (não mais zero na criação inicial).
- **FIX (Dashboard)**: Indicadores financeiros agora consideram contas com status `pendente` e `atrasado`.
- **FIX (Clientes)**: Adicionadas validações robustas para CPF/CNPJ (normalização, duplicidade e formato), com mensagens de erro amigáveis.
- **VALIDATION**: Adicionadas validações de quantidade/preço > 0 e exigência de data de vencimento para vendas/compras não pagas.
- **TEST**: Suíte de integração ampliada para 19 testes cobrindo compras, vendas, contas, dashboard e cadastro de clientes.

## Changelog - 18/03/2026 (Financeiro Interativo)

- **FEAT**: Nova tela **Financeiro** com visão completa de Contas a Pagar e Contas a Receber.
- **FEAT**: Filtros por status, período de vencimento e faixa de valor em ambos os módulos financeiros.
- **FEAT**: Atualização individual de contas com data, método de pagamento e observações.
- **FEAT**: Histórico de alterações/pagamentos armazenado em cada conta (`historico_pagamentos`).
- **FEAT**: Cards de Contas a Pagar/Receber no Dashboard agora são clicáveis e levam para a tela financeira.
- **FEAT**: Relatório visual de fluxo de caixa previsto por mês com alertas de vencidas e próximas do vencimento.
- **VALIDATION**: Regras de negócio para exigir justificativa em contas não pagas e data+método em contas pagas.
- **BACKEND**: Endpoints com filtros e resumos gerenciais via `/api/compras/contas-pagar/summary/` e `/api/vendas/contas-receber/summary/`.

## Changelog - 18/03/2026 (Financeiro em Tempo Real + Responsivo)

- **FIX (A Receber)**: Valores marcados como **Não Pago** deixam de compor o total de valores a receber no topo da tela.
- **FIX (Tempo Real)**: Atualização de status em contas agora reflete instantaneamente nos cards e totalizadores sem recarregar a página.
- **RESPONSIVE**: Implementado menu lateral mobile com overlay, botão hamburguer e fechamento por toque.
- **RESPONSIVE**: Breakpoints aplicados para mobile (320-768), tablet (769-1024) e desktop (1025+).
- **RESPONSIVE**: Tabelas e conteúdo financeiro adaptados com rolagem horizontal segura e área touch-friendly.
- **A11Y/UX**: Ajustes de alvos de toque e hierarquia visual para manter usabilidade em diferentes dispositivos.
- **TEST**: Adicionado teste de integração validando dedução do total a receber ao alterar status para não pago.

## Changelog - 18/03/2026 (Pré-Go-Live Produção)

- **FIX (Financeiro)**: Nome de cliente e fornecedor agora exibidos diretamente nas listagens financeiras.
- **SECURITY**: Hardening aplicado com headers de segurança, sessão mais rígida, rate limiting em login e throttling de API.
- **SECURITY**: CORS e origens CSRF configuráveis por ambiente (`CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`).
- **CONCURRENCY**: Atualizações de contas agora usam lock transacional (`select_for_update`) para evitar corrida entre dispositivos.
- **PROD**: Adicionados scripts de setup PostgreSQL, migração SQLite→PostgreSQL e backup automático.
- **OPS**: Adicionado comando `purge_test_data` para limpeza de dados de teste antes da migração.
- **CLEANUP**: Removidos artefatos de desenvolvimento (`.github` e `__pycache__`).

## Changelog - 24/03/2026 (Dashboard de Vendas Pago)

- **FIX (Dashboard)**: Totais de **Vendas Hoje** e **Vendas Mês** agora consideram apenas vendas com `status_pagamento='pago'`.
- **FIX (Regra de Negócio)**: Vendas `pendente` e `atrasado` não entram mais no faturamento exibido no dashboard.
- **TEST**: Adicionado teste de integração cobrindo transição de status `pendente -> atrasado -> pago` para validar atualização correta dos totais.

## Changelog - 24/03/2026 (Cadastros Rápidos e Exclusão Segura)

- **FEAT (Produtos)**: Inclusão de criação rápida de categoria dentro do formulário de produto, sem sair da tela.
- **FEAT (Compras)**: Inclusão de criação rápida de fornecedor no formulário de compra, com campos essenciais.
- **FEAT (UX)**: Novos feedbacks visuais para sucesso/erro nas criações rápidas e atualização imediata dos selects.
- **FIX (Delete)**: Endpoints de exclusão de produtos/clientes/categorias/fornecedores com verificação de vínculos e mensagens claras.
- **SECURITY**: Exclusões agora validam permissão explícita por recurso e adicionam auditoria de deleção.
- **SECURITY**: Rate limiting por escopo aplicado em categorias, fornecedores, clientes, produtos, compras, vendas e financeiro.
- **DATA**: Soft delete implementado para cadastros mestres quando houver histórico vinculado.
- **TEST**: Novos testes de integração cobrindo exclusão segura, auditoria, permissões e criação rápida de cadastros.

## Changelog - 24/03/2026 (Estabilidade Global + Ranking Pago)

- **FIX CRÍTICO**: Corrigida indisponibilidade geral de módulos causada por divergência entre schema e código (migrações pendentes).
- **RESILIÊNCIA**: Middleware de exceção de API agora converte falhas de schema em erro controlado com mensagem de ação imediata.
- **MONITORAMENTO**: Novo endpoint de saúde em `/api/dashboard/health/` com status do banco e contagem de migrações pendentes.
- **MONITORAMENTO**: Frontend passou a verificar saúde periodicamente e alertar sobre pendências de migração.
- **FIX (Dashboard Top 5)**: Ranking de produtos mais vendidos agora considera apenas itens de vendas com `status_pagamento='pago'`.
- **TEST**: Adicionado teste de integração validando que vendas `pendente/atrasado` não entram no Top 5 até mudança para `pago`.

## Changelog - 24/03/2026 (Produtos: Reativação e Estoque Baixo)

- **FIX (Produtos)**: Cadastro de produto com mesmo nome de item excluído logicamente agora reativa o registro anterior em vez de falhar com duplicidade.
- **FIX (Produtos)**: Código de barras vazio é normalizado como `null` no envio do formulário, evitando conflitos indevidos.
- **FIX (UI)**: Indicador vermelho de estoque baixo agora compara valores numéricos (`parseFloat`), eliminando falso alerta por comparação textual.
- **TEST**: Novo teste de integração garante reativação correta de produto excluído logicamente.

## Changelog - 24/03/2026 (Compras e Responsivo Mobile)

- **FIX (Compras)**: Número da Nota Fiscal no cadastro de compra passou a ser opcional em backend e frontend.
- **FIX (Compras/Mobile)**: Tabela de compras agora permite rolagem horizontal no mobile para visualizar todas as colunas.
- **FIX (Header/Mobile)**: Nome e avatar do usuário foram ocultados no topo em telas pequenas, mantendo status de conexão e pendências visíveis.
- **TEST**: Novo teste de integração para criação de compra sem número de nota fiscal.

## Changelog - 24/03/2026 (Auditoria de Segurança para Repositório Público)

- **SECURITY**: Criado `.gitignore` robusto para bloquear `.env`, bancos locais (`*.sqlite3`), logs, dumps, backups, chaves/certificados e ambiente virtual.
- **SECURITY**: Criado `.env.example` com todas as variáveis obrigatórias e placeholders seguros.
- **SECURITY**: `SECRET_KEY` padrão alterada para valor de desenvolvimento explícito (`unsafe-dev-secret-key-change-me`) e orientação de uso por variável de ambiente.
- **SECURITY**: Script de migração `migrate_sqlite_to_postgres.ps1` removido de string de conexão hardcoded e ajustado para usar parâmetros/`DATABASE_URL`.
- **SECURITY**: Script `backup_db.py` endurecido para evitar shell com URL completa (reduz risco de exposição/injeção), usando argumentos seguros no `pg_dump`.
- **SECURITY**: Documentação atualizada para remover exemplos de senha ambíguos e manter apenas placeholders.

## Documentação de Produção

- Guia de deploy e migração: [PRODUCAO_POSTGRES.md](file:///c:/Users/Peu/Documents/sistema_estoque/Sistema_Gestao/docs/PRODUCAO_POSTGRES.md)
- Checklist de segurança: [SECURITY_CHECKLIST.md](file:///c:/Users/Peu/Documents/sistema_estoque/Sistema_Gestao/docs/SECURITY_CHECKLIST.md)
- Tutorial PostgreSQL para iniciantes: [TUTORIAL_POSTGRESQL_INICIANTE.md](file:///c:/Users/Peu/Documents/sistema_estoque/Sistema_Gestao/docs/TUTORIAL_POSTGRESQL_INICIANTE.md)

## Manual Rápido - Gestão Financeira

1. Acesse **Financeiro** no menu lateral ou clique em **Contas a Pagar/Receber** no Dashboard.
2. Selecione o módulo desejado (Pagar ou Receber) usando as abas no topo.
3. Aplique filtros de status, vencimento e valor para localizar contas específicas.
4. Clique em **Atualizar** na linha da conta para registrar pagamento ou marcar como não paga.
5. Para marcar como **Pago**, informe obrigatoriamente a data e o método.
6. Para manter como **Pendente/Não Pago**, informe justificativa.
7. Acompanhe alertas e o gráfico de fluxo de caixa previsto no final da página.
