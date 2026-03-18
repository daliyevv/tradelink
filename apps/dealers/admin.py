from django.contrib import admin
from django.utils.html import format_html
from .models import DealerProfile


@admin.register(DealerProfile)
class DealerProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for dealer profiles.
    Displays location with map link, coverage radius, and availability.
    """
    
    list_display = ('user_link', 'company_name', 'coverage_radius_display', 'availability_badge', 'created_at')
    list_filter = ('is_available', 'created_at')
    search_fields = ('user__phone', 'user__full_name', 'company_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Dealer Info', {
            'fields': ('id', 'user', 'company_name', 'bio')
        }),
        ('Location & Coverage', {
            'fields': ('latitude', 'longitude', 'coverage_radius_km')
        }),
        ('Manufacturers', {
            'fields': ('manufacturers',)
        }),
        ('Status & Rating', {
            'fields': ('is_available', 'rating')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ('-created_at',)
    
    def user_link(self, obj):
        """Display user as link."""
        return format_html(
            '<a href="/admin/users/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.full_name or obj.user.phone
        )
    user_link.short_description = 'Dealer'
    
    def coverage_radius_display(self, obj):
        """Display coverage radius."""
        return format_html(
            '<span style="font-weight: bold;">{} km</span>',
            obj.coverage_radius
        )
    coverage_radius_display.short_description = 'Coverage'
    
    def availability_badge(self, obj):
        """Display availability status."""
        if obj.is_available:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ Available</span>')
        return format_html('<span style="color: #dc3545; font-weight: bold;">✗ Unavailable</span>')
    availability_badge.short_description = 'Status'

