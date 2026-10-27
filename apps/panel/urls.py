from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="panel-dashboard"),
    path("inventory/", views.inventory_list, name="panel-inventory"),
    path("inventory/<int:pk>/", views.inventory_update, name="panel-inventory-update"),
    path("reservations/", views.reservation_list, name="panel-reservations"),
    path("reservations/<int:pk>/<str:action>/", views.reservation_action, name="panel-reservation-action"),
    path("expiring/", views.expiring, name="panel-expiring"),
    path("orders/", views.pharmacy_orders, name="panel-orders"),
    path("orders/<int:pk>/<str:action>/", views.pharmacy_order_action, name="panel-order-action"),
]
