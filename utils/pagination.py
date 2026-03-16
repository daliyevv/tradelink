"""
Pagination classes for API responses.
"""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Standard pagination with 20 items per page."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargePagination(PageNumberPagination):
    """Pagination for large datasets with 50 items per page."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class SmallPagination(PageNumberPagination):
    """Pagination for small datasets with 10 items per page."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
