from django.urls import path

from . import views

urlpatterns = [
    path("stats/", views.stats),
    path("users/", views.users),
    path("users/<int:pk>/toggle/", views.user_toggle),
    path("pharmacies/", views.pharmacies),
    path("pharmacies/<int:pk>/toggle/", views.pharmacy_toggle),
    path("orders/", views.orders),
    path("taxi/", views.taxi),
    path("payments/", views.payments),
    path("reservations/", views.reservations),
]
