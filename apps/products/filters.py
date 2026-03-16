import django_filters
from django.db.models import Q
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Product, Category


class ProductFilter(django_filters.FilterSet):
    """
    Custom filter for products with advanced filtering capabilities.
    """

    # Category filter including child categories
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.filter(is_active=True),
        method='filter_category',
        label='Category (includes subcategories)',
    )

    # Price range filters
    min_price = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='gte',
        label='Minimum Price',
    )
    max_price = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='lte',
        label='Maximum Price',
    )

    # Stock availability
    in_stock = django_filters.BooleanFilter(
        method='filter_in_stock',
        label='In Stock',
    )

    # Manufacturer filter
    manufacturer = django_filters.UUIDFilter(
        field_name='manufacturer__id',
        label='Manufacturer ID',
    )

    class Meta:
        model = Product
        fields = ['category', 'min_price', 'max_price', 'in_stock', 'manufacturer']

    def filter_category(self, queryset, name, value):
        """
        Filter products by category including products in child categories.
        """
        if not value:
            return queryset
        
        # Get the selected category and all its children
        category_ids = [value.id]
        
        # Recursively get all child category IDs
        def get_children_ids(parent_category):
            children = parent_category.children.filter(is_active=True)
            ids = []
            for child in children:
                ids.append(child.id)
                ids.extend(get_children_ids(child))
            return ids
        
        category_ids.extend(get_children_ids(value))
        
        return queryset.filter(category_id__in=category_ids)

    def filter_in_stock(self, queryset, name, value):
        """
        Filter products by stock availability.
        True = stock > 0, False = stock = 0
        """
        if value is None:
            return queryset
        
        if value:
            return queryset.filter(stock__gt=0)
        else:
            return queryset.filter(stock=0)
