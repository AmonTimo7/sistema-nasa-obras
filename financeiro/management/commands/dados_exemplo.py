"""Dados FICTÍCIOS para demonstrar o sistema. Nada aqui vem da planilha real.

    python manage.py dados_exemplo           # cria a obra de demonstração
    python manage.py dados_exemplo --apagar  # remove tudo que ele criou
"""
import random
from datetime import date, timedelta
from decimal import Decimal as D

from django.core.management.base import BaseCommand
from django.db import transaction

from compras.models import Fornecedor
from financeiro import regras
from financeiro.models import (
    Aditivo,
    Categoria,
    ContaAPagar,
    ContaBancaria,
    Empreita,
    ItemChecklist,
    Lancamento,
    LocacaoRecorrente,
    Medicao,
    Obra,
    Responsavel,
    Subcategoria,
)
from juridico.models import Prestador

MARCA = "[DEMO]"
OBRA = f"{MARCA} Centro Logístico Vale Verde"

PESSOAS = [("Paulo Henrique Lima", "Pedreiro", 220), ("Marcos Tavares", "Ajudante", 140),
           ("Rafael Nunes", "Ajudante", 140), ("Sérgio Almeida", "Eletricista", 250),
           ("Diego Moreira", "Carpinteiro", 230), ("Wellington Souza", "Pedreiro", 220),
           ("André Batista", "Ajudante", 140), ("Luiz Fernando Rocha", "Encarregado", 300)]
LOJAS = [("Madeireira Cerrado", "madeira", "recorrente"), ("Concreteira Planalto", "concreto", "recorrente"),
         ("Ferro & Aço Central", "ferragens", "recorrente"), ("Elétrica Luz Forte", "elétrica", "cotacao"),
         ("Hidro Tubos", "hidráulica", "cotacao"), ("Areial São Jorge", "areia e brita", "recorrente"),
         ("Posto Rodovia", "combustível", "recorrente"), ("Restaurante Sabor da Obra", "refeição", "recorrente"),
         ("Locadora Máquinas Já", "locação", "cotacao"), ("Contêineres Goiás", "contêiner", "recorrente"),
         ("Terraplenagem Horizonte", "terraplanagem", "cotacao"), ("Pavimenta Bem", "intertravado", "cotacao"),
         ("Cimenteira Brasil", "cimento", "recorrente"), ("Gráfica Rápida", "impressão", "cotacao")]


class Command(BaseCommand):
    help = "Cria (ou apaga, com --apagar) uma obra de demonstração com dados fictícios."

    def add_arguments(self, parser):
        parser.add_argument("--apagar", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["apagar"]:
            self.apagar()
            return
        if Obra.objects.filter(nome=OBRA).exists():
            self.stdout.write("A obra de demonstração já existe. Use --apagar antes para recriar.")
            return
        random.seed(7)
        hoje = date.today()
        inicio = (hoje.replace(day=1) - timedelta(days=150)).replace(day=3)
        obra = Obra.objects.create(
            nome=OBRA, cliente="Cliente Demonstração S.A.", numero_contrato="DEMO-2026-001",
            escopo="Galpão, pátio intertravado e escritórios", nicho="obras", cidade="Goiânia",
            valor_contrato=D("4800000"), data_inicio=inicio, data_termino=inicio + timedelta(days=240),
            aliquota_imposto=D("5.5"), retencao_padrao=D("3"),
        )
        Aditivo.objects.create(obra=obra, descricao="Aditivo I — ampliação do pátio", valor=D("320000"),
                               data=inicio + timedelta(days=90))
        regras.criar_checklist(obra)
        for i, item in enumerate(obra.checklist.all()):
            if i < 9:
                item.situacao = ItemChecklist.FEITO
            elif i < 13:
                item.situacao = ItemChecklist.ANDAMENTO
                item.prazo = hoje + timedelta(days=random.randint(-5, 20))
            item.save()

        resp = [Responsavel.objects.get_or_create(nome=n)[0] for n in (f"{MARCA} Carla", f"{MARCA} Bruna", f"{MARCA} Jonas")]
        caixa = ContaBancaria.objects.get(nome="Caixa")
        pessoas = [Prestador.objects.create(nome=f"{MARCA} {n}", funcao=f, valor_diaria=D(v), cidade="Goiânia",
                                            chave_pix=f"(62) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}")
                   for n, f, v in PESSOAS]
        lojas = {r: Fornecedor.objects.create(nome=f"{MARCA} {n}", ramo=r, tipo=t, cidade="Goiânia",
                                              telefone=f"(62) 3{random.randint(100, 999)}-{random.randint(1000, 9999)}")
                 for n, r, t in LOJAS}

        def sub(cod, nome):
            return Subcategoria.objects.get(categoria__codigo=cod, nome=nome)

        def lancar(**kw):
            kw.setdefault("conta_bancaria", caixa)
            kw.setdefault("responsavel", random.choice(resp))
            kw.setdefault("comprovante", "demo/comprovante.pdf" if random.random() > .15 else "")
            l = Lancamento(obra=obra, **kw)
            erros = regras.preparar_lancamento(l)
            if erros:
                raise RuntimeError(erros)
            l.save()
            regras.sincronizar_contas(l)
            return l

        cat = {c.codigo: c for c in Categoria.objects.all()}
        # semanas de mão de obra: toda sexta, a equipe cresce com a obra
        sexta = inicio + timedelta(days=(4 - inicio.weekday()) % 7)
        n_sem = 0
        while sexta <= hoje:
            n_sem += 1
            equipe = pessoas[:min(len(pessoas), 3 + n_sem // 3)]
            for p in equipe:
                if random.random() < .12:
                    lancar(categoria=cat[1], prestador=p, data=sexta - timedelta(days=3), tipo_mao_de_obra="adiantamento",
                           valor=D("100"), descricao="Vale", comprovante="demo/comprovante.pdf")
                    desconto = D("100")
                else:
                    desconto = D("0")
                dias = D(random.choice([4, 5, 5, 5, 6]))
                lancar(categoria=cat[1], prestador=p, data=sexta, tipo_mao_de_obra="diarias", diarias=dias,
                       valor_diaria=p.valor_diaria, desconto=desconto, valor=None,
                       descricao=f"{int(dias)} diárias da semana")
            sexta += timedelta(days=7)

        # materiais ao longo dos meses
        compras = [("Concreto", "concreteira", "Concreto FCK 25", "m³", (8, 40), (560, 610)),
                   ("Madeira", "madeira", "Tábua pinus e pontalete", None, None, (1500, 4500)),
                   ("Ferragens", "ferragens", "Vergalhão 10mm e arame", "kg", (300, 1200), (8, 11)),
                   ("Areia", "areia e brita", "Areia lavada", "m³", (10, 30), (110, 140)),
                   ("Brita", "areia e brita", "Brita 1", "m³", (10, 25), (120, 150)),
                   ("Cimento", "cimento", "Cimento CP-II", "sc", (60, 150), (34, 38)),
                   ("Instalações elétricas", "elétrica", "Cabos, disjuntores e eletrodutos", None, None, (1800, 9000)),
                   ("Instalações hidráulicas", "hidráulica", "Tubos e conexões PVC", None, None, (900, 5200))]
        d = inicio + timedelta(days=6)
        while d <= hoje:
            for nome, loja, desc, un, faixa_q, faixa_p in random.sample(compras, 4):
                forma = random.choice(["pix", "pix", "boleto", "debito"])
                kw = {"categoria": cat[3], "subcategoria": sub(3, nome), "fornecedor": lojas[loja if loja != "concreteira" else "concreto"],
                      "data": d + timedelta(days=random.randint(0, 9)), "descricao": desc, "forma_pagamento": forma,
                      "numero_nf": str(random.randint(10000, 99999)) if random.random() > .2 else "",
                      "parcelas": 2 if forma == "boleto" and random.random() > .5 else 1}
                if kw["data"] > hoje:
                    continue
                if un:
                    kw.update(quantidade=D(random.randint(*faixa_q)), unidade=un,
                              valor_unitario=D(random.randint(*faixa_p)), valor=None)
                else:
                    kw["valor"] = D(random.randint(*faixa_p))
                lancar(**kw)
            for _ in range(3):
                dia = d + timedelta(days=random.randint(0, 12))
                if dia <= hoje:
                    litros = D(random.randint(40, 180))
                    lancar(categoria=cat[7], subcategoria=sub(7, random.choice(["Diesel", "Gasolina"])), fornecedor=lojas["combustível"],
                           data=dia, quantidade=litros, unidade="L", valor_unitario=D("6.19"), valor=None,
                           descricao=random.choice(["Gerador", "Caminhão", "Saveiro"]), forma_pagamento="debito")
            for _ in range(2):
                dia = d + timedelta(days=random.randint(0, 12))
                if dia <= hoje:
                    lancar(categoria=cat[6], subcategoria=sub(6, "Marmitas"), fornecedor=lojas["refeição"], data=dia,
                           quantidade=D(random.randint(40, 90)), unidade="un", valor_unitario=D("21"), valor=None,
                           descricao="Marmitas da semana")
            dia = d + timedelta(days=5)
            if dia <= hoje:
                lancar(categoria=cat[5], fornecedor=lojas["refeição"], data=dia, valor=D(random.randint(90, 380)),
                       descricao="Almoço dos sócios", forma_pagamento="debito")
                lancar(categoria=cat[8], subcategoria=sub(8, random.choice(["Plotagem / impressão", "Uniforme / EPI", "Energia / água"])),
                       fornecedor=lojas["impressão"], data=dia, valor=D(random.randint(150, 1600)), descricao="Despesa da obra")
            d += timedelta(days=14)

        # serviços: terraplanagem no começo e empreita de intertravado por m²
        for i, valor in enumerate((55000, 62000, 48000)):
            lancar(categoria=cat[2], subcategoria=sub(2, "Terraplanagem"), fornecedor=lojas["terraplanagem"],
                   data=inicio + timedelta(days=10 + 12 * i), valor=D(valor), descricao=f"Terraplanagem — {i + 2}ª medição",
                   nf_emitida=True, arquivo_nf="demo/nf.pdf")
        emp = Empreita(obra=obra, descricao="Assentamento de piso intertravado", fornecedor=lojas["intertravado"],
                       unidade="m²", quantidade_prevista=D("9000"), preco_unitario=D("16"), retencao_pct=D("10"),
                       data_inicio=inicio + timedelta(days=80))
        regras.preparar_empreita(emp)
        emp.save()
        for i, m2 in enumerate((1800, 1650, 2100)):
            dia = inicio + timedelta(days=95 + 14 * i)
            if dia <= hoje:
                lancar(categoria=cat[2], subcategoria=sub(2, "Pavimentação"), empreita=emp, fornecedor=emp.fornecedor,
                       data=dia, quantidade=D(m2), unidade="m²", valor=None, descricao=f"Medição {i + 1} — {m2} m²",
                       nf_emitida=True)

        # locações mensais (geram as contas sozinhas) e avulsas
        for desc, valor, dia in (("Contêiner escritório e almoxarifado", "1650", 15), ("Contêiner banheiro", "1250", 10),
                                 ("Gerador 80 kVA", "4200", 5)):
            loc = LocacaoRecorrente.objects.create(
                obra=obra, fornecedor=lojas["locação" if "Gerador" in desc else "contêiner"],
                subcategoria=sub(4, "Gerador" if "Gerador" in desc else "Contêiner"), descricao=desc,
                inicio=inicio + timedelta(days=12), dia_vencimento=dia, valor_mensal=D(valor), forma_pagamento="boleto")
            regras.gerar_contas_de_locacao(loc)
            for c in loc.contas.filter(vencimento__lt=hoje - timedelta(days=3)):
                regras.pagar_conta(c, c.vencimento, caixa)
        for i in range(4):
            dia = inicio + timedelta(days=20 + 30 * i)
            if dia <= hoje:
                lancar(categoria=cat[4], subcategoria=sub(4, random.choice(["Rolo compactador", "Munck / guindaste", "Caçamba"])),
                       fornecedor=lojas["locação"], data=dia, valor=D(random.randint(450, 3200)), descricao="Locação avulsa")

        # pagamento em duplicidade e o estorno (o caso que a planilha não pegava)
        dup = lancar(categoria=cat[2], subcategoria=sub(2, "Terraplanagem"), fornecedor=lojas["terraplanagem"],
                     data=inicio + timedelta(days=36), valor=D("48000"), descricao="Pago em duplicidade",
                     comprovante="demo/comprovante.pdf")
        lancar(categoria=cat[11], fornecedor=lojas["terraplanagem"], data=inicio + timedelta(days=38), valor=D("48000"),
               estorno_de=dup, descricao="Estorno do pagamento em duplicidade")

        # medições: entrada paga, 1ª paga, 2ª emitida e atrasada
        for desc, pct, emissao, pago in (("Entrada", "10", 5, 15), ("Medição 01", "20", 70, 95), ("Medição 02", "15", 125, None)):
            m = Medicao(obra=obra, descricao=desc, percentual=D(pct), valor=None, retencao_pct=D("3"),
                        numero_nf=str(random.randint(100, 999)), data_emissao=inicio + timedelta(days=emissao),
                        data_pagamento=(inicio + timedelta(days=pago)) if pago else None)
            regras.preparar_medicao(m)
            if m.data_emissao <= hoje:
                m.save()
                regras.sincronizar_imposto(m)
        # algumas contas pagas, outras vencidas
        for c in ContaAPagar.objects.filter(obra=obra, lancamento__isnull=False, vencimento__lt=hoje - timedelta(days=10)):
            if random.random() > .15:
                regras.pagar_conta(c, c.vencimento, caixa)
        self.stdout.write(self.style.SUCCESS(
            f"Obra de demonstração criada: {obra.lancamentos.count()} lançamentos, "
            f"{ContaAPagar.objects.filter(obra=obra).count()} contas. Tudo marcado com {MARCA}."))

    def apagar(self):
        obras = Obra.objects.filter(nome__startswith=MARCA)
        for o in obras:
            ContaAPagar.objects.filter(obra=o).delete()
            Lancamento.objects.filter(obra=o, estorno_de__isnull=False).delete()
            o.lancamentos.all().delete()
            o.locacoes.all().delete()
            o.empreitas.all().delete()
            o.delete()
        Prestador.objects.filter(nome__startswith=MARCA).delete()
        Fornecedor.objects.filter(nome__startswith=MARCA).delete()
        Responsavel.objects.filter(nome__startswith=MARCA).delete()
        self.stdout.write(self.style.SUCCESS("Dados de demonstração apagados."))
