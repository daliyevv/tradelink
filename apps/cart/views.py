from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Prefetch

from utils.permissions import IsStoreOwner
from utils.responses import success_response, error_response
from .models import Cart, CartItem
from .permissions import IsCartOwner
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    CartAddItemSerializer,
    CartUpdateItemSerializer,
    SelectDealerSerializer,
)
from apps.products.models import Product, ProductImage
from apps.dealers.models import DealerProfile
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.orders.serializers import OrderDetailSerializer, CheckoutSerializer


class CartViewSet(viewsets.ViewSet):
    """
    ViewSet for shopping cart management.
    
    Endpoints:
    - GET /api/v1/cart/ — Get current cart with items
    - DELETE /api/v1/cart/ — Clear all items from cart
    - POST /api/v1/cart/items/ — Add item to cart
    - PATCH /api/v1/cart/items/{id}/ — Update item quantity
    - DELETE /api/v1/cart/items/{id}/ — Remove item from cart
    - POST /api/v1/cart/select-dealer/ — Select delivery dealer
    """

    permission_classes = [IsAuthenticated]

    def get_cart(self, request):
        """Get or create cart for current user with optimized queries."""
        cart, created = Cart.objects.select_related(
            'owner',
            'dealer',
            'dealer__user'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=CartItem.objects.select_related('product').prefetch_related(
                    Prefetch('product__images', queryset=ProductImage.objects.filter(is_primary=True))
                )
            )
        ).get_or_create(owner=request.user)
        return cart

    def list(self, request):
        """GET /api/v1/cart/ — Retrieve current cart with items (optimized queries)."""
        cart = self.get_cart(request)
        serializer = CartSerializer(cart)
        
        return success_response(
            data=serializer.data,
            message='Savatcha ma\'lumotlari',
            status_code=status.HTTP_200_OK
        )

    def destroy(self, request):
        """DELETE /api/v1/cart/ — Clear all items from cart."""
        cart = self.get_cart(request)
        
        with transaction.atomic():
            item_count = cart.items.count()
            cart.items.all().delete()
            cart.dealer = None
            cart.save()
        
        return success_response(
            message=f'{item_count} ta mahsulot savatdan o\'chirildi',
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='items')
    def add_item(self, request):
        """POST /api/v1/cart/items/ — Add item to cart."""
        serializer = CartAddItemSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Mahsulot qo\'shishda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        product = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        cart = self.get_cart(request)

        # If cart has a dealer selected, verify all products are from same dealer
        if cart.dealer:
            # Get the dealer of this product
            product_dealers = DealerProfile.objects.filter(
                manufacturers=product.manufacturer
            )
            if not product_dealers.filter(id=cart.dealer.id).exists():
                return error_response(
                    errors={'product_id': 'Bu mahsulot tanlangan dillerning assortimentida yo\'q'},
                    message='Mahsulot noto\'g\'ri',
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        try:
            with transaction.atomic():
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={
                        'quantity': quantity,
                        'price_snapshot': product.price
                    }
                )

                if not created:
                    # Product already in cart, update quantity
                    cart_item.quantity += quantity
                    cart_item.save()

            item_serializer = CartItemSerializer(cart_item)
            return success_response(
                data=item_serializer.data,
                message='Mahsulot savatga qo\'shildi',
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Mahsulot qo\'shishda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['patch'], url_path='items/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """PATCH /api/v1/cart/items/{id}/ — Update item quantity."""
        cart = self.get_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        serializer = CartUpdateItemSerializer(
            data=request.data,
            context={'cart_item': cart_item}
        )

        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Miqdorni yangilashda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        quantity = serializer.validated_data['quantity']

        try:
            with transaction.atomic():
                cart_item.quantity = quantity
                cart_item.save()

            item_serializer = CartItemSerializer(cart_item)
            return success_response(
                data=item_serializer.data,
                message='Mahsulot miqdori yangilandi',
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Yangilashda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['delete'], url_path='items/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """DELETE /api/v1/cart/items/{id}/ — Remove item from cart."""
        cart = self.get_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        product_name = cart_item.product.name
        
        try:
            with transaction.atomic():
                cart_item.delete()

            return success_response(
                message=f'{product_name} savatdan o\'chirildi',
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Mahsulot o\'chirishda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], url_path='select-dealer')
    def select_dealer(self, request):
        """POST /api/v1/cart/select-dealer/ — Select delivery dealer."""
        serializer = SelectDealerSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Diller tanlanishda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        dealer = serializer.validated_data['dealer_id']
        cart = self.get_cart(request)

        # Verify all items in cart are from selected dealer's manufacturers
        if cart.items.exists():
            # Get manufacturers of all products in cart
            cart_manufacturers = set(
                cart.items.values_list('product__manufacturer_id', flat=True)
            )
            
            # Get manufacturers this dealer works with
            dealer_manufacturers = set(
                dealer.manufacturers.values_list('id', flat=True)
            )

            # Check if all cart products are from dealer's manufacturers
            if not cart_manufacturers.issubset(dealer_manufacturers):
                return error_response(
                    errors={'dealer_id': 'Savatidagi ba\'zi mahsulotlar bu dillerning assortimentida yo\'q'},
                    message='Diller tanlanishi mumkin emas',
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        try:
            with transaction.atomic():
                cart.dealer = dealer
                cart.save()

            cart_serializer = CartSerializer(cart)
            return success_response(
                data=cart_serializer.data,
                message='Diller tanlab olindi',
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Diller tanlanishda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout(self, request):
        """
        POST /api/v1/cart/checkout/ — Create order from cart.
        
        Request body:
        {
            "delivery_address": "123 Main St, City",
            "delivery_note": "Leave at door",
            "delivery_latitude": 41.29,
            "delivery_longitude": 69.24
        }
        
        Atomic transaction:
        1. Validate cart not empty, dealer selected
        2. Lock product rows, validate stock
        3. Decrease stock
        4. Create Order + OrderItems
        5. Clear cart items
        6. Trigger notification to dealer
        """
        serializer = CheckoutSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Checkout xatosi',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        cart = serializer.context['cart']
        dealer = serializer.context['dealer']
        delivery_data = serializer.validated_data

        try:
            with transaction.atomic():
                # Get all products in cart and lock them for update
                product_ids = list(cart.items.values_list('product_id', flat=True))
                products = Product.objects.select_for_update().filter(id__in=product_ids)
                products_dict = {str(p.id): p for p in products}

                # Validate stock for each cart item
                for cart_item in cart.items.all():
                    product = products_dict.get(str(cart_item.product_id))
                    if not product:
                        raise ValueError(f'Product {cart_item.product.name} not found.')
                    
                    if product.stock < cart_item.quantity:
                        raise ValueError(
                            f'{product.name}: Zaxirada {product.stock} dona bo\'lsa, siz {cart_item.quantity} dona so\'rashni tanlagan.'
                        )

                # Calculate total price from cart items
                total_price = cart.total_price

                # Create order
                order = Order.objects.create(
                    store=request.user,
                    dealer=dealer,
                    status=OrderStatus.PENDING,
                    total_price=total_price,
                    delivery_address=delivery_data['delivery_address'],
                    delivery_note=delivery_data.get('delivery_note', ''),
                    delivery_latitude=delivery_data.get('delivery_latitude'),
                    delivery_longitude=delivery_data.get('delivery_longitude'),
                )

                # Create order items and decrease stock
                for cart_item in cart.items.all():
                    product = products_dict[str(cart_item.product_id)]
                    
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.price_snapshot,
                    )

                    # Decrease product stock
                    product.stock -= cart_item.quantity
                    product.save(update_fields=['stock'])

                # Clear cart items
                cart.items.all().delete()
                cart.dealer = None
                cart.save()

                # TODO: Trigger notification to dealer via Celery
                # send_order_notification_to_dealer.delay(order.id)

                # Return created order
                order_serializer = OrderDetailSerializer(order)
                return success_response(
                    data=order_serializer.data,
                    message='Buyurtma muvaffaqiyatli yaratildi',
                    status_code=status.HTTP_201_CREATED
                )

        except ValueError as e:
            return error_response(
                errors={'validation': str(e)},
                message='Validatsiya xatosi',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Buyurtma yaratishda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )
