from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import Order, OrderItem, OrderStatus
from apps.cart.models import Cart, CartItem
from apps.products.models import Product
from apps.dealers.models import DealerProfile

User = get_user_model()


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for individual order items.
    """
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_unit',
            'quantity',
            'unit_price',
            'subtotal',
        ]
        read_only_fields = ['id', 'product_name', 'product_unit', 'subtotal']

    def get_subtotal(self, obj):
        """Return subtotal as float."""
        return float(obj.subtotal)


class OrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for order list.
    """
    
    store_name = serializers.CharField(source='store.full_name', read_only=True)
    dealer_name = serializers.CharField(source='dealer.company_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'store_name',
            'dealer_name',
            'status',
            'status_display',
            'total_price',
            'total_items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_total_items(self, obj):
        """Return total number of items."""
        return obj.total_items


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Full order details with all items.
    """
    
    items = OrderItemSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source='store.full_name', read_only=True)
    dealer_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'store_name',
            'dealer_info',
            'status',
            'status_display',
            'total_price',
            'total_items',
            'delivery_address',
            'delivery_note',
            'delivery_latitude',
            'delivery_longitude',
            'cancelled_reason',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_dealer_info(self, obj):
        """Return dealer information."""
        return {
            'id': str(obj.dealer.id),
            'company_name': obj.dealer.company_name,
            'user_name': obj.dealer.user.full_name,
            'coverage_radius_km': obj.dealer.coverage_radius_km,
        }

    def get_total_items(self, obj):
        """Return total number of items."""
        return obj.total_items


class CheckoutSerializer(serializers.Serializer):
    """
    Serializer for cart checkout to create order.
    """
    
    delivery_address = serializers.CharField(
        max_length=500,
        help_text='Delivery address'
    )
    delivery_note = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Optional delivery notes'
    )
    delivery_latitude = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text='Delivery location latitude'
    )
    delivery_longitude = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text='Delivery location longitude'
    )

    def validate_delivery_latitude(self, value):
        """Validate latitude is within valid range."""
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError('Latitude must be between -90 and 90.')
        return value

    def validate_delivery_longitude(self, value):
        """Validate longitude is within valid range."""
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError('Longitude must be between -180 and 180.')
        return value

    def validate(self, data):
        """Validate checkout prerequisites."""
        request = self.context.get('request')
        
        # Get user's cart
        try:
            cart = request.user.cart
        except:
            raise serializers.ValidationError({'cart': 'Cart not found.'})

        # Check cart is not empty
        if cart.is_empty:
            raise serializers.ValidationError({'items': 'Cart is empty.'})

        # Check dealer is selected
        if not cart.dealer:
            raise serializers.ValidationError({'dealer': 'Please select a delivery dealer.'})

        # Store cart and dealer in context for use in create method
        self.context['cart'] = cart
        self.context['dealer'] = cart.dealer

        return data


class OrderStatusUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating order status.
    """
    
    status = serializers.ChoiceField(choices=OrderStatus.choices)

    def validate_status(self, value):
        """Validate status is a valid choice."""
        if value not in dict(OrderStatus.choices):
            raise serializers.ValidationError('Invalid status choice.')
        return value

    def validate(self, data):
        """Validate transition is allowed."""
        order = self.context.get('order')
        new_status = data['status']

        if not order.can_transition_to(new_status):
            raise serializers.ValidationError(
                {
                    'status': f'Cannot transition from {order.get_status_display()} to {dict(OrderStatus.choices).get(new_status, new_status)}.'
                }
            )

        return data


class OrderCancelSerializer(serializers.Serializer):
    """
    Serializer for cancelling order.
    """
    
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Reason for cancellation'
    )
