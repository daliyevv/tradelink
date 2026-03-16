from rest_framework import serializers
from django.db import transaction
from decimal import Decimal

from .models import Cart, CartItem
from apps.products.models import Product
from apps.dealers.models import DealerProfile


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for individual cart items.
    Includes product info and calculated subtotal.
    """
    
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    product_manufacturer = serializers.StringRelatedField(
        source='product.manufacturer',
        read_only=True
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id',
            'product_id',
            'product_name',
            'product_unit',
            'product_manufacturer',
            'quantity',
            'price_snapshot',
            'subtotal',
            'added_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'product_name', 'product_unit', 'product_manufacturer', 'subtotal', 'added_at', 'updated_at']

    def get_subtotal(self, obj):
        """Return the subtotal for this cart item."""
        return float(obj.subtotal)


class CartAddItemSerializer(serializers.Serializer):
    """
    Serializer for adding items to cart.
    Validates product availability and quantity constraints.
    """
    
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, data):
        """Validate product is active and has sufficient stock."""
        product = data['product_id']
        quantity = data['quantity']

        # Check if product is active
        if not product.is_active:
            raise serializers.ValidationError(
                {'product_id': 'This product is no longer available.'}
            )

        # Check minimum order quantity
        if quantity < product.min_order_qty:
            raise serializers.ValidationError(
                {
                    'quantity': f'Minimum order quantity is {product.min_order_qty}. '
                    f'You ordered {quantity}.'
                }
            )

        # Check stock availability
        if quantity > product.stock:
            raise serializers.ValidationError(
                {
                    'quantity': f'Only {product.stock} items in stock. '
                    f'You requested {quantity}.'
                }
            )

        return data


class CartUpdateItemSerializer(serializers.Serializer):
    """
    Serializer for updating cart item quantity.
    Validates against product constraints.
    """
    
    quantity = serializers.IntegerField(min_value=1)

    def validate_quantity(self, value):
        """Validate quantity against product constraints."""
        # We'll get the cart_item from context in the view
        cart_item = self.context.get('cart_item')
        if not cart_item:
            return value

        product = cart_item.product

        # Check minimum order quantity
        if value < product.min_order_qty:
            raise serializers.ValidationError(
                f'Minimum order quantity is {product.min_order_qty}.'
            )

        # Check stock availability
        if value > product.stock:
            raise serializers.ValidationError(
                f'Only {product.stock} items in stock.'
            )

        return value


class DealerInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for dealer information displayed in cart.
    """
    
    company_name = serializers.CharField()
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    coverage_radius_km = serializers.FloatField()
    rating = serializers.DecimalField(max_digits=3, decimal_places=2)

    class Meta:
        model = DealerProfile
        fields = ['id', 'company_name', 'user_name', 'coverage_radius_km', 'rating']
        read_only_fields = ['id', 'user_name']


class CartSerializer(serializers.ModelSerializer):
    """
    Main serializer for shopping cart.
    Includes items, totals, and dealer information.
    """
    
    items = CartItemSerializer(many=True, read_only=True)
    dealer = DealerInfoSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    is_empty = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id',
            'total_items',
            'total_price',
            'items',
            'dealer',
            'is_empty',
            'updated_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_total_price(self, obj):
        """Return total cart price as float."""
        return float(obj.total_price)

    def get_total_items(self, obj):
        """Return total number of items."""
        return obj.total_items

    def get_is_empty(self, obj):
        """Return whether cart is empty."""
        return obj.is_empty


class SelectDealerSerializer(serializers.Serializer):
    """
    Serializer for selecting a dealer for cart delivery.
    """
    
    dealer_id = serializers.PrimaryKeyRelatedField(
        queryset=DealerProfile.objects.filter(is_available=True)
    )

    def validate_dealer_id(self, value):
        """Validate dealer is available."""
        if not value.is_available:
            raise serializers.ValidationError('This dealer is not available.')
        return value
