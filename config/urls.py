from django.urls import path

from scoreboard import views

urlpatterns = [
    path("", views.index),                                  # phone / controller: buttons + board
    path("display/", views.index, {"mode": "display"}),     # laptop / stream: board only
    path("api/state/", views.state_api),
    path("api/images/", views.images_api),
]
