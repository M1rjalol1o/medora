from django.urls import path

from . import views

urlpatterns = [
    path("medicines/", views.medicine_search, name="medicine-search"),
    path("medicines/<int:medicine_id>/offers/", views.medicine_offers, name="medicine-offers"),
    path("basket/", views.basket_search, name="basket-search"),
]
