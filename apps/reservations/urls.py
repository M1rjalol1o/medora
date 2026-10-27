from django.urls import path

from . import views

urlpatterns = [
    path("", views.my_reservations, name="my-reservations"),
    path("<int:pk>/cancel/", views.cancel_reservation, name="reservation-cancel"),
]
