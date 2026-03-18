from django.contrib import admin
from django.utils.html import format_html
from .models import DealerProfile


@admin.register(DealerProfile)
class DealerProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for dealer profiles.
    Displays location with map link, coverage radius, and availability.
    """
    
    list_display = ('user_link', 'business_name', 'location_link', 'coverage_radius_display', 'availability_badge', 'created_at')
    list_filter = ('is_available', 'created_at', 'location')
    search_fields = ('user__phone', 'user__full_name', 'business_name', 'location__city')
    readonly_fields = ('id', 'created_at', 'updated_at', 'map_view')
    
    fieldsets = (
        ('Dealer Info', {
            'fields': ('id', 'user', 'business_name', 'phone_number')
        }),
        ('Location & Coverage', {
            'fields': ('location', 'coverage_radius', 'map_view'),
            'description': 'Coverage radius in kilometers. Dealers serve customers within this radius of their location.'
        }),
        ('Status', {
            'fields': ('is_available',)
        }),
        ('Verification', {
            'fields': ('verification_status', 'verification_document'),
            'classes': ('collapse',)
        }),
        ('Bank Details', {
            'fields': ('bank_account', 'bank_name'),
            'classes': ('collapse',)
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
    
    def location_link(self, obj):
        """Display location with link to Google Maps."""
        if obj.location:
            maps_url = f'https://www.google.com/maps?q={obj.location.latitude},{obj.location.longitude}'
            return format_html(
                '<a href="{}" target="_blank" style="color: #007bff; text-decoration: none;">📍 {}</a>',
                maps_url,
                obj.location.city
            )
        return '—'
    location_link.short_description = 'Location'
    
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
    
    def map_view(self, obj):
        """Display map view of dealer location."""
        if obj.location:
            maps_url = f'https://www.google.com/maps?q={obj.location.latitude},{obj.location.longitude}'
            return format_html(
                '<a href="{}" target="_blank" class="button" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">View on Google Maps →</a>',
                maps_url
            )
        return 'No location set'
    map_view.short_description = 'Map'

