from rest_framework import serializers
from apps.notifications.models import Notification, FCMToken, DeviceType


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'body',
            'type',
            'type_display',
            'data',
            'is_read',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FCMTokenSerializer(serializers.ModelSerializer):
    device_type_display = serializers.CharField(source='get_device_type_display', read_only=True)

    class Meta:
        model = FCMToken
        fields = [
            'id',
            'token',
            'device_type',
            'device_type_display',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']
        extra_kwargs = {
            'token': {'write_only': True},
        }

    def validate_device_type(self, value):
        """Validate device_type is one of the allowed choices."""
        valid_types = [choice[0] for choice in DeviceType.choices]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid device type. Allowed values are: {', '.join(valid_types)}"
            )
        return value

    def create(self, validated_data):
        """Create or update FCM token for user."""
        user = self.context['request'].user
        token = validated_data.get('token')
        device_type = validated_data.get('device_type', DeviceType.ANDROID)

        # Get or create FCM token
        fcm_token, created = FCMToken.objects.get_or_create(
            user=user,
            token=token,
            defaults={'device_type': device_type}
        )

        # If token already existed with different device_type, update it
        if not created and fcm_token.device_type != device_type:
            fcm_token.device_type = device_type
            fcm_token.save()

        # Reactivate if was deactivated
        if not fcm_token.is_active:
            fcm_token.is_active = True
            fcm_token.save()

        return fcm_token
