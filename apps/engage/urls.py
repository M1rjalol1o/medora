from django.urls import path

from . import views

urlpatterns = [
    path("home/", views.home),
    path("watches/", views.watches),
    path("watches/<int:pk>/", views.watch_detail),
    path("notifications/", views.notifications),
    path("notifications/read/", views.notifications_read),
]
