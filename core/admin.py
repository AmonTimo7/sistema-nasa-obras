from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Perfil, RegistroAuditoria


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False


admin.site.unregister(get_user_model())


@admin.register(get_user_model())
class UsuarioAdmin(UserAdmin):
    inlines = [PerfilInline]


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("quando", "usuario", "acao", "modelo", "descricao")
    list_filter = ("acao", "modelo")
    search_fields = ("descricao",)

    # Auditoria só se lê.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
