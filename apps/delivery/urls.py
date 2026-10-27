from django.urls import path

from . import views

urlpatterns = [
    path("driver/me/", views.driver_me),
    path("driver/online/", views.driver_online),
    path("driver/location/", views.driver_location),
    path("driver/available/", views.driver_available),
    path("driver/current/", views.driver_current),
    path("driver/history/", views.driver_history),
    path("driver/deliveries/<int:pk>/accept/", views.driver_accept),
    path("driver/stops/<int:pk>/done/", views.driver_stop_done),
    path("park/dashboard/", views.park_dashboard),
    path("park/drivers/", views.park_drivers),
    path("park/deliveries/", views.park_deliveries),
    path("park/deliveries/<int:pk>/assign/", views.park_assign),
]
