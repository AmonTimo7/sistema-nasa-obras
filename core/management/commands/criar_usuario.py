import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.models import Perfil


class Command(BaseCommand):
    help = (
        "Cria um usuário com senha provisória. Na primeira entrada o sistema "
        "exige a troca antes de abrir qualquer tela."
    )

    def add_arguments(self, parser):
        parser.add_argument("login")
        parser.add_argument("--papel", choices=[p for p, _ in Perfil.PAPEIS], default=Perfil.OPERACAO)
        parser.add_argument("--nome", default="")
        parser.add_argument("--senha", help="Senha provisória. Sem ela, uma aleatória é gerada e mostrada uma vez.")

    def handle(self, *args, **opts):
        User = get_user_model()
        if User.objects.filter(username=opts["login"]).exists():
            raise CommandError(f"Já existe o usuário {opts['login']}.")
        senha = opts["senha"] or secrets.token_urlsafe(9)
        user = User.objects.create_user(
            username=opts["login"],
            password=senha,
            first_name=opts["nome"],
            is_staff=opts["papel"] == Perfil.SOCIO,
        )
        perfil = user.perfil
        perfil.papel = opts["papel"]
        perfil.precisa_trocar_senha = True
        perfil.save()
        self.stdout.write(self.style.SUCCESS(f"Usuário {user.username} criado ({perfil.get_papel_display()})."))
        if not opts["senha"]:
            self.stdout.write(f"Senha provisória (vale só até a primeira entrada): {senha}")
