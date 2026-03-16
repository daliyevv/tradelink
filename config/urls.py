"""
TradeLink API URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include([
        # Authentication and Profile endpoints
        path('', include('apps.users.urls')),
        
        # Business endpoints (products, orders, cart, etc.)
        path('products/', include('apps.products.urls')),
        path('orders/', include('apps.orders.urls')),
        path('cart/', include('apps.cart.urls')),
        path('dealers/', include('apps.dealers.urls')),
        path('locations/', include('apps.locations.urls')),
        path('notifications/', include('apps.notifications.urls')),
        path('analytics/', include('apps.analytics.urls')),
    ])),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug Toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
