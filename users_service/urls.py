from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

from users_service.views import CreateUserView, ManageUserView

urlpatterns = [
    path("", CreateUserView.as_view(), name="register"),
    path("me/", ManageUserView.as_view(), name="me"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("token-refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token-verify/", TokenVerifyView.as_view(), name="token_verify"),
]

app_name="users_service"
