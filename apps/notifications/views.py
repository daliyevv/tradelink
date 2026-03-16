from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from apps.notifications.models import Notification, FCMToken
from apps.notifications.serializers import (
    NotificationSerializer,
    FCMTokenSerializer,
)
from utils.responses import success_response, error_response


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for notifications.
    - List: GET /api/v1/notifications/?is_read=true|false
    - Retrieve: GET /api/v1/notifications/{id}/
    - Read All: POST /api/v1/notifications/read-all/
    - Save FCM Token: POST /api/v1/notifications/fcm-token/
    
    RBAC Test Matrix:
    Action               | Unauthenticated | Authenticated
    -------------------- | --------------- | -----
    GET list             | 401             | 200*
    GET retrieve         | 401             | 200*
    POST read-all        | 401             | 200*
    POST fcm-token       | 401             | 201*
    GET unread-count     | 401             | 200*
    
    * User sees only their own notifications
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_read', 'type']
    ordering_fields = ['created_at', 'is_read']
    ordering = ['-created_at']
    pagination_class = None  # Can be updated to pagination_class if needed

    def get_queryset(self):
        """Get notifications only for the logged-in user."""
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        """
        Mark all notifications as read for the current user.
        POST /api/v1/notifications/read-all/
        """
        try:
            updated_count = Notification.objects.filter(
                user=request.user,
                is_read=False
            ).update(is_read=True)

            return success_response(
                data={'marked_as_read': updated_count},
                message=f"Marked {updated_count} notification(s) as read."
            )
        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Failed to mark as read',
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='read')
    def read(self, request, pk=None):
        """
        Mark a single notification as read.
        POST /api/v1/notifications/{id}/read/
        """
        try:
            notification = self.get_object()
            if notification.user != request.user:
                return error_response(
                    errors={'detail': 'You can only read your own notifications.'},
                    message='Permission denied',
                    status_code=status.HTTP_403_FORBIDDEN
                )

            notification.is_read = True
            notification.save()

            serializer = self.get_serializer(notification)
            return success_response(
                data=serializer.data,
                message="Notification marked as read."
            )
        except Notification.DoesNotExist:
            return error_response(
                errors={'detail': 'Notification not found.'},
                message='Not found',
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Failed to read notification',
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], url_path='fcm-token')
    def fcm_token(self, request):
        """
        Save or update FCM token for push notifications.
        POST /api/v1/notifications/fcm-token/
        
        Request body:
        {
            "token": "FCM_TOKEN_STRING",
            "device_type": "android|ios|web"
        }
        """
        try:
            serializer = FCMTokenSerializer(data=request.data, context={'request': request})
            if not serializer.is_valid():
                return error_response(
                    errors=serializer.errors,
                    message='Invalid request data',
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            fcm_token = serializer.save(user=request.user)

            return success_response(
                data=FCMTokenSerializer(fcm_token).data,
                message="FCM token saved successfully.",
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Failed to save FCM token',
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """
        Get count of unread notifications.
        GET /api/v1/notifications/unread-count/
        """
        try:
            unread_count = Notification.objects.filter(
                user=request.user,
                is_read=False
            ).count()

            return success_response(
                data={'unread_count': unread_count},
                message="Unread notification count retrieved."
            )
        except Exception as e:
            return error_response(
                errors={'detail': str(e)},
                message='Failed to retrieve unread count',
                status_code=status.HTTP_400_BAD_REQUEST
            )
