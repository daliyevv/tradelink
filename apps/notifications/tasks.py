import json
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.notifications.models import Notification, FCMToken, NotificationType
from apps.orders.models import Order
from apps.users.models import OTPCode

logger = logging.getLogger(__name__)


def get_firebase_app():
    """
    Initialize and return Firebase app instance.
    Handles already initialized case gracefully.
    """
    import firebase_admin
    from firebase_admin import credentials, messaging

    try:
        # Check if Firebase app already initialized
        app = firebase_admin.get_app()
        return app
    except ValueError:
        # Not initialized yet, initialize with service account
        if not settings.FIREBASE_CREDENTIALS_PATH:
            raise ValueError("FIREBASE_CREDENTIALS_PATH not configured")

        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            app = firebase_admin.initialize_app(cred)
            return app
        except FileNotFoundError:
            raise ValueError(f"Firebase credentials file not found at {settings.FIREBASE_CREDENTIALS_PATH}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in Firebase credentials file: {settings.FIREBASE_CREDENTIALS_PATH}")


@shared_task(bind=True, max_retries=3)
def send_push_notification(self, user_id, title, body, notification_type, data=None):
    """
    Send push notification to a user via Firebase Admin SDK.
    Uses HTTP v1 API (not the deprecated FCM Server Key method).
    Retries up to 3 times with exponential backoff on failure.
    
    Args:
        user_id: UUID of the user to send notification to
        title: Notification title
        body: Notification message body
        notification_type: Type of notification (from NotificationType choices)
        data: Optional dict with custom data payload
    
    Returns:
        Status message
    """
    from django.contrib.auth import get_user_model
    from firebase_admin import messaging
    
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
            logger.info(f"No FCM tokens for user {user_id}, saved to DB only")
            return f"No FCM tokens for user {user_id}, saved to DB only"

        # Initialize Firebase
        try:
            get_firebase_app()
        except ValueError as e:
            logger.error(f"Firebase initialization error: {str(e)}")
            # Still save to DB even if Firebase is not ready
            Notification.objects.create(
                user=user,
                title=title,
                body=body,
                type=notification_type,
                data=data,
            )
            raise self.retry(exc=e, countdown=60)

        # Send to each FCM token
        failed_tokens = []
        successful_count = 0

        for fcm_token in fcm_tokens:
            try:
                # Build message using Firebase Messaging API
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=data,
                    token=fcm_token.token,
                    android=messaging.AndroidConfig(
                        priority="high",
                        notification=messaging.AndroidNotification(
                            sound="default",
                            click_action="FLUTTER_NOTIFICATION_CLICK",
                        ),
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                sound="default",
                            ),
                        ),
                    ),
                )

                # Send the message
                response = messaging.send(message)
                successful_count += 1
                logger.info(f"Push notification sent successfully. Message ID: {response}")

            except messaging.InvalidArgumentError:
                # Invalid token - deactivate it
                logger.warning(f"Invalid FCM token: {fcm_token.token}")
                fcm_token.is_active = False
                fcm_token.save()
                failed_tokens.append(fcm_token.token)

            except messaging.UnregisteredError:
                # Token no longer registered - deactivate it
                logger.warning(f"Unregistered FCM token: {fcm_token.token}")
                fcm_token.is_active = False
                fcm_token.save()
                failed_tokens.append(fcm_token.token)

            except messaging.MissingRegistrationTokenError:
                # Missing or invalid registration token
                logger.warning(f"Missing registration token")
                fcm_token.is_active = False
                fcm_token.save()
                failed_tokens.append(fcm_token.token)

            except messaging.MessageNotSentError as e:
                # Send failed - will retry later
                logger.error(f"Failed to send message: {str(e)}")
                failed_tokens.append(fcm_token.token)

            except Exception as e:
                # Generic error
                logger.error(f"Unexpected error sending notification: {str(e)}")
                failed_tokens.append(fcm_token.token)

        # Save notification to DB regardless of FCM success
        notification = Notification.objects.create(
            user=user,
            title=title,
            body=body,
            type=notification_type,
            data=data,
        )

        # Return status
        if failed_tokens:
            msg = f"Notification sent to {successful_count}/{fcm_tokens.count()} devices. {len(failed_tokens)} failed."
            logger.warning(msg)
            return msg
        else:
            msg = f"Notification sent successfully to {successful_count} devices for user {user_id}"
            logger.info(msg)
            return msg

    except User.DoesNotExist:
        msg = f"User {user_id} does not exist"
        logger.error(msg)
        return msg

    except Exception as exc:
        # Retry with exponential backoff
        retry_in = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        logger.error(f"Retrying notification task in {retry_in}s: {str(exc)}")
        raise self.retry(exc=exc, countdown=retry_in)


@shared_task
def send_new_order_notification(order_id):
    """
    Send notification to dealer when a new order is placed.
    
    Args:
        order_id: UUID of the order
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

        logger.info(f"New order notification task created for order {order_id}")
        return f"Notification task created for order {order_id}"

    except Order.DoesNotExist:
        msg = f"Order {order_id} does not exist"
        logger.error(msg)
        return msg

    except Exception as e:
        msg = f"Error sending new order notification: {str(e)}"
        logger.error(msg)
        return msg


@shared_task
def send_order_status_notification(order_id, new_status):
    """
    Send notification to store owner when order status changes.
    
    Args:
        order_id: UUID of the order
        new_status: New status value
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

        logger.info(f"Status notification task created for order {order_id}")
        return f"Status notification task created for order {order_id}"

    except Order.DoesNotExist:
        msg = f"Order {order_id} does not exist"
        logger.error(msg)
        return msg

    except Exception as e:
        msg = f"Error sending order status notification: {str(e)}"
        logger.error(msg)
        return msg


@shared_task
def send_order_cancelled_notification(order_id, reason=None):
    """
    Send notification to dealer when order is cancelled.
    
    Args:
        order_id: UUID of the order
        reason: Optional cancellation reason
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

        logger.info(f"Cancellation notification task created for order {order_id}")
        return f"Cancellation notification task created for order {order_id}"

    except Order.DoesNotExist:
        msg = f"Order {order_id} does not exist"
        logger.error(msg)
        return msg

    except Exception as e:
        msg = f"Error sending cancellation notification: {str(e)}"
        logger.error(msg)
        return msg


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

        msg = f"Cleaned up {deleted_count} expired OTP codes"
        logger.info(msg)
        return msg

    except Exception as e:
        msg = f"Error cleaning up OTP codes: {str(e)}"
        logger.error(msg)
        return msg
