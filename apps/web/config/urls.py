from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("gestione/", admin.site.urls),
    path("amministrazione/", include("amministrazione.urls")),
    path("moderazione/", include("moderazione.urls")),
    path("", include("portale.urls")),
]
