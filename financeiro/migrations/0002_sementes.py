from django.db import migrations

from financeiro.sementes import CATEGORIAS, CHECKLIST, CONTAS_BANCARIAS, SUBCATEGORIAS


def semear(apps, schema_editor):
    Categoria = apps.get_model("financeiro", "Categoria")
    Subcategoria = apps.get_model("financeiro", "Subcategoria")
    ContaBancaria = apps.get_model("financeiro", "ContaBancaria")
    ModeloChecklist = apps.get_model("financeiro", "ModeloChecklist")
    for codigo, nome, descricao in CATEGORIAS:
        cat, _ = Categoria.objects.update_or_create(codigo=codigo, defaults={"nome": nome, "descricao": descricao})
        for sub, unidade in SUBCATEGORIAS.get(codigo, []):
            Subcategoria.objects.get_or_create(categoria=cat, nome=sub, defaults={"unidade": unidade})
    for nome in CONTAS_BANCARIAS:
        ContaBancaria.objects.get_or_create(nome=nome)
    for grupo, itens in CHECKLIST.items():
        for i, nome in enumerate(itens, 1):
            ModeloChecklist.objects.get_or_create(grupo=grupo, nome=nome, defaults={"ordem": i})


class Migration(migrations.Migration):
    dependencies = [("financeiro", "0001_initial")]
    operations = [migrations.RunPython(semear, migrations.RunPython.noop)]
