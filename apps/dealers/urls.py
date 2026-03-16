from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DealerProfileViewSet

app_name = 'dealers'

router = DefaultRouter()
router.register(r'', DealerProfileViewSet, basename='dealer')

urlpatterns = [
    path('', include(router.urls)),
]
