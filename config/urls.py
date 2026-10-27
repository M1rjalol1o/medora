from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.search.urls")),
    path("api/reservations/", include("apps.reservations.urls")),
    path("api/panel/", include("apps.panel.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/", include("apps.delivery.urls")),
    path("api/", include("apps.prescriptions.urls")),
    path("api/admin/", include("apps.adminpanel.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

# Mobil ilova frontendini shu server o'zi beradi (SERVE_FRONTEND=1):
# http://127.0.0.1:8000/  -> frontend/index.html
# Telefon ilovasida (Capacitor) frontend ilova ichida bo'ladi, server faqat API beradi.
urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
if settings.SERVE_FRONTEND:
    urlpatterns += [
        path("", serve, {"path": "index.html", "document_root": settings.FRONTEND_DIR}),
        re_path(r"^(?P<path>(css|js|icons|vendor)/.*|manifest\.webmanifest|sw\.js)$", serve,
                {"document_root": settings.FRONTEND_DIR}),
    ]
