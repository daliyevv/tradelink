from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Inline admin for OrderItem within Order."""
    model = OrderItem
    extra = 0
    readonly_fields = ['id', 'product', 'unit_price', 'quantity_with_price', 'created_at']
    fields = ['product', 'quantity', 'unit_price', 'quantity_with_price', 'created_at']
    
    def quantity_with_price(self, obj):
        """Display subtotal (quantity × price)."""
        total = obj.quantity * obj.unit_price
        return format_html(
            '<span style="font-weight: bold; color: #007bff;">{:,} som</span>',
            int(total)
        )
    quantity_with_price.short_description = 'Subtotal'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for orders."""
    
    list_display = ('order_id_short', 'store_link', 'dealer_link', 'status_badge', 'total_price_display', 'created_at')
    list_filter = ('status', 'created_at', 'dealer')
    search_fields = ('id', 'user__phone', 'user__full_name', 'dealer__full_name')
    readonly_fields = ('id', 'total_amount', 'created_at', 'updated_at', 'order_summary')
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Order Info', {
            'fields': ('id', 'user', 'dealer', 'order_summary')
        }),
        ('Details', {
            'fields': ('delivery_address', 'notes', 'total_amount'),
            'classes': ('wide',)
        }),
        ('Status & Timeline', {
            'fields': ('status', 'accepted_by', 'accepted_at', 'delivered_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ('-created_at',)
    
    def order_id_short(self, obj):
        """Display shortened order ID."""
        return str(obj.id)[:8] + '...'
    order_id_short.short_description = 'Order ID'
    
    def store_link(self, obj):
        """Display store owner as link."""
        return format_html(
            '<a href="/admin/users/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.full_name or obj.user.phone
        )
    store_link.short_description = 'Store'
    
    def dealer_link(self, obj):
        """Display dealer as link."""
        if obj.dealer:
            return format_html(
                '<a href="/admin/users/user/{}/change/">{}</a>',
                obj.dealer.id,
                obj.dealer.full_name
            )
        return '—'
    dealer_link.short_description = 'Dealer'
    
    def status_badge(self, obj):
        """Display order status with colored badge."""
        colors = {
            'pending': '#ffc107',
            'accepted': '#0dcaf0',
            'delivered': '#28a745',
            'cancelled': '#dc3545',
        }
        labels = {
            'pending': 'Kutilmoqda',
            'accepted': 'Qabul qilindi',
            'delivered': "Yetkazildi",
            'cancelled': 'Bekor qilindi',
        }
        color = colors.get(obj.status, '#6c757d')
        label = labels.get(obj.status, obj.status)
        return format_html(
            '<span style="color: white; background-color: {}; padding: 4px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            label
        )
    status_badge.short_description = 'Status'
    
    def total_price_display(self, obj):
        """Display total price formatted."""
        return format_html(
            '<span style="font-weight: bold; color: #28a745;">{:,} som</span>',
            int(obj.total_amount)
        )
    total_price_display.short_description = 'Total'
    
    def order_summary(self, obj):
        """Display order summary."""
        items = obj.items.all()
        summary = '<ul style="margin: 0; padding-left: 20px;">'
        for item in items:
            summary += f'<li>{item.product.name} × {item.quantity} = {int(item.unit_price * item.quantity):,} som</li>'
        summary += '</ul>'
        return format_html(summary)
    order_summary.short_description = 'Items'

    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for orders."""
    
    list_display = ['id', 'store', 'dealer', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'created_at', 'dealer']
    search_fields = ['store__full_name', 'store__phone', 'dealer__company_name']
    readonly_fields = ['id', 'store', 'dealer', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Info', {
            'fields': ['id', 'store', 'dealer', 'status']
        }),
        ('Pricing & Total', {
            'fields': ['total_price']
        }),
        ('Delivery', {
            'fields': [
                'delivery_address',
                'delivery_note',
                'delivery_latitude',
                'delivery_longitude'
            ]
        }),
        ('Cancellation', {
            'fields': ['cancelled_reason'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    )

    def has_add_permission(self, request):
        """Prevent adding orders directly; use checkout endpoint."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting orders; use cancellation logic instead."""
        return False


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin interface for individual order items."""
    
    list_display = ['id', 'order', 'product', 'quantity', 'unit_price']
    list_filter = ['order__created_at', 'product']
    search_fields = ['order__id', 'product__name']
    readonly_fields = ['id', 'order', 'product', 'unit_price', 'created_at']
    
    fieldsets = (
        ('Item Info', {
            'fields': ['id', 'order', 'product', 'quantity', 'unit_price']
        }),
        ('Timestamps', {
            'fields': ['created_at'],
            'classes': ['collapse']
        }),
    )

    def has_add_permission(self, request):
        """Prevent adding items directly; add through OrderAdmin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting items; manage through Order."""
        return False
