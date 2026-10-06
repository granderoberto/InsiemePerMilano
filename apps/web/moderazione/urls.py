from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="moderazione"),
    path("segnalazioni/<int:pk>/", views.segnalazione, name="moderazione_segnalazione"),
    path("segnalazioni/<int:pk>/<str:azione>/", views.azione_segnalazione, name="azione_segnalazione"),
    path("commenti/<int:cid>/<str:azione>/", views.azione_commento, name="azione_commento"),
    path("verifiche/<int:vid>/decidi/", views.decidi_verifica, name="decidi_verifica"),
]
