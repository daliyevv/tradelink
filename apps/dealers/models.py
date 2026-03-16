from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from math import radians, cos, sin, asin, sqrt

User = get_user_model()


class DealerProfile(models.Model):
    """
    Dealer profile model with geolocation support.
    Stores dealer information, location, coverage area, and available manufacturers.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='dealer_profile',
        help_text='Associated dealer user'
    )
    company_name = models.CharField(
        max_length=200,
        help_text='Dealer company name'
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text='Current GPS latitude'
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text='Current GPS longitude'
    )
    coverage_radius_km = models.FloatField(
        default=10.0,
        validators=[MinValueValidator(0.1)],
        help_text='Delivery coverage radius in kilometers'
    )
    manufacturers = models.ManyToManyField(
        User,
        related_name='dealers',
        blank=True,
        limit_choices_to={'role': 'manufacturer'},
        help_text='Manufacturers this dealer works with'
    )
    is_available = models.BooleanField(
        default=True,
        help_text='Whether dealer is online and accepting orders'
    )
    bio = models.TextField(
        blank=True,
        help_text='Dealer bio and description'
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=5.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text='Average rating (0-5)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Dealer Profile'
        verbose_name_plural = 'Dealer Profiles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_available', '-rating']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f'{self.company_name} ({self.user.full_name})'

    def is_in_coverage(self, lat, lon):
        """
        Check if a point is within delivery coverage radius using Haversine formula.
        
        Args:
            lat: Latitude of the point
            lon: Longitude of the point
        
        Returns:
            bool: True if point is within coverage radius
        """
        if not self.latitude or not self.longitude:
            return False
        
        # Haversine formula to calculate distance between two points
        lon1, lat1, lon2, lat2 = map(radians, [self.longitude, self.latitude, lon, lat])
        
        # Haversine formula
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 6371  # Radius of earth in kilometers
        
        distance_km = c * r
        return distance_km <= self.coverage_radius_km


@receiver(post_save, sender=User)
def create_dealer_profile(sender, instance, created, **kwargs):
    """
    Signal to auto-create DealerProfile when a User with role='dealer' is created.
    """
    if created and instance.role == 'dealer':
        DealerProfile.objects.get_or_create(
            user=instance,
            defaults={'company_name': instance.full_name}
        )


@receiver(post_save, sender=User)
def save_dealer_profile(sender, instance, **kwargs):
    """
    Signal to ensure DealerProfile exists for dealer users.
    """
    if instance.role == 'dealer' and hasattr(instance, 'dealer_profile'):
        instance.dealer_profile.save()

