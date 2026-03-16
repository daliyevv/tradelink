import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


class OrderStatus(models.TextChoices):
    """Order status choices."""
    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    PREPARING = 'preparing', 'Preparing'
    DELIVERING = 'delivering', 'Delivering'
    DELIVERED = 'delivered', 'Delivered'
    CANCELLED = 'cancelled', 'Cancelled'


class Order(models.Model):
    """
    Order model representing a purchase from store via dealer.
    Status flow: pending → accepted → preparing → delivering → delivered
    Special case: any status → cancelled
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        limit_choices_to={'role': 'store'},
        help_text='Store owner who placed the order'
    )
    dealer = models.ForeignKey(
        'dealers.DealerProfile',
        on_delete=models.PROTECT,
        related_name='orders',
        help_text='Dealer handling delivery'
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        help_text='Order status'
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Total order price (sum of order items)'
    )
    delivery_address = models.TextField(help_text='Delivery address')
    delivery_note = models.TextField(
        blank=True,
        help_text='Additional delivery notes'
    )
    delivery_latitude = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text='Delivery location latitude'
    )
    delivery_longitude = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text='Delivery location longitude'
    )
    cancelled_reason = models.TextField(
        blank=True,
        help_text='Reason for cancellation if cancelled'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['dealer', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f'Order {self.id} by {self.store.full_name}'

    @property
    def total_items(self) -> int:
        """Get total number of items in order."""
        return sum(item.quantity for item in self.items.all())

    def can_transition_to(self, new_status: str) -> bool:
        """
        Validate status transition is allowed.
        Allowed transitions:
        - pending → accepted, cancelled
        - accepted → preparing, cancelled
        - preparing → delivering, cancelled
        - delivering → delivered, cancelled
        - delivered → (no transitions allowed)
        - cancelled → (no transitions allowed)
        """
        allowed_transitions = {
            OrderStatus.PENDING: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
            OrderStatus.ACCEPTED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
            OrderStatus.PREPARING: [OrderStatus.DELIVERING, OrderStatus.CANCELLED],
            OrderStatus.DELIVERING: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
            OrderStatus.DELIVERED: [],
            OrderStatus.CANCELLED: [],
        }
        return new_status in allowed_transitions.get(self.status, [])


class OrderItem(models.Model):
    """
    Individual item in an order.
    Stores product snapshot (name, unit_price) at order time.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Associated order'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='order_items',
        help_text='Product in this order item'
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text='Quantity ordered'
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Product price at time of order (snapshot)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f'{self.product.name} ({self.quantity}) in Order {self.order.id}'

    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal for this item."""
        return self.quantity * self.unit_price
