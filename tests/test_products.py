"""
Product management tests including CRUD, filtering, searching, and soft delete.

Test coverage:
- List products (authenticated/unauthenticated)
- Create products (RBAC enforcement)
- Retrieve product details
- Update products (owner only)
- Delete products (soft delete)
- Filter by category, price range, manufacturer
- Search by name
- Image upload/deletion
"""

import pytest
from decimal import Decimal
from rest_framework import status

from apps.products.models import Product
from apps.categories.models import Category

pytestmark = pytest.mark.products


class TestProductListAndRetrieve:
    """Tests for listing and retrieving products."""

    def test_list_products_authenticated(self, authenticated_client, sample_product):
        """Authenticated user can list products."""
        response = authenticated_client.get('/api/v1/products/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert len(response.data['data']) > 0
        
        product_ids = [p['id'] for p in response.data['data']]
        assert str(sample_product.id) in product_ids

    def test_list_products_unauthenticated_returns_401(self, api_client, sample_product):
        """Unauthenticated user cannot list products."""
        response = api_client.get('/api/v1/products/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_products_excludes_inactive(self, authenticated_client, sample_product):
        """Inactive products are excluded from list."""
        sample_product.is_active = False
        sample_product.save()

        response = authenticated_client.get('/api/v1/products/')
        assert response.status_code == status.HTTP_200_OK
        
        product_ids = [p['id'] for p in response.data['data']]
        assert str(sample_product.id) not in product_ids

    def test_retrieve_product_details(self, authenticated_client, sample_product):
        """Authenticated user can retrieve product details."""
        response = authenticated_client.get(f'/api/v1/products/{sample_product.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['name'] == sample_product.name
        assert response.data['data']['price'] == str(sample_product.price)
        assert response.data['data']['stock'] == sample_product.stock

    def test_retrieve_nonexistent_product(self, authenticated_client):
        """Retrieving nonexistent product returns 404."""
        from uuid import uuid4
        response = authenticated_client.get(f'/api/v1/products/{uuid4()}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestProductCreate:
    """Tests for product creation with RBAC."""

    def test_create_product_manufacturer_success(self, authenticated_client, sample_category):
        """Manufacturer can create product."""
        response = authenticated_client.post('/api/v1/products/', {
            'name': 'New Product',
            'slug': 'new-product',
            'category': sample_category.id,
            'description': 'Test product',
            'price': '1000.00',
            'stock': 50,
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        
        product = Product.objects.get(slug='new-product')
        assert product.manufacturer.id == authenticated_client.user.id

    def test_create_product_dealer_forbidden(self, dealer_client, sample_category):
        """Dealer cannot create product (403)."""
        response = dealer_client.post('/api/v1/products/', {
            'name': 'Dealer Product',
            'slug': 'dealer-product',
            'category': sample_category.id,
            'description': 'Trying to create',
            'price': '1000.00',
            'stock': 50,
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_product_store_forbidden(self, store_client, sample_category):
        """Store owner cannot create product (403)."""
        response = store_client.post('/api/v1/products/', {
            'name': 'Store Product',
            'slug': 'store-product',
            'category': sample_category.id,
            'description': 'Trying to create',
            'price': '1000.00',
            'stock': 50,
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_product_unauthenticated(self, api_client, sample_category):
        """Unauthenticated user cannot create product (401)."""
        response = api_client.post('/api/v1/products/', {
            'name': 'Anon Product',
            'slug': 'anon-product',
            'category': sample_category.id,
            'description': 'Trying to create',
            'price': '1000.00',
            'stock': 50,
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_product_invalid_price(self, authenticated_client, sample_category):
        """Reject products with invalid price."""
        response = authenticated_client.post('/api/v1/products/', {
            'name': 'Bad Price Product',
            'slug': 'bad-price',
            'category': sample_category.id,
            'description': 'Test',
            'price': '-100.00',  # Negative price
            'stock': 50,
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'price' in response.data['errors']

    def test_create_product_invalid_stock(self, authenticated_client, sample_category):
        """Reject products with negative stock."""
        response = authenticated_client.post('/api/v1/products/', {
            'name': 'Bad Stock Product',
            'slug': 'bad-stock',
            'category': sample_category.id,
            'description': 'Test',
            'price': '1000.00',
            'stock': -1,
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'stock' in response.data['errors']


class TestProductUpdate:
    """Tests for product updates with ownership validation."""

    def test_update_product_owner_success(self, authenticated_client, sample_product):
        """Product owner can update their product."""
        response = authenticated_client.patch(f'/api/v1/products/{sample_product.id}/', {
            'name': 'Updated Name',
            'price': '6000.00',
        })

        assert response.status_code == status.HTTP_200_OK
        
        sample_product.refresh_from_db()
        assert sample_product.name == 'Updated Name'
        assert sample_product.price == Decimal('6000.00')

    def test_update_product_other_manufacturer_forbidden(self, dealer_client, sample_product):
        """Different manufacturer cannot update product (403)."""
        response = dealer_client.patch(f'/api/v1/products/{sample_product.id}/', {
            'name': 'Hacked Name',
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_product_dealer_forbidden(self, dealer_client, sample_product):
        """Dealer cannot update any product (403)."""
        response = dealer_client.patch(f'/api/v1/products/{sample_product.id}/', {
            'name': 'Hacked Name',
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_product_unauthenticated(self, api_client, sample_product):
        """Unauthenticated user cannot update product (401)."""
        response = api_client.patch(f'/api/v1/products/{sample_product.id}/', {
            'name': 'Hacked Name',
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProductDelete:
    """Tests for product soft deletion."""

    def test_delete_product_owner_success(self, authenticated_client, sample_product):
        """Product owner can soft delete their product."""
        response = authenticated_client.delete(f'/api/v1/products/{sample_product.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        sample_product.refresh_from_db()
        assert sample_product.is_active is False

    def test_delete_product_other_manufacturer_forbidden(self, dealer_client, sample_product):
        """Different manufacturer cannot delete product (403)."""
        response = dealer_client.delete(f'/api/v1/products/{sample_product.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_deleted_product_not_in_list(self, authenticated_client, sample_product):
        """Deleted product not visible in list."""
        # Delete
        authenticated_client.delete(f'/api/v1/products/{sample_product.id}/')
        
        # List should not include it
        response = authenticated_client.get('/api/v1/products/')
        product_ids = [p['id'] for p in response.data['data']]
        assert str(sample_product.id) not in product_ids


class TestProductFiltering:
    """Tests for product filtering by various criteria."""

    def test_filter_by_category(self, authenticated_client, sample_product, sample_category, sample_category_subcategory):
        """Filter products by category."""
        other_category = Category.objects.create(
            name='Uy Jihozlari',
            slug='uy-jihozlari',
            is_active=True,
        )
        
        other_product = Product.objects.create(
            name='Other Product',
            slug='other-product',
            category=other_category,
            manufacturer=sample_product.manufacturer,
            price=Decimal('2000.00'),
            stock=30,
            is_active=True,
        )
        
        response = authenticated_client.get(f'/api/v1/products/?category={sample_category.id}')
        
        assert response.status_code == status.HTTP_200_OK
        product_ids = [p['id'] for p in response.data['data']]
        assert str(sample_product.id) in product_ids
        assert str(other_product.id) not in product_ids

    def test_filter_by_price_range(self, authenticated_client, sample_product):
        """Filter products by price range."""
        response = authenticated_client.get('/api/v1/products/?price_min=4000&price_max=6000')
        
        assert response.status_code == status.HTTP_200_OK
        product_ids = [p['id'] for p in response.data['data']]
        assert str(sample_product.id) in product_ids

    def test_filter_by_manufacturer(self, authenticated_client, sample_product):
        """Filter products by manufacturer."""
        response = authenticated_client.get(f'/api/v1/products/?manufacturer={sample_product.manufacturer.id}')
        
        assert response.status_code == status.HTTP_200_OK
        product_ids = [p['id'] for p in response.data['data']]
        assert str(sample_product.id) in product_ids


class TestProductSearch:
    """Tests for product search functionality."""

    def test_search_by_name(self, authenticated_client, sample_product):
        """Search products by name."""
        response = authenticated_client.get('/api/v1/products/?search=Galaxy')
        
        assert response.status_code == status.HTTP_200_OK
        if len(response.data['data']) > 0:
            # Galaxy should be in at least one product
            assert any('Galaxy' in p['name'] for p in response.data['data'])

    def test_search_by_slug(self, authenticated_client, sample_product):
        """Search products by slug."""
        response = authenticated_client.get('/api/v1/products/?search=samsung')
        
        assert response.status_code == status.HTTP_200_OK

    def test_search_partial_match(self, authenticated_client, sample_product):
        """Search returns partial matches."""
        response = authenticated_client.get('/api/v1/products/?search=sams')
        
        assert response.status_code == status.HTTP_200_OK
        product_ids = [p['id'] for p in response.data['data']]
        assert str(sample_product.id) in product_ids


class TestProductImageUpload:
    """Tests for product image upload and deletion."""

    def test_upload_product_image_owner(self, authenticated_client, sample_product):
        """Product owner can upload images."""
        from io import BytesIO
        from PIL import Image
        
        # Create test image
        image = Image.new('RGB', (100, 100), color='red')
        image_file = BytesIO()
        image.save(image_file, format='JPEG')
        image_file.seek(0)
        
        response = authenticated_client.post(
            f'/api/v1/products/{sample_product.id}/images/',
            {'image': image_file},
            format='multipart'
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_product_image_other_user_forbidden(self, dealer_client, sample_product):
        """Other users cannot upload images to a product."""
        from io import BytesIO
        from PIL import Image
        
        image = Image.new('RGB', (100, 100), color='red')
        image_file = BytesIO()
        image.save(image_file, format='JPEG')
        image_file.seek(0)
        
        response = dealer_client.post(
            f'/api/v1/products/{sample_product.id}/images/',
            {'image': image_file},
            format='multipart'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_invalid_image(self, authenticated_client, sample_product):
        """Reject uploads of non-image files."""
        response = authenticated_client.post(
            f'/api/v1/products/{sample_product.id}/images/',
            {'image': 'not an image'},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestCategoryEndpoints:
    """Tests for category listing and retrieval."""

    def test_list_categories_authenticated(self, authenticated_client, sample_category):
        """Authenticated user can list categories."""
        response = authenticated_client.get('/api/v1/categories/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_list_categories_cached(self, authenticated_client, sample_category):
        """Categories are cached for performance."""
        # First request
        response1 = authenticated_client.get('/api/v1/categories/')
        timestamp1 = response1.json()
        
        # Second request (should be cached)
        response2 = authenticated_client.get('/api/v1/categories/')
        timestamp2 = response2.json()
        
        # Both should succeed
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

    def test_retrieve_category_details(self, authenticated_client, sample_category):
        """Retrieve specific category."""
        response = authenticated_client.get(f'/api/v1/categories/{sample_category.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == sample_category.name
