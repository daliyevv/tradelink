import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from apps.notifications.models import Notification, FCMToken, NotificationType
from apps.orders.models import Order
from apps.users.models import OTPCode


@shared_task(bind=True, max_retries=3)
def send_push_notification(self, user_id, title, body, notification_type, data=None):
    """
    Send push notification to a user via FCM.
    Retries up to 3 times with exponential backoff on failure.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    data = data or {}

    try:
        # Get user
        user = User.objects.get(id=user_id)

        # Get all active FCM tokens for this user
        fcm_tokens = FCMToken.objects.filter(user=user, is_active=True)

        if not fcm_tokens.exists():
            # No tokens to send to, just create notification in DB
            Notification.objects.create(
                user=user,
                title=title,
                body=body,
                type=notification_type,
                data=data,
            )
            return f"No FCM tokens for user {user_id}, saved to DB only"

        # Send to FCM
        fcm_server_key = settings.FCM_SERVER_KEY
        if not fcm_server_key:
            raise ValueError("FCM_SERVER_KEY not configured")

        fcm_url = "https://fcm.googleapis.com/fcm/send"
        headers = {
            "Authorization": f"key={fcm_server_key}",
            "Content-Type": "application/json",
        }

        failed_tokens = []
        for fcm_token in fcm_tokens:
            payload = {
                "to": fcm_token.token,
                "notification": {
                    "title": title,
                    "body": body,
                    "sound": "default",
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                },
                "data": data,
            }

            try:
                response = requests.post(fcm_url, json=payload, headers=headers, timeout=5)
                if response.status_code != 200:
                    failed_tokens.append(fcm_token.token)
                    if "NotRegistered" in response.text or "InvalidRegistration" in response.text:
                        # Mark token as inactive
                        fcm_token.is_active = False
                        fcm_token.save()
            except requests.RequestException as e:
                failed_tokens.append(fcm_token.token)

        # Save notification to DB regardless of FCM success
        notification = Notification.objects.create(
            user=user,
            title=title,
            body=body,
            type=notification_type,
            data=data,
        )

        if failed_tokens:
            return f"Notification created for user {user_id}, but {len(failed_tokens)} FCM sends failed"

        return f"Notification sent successfully to {fcm_tokens.count()} devices for user {user_id}"

    except User.DoesNotExist:
        return f"User {user_id} does not exist"
    except Exception as exc:
        # Retry with exponential backoff
        retry_in = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=retry_in)


@shared_task
def send_new_order_notification(order_id):
    """
    Send notification to dealer when a new order is placed.
    """
    try:
        order = Order.objects.get(id=order_id)

        title = f"New Order from {order.store.get_full_name()}"
        body = f"Order #{str(order.id)[:8]} - {order.total_items} items"

        send_push_notification.delay(
            user_id=str(order.dealer.user.id),
            title=title,
            body=body,
            notification_type=NotificationType.NEW_ORDER,
            data={
                "order_id": str(order.id),
                "order_status": order.status,
                "total_items": order.total_items,
            },
        )

        return f"Notification task created for order {order_id}"
    except Order.DoesNotExist:
        return f"Order {order_id} does not exist"
    except Exception as e:
        return f"Error sending new order notification: {str(e)}"


@shared_task
def send_order_status_notification(order_id, new_status):
    """
    Send notification to store owner when order status changes.
    """
    try:
        order = Order.objects.get(id=order_id)

        status_display = dict(order.OrderStatus.choices).get(new_status, new_status)
        title = f"Order Status Updated"
        body = f"Order #{str(order.id)[:8]} is now {status_display}"

        send_push_notification.delay(
            user_id=str(order.store.id),
            title=title,
            body=body,
            notification_type=NotificationType.ORDER_STATUS,
            data={
                "order_id": str(order.id),
                "order_status": new_status,
                "dealer_name": order.dealer.business_name,
            },
        )

        return f"Status notification task created for order {order_id}"
    except Order.DoesNotExist:
        return f"Order {order_id} does not exist"
    except Exception as e:
        return f"Error sending order status notification: {str(e)}"


@shared_task
def send_order_cancelled_notification(order_id, reason=None):
    """
    Send notification to dealer when order is cancelled.
    """
    try:
        order = Order.objects.get(id=order_id)

        title = "Order Cancelled"
        body = f"Order #{str(order.id)[:8]} has been cancelled"
        if reason:
            body += f": {reason}"

        send_push_notification.delay(
            user_id=str(order.dealer.user.id),
            title=title,
            body=body,
            notification_type=NotificationType.ORDER_CANCELLED,
            data={
                "order_id": str(order.id),
                "reason": reason or "No reason provided",
            },
        )

        return f"Cancellation notification task created for order {order_id}"
    except Order.DoesNotExist:
        return f"Order {order_id} does not exist"
    except Exception as e:
        return f"Error sending cancellation notification: {str(e)}"


@shared_task
def cleanup_expired_otps():
    """
    Delete expired OTP codes that have been used.
    Scheduled to run daily at 3:00 AM Tashkent time.
    """
    try:
        now = timezone.now()
        deleted_count, _ = OTPCode.objects.filter(
            expires_at__lt=now,
            is_used=True
        ).delete()

        return f"Cleaned up {deleted_count} expired OTP codes"
    except Exception as e:
        return f"Error cleaning up OTP codes: {str(e)}"
