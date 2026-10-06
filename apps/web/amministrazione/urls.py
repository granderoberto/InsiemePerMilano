from django.urls import path

from . import views

urlpatterns = [
    path("", views.indice, name="amministrazione"),
    path("utenti/", views.elenco_utenti, name="amm_utenti"),
    path("utenti/<int:pk>/", views.scheda_utente, name="amm_utente"),
    path("utenti/<int:pk>/<str:azione>/", views.azione_utente, name="amm_azione_utente"),
    path("registro/", views.registro, name="amm_registro"),
    path("statistiche/", views.statistiche_complete, name="amm_statistiche"),
    path("statistiche/<str:nome>.csv", views.esporta_csv, name="amm_csv"),
    path("categorie/", views.categorie, name="amm_categorie"),
    path("normative/", views.documenti, name="amm_documenti"),
]
