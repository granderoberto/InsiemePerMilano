from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

from spid_cie_oidc.entity.urls import urlpatterns as entity_urlpatterns
from spid_cie_oidc.entity.views import entity_configuration, resolve_entity_statement
from spid_cie_oidc.relying_party.urls import urlpatterns as rp_urlpatterns

urlpatterns = [
    path(settings.ADMIN_PATH, admin.site.urls),
    path("ponte/", include("ponte.urls")),
]
urlpatterns += entity_urlpatterns
urlpatterns += rp_urlpatterns
urlpatterns += [
    path("oidc/rp/.well-known/openid-federation", entity_configuration, name="oidc_rp_entity_configuration"),
    path("oidc/rp/resolve", resolve_entity_statement, name="oidc_rp_resolve"),
]
if settings.DEBUG:
    from django.urls import re_path
    urlpatterns.append(re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}))
