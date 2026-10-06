from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("segnalazioni/nuova/", views.nuova, name="nuova"),
    path("segnalazioni/<int:pk>/", views.dettaglio, name="dettaglio"),
    path("segnalazioni/<int:pk>/sostieni/", views.sostieni, name="sostieni"),
    path("segnalazioni/<int:pk>/commenta/", views.commenta, name="commenta"),
    path("segnalazioni/<int:pk>/commenti/<int:cid>/elimina/", views.elimina_commento, name="elimina_commento"),
    path("api/segnalazioni.geojson", views.geojson, name="geojson"),
    path("api/suggerisci-categorie/", views.suggerisci_categorie, name="suggerisci_categorie"),
    path("api/quartiere/", views.quartiere_da_posizione, name="quartiere_da_posizione"),
    path("accedi/", views.accedi, name="accedi"),
    path("accedi/spid/", views.spid_simulato, name="spid"),
    path("esci/", views.esci, name="esci"),
    path("registrati/", views.registrati, name="registrati"),
    path("profilo/", views.profilo, name="profilo"),
    path("notifiche/", views.notifiche, name="notifiche"),
    path("statistiche/", views.statistiche, name="statistiche"),
    path("media/<path:path>", views.media_file, name="media"),
]
