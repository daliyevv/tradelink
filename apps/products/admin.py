from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Q

from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    """Inline admin for product images."""
    model = ProductImage
    extra = 1
    fields = ('image', 'image_preview', 'is_primary', 'order')
    readonly_fields = ('image_preview', 'created_at')
    
    def image_preview(self, obj):
        """Display image thumbnail in list."""
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="border-radius: 4px; object-fit: cover;" />',
                obj.image.url
            )
        return '—'
    image_preview.short_description = 'Preview'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for product categories."""
    
    list_display = ('name', 'parent_link', 'is_active_badge', 'order', 'products_count')
    list_filter = ('is_active', 'parent', 'created_at')
    search_fields = ('name', 'slug', 'description')
    readonly_fields = ('slug', 'created_at', 'updated_at', 'id')
    
    fieldsets = (
        ('Category Info', {
            'fields': ('id', 'name', 'slug', 'parent')
        }),
        ('Description', {
            'fields': ('description',),
            'classes': ('wide',)
        }),
        ('Status & Order', {
            'fields': ('is_active', 'order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ('order', 'name')
    
    def parent_link(self, obj):
        """Display parent category link."""
        if obj.parent:
            return format_html(
                '<a href="/admin/products/category/{}/change/">{}</a>',
                obj.parent.id,
                obj.parent.name
            )
        return '—'
    parent_link.short_description = 'Parent'
    
    def is_active_badge(self, obj):
        """Display active status as badge."""
        if obj.is_active:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓</span>')
        return format_html('<span style="color: #dc3545; font-weight: bold;">✗</span>')
    is_active_badge.short_description = 'Active'
    
    def products_count(self, obj):
        """Display number of products in category."""
        count = obj.products.filter(is_active=True).count()
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">{}</span>',
            count
        )
    products_count.short_description = 'Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin interface for products."""
    
    list_display = ('name_with_image', 'manufacturer_link', 'category_link', 'price_display', 'stock_display', 'status_badge', 'created_at')
    list_filter = ('category', 'manufacturer', 'is_active', 'created_at')
    search_fields = ('name', 'slug', 'description', 'manufacturer__full_name')
    readonly_fields = ('slug', 'image_preview', 'created_at', 'updated_at', 'id')
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Product Info', {
            'fields': ('id', 'name', 'slug', 'category', 'manufacturer')
        }),
        ('Description & Details', {
            'fields': ('description',),
            'classes': ('wide',)
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'stock', 'min_order')
        }),
        ('Images', {
            'fields': ('image_preview',),
            'description': 'Main image (images managed in inline section below)'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ('-created_at',)
    
    def name_with_image(self, obj):
        """Display product name with thumbnail."""
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 4px; object-fit: cover; margin-right: 10px; vertical-align: middle;" />'
                '<span style="font-weight: bold;">{}</span>',
                obj.image.url,
                obj.name
            )
        return format_html('<span style="font-weight: bold;">{}</span>', obj.name)
    name_with_image.short_description = 'Product'
    
    def image_preview(self, obj):
        """Display main image."""
        if obj.image:
            return format_html(
                '<img src="{}" width="200" style="border-radius: 4px; object-fit: cover; max-width: 100%;" />',
                obj.image.url
            )
        return '—'
    image_preview.short_description = 'Preview'
    
    def manufacturer_link(self, obj):
        """Display manufacturer as link."""
        return format_html(
            '<a href="/admin/users/user/{}/change/">{}</a>',
            obj.manufacturer.id,
            obj.manufacturer.full_name
        )
    manufacturer_link.short_description = 'Manufacturer'
    
    def category_link(self, obj):
        """Display category as link."""
        return format_html(
            '<a href="/admin/products/category/{}/change/">{}</a>',
            obj.category.id,
            obj.category.name
        )
    category_link.short_description = 'Category'
    
    def price_display(self, obj):
        """Display price formatted."""
        return format_html(
            '<span style="font-weight: bold; color: #28a745;">{:,} som</span>',
            int(obj.price)
        )
    price_display.short_description = 'Price'
    
    def stock_display(self, obj):
        """Display stock with color based on level."""
        if obj.stock == 0:
            color = '#dc3545'
            label = 'Out of Stock'
        elif obj.stock < 10:
            color = '#ffc107'
            label = f'{obj.stock} left'
        else:
            color = '#28a745'
            label = f'{obj.stock} in stock'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            label
        )
    stock_display.short_description = 'Stock'
    
    def status_badge(self, obj):
        """Display active status badge."""
        if obj.is_active:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ Active</span>')
        return format_html('<span style="color: #dc3545; font-weight: bold;">✗ Inactive</span>')
    status_badge.short_description = 'Status'

from .models import Category, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for Product Categories.
    """

    list_display = ['name', 'slug', 'parent', 'order', 'is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['is_active', 'parent']
    ordering = ['order', 'name']
    fields = ['name', 'slug', 'icon', 'parent', 'order', 'is_active']


class ProductImageInline(admin.TabularInline):
    """
    Inline admin for product images.
    """

    model = ProductImage
    extra = 1
    fields = ['image', 'is_primary', 'order']
    ordering = ['order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Products.
    """

    list_display = [
        'name',
        'manufacturer',
        'category',
        'price',
        'stock',
        'unit',
        'is_active',
        'created_at',
    ]
    list_filter = ['is_active', 'category', 'manufacturer', 'created_at', 'unit']
    search_fields = ['name', 'description', 'manufacturer__full_name']
    readonly_fields = ['created_at', 'updated_at', 'id']
    fieldsets = (
        ('Basic Information', {
            'fields': ['id', 'name', 'description']
        }),
        ('Manufacturer & Category', {
            'fields': ['manufacturer', 'category']
        }),
        ('Pricing & Inventory', {
            'fields': ['price', 'stock', 'unit', 'min_order_qty']
        }),
        ('Status & Timestamps', {
            'fields': ['is_active', 'created_at', 'updated_at']
        }),
    )
    inlines = [ProductImageInline]
    ordering = ['-created_at']

    def get_readonly_fields(self, request, obj=None):
        """Make manufacturer read-only for existing products."""
        if obj:
            return self.readonly_fields + ['manufacturer']
        return self.readonly_fields


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    Admin interface for Product Images.
    """

    list_display = ['product', 'image', 'is_primary', 'order', 'created_at']
    list_filter = ['is_primary', 'product', 'created_at']
    search_fields = ['product__name']
    readonly_fields = ['created_at', 'id']
    fields = ['id', 'product', 'image', 'is_primary', 'order', 'created_at']
    ordering = ['product', 'order']
