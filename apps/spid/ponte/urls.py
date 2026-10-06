from django.urls import path

from . import views

urlpatterns = [
    path("avvia/", views.avvia, name="ponte_avvia"),
    path("consegna/", views.consegna, name="ponte_consegna"),
    path("salute/", views.salute, name="ponte_salute"),
]
