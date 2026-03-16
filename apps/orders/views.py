from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Prefetch

from utils.permissions import IsStoreOwner, IsDealer
from utils.responses import success_response, error_response
from .models import Order, OrderItem, OrderStatus
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    CheckoutSerializer,
    OrderStatusUpdateSerializer,
    OrderCancelSerializer,
)
from apps.cart.models import Cart, CartItem
from apps.products.models import Product
from apps.dealers.models import DealerProfile


class CartCheckoutViewSet(viewsets.ViewSet):
    """
    ViewSet for cart checkout to create orders.
    
    Endpoints:
    - POST /api/v1/cart/checkout/ — Create order from cart (atomic transaction)
    """

    permission_classes = [IsAuthenticated]

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


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing orders.
    
    Endpoints:
    - GET /api/v1/orders/ — List orders (filtered by role)
    - GET /api/v1/orders/{id}/ — Order details
    - PATCH /api/v1/orders/{id}/status/ — Update status (dealer only)
    - POST /api/v1/orders/{id}/cancel/ — Cancel order (store owner only)
    
    RBAC Test Matrix:
    Action                 | Unauthenticated | Store Owner | Dealer | Manufacturer
    ---------------------- | --------------- | ----------- | ------ | -----
    GET list               | 401             | 200**       | 200*** | 403
    GET retrieve           | 401             | 200**       | 200*** | 403
    PATCH status           | 401             | 403         | 200    | 403
    POST cancel            | 401             | 200**       | 403    | 403
    
    ** Store owner sees only their own orders
    *** Dealer sees orders assigned to their profile
    """

    permission_classes = [IsAuthenticated]
    filterset_fields = ['status']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Filter orders based on user role.
        - Store owners see their own orders
        - Dealers see orders assigned to them
        """
        user = self.request.user
        
        if user.role == 'store':
            # Store owner sees only their orders
            queryset = Order.objects.filter(store=user)
        elif user.role == 'dealer':
            # Dealer sees orders assigned to their profile
            try:
                dealer_profile = user.dealer_profile
                queryset = Order.objects.filter(dealer=dealer_profile)
            except:
                queryset = Order.objects.none()
        else:
            queryset = Order.objects.none()

        return queryset.select_related(
            'store',
            'dealer',
            'dealer__user'
        ).prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return OrderListSerializer
        return OrderDetailSerializer

    def list(self, request, *args, **kwargs):
        """List orders filtered by role."""
        response = super().list(request, *args, **kwargs)
        
        if isinstance(response.data, list):
            return success_response(
                data=response.data,
                message='Buyurtmalar ro\'yxati',
                status_code=status.HTTP_200_OK
            )
        elif isinstance(response.data, dict) and 'results' in response.data:
            return success_response(
                data=response.data,
                message='Buyurtmalar ro\'yxati',
                status_code=status.HTTP_200_OK
            )
        return response

    def retrieve(self, request, *args, **kwargs):
        """Retrieve order details."""
        order = self.get_object()
        serializer = self.get_serializer(order)
        
        return success_response(
            data=serializer.data,
            message='Buyurtma tafsilotlari',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        """
        PATCH /api/v1/orders/{id}/status/ — Update order status.
        Only dealers can update status.
        
        Request body:
        {
            "status": "accepted"
        }
        
        Valid transitions:
        - pending → accepted, cancelled
        - accepted → preparing, cancelled
        - preparing → delivering, cancelled
        - delivering → delivered, cancelled
        """
        order = self.get_object()

        # Check if user is a dealer
        if request.user.role != 'dealer':
            return error_response(
                message='Faqat dillerlar buyurtma statusini o\'zgartirishlari mumkin',
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Check if dealer is the one handling this order
        try:
            if order.dealer.user_id != request.user.id:
                return error_response(
                    message='Bu buyurtma sizga tayinlanmagan',
                    status_code=status.HTTP_403_FORBIDDEN
                )
        except:
            return error_response(
                message='Authorized error',
                status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = OrderStatusUpdateSerializer(
            data=request.data,
            context={'order': order}
        )

        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Status yangilanishida xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                new_status = serializer.validated_data['status']
                order.status = new_status
                order.save(update_fields=['status', 'updated_at'])

                # TODO: Trigger FCM notification to store owner
                # send_order_status_notification.delay(order.id, new_status)

            order_serializer = OrderDetailSerializer(order)
            return success_response(
                data=order_serializer.data,
                message=f'Status {dict(OrderStatus.choices).get(new_status)} ga o\'zgartirildi',
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Status yangilanishida xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        POST /api/v1/orders/{id}/cancel/ — Cancel order.
        Only store owner can cancel, and only if status is PENDING.
        Restores stock atomically.
        
        Request body (optional):
        {
            "reason": "Changed my mind"
        }
        """
        order = self.get_object()

        # Check if user is the one who placed the order
        if order.store_id != request.user.id:
            return error_response(
                message='Siz bu buyurtmani bekor qila olmaysiz',
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Check if order can be cancelled (only pending orders)
        if order.status != OrderStatus.PENDING:
            return error_response(
                errors={'status': f'Faqat {OrderStatus.PENDING} statusidagi buyurtmaka bekor qilish mumkin.'},
                message='Buyurtmani bekor qilib bo\'lmaydi',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = OrderCancelSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Bekor qilishda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Restore stock for all items in the order
                for order_item in order.items.all():
                    product = order_item.product
                    product.stock += order_item.quantity
                    product.save(update_fields=['stock'])

                # Cancel the order
                order.status = OrderStatus.CANCELLED
                order.cancelled_reason = serializer.validated_data.get('reason', '')
                order.save(update_fields=['status', 'cancelled_reason', 'updated_at'])

                # TODO: Trigger notification to dealer
                # send_order_cancelled_notification.delay(order.id)

            order_serializer = OrderDetailSerializer(order)
            return success_response(
                data=order_serializer.data,
                message='Buyurtma bekor qilindi',
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Bekor qilishda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )
