from django.urls import path

from . import views

urlpatterns = [
    path("prescriptions/", views.prescriptions),
    path("prescriptions/<int:pk>/", views.prescription_detail),
    path("prescriptions/<int:pk>/confirm/", views.prescription_confirm),
    path("courses/", views.courses),
    path("courses/<int:pk>/", views.course_detail),
    path("courses/<int:pk>/log/", views.course_log),
]
