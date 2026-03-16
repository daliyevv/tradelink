import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

User = get_user_model()


class Cart(models.Model):
    """
    Shopping cart model storing items for a customer.
    One cart per user, automatically created when user is created.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        help_text='Cart owner (customer/store account)'
    )
    dealer = models.ForeignKey(
        'dealers.DealerProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts',
        help_text='Selected delivery dealer for this cart'
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
        ordering = ['-updated_at']

    def __str__(self):
        return f'Cart of {self.owner.full_name}'

    @property
    def total_price(self) -> Decimal:
        """Calculate total price of all items in cart."""
        total = self.items.aggregate(
            total=models.Sum(
                models.F('quantity') * models.F('price_snapshot'),
                output_field=models.DecimalField(max_digits=12, decimal_places=2)
            )
        )['total']
        return total or Decimal('0.00')

    @property
    def total_items(self) -> int:
        """Calculate total quantity of items in cart."""
        total = self.items.aggregate(
            total=models.Sum('quantity')
        )['total']
        return total or 0

    @property
    def is_empty(self) -> bool:
        """Check if cart is empty."""
        return self.total_items == 0


class CartItem(models.Model):
    """
    Individual item in a shopping cart.
    Stores product, quantity, and price snapshot at time of addition.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Associated shopping cart'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='cart_items',
        help_text='Product in this cart item'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Quantity of the product'
    )
    price_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Product price at the time of adding to cart'
    )
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ('cart', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.product.name} ({self.quantity}) in {self.cart.owner.full_name}\'s cart'

    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal for this item."""
        return self.quantity * self.price_snapshot


@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    """
    Signal to auto-create Cart when a new User is created.
    Automatically creates a shopping cart for store owners/customers.
    """
    if created:
        Cart.objects.get_or_create(owner=instance)


@receiver(post_save, sender=User)
def save_user_cart(sender, instance, **kwargs):
    """
    Signal to ensure Cart exists for user.
    If cart doesn't exist, create it.
    """
    if hasattr(instance, 'cart'):
        instance.cart.save()
    else:
        Cart.objects.get_or_create(owner=instance)
