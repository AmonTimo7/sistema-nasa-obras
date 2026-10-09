# Nasa Obras — gestão financeira de obras

Sistema web que substitui a planilha de controle da obra. Faz o mesmo
trabalho da planilha, mas **sem fórmula para quebrar**: todo total é
calculado pelo sistema a partir dos lançamentos. Nasce vazio (não importa
os dados da planilha) e é usado no lugar dela.

Visual no estilo macOS (janela, vidro, widgets, modo escuro automático). A
fonte de verdade visual é o [DESIGN.md](DESIGN.md).

## Rodar no computador

```powershell
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py criar_usuario amon --papel socio --nome "Amon"
.venv\Scripts\python manage.py runserver
```

Abra http://127.0.0.1:8000. A senha que o `criar_usuario` mostra é
provisória: no primeiro acesso o sistema exige a troca e não abre nada antes.

Demonstração com dados **fictícios** (nada da planilha real):

```powershell
.venv\Scripts\python manage.py dados_exemplo           # cria a obra [DEMO]
.venv\Scripts\python manage.py dados_exemplo --apagar  # remove tudo da demo
```

Testes: `.venv\Scripts\python manage.py test`

## Demonstração no GitHub Pages

https://amontimo7.github.io/sistema-nasa-obras/ — cópia estática das telas com a
obra `[DEMO]` (dados fictícios). Salvar, filtrar e pagar mostram um aviso: lá não
há servidor. Para regerar a pasta `docs/`: `.\publicar_demo.ps1` (usa um banco
descartável; o banco de trabalho não é tocado).

## Produção (Docker + PostgreSQL)

Copie `.env.example` para `.env`, preencha, e `docker compose up -d --build`.
HTTPS obrigatório na frente (Nginx/Caddy). Comprovantes e NFs ficam no volume
`arquivos` e só abrem com login (`/financeiro/arquivo/...`), nunca por link público.

## Da planilha para o sistema

| Aba da planilha | No sistema |
|---|---|
| 01 - FINANCEIRO OBRA (blocos por mês e categoria) | **Lançamentos**, com formulário próprio por categoria; **Mês a mês** monta o bloco do mês |
| Visão geral da obra / compras por materiais | **Relatórios** → Mês × categoria, Materiais |
| Planilha3 (controle de concreto) | **Relatórios** → Concreto (m³, R$/m³) |
| Planilha4 / Planilha3 (resumo da obra) | **Painel** e **Contrato e medições** |
| NF DE ENTRADA | **Contrato e medições** (medições, retenção, situação) |
| CONTROLE - BOLETOS | **Contas a pagar** (nascem sozinhas das compras a prazo) |
| Planilha5 (controle de contêiner) | **Locações mensais** (geram a conta de cada mês) |
| Planilha6 (acerto de mão de obra) | **Mão de obra** → página de cada prestador, mês a mês |
| Planilha1 (empreiteiro por metragem) | **Empreitas** (m², preço, retenção, saldo) |
| SETLIST OBRA e DOCUMENTAÇÃO | **Checklist e documentos** (com prazo, link e arquivo) |
| Bloco "CRÉDITO PIX" | Categoria **Estornos e créditos** (entra negativo) |
| Bloco "GARANTIA DE OBRA" | Categoria **Garantia de obra** |

## Regras que o sistema garante (ver `financeiro/regras.py`)

- **Mão de obra**: valor = diárias × diária + empreita − vales. A diária vem do
  cadastro do prestador. Vale (adiantamento) fica em aberto e é descontado nos
  pagamentos seguintes; não dá para descontar mais do que o vale em aberto.
- **Compra a prazo** (boleto ou faturado): vira N contas a pagar, uma por
  parcela, e as parcelas somam exatamente o valor (sobra de centavo na última).
  Com parcela paga, valor, parcelas e forma ficam travados.
- **Quantidade × preço** calcula o valor (concreto em m³, combustível em litros).
- **Empreita por medida**: metragem × preço − retenção; saldo = contratado − (pago + retido).
- **Medição**: % do contrato calcula o valor; retenção calcula o líquido; as
  medições não passam do contrato + aditivos. **NF emitida gera o imposto**
  (alíquota da obra) como lançamento, e ele some se a emissão for desfeita.
- **Locação mensal** gera a conta de cada mês (sem duplicar); paga, vira gasto da obra.
- **Estorno** entra negativo e abate o gasto (caso visto na planilha: pagamento em
  duplicidade + estorno, que a planilha somava como gasto).
- **Avisos antes de salvar**: pagamento parecido com outro (mesmo favorecido e
  valor em até 3 dias), data fora do período da obra, data no futuro.
- **Pendências**: pagamento sem comprovante, compra sem NF, serviço sem nota.
- Valor com vírgula ou ponto ("1.234,56", "1234.56"); valor ambíguo é recusado.

## Perfis

| Perfil | Vê |
|---|---|
| Sócios / financeiro | tudo |
| Compras | fornecedores; lança e vê só materiais, locações, refeições obra, combustível e diversas |
| Jurídico | cadastro de prestadores; checklist e documentos |
| Operação | checklist e documentos |

A permissão é conferida na rota (endereço digitado também é barrado).
Todo criar/alterar/excluir fica na auditoria (admin → Auditoria).

## Onde mexer

| Arquivo | O quê |
|---|---|
| `financeiro/models.py` | dados |
| `financeiro/regras.py` | regras de negócio (testadas em `financeiro/tests.py`) |
| `financeiro/consultas.py` | números das telas, cada um com o seu denominador |
| `financeiro/sementes.py` | categorias, tipos de material/equipamento, checklist padrão |
| `static/css/sistema.css` | visual (só tokens do DESIGN.md) |
| `core/` | usuários, perfis, troca de senha, auditoria |

Listas (tipos de material, equipamentos, contas bancárias, checklist padrão)
são editáveis em `/admin/`.
