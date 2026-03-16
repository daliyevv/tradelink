from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from apps.products.models import Category


@receiver(post_save, sender=Category)
def invalidate_category_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate category tree cache when a category is saved.
    """
    cache.delete('category_tree')


@receiver(post_delete, sender=Category)
def invalidate_category_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate category tree cache when a category is deleted.
    """
    cache.delete('category_tree')
