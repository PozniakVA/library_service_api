from django.urls import path, include
from rest_framework import routers

from payments_service import views
from payments_service.views import PaymentsViewSet

router = routers.DefaultRouter()
router.register("payments", PaymentsViewSet, basename="payments")
urlpatterns = [
    path("", include(router.urls)),
    path("webhook/", views.my_webhook_view, name="stripe-webhook"),
    path("successful_page/", views.successful_page, name="successful_page"),
    path("canceled_page/", views.canceled_page, name="canceled_page"),
    path(
        "fine_payment/<int:borrowing_id>/",
        views.fine_payment,
        name="fine_payment"
    ),
    path(
        "renew_payment/<int:borrowing_id>/",
        views.renew_payment,
        name="renew_payment"
    )
]

app_name = "payments_service"
