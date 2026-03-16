from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    """Inline admin for CartItem within Cart."""
    model = CartItem
    extra = 0
    readonly_fields = ['id', 'product', 'price_snapshot', 'added_at', 'updated_at']
    fields = ['product', 'quantity', 'price_snapshot', 'added_at', 'updated_at']
    can_delete = True


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin interface for shopping carts."""
    
    list_display = ['owner', 'total_items', 'total_price', 'dealer', 'updated_at']
    list_filter = ['updated_at', 'created_at', 'dealer']
    search_fields = ['owner__full_name', 'owner__email']
    readonly_fields = ['id', 'owner', 'created_at', 'updated_at']
    inlines = [CartItemInline]
    
    fieldsets = (
        ('Cart Info', {
            'fields': ['id', 'owner', 'dealer']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make owner readonly when editing existing cart."""
        if obj:
            return self.readonly_fields + ['dealer']
        return self.readonly_fields


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Admin interface for individual cart items."""
    
    list_display = ['id', 'cart', 'product', 'quantity', 'price_snapshot', 'added_at']
    list_filter = ['added_at', 'cart__owner']
    search_fields = ['cart__owner__full_name', 'product__name']
    readonly_fields = ['id', 'cart', 'product', 'price_snapshot', 'added_at', 'updated_at']
    
    fieldsets = (
        ('Item Info', {
            'fields': ['id', 'cart', 'product', 'quantity', 'price_snapshot']
        }),
        ('Timestamps', {
            'fields': ['added_at', 'updated_at'],
            'classes': ['collapse']
        }),
    )

    def has_add_permission(self, request):
        """Prevent adding items directly; add through CartAdmin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deleting items."""
        return True
