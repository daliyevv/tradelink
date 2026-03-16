"""
Example ViewSet implementation using TradeLink DRF configuration.

This demonstrates best practices for creating ViewSets with proper
authentication, permissions, response formatting, and exception handling.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from utils.responses import CombinedResponseMixin
from utils.permissions import IsManufacturer, IsOwnerOrReadOnly


# ===========================
# Example: Product ViewSet
# ===========================

class ExampleProductViewSet(CombinedResponseMixin, viewsets.ModelViewSet):
    """
    Example ViewSet for Product management.
    
    Features:
    - Automatic response wrapping (StandardResponseMixin)
    - Custom action response handling (ActionResponseMixin)
    - Role-based access control
    - Filtering, searching, and ordering
    - Proper exception handling
    
    Responses automatically wrapped in:
    {
        "success": true,
        "data": {...},
        "message": "Muvaffaqiyatli olingan"
    }
    """
    
    # Queryset and serializer (must be defined in actual implementation)
    # queryset = Product.objects.all()
    # serializer_class = ProductSerializer
    
    # Permissions
    permission_classes = [IsAuthenticated, IsManufacturer]
    
    # Filtering and Search
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'manufacturer', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'price', 'name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        - Manufacturers see only their products
        - Admins see all products
        """
        user = self.request.user
        queryset = self.queryset
        
        if user.role == 'manufacturer':
            return queryset.filter(manufacturer=user)
        return queryset
    
    # ===========================
    # Standard CRUD Operations (Automatically Wrapped)
    # ===========================
    
    # GET /api/v1/products/
    # Response: {"success": true, "data": {...}, "message": "Muvaffaqiyatli olingan"}
    
    # POST /api/v1/products/
    # Response: {"success": true, "data": {...}, "message": "Muvaffaqiyatli yaratildi"}
    
    # GET /api/v1/products/{id}/
    # Response: {"success": true, "data": {...}, "message": "Muvaffaqiyatli olingan"}
    
    # PATCH /api/v1/products/{id}/
    # Response: {"success": true, "data": {...}, "message": "Muvaffaqiyatli yangilandi"}
    
    # DELETE /api/v1/products/{id}/
    # Response: {"success": true, "data": null, "message": "Muvaffaqiyatli o'chirildi"}
    
    # ===========================
    # Custom Actions
    # ===========================
    
    @action(detail=False, methods=['get'])
    def my_products(self, request):
        """
        Get only the current manufacturer's products.
        
        GET /api/v1/products/my_products/
        
        Response wrapped automatically:
        {
            "success": true,
            "data": [...],
            "message": "Muvaffaqiyatli olingan"
        }
        """
        queryset = self.get_queryset().filter(manufacturer=request.user)
        serializer = self.get_serializer(queryset, many=True)
        
        # Automatically wrapped by mixin
        return self.action_success(
            data=serializer.data,
            message='Sizning mahsulotlaringiz'
        )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activate a product.
        
        POST /api/v1/products/{id}/activate/
        
        Response:
        {
            "success": true,
            "data": {...},
            "message": "Muvaffaqiyatli faollashtirildi"
        }
        """
        product = self.get_object()
        product.is_active = True
        product.save()
        serializer = self.get_serializer(product)
        
        return self.action_success(
            data=serializer.data,
            message='Mahsulot faollashtirildi'
        )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Deactivate a product.
        
        POST /api/v1/products/{id}/deactivate/
        
        Response:
        {
            "success": true,
            "data": {...},
            "message": "Muvaffaqiyatli nofaol qilindi"
        }
        """
        product = self.get_object()
        product.is_active = False
        product.save()
        serializer = self.get_serializer(product)
        
        return self.action_success(
            data=serializer.data,
            message='Mahsulot nofaol qilindi'
        )
    
    @action(detail=False, methods=['post'])
    def bulk_activate(self, request):
        """
        Activate multiple products at once.
        
        POST /api/v1/products/bulk_activate/
        Body: {"product_ids": ["id1", "id2", "id3"]}
        
        Response:
        {
            "success": true,
            "data": {
                "activated_count": 3
            },
            "message": "3 ta mahsulot faollashtirildi"
        }
        """
        product_ids = request.data.get('product_ids', [])
        updated = self.queryset.filter(
            id__in=product_ids,
            manufacturer=request.user
        ).update(is_active=True)
        
        return self.action_success(
            data={'activated_count': updated},
            message=f'{updated} ta mahsulot faollashtirildi'
        )


# ===========================
# Example Usage in urls.py
# ===========================

"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.products.views import ExampleProductViewSet

router = DefaultRouter()
router.register(r'products', ExampleProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
]

This generates these endpoints:
- GET    /api/v1/products/                    (list)
- POST   /api/v1/products/                    (create)
- GET    /api/v1/products/{id}/               (retrieve)
- PATCH  /api/v1/products/{id}/               (partial_update)
- DELETE /api/v1/products/{id}/               (destroy)
- GET    /api/v1/products/my_products/        (custom list action)
- POST   /api/v1/products/{id}/activate/      (custom detail action)
- POST   /api/v1/products/{id}/deactivate/    (custom detail action)
- POST   /api/v1/products/bulk_activate/      (custom non-detail action)
"""


# ===========================
# Exception Handling Examples
# ===========================

"""
These errors are automatically handled by custom_exception_handler:

1. Validation Error (400):
   Request: {"name": "", "price": "abc"}
   Response:
   {
       "success": false,
       "message": "Validatsiya xatosi",
       "errors": {
           "name": ["Bu maydon majburiydir."],
           "price": ["Raqam bo'lishi kerak."]
       }
   }

2. Not Found (404):
   Request: GET /api/v1/products/nonexistent-id/
   Response:
   {
       "success": false,
       "message": "Resurs topilmadi",
       "errors": {}
   }

3. Permission Denied (403):
   Request: GET /api/v1/products/ (without manufacturer role)
   Response:
   {
       "success": false,
       "message": "Bu amalga ruxsat yo'q",
       "errors": {}
   }

4. Authentication Required (401):
   Request: GET /api/v1/products/ (without token)
   Response:
   {
       "success": false,
       "message": "Autentifikatsiya talab qilinadi",
       "errors": {}
   }

5. Rate Limit Exceeded (429):
   Response:
   {
       "success": false,
       "message": "Juda ko'p so'rovlar. Iltimos, biroz kuting",
       "errors": {}
   }

All handled automatically without needing try-except blocks!
"""
