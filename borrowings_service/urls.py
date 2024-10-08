from rest_framework import routers

from borrowings_service.views import BorrowingsViewSet

router = routers.DefaultRouter()
router.register("", BorrowingsViewSet)

urlpatterns = router.urls

app_name = "borrowings_service"
