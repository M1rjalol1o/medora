from django.urls import path

from . import views

urlpatterns = [
    path("cards/", views.cards),
    path("cards/verify/", views.verify_card),
    path("cards/<int:pk>/", views.delete_card),
    path("orders/<int:pk>/pay/", views.pay_order),
]
