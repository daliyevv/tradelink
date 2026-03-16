from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import User, OTPCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin configuration.
    """

    # List display
    list_display = ('phone', 'full_name_display', 'role_badge', 'verified_badge', 'is_active_badge', 'created_at')
    list_filter = ('role', 'is_verified', 'is_active', 'created_at')
    search_fields = ('phone', 'email', 'full_name')
    ordering = ('-created_at',)

    # Form configuration
    fieldsets = (
        (_('Authentication'), {'fields': ('phone', 'password')}),
        (_('Personal'), {'fields': ('full_name', 'email', 'avatar')}),
        (_('Role & Status'), {'fields': ('role', 'is_verified', 'is_active')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
        (_('Activity'), {'fields': ('last_login',), 'classes': ('collapse',)}),
    )

    # Add form (when creating new user)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'full_name', 'role', 'password1', 'password2'),
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'last_login', 'id')

    def full_name_display(self, obj):
        """Display full_name with color based on verification."""
        color = '#28a745' if obj.is_verified else '#dc3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.full_name or '—'
        )
    full_name_display.short_description = 'Full Name'

    def role_badge(self, obj):
        """Display role with colored badge."""
        colors = {
            'manufacturer': '#007bff',
            'dealer': '#ffc107',
            'store': '#28a745',
        }
        labels = {
            'manufacturer': 'Ishlab chiqaruvchi',
            'dealer': 'Diller',
            'store': "Do'kon egasi",
        }
        color = colors.get(obj.role, '#6c757d')
        label = labels.get(obj.role, obj.role)
        return format_html(
            '<span style="color: white; background-color: {}; padding: 4px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            label
        )
    role_badge.short_description = 'Role'

    def verified_badge(self, obj):
        """Display verification status with icon."""
        if obj.is_verified:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ Verified</span>')
        return format_html('<span style="color: #dc3545; font-weight: bold;">✗ Not Verified</span>')
    verified_badge.short_description = 'Verified'

    def is_active_badge(self, obj):
        """Display active status with icon."""
        if obj.is_active:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ Active</span>')
        return format_html('<span style="color: #dc3545; font-weight: bold;">✗ Inactive</span>')
    is_active_badge.short_description = 'Active'


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    """
    OTP Code admin configuration.
    """

    list_display = ('code', 'user', 'is_valid', 'is_used', 'expires_at', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('code', 'user__phone')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'is_valid')

    fieldsets = (
        (None, {'fields': ('id', 'user', 'code')}),
        (_('Status'), {'fields': ('is_used', 'is_valid')}),
        (_('Expiry'), {'fields': ('expires_at',)}),
        (_('Timestamp'), {'fields': ('created_at',)}),
    )

    actions = ['mark_as_used']

    def is_valid(self, obj):
        """Display OTP validity status."""
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Valid?'

    def mark_as_used(self, request, queryset):
        """Mark selected OTPs as used."""
        updated = queryset.update(is_used=True)
        self.message_user(request, f'{updated} OTP code(s) marked as used.')
    mark_as_used.short_description = 'Mark selected OTPs as used'
