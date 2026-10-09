# DESIGN.md — Sistema Nasa (gestão de obras)

Fonte de verdade visual deste projeto. Toda tela usa só os tokens abaixo.
Precisa de um token novo? Pergunte antes de inventar.

**Linguagem: macOS (Sonoma/Sequoia).** Pedido do cliente em 09/10/2026:
"bem bonito, estilo Mac, bem chique". Isso quer dizer:

- uma **janela** de cantos arredondados flutuando sobre um **papel de parede**
  colorido e desfocado, com os três botões (vermelho, amarelo, verde);
- **barra lateral translúcida** (vibrancy): vidro sobre o papel de parede;
- **título grande** em negrito, barra de ferramentas que gruda no topo;
- cartões como **widgets**: vidro claro, borda de luz de 1px, sombra macia;
- ícones de traço fino no estilo SF Symbols; **controle segmentado** para filtro;
- **modo escuro automático**, seguindo o sistema.

Continua valendo o princípio do cliente: número de bater o olho, sem letra
miúda, detalhe ao clicar.

## 1. Cor

Vidro só existe se tiver cor atrás: o papel de parede é o que faz a lateral e
os cartões parecerem vidro. Opacidade alta de propósito (lição do Sistema
Produção: halo fraco não atravessa vidro).

### Papel de parede (fixo atrás de tudo)
| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--papel-base` | `#e9edf5` | `#101114` | cor de fundo do papel de parede |
| `--papel-1` | `rgba(0,113,227,.42)` | `rgba(10,132,255,.34)` | mancha azul |
| `--papel-2` | `rgba(175,82,222,.34)` | `rgba(175,82,222,.26)` | mancha violeta |
| `--papel-3` | `rgba(255,149,0,.30)` | `rgba(255,149,0,.18)` | mancha laranja |
| `--papel-4` | `rgba(52,199,89,.22)` | `rgba(48,209,88,.14)` | mancha verde |

### Materiais (vidro)
| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--janela` | `rgba(250,250,252,.78)` | `rgba(30,30,32,.80)` | área de conteúdo da janela |
| `--lateral` | `rgba(236,236,242,.55)` | `rgba(44,44,48,.55)` | barra lateral (vibrancy) |
| `--cartao` | `rgba(255,255,255,.80)` | `rgba(44,44,46,.72)` | widget / cartão |
| `--cartao-solido` | `#ffffff` | `#2c2c2e` | campo, menu, segmento ativo (sem desfoque) |
| `--preenchimento` | `rgba(120,120,128,.12)` | `rgba(120,120,128,.24)` | trilho, segmentado, hover |
| `--borda-luz` | `rgba(255,255,255,.70)` | `rgba(255,255,255,.08)` | borda de 1px do vidro |
| `--separador` | `rgba(60,60,67,.14)` | `rgba(84,84,88,.55)` | linha fina entre itens |

### Texto
| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--tinta` | `#1d1d1f` | `#f5f5f7` | texto principal, número |
| `--tinta-2` | `#6e6e73` | `#a1a1a6` | rótulo, secundário (4,9:1 / 7:1) |
| `--tinta-3` | `#86868b` | `#8e8e93` | só texto ≥ 15px ou ícone |

### Destaque (azul de sistema da Apple)
| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--acento` | `#0071e3` | `#0a84ff` | botão principal, item ativo, foco |
| `--acento-texto` | `#0066cc` | `#2997ff` | link e texto em azul |
| `--acento-suave` | `rgba(0,113,227,.12)` | `rgba(10,132,255,.20)` | fundo de item selecionado |
| `--sobre-acento` | `#ffffff` | `#ffffff` | texto sobre `--acento` (4,7:1) |

### Séries de gráfico (validadas com o script do skill de dataviz)
| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--serie-1` | `#0071e3` | `#0a84ff` | gasto |
| `--serie-2` | `#e8590c` | `#e0660d` | faturado (só no acumulado) |

Regra: **um gráfico, uma série**, salvo o acumulado gasto × faturado. As dez
categorias viram barras horizontais numa cor só. Texto nunca usa cor de série.

### Situação (cores de sistema; sempre com palavra + forma)
| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--ok` | `#34c759` | `#30d158` | ponto: pago, feito |
| `--atencao` | `#ff9f0a` | `#ffd60a` | ponto: vence logo, a conferir |
| `--critico` | `#ff3b30` | `#ff453a` | ponto: vencido, erro de conta |
| `--ok-texto` | `#1e7f36` | `#30d158` | palavra da situação ok |
| `--atencao-texto` | `#9a5b00` | `#ffd60a` | palavra da situação atenção |
| `--critico-texto` | `#c9251b` | `#ff6961` | palavra da situação crítica, número negativo |

Botões da janela: `--semaforo-1 #ff5f57`, `--semaforo-2 #febc2e`,
`--semaforo-3 #28c840` (decorativos, iguais nos dois modos).

### Ícone de app (quadradinho com gradiente, glifo branco)
Identificam o widget e a categoria, como os ícones de Ajustes do macOS. São
identidade, não dado: dois itens podem repetir cor. Iguais nos dois modos.

| Classe | Gradiente (160°) | Onde |
|---|---|---|
| `.ic-azul` | `#3d9bff → #0071e3` | contrato, mão de obra |
| `.ic-laranja` | `#ffb340 → #f27d0c` | gasto, serviços, refeições obra |
| `.ic-verde` | `#4cd964 → #1f9e45` | faturado, diversas, garantia |
| `.ic-roxo` | `#c27cf0 → #8e44d6` | caixa, materiais, empreitas |
| `.ic-vermelho` | `#ff6b61 → #e0302a` | vencidas, combustível |
| `.ic-ciano` | `#5ac8fa → #0a8fd6` | recebido, locações |
| `.ic-rosa` | `#ff7aa2 → #e0386b` | refeições sócios |
| `.ic-cinza` | `#a1a1a6 → #6e6e73` | impostos, estornos, avatar |

O logo usa `--acento → --serie-2` (azul para laranja).

## 2. Tipografia

Pilha: `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", "Segoe UI", sans-serif`.
No Mac e no iPhone sai a SF Pro de verdade; no Windows, a Inter (a mais próxima).
Títulos e números: `"SF Pro Display", "Inter Tight", "Inter"`, peso 700,
`letter-spacing: -0.022em`. Número sempre `tabular-nums`.

| Token | Tamanho | Uso |
|---|---|---|
| `--t-hero` | `clamp(26px, 2.5vw, 36px)` | número do widget (nunca quebra linha) |
| `--t-titulo` | `30px` | título grande da página |
| `--t-sub` | `17px` | título de widget/seção (o "headline" do macOS) |
| `--t-corpo` | `15px` | corpo, tabela |
| `--t-rotulo` | `13px` | rótulo, legenda (mínimo do sistema) |

## 3. Espaçamento

Escala de 4: `--e-1: 4px`, `--e-2: 8px`, `--e-3: 12px`, `--e-4: 16px`,
`--e-5: 24px`, `--e-6: 32px`, `--e-7: 48px`. Margem lateral no celular: 16px.

## 4. Raio, sombra, desfoque

| Token | Valor | Uso |
|---|---|---|
| `--r-janela` | `14px` | a janela |
| `--r-cartao` | `20px` | widget / cartão |
| `--r-campo` | `9px` | botão, campo, item da lateral |
| `--r-barra` | `4px` | ponta de barra de gráfico |
| `--sombra-janela` | `0 30px 80px rgba(0,0,0,.22), 0 0 0 .5px rgba(0,0,0,.18)` | a janela |
| `--sombra-cartao` | `0 1px 1px rgba(0,0,0,.04), 0 6px 24px rgba(0,0,0,.06)` | widget |
| `--desfoque` | `blur(30px) saturate(180%)` | lateral, barra de ferramentas |
| `--desfoque-cartao` | `blur(20px) saturate(160%)` | widget |

Vidro não se empilha: dentro de um cartão, nada tem `backdrop-filter`.
Sem suporte a `backdrop-filter`, os materiais viram sólidos (`--cartao-solido`).

## 5. Componentes

- **Controle**: altura única de 34px (botão, campo, seletor, segmentado).
- **Item da lateral**: ícone 18px + texto; ativo = fundo `--acento` e texto branco.
- **Widget de número**: rótulo · número (`--t-hero`) · frase com o denominador.
- **Pista de ritmo**: três barras contra 100% — prazo, gasto, faturado.
- **Segmentado**: trilho `--preenchimento`, segmento ativo `--cartao-solido` com sombra.
- **Pílula de situação**: ponto colorido (círculo, losango ou quadrado) + palavra.
- **Tabela**: dentro do widget, linhas separadas por `--separador`, hover `--preenchimento`.
- **Vazio**: nunca some — escreve o motivo.
