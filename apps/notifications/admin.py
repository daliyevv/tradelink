from django.contrib import admin
from apps.notifications.models import Notification, FCMToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['user__full_name', 'user__email', 'title', 'body']
    readonly_fields = ['id', 'user', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'title', 'body')
        }),
        ('Details', {
            'fields': ('type', 'data', 'is_read')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']

    def has_add_permission(self, request):
        # Notifications are created by tasks, not manually
        return False

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion by superusers in specific cases
        return request.user.is_superuser


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'device_type', 'is_active', 'created_at']
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = ['user__full_name', 'user__email', 'token']
    readonly_fields = ['id', 'token', 'created_at', 'updated_at']
    fieldsets = (
        ('User & Token', {
            'fields': ('id', 'user', 'token')
        }),
        ('Device Information', {
            'fields': ('device_type', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']

    def has_add_permission(self, request):
        # FCM tokens are saved via API, not manually in admin
        return False
