from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permissions import IsManufacturer, IsOwner
from utils.responses import success_response, error_response
from .models import Category, Product, ProductImage
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductImageSerializer,
    ProductImageUploadSerializer,
)
from .filters import ProductFilter


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing product categories with hierarchical structure.
    GET /api/v1/categories/ — List all active categories with children (cached for 1 hour)
    GET /api/v1/categories/{id}/ — Retrieve single category
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer
    filterset_fields = ['parent']
    ordering = ['order', 'name']

    def get_queryset(self):
        """Build optimized category queryset with children prefetch."""
        queryset = Category.objects.filter(is_active=True).prefetch_related(
            Prefetch('children', queryset=Category.objects.filter(is_active=True).order_by('order'))
        ).order_by('order', 'name')
        return queryset

    def list(self, request, *args, **kwargs):
        """
        List categories with caching.
        Cache key: 'category_tree' — expires in 1 hour (3600 seconds)
        """
        # Try to get from cache
        cached_data = cache.get('category_tree')
        if cached_data is not None:
            return success_response(
                data=cached_data,
                message='Kategoriyalar ro\'yxati',
                status_code=status.HTTP_200_OK
            )

        # Fetch from database
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # Cache for 1 hour (3600 seconds)
        cache.set('category_tree', data, 3600)

        return success_response(
            data=data,
            message='Kategoriyalar ro\'yxati',
            status_code=status.HTTP_200_OK
        )


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for product management with filtering, searching, and image uploads.
    
    Endpoints:
    - GET /api/v1/products/ — List all active products (all authenticated users)
    - POST /api/v1/products/ — Create product (manufacturers only)
    - GET /api/v1/products/{id}/ — Retrieve product details
    - PATCH /api/v1/products/{id}/ — Update product (manufacturer + owner)
    - DELETE /api/v1/products/{id}/ — Soft delete product (set is_active=False)
    - POST /api/v1/products/{id}/images/ — Upload images
    - DELETE /api/v1/products/{id}/images/{image_id}/ — Delete image
    
    RBAC Test Matrix:
    Action         | Unauthenticated | Dealer | Manufacturer | Other Manufacturer
    -----------    | --------------- | ------ | ------------ | ------------------
    GET list       | 401             | 200    | 200          | 200
    POST create    | 401             | 403    | 201          | 201
    GET retrieve   | 401             | 200    | 200          | 200
    PATCH update   | 401             | 403    | 200*         | 403
    DELETE destroy | 401             | 403    | 200*         | 403
    POST images    | 401             | 403    | 201*         | 403
    
    * Only the product owner (manufacturer) can modify/delete
    """

    queryset = Product.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Optimize queries with select_related and prefetch_related.
        """
        if self.action == 'retrieve':
            return self.queryset.select_related(
                'manufacturer',
                'category'
            ).prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.order_by('order'))
            )
        else:
            return self.queryset.select_related(
                'manufacturer',
                'category'
            ).prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
            )

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'list':
            return ProductListSerializer
        elif self.action == 'create' or self.action == 'update' or self.action == 'partial_update':
            return ProductCreateUpdateSerializer
        elif self.action == 'images_upload':
            return ProductImageUploadSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.action in ['create']:
            return [IsAuthenticated(), IsManufacturer()]
        elif self.action in ['update', 'partial_update', 'destroy', 'images_upload', 'images_delete']:
            return [IsAuthenticated(), IsManufacturer(), IsOwner()]
        return [IsAuthenticated()]

    @extend_schema(
        summary='Create new product',
        tags=['products'],
        responses={
            201: OpenApiResponse(description='Product created successfully'),
            400: OpenApiResponse(description='Invalid product data'),
            403: OpenApiResponse(description='You must be a manufacturer to create products'),
        },
    )
    def create(self, request, *args, **kwargs):
        """Create product as current user (manufacturer)."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Mahsulot yaratishda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        product = serializer.save()
        output_serializer = ProductDetailSerializer(product, context={'request': request})
        
        return success_response(
            data=output_serializer.data,
            message='Mahsulot muvaffaqiyatli yaratildi',
            status_code=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary='Update product details',
        tags=['products'],
        responses={
            200: OpenApiResponse(description='Product updated successfully'),
            400: OpenApiResponse(description='Invalid product data'),
            403: OpenApiResponse(description='You can only update your own products'),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        """Update product (manufacturer only)."""
        product = self.get_object()
        self.check_object_permissions(request, product)

        serializer = self.get_serializer(product, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Mahsulot yangilanishida xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        product = serializer.save()
        output_serializer = ProductDetailSerializer(product, context={'request': request})
        
        return success_response(
            data=output_serializer.data,
            message='Mahsulot muvaffaqiyatli yangilandi',
            status_code=status.HTTP_200_OK
        )

    def list(self, request, *args, **kwargs):
        """List products with filtering and search."""
        response = super().list(request, *args, **kwargs)
        if isinstance(response.data, list):
            return success_response(
                data=response.data,
                message='Mahsulotlar ro\'yxati',
                status_code=status.HTTP_200_OK
            )
        return response

    def retrieve(self, request, *args, **kwargs):
        """Retrieve product details."""
        product = self.get_object()
        serializer = self.get_serializer(product)
        
        return success_response(
            data=serializer.data,
            message='Mahsulot tafsilotlari',
            status_code=status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        """Soft delete product (set is_active=False)."""
        product = self.get_object()
        self.check_object_permissions(request, product)

        product.is_active = False
        product.save()

        return success_response(
            message='Mahsulot o\'chirildi',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='images')
    def images_upload(self, request, pk=None):
        """
        Upload image for product.
        POST /api/v1/products/{id}/images/
        
        Request:
            multipart/form-data:
            - image: file
            - is_primary: boolean (optional)
            - order: integer (optional)
        """
        product = self.get_object()
        self.check_object_permissions(request, product)

        serializer = self.get_serializer(
            data=request.data,
            context={'product_id': product.id, 'request': request}
        )
        
        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Rasm yuklashda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        image = serializer.save(product=product)
        output_serializer = ProductImageSerializer(image)
        
        return success_response(
            data=output_serializer.data,
            message='Rasm muvaffaqiyatli yuklandi',
            status_code=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path='images/(?P<image_id>[^/.]+)')
    def images_delete(self, request, pk=None, image_id=None):
        """
        Delete product image.
        DELETE /api/v1/products/{id}/images/{image_id}/
        """
        product = self.get_object()
        self.check_object_permissions(request, product)

        image = get_object_or_404(ProductImage, id=image_id, product=product)
        image.delete()

        return success_response(
            message='Rasm o\'chirildi',
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def by_manufacturer(self, request):
        """
        Get all products by current manufacturer.
        GET /api/v1/products/by_manufacturer/
        """
        if request.user.role != 'manufacturer':
            return error_response(
                message='Faqat ishlab chiqaruvchilar bu amaldan foydalana oladi',
                status_code=status.HTTP_403_FORBIDDEN
            )

        products = Product.objects.filter(
            manufacturer=request.user,
            is_active=True
        ).select_related('category').order_by('-created_at')

        serializer = ProductListSerializer(products, many=True, context={'request': request})
        
        return success_response(
            data=serializer.data,
            message='Siz yaratgan mahsulotlar',
            status_code=status.HTTP_200_OK
        )
