"""Listas fixas tiradas da estrutura da planilha (não dos dados dela).

Usadas pela migração inicial. Mudar aqui não muda o banco já criado:
subcategoria e checklist padrão são editáveis no admin.
"""

CATEGORIAS = [
    (1, "Mão de obra", "Diárias, empreitas e vales de autônomos."),
    (2, "Serviços contratados", "Terraplanagem, frete, empreitas por metragem, topografia."),
    (3, "Compra de materiais", "Tudo que vira obra: areia, concreto, ferragem, madeira..."),
    (4, "Locações", "Equipamentos, contêineres, kits e caçambas."),
    (5, "Refeições sócios", "Refeições dos sócios na obra."),
    (6, "Refeições obra", "Marmitas, água e café da equipe."),
    (7, "Combustível", "Gerador, veículos e máquinas."),
    (8, "Compras diversas", "Energia, plotagem, uniforme, farmácia, hospedagem."),
    (9, "Impostos", "Imposto sobre as NF emitidas ao cliente."),
    (10, "Garantia de obra", "Gastos depois da entrega, dentro da garantia."),
    (11, "Estornos e créditos", "Dinheiro que volta: pagamento em duplicidade, devolução."),
]

SUBCATEGORIAS = {
    2: [("Terraplanagem", ""), ("Frete", ""), ("Empreita", ""), ("Topografia", ""), ("Estrutura metálica", ""),
        ("Pavimentação", "m²"), ("Asfalto", "m²")],
    3: [("Materiais diversos", ""), ("Areia", "m³"), ("Brita", "m³"), ("Cimento", "sc"), ("Concreto", "m³"),
        ("Combate a incêndio", ""), ("Cobertura", ""), ("Artefatos de concreto", "un"),
        ("Esquadrias / vidros / porta automática", ""), ("Estrutura metálica", "kg"), ("Ferragens", "kg"),
        ("Instalações elétricas", ""), ("Instalações hidráulicas", ""), ("Cabeamento de rede", "m"),
        ("Aterro", "m³"), ("Madeira", ""), ("Pavimentação / intertravado / blocos", "m²"), ("Pintura", "L"),
        ("Revestimento", "m²"), ("Drywall", "m²"), ("Ar-condicionado", "un")],
    4: [("Kits / imóvel", "mês"), ("Contêiner", "mês"), ("Caçamba", "un"), ("Gerador", "mês"),
        ("Empilhadeira", "h"), ("Máquinas", "diária"), ("Rolo compactador", "diária"), ("Munck / guindaste", "h"),
        ("Vibrador", "diária"), ("Bobcat / minicarregadeira", "diária"), ("Retroescavadeira", "h"),
        ("Andaimes", "mês"), ("Rompedor", "diária"), ("Placa vibratória", "diária"), ("Betoneira", "mês"),
        ("Compactador", "diária"), ("Perfurador", "diária"), ("Motosserra", "diária")],
    6: [("Marmitas", "un"), ("Água", "un"), ("Café / lanche", "")],
    7: [("Gasolina", "L"), ("Diesel", "L")],
    8: [("Energia / água", ""), ("Plotagem / impressão", ""), ("Placas e sinalização", ""),
        ("Uniforme / EPI", ""), ("Farmácia / protetor", ""), ("Hospedagem", "diária"),
        ("Material de limpeza", ""), ("Manutenção de veículo", "")],
}

CONTAS_BANCARIAS = ["Caixa", "Nubank", "Santander", "BRB"]

CHECKLIST = {
    "1. Início da obra": [
        "Assinatura do contrato", "Emissão de ART", "Emissão da NF de entrada", "Placa de obra",
        "Locação de apartamento", "Locação de contêineres (escritório / depósito)", "Limpeza de lote",
        "CNO da obra",
    ],
    "2. Documentos da obra": [
        "Ligação de água e energia", "Projetos aprovados", "Contratos de prestação de serviços",
        "Contrato de assinatura de carteira", "Diário de obra", "Recibos", "Documento de uniforme",
        "Cronograma",
    ],
    "3. Contratos (modelos)": [
        "Empreita", "Colaborador", "Locação", "Execução de fachada de vidro", "Ar-condicionado",
        "Serviços elétricos",
    ],
    "4. Formulários e modelos": [
        "Cadastro de colaborador", "Diário de obra", "Recibo", "Documento de uniforme", "Cronograma",
    ],
    "5. Documentação final": ["Diários de obra", "Recibos", "Projetos", "ART"],
}
