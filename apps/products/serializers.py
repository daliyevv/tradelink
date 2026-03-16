from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Category, Product, ProductImage

User = get_user_model()


class CategoryChildrenSerializer(serializers.ModelSerializer):
    """
    Serializer for child categories (non-recursive to avoid infinite nesting).
    """

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'order']
        read_only_fields = ['id']


class CategorySerializer(serializers.ModelSerializer):
    """
    Category serializer with recursive children support (max 2 levels deep).
    """

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'children', 'order', 'is_active']
        read_only_fields = ['id', 'slug']

    def get_children(self, obj):
        """
        Return child categories if parent is active.
        Limited to one level of recursion to avoid infinite nesting.
        """
        if obj.is_active:
            children = obj.children.filter(is_active=True).order_by('order')
            return CategoryChildrenSerializer(children, many=True).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer for product images.
    """

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'order']
        read_only_fields = ['id']


class ManufacturerSimpleSerializer(serializers.ModelSerializer):
    """
    Simple manufacturer info for product details.
    """

    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'phone', 'full_name', 'role', 'role_display', 'email', 'avatar']
        read_only_fields = ['id']


class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for product list view.
    Includes only essential fields for efficient list display.
    """

    category_name = serializers.CharField(source='category.name', read_only=True)
    manufacturer_name = serializers.CharField(source='manufacturer.full_name', read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'price',
            'unit',
            'min_order_qty',
            'stock',
            'primary_image',
            'category_name',
            'manufacturer_name',
        ]
        read_only_fields = ['id']

    def get_primary_image(self, obj):
        """Return URL of primary image if exists."""
        primary = obj.images.filter(is_primary=True).first()
        if primary and primary.image:
            return self.context['request'].build_absolute_uri(primary.image.url)
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Full product details serializer with all information and images.
    """

    images = ProductImageSerializer(many=True, read_only=True)
    manufacturer = ManufacturerSimpleSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_display = serializers.CharField(source='get_unit_display', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'price',
            'stock',
            'unit',
            'unit_display',
            'min_order_qty',
            'is_active',
            'created_at',
            'updated_at',
            'category_name',
            'category',
            'manufacturer',
            'images',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'manufacturer']


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating products.
    Manufacturers can only edit their own products.
    """

    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'price',
            'stock',
            'unit',
            'min_order_qty',
            'category',
            'is_active',
        ]

    def validate_price(self, value):
        """Ensure price is non-negative."""
        if value < 0:
            raise serializers.ValidationError('Narxi manfiy bo\'lishi mumkin emas.')
        return value

    def validate_min_order_qty(self, value):
        """Ensure minimum order quantity is at least 1."""
        if value < 1:
            raise serializers.ValidationError('Minimum buyurtma miqdori kamida 1 bo\'lishi kerak.')
        return value

    def validate_stock(self, value):
        """Ensure stock is non-negative."""
        if value < 0:
            raise serializers.ValidationError('Zaxira manfiy bo\'lishi mumkin emas.')
        return value

    def create(self, validated_data):
        """Create product with current user as manufacturer."""
        validated_data['manufacturer'] = self.context['request'].user
        return super().create(validated_data)


class ProductImageUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for uploading product images.
    """

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'order']
        read_only_fields = ['id']

    def create(self, validated_data):
        """Create image for the product from context."""
        validated_data['product_id'] = self.context['product_id']
        return super().create(validated_data)
