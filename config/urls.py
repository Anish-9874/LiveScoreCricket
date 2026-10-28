from django.urls import path
from scoreboard import views

urlpatterns = [
    path("", views.index),
]