from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views as core

admin.site.site_header = "Nasa Obras — administração"
admin.site.site_title = "Nasa Obras"

urlpatterns = [
    path("", core.inicio, name="inicio"),
    path("entrar/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("senha/", core.trocar_senha, name="trocar_senha"),
    path("financeiro/", include("financeiro.urls")),
    path("compras/", include("compras.urls")),
    path("juridico/", include("juridico.urls")),
    path("admin/", admin.site.urls),
]
