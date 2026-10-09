from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Base"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save

        from .models import Perfil

        def criar_perfil(sender, instance, created, **kwargs):
            if created:
                Perfil.objects.get_or_create(
                    usuario=instance,
                    defaults={"papel": Perfil.SOCIO if instance.is_superuser else Perfil.OPERACAO},
                )

        post_save.connect(criar_perfil, sender=get_user_model(), dispatch_uid="core-criar-perfil")
