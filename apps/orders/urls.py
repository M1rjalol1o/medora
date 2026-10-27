from django.urls import path

from . import views

urlpatterns = [
    path("quote/", views.quote),
    path("", views.orders),
    path("<int:pk>/", views.order_detail),
    path("<int:pk>/cancel/", views.order_cancel),
]
