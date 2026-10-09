from datetime import date, timedelta
from decimal import Decimal as D

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from compras.models import Fornecedor
from core.models import Perfil
from core.texto import dinheiro
from juridico.models import Prestador

from . import consultas, regras
from .models import Categoria, ContaAPagar, Lancamento, LocacaoRecorrente, Medicao, Obra


def cat(codigo):
    return Categoria.objects.get(codigo=codigo)


class Base(TestCase):
    def setUp(self):
        self.obra = Obra.objects.create(nome="Obra Teste", valor_contrato=D("1000000"), data_inicio=date(2026, 5, 1),
                                        data_termino=date(2026, 12, 31), aliquota_imposto=D("6"),
                                        retencao_padrao=D("5"))
        self.pedreiro = Prestador.objects.create(nome="João da Silva", funcao="Pedreiro", valor_diaria=D("220"))
        self.loja = Fornecedor.objects.create(nome="Madeireira Boa")

    def lancar(self, **kw):
        l = Lancamento(obra=self.obra, **kw)
        erros = regras.preparar_lancamento(l)
        self.assertEqual(erros, [], erros)
        l.save()
        regras.sincronizar_contas(l)
        return l


class Dinheiro(TestCase):
    def test_formatos_aceitos(self):
        self.assertEqual(dinheiro("1.234,56"), D("1234.56"))
        self.assertEqual(dinheiro("R$ 880,00"), D("880.00"))
        self.assertEqual(dinheiro("1234.5"), D("1234.50"))
        self.assertEqual(dinheiro("1.089"), D("1089.00"))
        self.assertEqual(dinheiro("3,000,00"), D("3000.00"))

    def test_recusa_o_que_nao_da_certeza(self):
        self.assertIsNone(dinheiro("vinte mil"))
        self.assertIsNone(dinheiro("12,3456"))

    def test_parcelas_fecham_no_centavo(self):
        partes = regras.dividir(D("100"), 3)
        self.assertEqual(partes, [D("33.33"), D("33.33"), D("33.34")])
        self.assertEqual(sum(partes), D("100.00"))


class MaoDeObra(Base):
    def test_diarias_calculam_o_valor(self):
        l = self.lancar(categoria=cat(1), prestador=self.pedreiro, data=date(2026, 6, 5), tipo_mao_de_obra="diarias",
                        diarias=D("4"), valor_diaria=D("0"), valor=None)
        self.assertEqual(l.valor_diaria, D("220"))  # veio do cadastro
        self.assertEqual(l.valor, D("880.00"))
        self.assertEqual(l.competencia, date(2026, 6, 1))

    def test_vale_e_descontado_e_nao_pode_passar_do_saldo(self):
        self.lancar(categoria=cat(1), prestador=self.pedreiro, data=date(2026, 6, 1), tipo_mao_de_obra="adiantamento",
                    valor=D("140"))
        self.assertEqual(regras.saldo_de_vales(self.pedreiro, self.obra), D("140"))
        l = self.lancar(categoria=cat(1), prestador=self.pedreiro, data=date(2026, 6, 5), tipo_mao_de_obra="diarias",
                        diarias=D("4"), valor_diaria=D("220"), desconto=D("140"), valor=None)
        self.assertEqual(l.valor, D("740.00"))
        self.assertEqual(regras.saldo_de_vales(self.pedreiro, self.obra), D("0"))
        demais = Lancamento(obra=self.obra, categoria=cat(1), prestador=self.pedreiro, data=date(2026, 6, 12),
                            tipo_mao_de_obra="diarias", diarias=D("1"), valor_diaria=D("220"), desconto=D("50"))
        self.assertTrue(any("vales em aberto" in e for e in regras.preparar_lancamento(demais)))

    def test_sem_prestador_nao_passa(self):
        l = Lancamento(obra=self.obra, categoria=cat(1), data=date(2026, 6, 5), diarias=D("1"), valor_diaria=D("100"))
        self.assertIn("Mão de obra precisa do prestador.", regras.preparar_lancamento(l))


class ComprasAPrazo(Base):
    def test_boleto_em_duas_vezes_vira_duas_contas(self):
        l = self.lancar(categoria=cat(3), fornecedor=self.loja, data=date(2026, 6, 10), valor=D("4132.01"),
                        forma_pagamento="boleto", parcelas=2)
        contas = list(l.contas.order_by("vencimento"))
        self.assertEqual(len(contas), 2)
        self.assertEqual(sum(c.valor for c in contas), D("4132.01"))
        self.assertEqual(contas[0].vencimento, date(2026, 7, 10))
        self.assertEqual(contas[1].vencimento, date(2026, 8, 10))
        self.assertEqual(regras.status_pagamento(l), "a pagar")
        regras.pagar_conta(contas[0], date(2026, 7, 10))
        self.assertEqual(regras.status_pagamento(l), "parcial")

    def test_parcela_paga_trava_valor(self):
        l = self.lancar(categoria=cat(3), fornecedor=self.loja, data=date(2026, 6, 10), valor=D("1000"),
                        forma_pagamento="boleto", parcelas=2)
        regras.pagar_conta(l.contas.first(), date(2026, 7, 10))
        l.valor = D("900")
        self.assertTrue(any("parcela paga" in e for e in regras.preparar_lancamento(l)))

    def test_pix_nao_gera_conta(self):
        l = self.lancar(categoria=cat(3), fornecedor=self.loja, data=date(2026, 6, 10), valor=D("500"))
        self.assertEqual(l.contas.count(), 0)

    def test_quantidade_vezes_preco(self):
        l = self.lancar(categoria=cat(3), fornecedor=self.loja, data=date(2026, 6, 10), quantidade=D("15"),
                        valor_unitario=D("580"), valor=None)
        self.assertEqual(l.valor, D("8700.00"))

    def test_compra_sem_fornecedor_nao_passa(self):
        l = Lancamento(obra=self.obra, categoria=cat(3), data=date(2026, 6, 10), valor=D("10"))
        self.assertIn("Informe o fornecedor.", regras.preparar_lancamento(l))


class Estorno(Base):
    def test_estorno_fica_negativo_e_abate_o_gasto(self):
        pago = self.lancar(categoria=cat(2), fornecedor=self.loja, data=date(2026, 7, 2), valor=D("37500"))
        self.lancar(categoria=cat(11), fornecedor=self.loja, data=date(2026, 7, 2), valor=D("37500"), estorno_de=pago)
        self.assertEqual(consultas.resumo_obra(self.obra)["gasto"], D("0.00"))

    def test_pagamento_repetido_e_avisado(self):
        self.lancar(categoria=cat(2), fornecedor=self.loja, data=date(2026, 6, 30), valor=D("37500"))
        repetido = Lancamento(obra=self.obra, categoria=cat(2), fornecedor=self.loja, data=date(2026, 7, 2),
                              valor=D("37500"))
        regras.preparar_lancamento(repetido)
        self.assertTrue(any("repetido" in a for a in regras.avisos_lancamento(repetido)))


class MedicoesEImposto(Base):
    def test_percentual_calcula_valor_retencao_e_imposto(self):
        m = Medicao(obra=self.obra, descricao="Entrada", percentual=D("10"), valor=None, retencao_pct=D("5"),
                    data_emissao=date(2026, 6, 16))
        self.assertEqual(regras.preparar_medicao(m), [])
        m.save()
        imposto = regras.sincronizar_imposto(m)
        self.assertEqual(m.valor, D("100000.00"))
        self.assertEqual(m.valor_retencao, D("5000.00"))
        self.assertEqual(m.valor_liquido, D("95000.00"))
        self.assertEqual(imposto.valor, D("6000.00"))
        self.assertEqual(imposto.categoria.codigo, Categoria.IMPOSTOS)
        m.data_emissao = None
        m.save()
        regras.sincronizar_imposto(m)
        self.assertFalse(m.impostos.exists())

    def test_medicoes_nao_passam_do_contrato(self):
        Medicao.objects.create(obra=self.obra, descricao="A", valor=D("900000"))
        m = Medicao(obra=self.obra, descricao="B", valor=D("200000"))
        self.assertTrue(any("passariam do valor do contrato" in e for e in regras.preparar_medicao(m)))

    def test_atrasada(self):
        m = Medicao(obra=self.obra, descricao="X", valor=D("1"), data_emissao=date(2026, 6, 1),
                    vencimento=date(2026, 7, 1))
        self.assertEqual(m.situacao(date(2026, 7, 2)), "atrasada")


class Locacao(Base):
    def test_gera_uma_conta_por_mes_e_paga_vira_gasto(self):
        loc = LocacaoRecorrente.objects.create(obra=self.obra, fornecedor=self.loja, descricao="Contêiner escritório",
                                               inicio=date(2026, 6, 16), dia_vencimento=21, valor_mensal=D("1800"))
        regras.gerar_contas_de_locacao(loc, ate=date(2026, 8, 31))
        regras.gerar_contas_de_locacao(loc, ate=date(2026, 8, 31))  # de novo: não duplica
        vencs = list(loc.contas.order_by("vencimento").values_list("vencimento", flat=True))
        self.assertEqual(vencs, [date(2026, 6, 21), date(2026, 7, 21), date(2026, 8, 21)])
        conta = loc.contas.first()
        regras.pagar_conta(conta, date(2026, 6, 21))
        self.assertEqual(consultas.resumo_obra(self.obra)["gasto"], D("1800.00"))
        regras.desfazer_pagamento(conta)
        self.assertEqual(consultas.resumo_obra(self.obra)["gasto"], D("0.00"))

    def test_dia_31_em_mes_de_30(self):
        self.assertEqual(regras.somar_meses(date(2026, 1, 31), 1), date(2026, 2, 28))


class Empreitas(Base):
    def test_metragem_retencao_e_saldo(self):
        from .models import Empreita
        e = Empreita(obra=self.obra, descricao="Intertravado", fornecedor=self.loja, unidade="m²",
                     quantidade_prevista=D("10000"), preco_unitario=D("16"), retencao_pct=D("10"))
        self.assertEqual(regras.preparar_empreita(e), [])
        e.save()
        self.assertEqual(e.valor_contratado, D("160000.00"))
        self.lancar(categoria=cat(2), empreita=e, fornecedor=self.loja, data=date(2026, 7, 23), quantidade=D("2000"),
                    valor=None)
        r = regras.resumo_empreita(e)
        self.assertEqual(r["pago"], D("28800.00"))   # 32.000 − 10%
        self.assertEqual(r["retido"], D("3200.00"))
        self.assertEqual(r["saldo"], D("128000.00"))
        self.assertEqual(r["pct_medido"], D("20.0"))


class Permissoes(TestCase):
    def entrar(self, papel):
        u = get_user_model().objects.create_user(f"u_{papel}", password="x-senha-longa-1")
        u.perfil.papel = papel
        u.perfil.precisa_trocar_senha = False
        u.perfil.save()
        self.client.force_login(u)
        Obra.objects.get_or_create(nome="O", defaults={"valor_contrato": D("1")})

    def test_operacao_nao_ve_financeiro(self):
        self.entrar(Perfil.OPERACAO)
        self.assertEqual(self.client.get(reverse("financeiro:painel")).status_code, 403)
        self.assertEqual(self.client.get(reverse("financeiro:checklist")).status_code, 200)

    def test_compras_lanca_material_mas_nao_mao_de_obra(self):
        self.entrar(Perfil.COMPRAS)
        self.assertEqual(self.client.get(reverse("financeiro:lancamento_novo", args=[3])).status_code, 200)
        self.assertEqual(self.client.get(reverse("financeiro:lancamento_novo", args=[1])).status_code, 403)
        self.assertEqual(self.client.get(reverse("financeiro:contas")).status_code, 403)

    def test_senha_provisoria_tranca_tudo(self):
        u = get_user_model().objects.create_user("novo", password="x-senha-longa-1")
        u.perfil.papel = Perfil.SOCIO
        u.perfil.save()
        self.client.force_login(u)
        r = self.client.get(reverse("financeiro:painel"))
        self.assertRedirects(r, reverse("trocar_senha"), fetch_redirect_response=False)

    def test_telas_do_socio_abrem(self):
        self.entrar(Perfil.SOCIO)
        for nome in ("painel", "visao_geral", "lancamentos", "lancamento_escolher", "fechamento", "pendencias",
                     "mao_de_obra", "empreitas", "contas", "contrato", "relatorios", "checklist", "obras",
                     "responsaveis"):
            self.assertEqual(self.client.get(reverse(f"financeiro:{nome}")).status_code, 200, nome)
        for codigo in range(1, 12):
            self.assertEqual(self.client.get(reverse("financeiro:lancamento_novo", args=[codigo])).status_code, 200)


class FormularioDeLancamento(Base):
    def setUp(self):
        super().setUp()
        u = get_user_model().objects.create_superuser("s", password="x-senha-longa-1")
        u.perfil.precisa_trocar_senha = False
        u.perfil.save()
        self.client.force_login(u)
        session = self.client.session
        session["obra_id"] = self.obra.pk
        session.save()

    def test_diarias_pela_tela(self):
        r = self.client.post(reverse("financeiro:lancamento_novo", args=[1]), {
            "data": "2026-06-05", "prestador": self.pedreiro.pk, "tipo_mao_de_obra": "diarias", "diarias": "5",
            "valor_diaria": "220,00", "adicional": "", "desconto": "", "forma_pagamento": "pix", "parcelas": "1",
        })
        self.assertEqual(r.status_code, 302, r.content.decode()[:3000] if r.status_code != 302 else "")
        l = Lancamento.objects.get()
        self.assertEqual(l.valor, D("1100.00"))

    def test_compra_boleto_pela_tela_cria_fornecedor_e_contas(self):
        r = self.client.post(reverse("financeiro:lancamento_novo", args=[3]), {
            "data": "2026-06-10", "fornecedor_nome": "Concreteira Nova", "valor": "13.050,00",
            "forma_pagamento": "boleto", "parcelas": "3", "quantidade": "22,5", "unidade": "m³",
        })
        self.assertEqual(r.status_code, 302)
        l = Lancamento.objects.get()
        self.assertEqual(l.fornecedor.nome, "Concreteira Nova")
        self.assertEqual(ContaAPagar.objects.filter(lancamento=l).count(), 3)
