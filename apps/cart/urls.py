from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CartViewSet

app_name = 'cart'

router = DefaultRouter()
router.register('', CartViewSet, basename='cart')

urlpatterns = router.urls
