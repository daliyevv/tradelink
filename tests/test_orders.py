"""
Order management tests including checkout, status transitions, and cancellation.

Test coverage:
- Checkout (creates order, reduces stock, clears cart)
- Checkout validations (empty cart, out of stock, insufficient stock)
- Status transitions (valid/invalid flows)
- Order cancellation (pending only, not accepted/delivered)
- Order listing and retrieval with RBAC
"""

import pytest
from decimal import Decimal
from rest_framework import status

from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from apps.products.models import Product

pytestmark = pytest.mark.orders


class TestCheckout:
    """Tests for order checkout process."""

    def test_checkout_creates_order_and_reduces_stock(self, store_client, store_user, dealer_user, cart_with_items, sample_product, low_stock_product):
        """Checkout creates order, reduces stock, and clears cart."""
        # Get initial stock
        initial_stock = sample_product.stock
        
        response = store_client.post('/api/v1/orders/checkout/', {
            'dealer_id': dealer_user.id,
            'delivery_address': 'Tashkent, Chilonzor',
            'notes': 'Tezda yetkazib bering',
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        
        # Order should be created
        order = Order.objects.get(user=store_user)
        assert order.status == 'pending'
        assert order.total_amount > 0
        
        # Stock should be reduced
        sample_product.refresh_from_db()
        assert sample_product.stock == initial_stock - 5  # cart_with_items has 5
        
        # Cart should be cleared
        cart = Cart.objects.get(user=store_user)
        assert cart.items.count() == 0

    def test_checkout_insufficient_stock_fails(self, store_client, dealer_user):
        """Checkout fails when product stock insufficient."""
        # Create cart with out of stock product
        cart = Cart.objects.create(user=store_client.user)
        
        out_of_stock = Product.objects.create(
            name='Out of Stock',
            category_id=1,  # Assuming exists
            manufacturer_id=store_client.user.id,
            price=Decimal('1000.00'),
            stock=0,
            is_active=True,
        )
        
        CartItem.objects.create(
            cart=cart,
            product=out_of_stock,
            quantity=1,
        )
        
        response = store_client.post('/api/v1/orders/checkout/', {
            'dealer_id': dealer_user.id,
            'delivery_address': 'Test Address',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'stock' in response.data['errors'].lower() or 'insufficient' in response.data['errors'].lower()

    def test_checkout_empty_cart_fails(self, store_client, store_user, dealer_user):
        """Checkout fails when cart is empty."""
        # Ensure cart exists but is empty
        Cart.objects.get_or_create(user=store_user)
        
        response = store_client.post('/api/v1/orders/checkout/', {
            'dealer_id': dealer_user.id,
            'delivery_address': 'Test Address',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_checkout_requires_authentication(self, api_client):
        """Unauthenticated user cannot checkout."""
        response = api_client.post('/api/v1/orders/checkout/', {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_checkout_requires_delivery_address(self, store_client, dealer_user, cart_with_items):
        """Checkout requires delivery address."""
        response = store_client.post('/api/v1/orders/checkout/', {
            'dealer_id': dealer_user.id,
            # Missing delivery_address
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'delivery_address' in response.data['errors']

    def test_checkout_invalid_dealer(self, store_client):
        """Checkout fails with invalid dealer."""
        from uuid import uuid4
        response = store_client.post('/api/v1/orders/checkout/', {
            'dealer_id': uuid4(),
            'delivery_address': 'Test Address',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestOrderStatusTransitions:
    """Tests for valid and invalid order status transitions."""

    def test_dealer_accepts_order(self, dealer_client, dealer_user, sample_order):
        """Dealer can accept pending order."""
        response = dealer_client.patch(f'/api/v1/orders/{sample_order.id}/', {
            'status': 'accepted',
        })

        assert response.status_code == status.HTTP_200_OK
        
        sample_order.refresh_from_db()
        assert sample_order.status == 'accepted'
        assert sample_order.accepted_by == dealer_user

    def test_dealer_marks_delivered(self, dealer_client, dealer_user, accepted_order):
        """Dealer can mark accepted order as delivered."""
        response = dealer_client.patch(f'/api/v1/orders/{accepted_order.id}/', {
            'status': 'delivered',
        })

        assert response.status_code == status.HTTP_200_OK
        
        accepted_order.refresh_from_db()
        assert accepted_order.status == 'delivered'

    def test_invalid_status_transition_fails(self, dealer_client, sample_order):
        """Cannot transition to invalid status."""
        response = dealer_client.patch(f'/api/v1/orders/{sample_order.id}/', {
            'status': 'invalid_status',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_transition_backward(self, dealer_client, accepted_order):
        """Cannot transition from accepted back to pending."""
        response = dealer_client.patch(f'/api/v1/orders/{accepted_order.id}/', {
            'status': 'pending',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_only_assigned_dealer_can_update(self, api_client, sample_order):
        """Only assigned dealer can update order status."""
        # Create different dealer
        from apps.users.models import User
        other_dealer = User.objects.create_user(
            phone='+998905555555',
            full_name='Other Dealer',
            role='dealer',
            password='Test@1234567',
        )
        
        # Try to update as different dealer
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(other_dealer)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = api_client.patch(f'/api/v1/orders/{sample_order.id}/', {
            'status': 'accepted',
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestOrderCancellation:
    """Tests for order cancellation rules."""

    def test_store_owner_cancels_pending_order(self, store_client, sample_order):
        """Store owner can cancel pending order."""
        response = store_client.post(f'/api/v1/orders/{sample_order.id}/cancel/', {})

        assert response.status_code == status.HTTP_200_OK
        
        sample_order.refresh_from_db()
        assert sample_order.status == 'cancelled'

    def test_store_owner_cannot_cancel_accepted_order(self, store_client, accepted_order):
        """Store owner cannot cancel accepted order."""
        response = store_client.post(f'/api/v1/orders/{accepted_order.id}/cancel/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_store_owner_cannot_cancel_delivered_order(self, store_client, delivered_order):
        """Store owner cannot cancel delivered order."""
        response = store_client.post(f'/api/v1/orders/{delivered_order.id}/cancel/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_dealer_cannot_cancel_order(self, dealer_client, sample_order):
        """Dealer cannot cancel order."""
        response = dealer_client.post(f'/api/v1/orders/{sample_order.id}/cancel/', {})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cancellation_restores_stock(self, store_client, sample_order, sample_product):
        """Cancelling order restores product stock."""
        # Create order item
        initial_stock = sample_product.stock
        sample_product.stock -= 1
        sample_product.save()
        
        response = store_client.post(f'/api/v1/orders/{sample_order.id}/cancel/', {})

        assert response.status_code == status.HTTP_200_OK
        
        sample_product.refresh_from_db()
        # Stock should be restored
        assert sample_product.stock >= initial_stock


class TestOrderListing:
    """Tests for order listing with proper RBAC."""

    def test_store_owner_sees_own_orders(self, store_client, store_user, sample_order):
        """Store owner sees their own orders."""
        response = store_client.get('/api/v1/orders/')

        assert response.status_code == status.HTTP_200_OK
        order_ids = [o['id'] for o in response.data['data']]
        assert str(sample_order.id) in order_ids

    def test_store_owner_does_not_see_other_orders(self, store_client, db):
        """Store owner doesn't see other store owner's orders."""
        from apps.users.models import User
        other_store = User.objects.create_user(
            phone='+998906666666',
            full_name='Other Store',
            role='store',
            password='Test@1234567',
        )
        
        other_order = Order.objects.create(
            user=other_store,
            status='pending',
            total_amount=Decimal('1000.00'),
            delivery_address='Other Address',
        )
        
        response = store_client.get('/api/v1/orders/')
        order_ids = [o['id'] for o in response.data['data']]
        assert str(other_order.id) not in order_ids

    def test_dealer_sees_assigned_orders(self, dealer_client, dealer_user, sample_order):
        """Dealer sees orders assigned to them."""
        sample_order.dealer = dealer_user
        sample_order.save()
        
        response = dealer_client.get('/api/v1/orders/')

        assert response.status_code == status.HTTP_200_OK
        order_ids = [o['id'] for o in response.data['data']]
        assert str(sample_order.id) in order_ids

    def test_dealer_does_not_see_other_dealer_orders(self, dealer_client, db):
        """Dealer doesn't see orders from other dealers."""
        from apps.users.models import User
        other_dealer = User.objects.create_user(
            phone='+998907777777',
            full_name='Other Dealer',
            role='dealer',
            password='Test@1234567',
        )
        
        other_order = Order.objects.create(
            user_id=db.user.id,  # Different store
            dealer=other_dealer,
            status='pending',
            total_amount=Decimal('1000.00'),
            delivery_address='Other Address',
        )
        
        response = dealer_client.get('/api/v1/orders/')
        order_ids = [o['id'] for o in response.data['data']]
        assert str(other_order.id) not in order_ids


class TestOrderRetrieval:
    """Tests for retrieving order details."""

    def test_retrieve_order_details(self, store_client, sample_order):
        """Retrieve full order details."""
        response = store_client.get(f'/api/v1/orders/{sample_order.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(sample_order.id)
        assert response.data['status'] == sample_order.status
        assert response.data['total_amount'] == str(sample_order.total_amount)
        assert len(response.data['items']) > 0

    def test_retrieve_order_items(self, store_client, sample_order):
        """Order items included in retrieval."""
        response = store_client.get(f'/api/v1/orders/{sample_order.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'items' in response.data
        assert len(response.data['items']) > 0
        
        # Check first item
        item = response.data['items'][0]
        assert 'product' in item
        assert 'quantity' in item
        assert 'unit_price' in item

    def test_cannot_retrieve_other_user_order(self, store_client, db):
        """Cannot retrieve order from different user."""
        from apps.users.models import User
        other_user = User.objects.create_user(
            phone='+998908888888',
            full_name='Other User',
            role='store',
            password='Test@1234567',
        )
        
        other_order = Order.objects.create(
            user=other_user,
            status='pending',
            total_amount=Decimal('1000.00'),
            delivery_address='Test',
        )
        
        response = store_client.get(f'/api/v1/orders/{other_order.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_nonexistent_order(self, store_client):
        """Retrieving nonexistent order returns 404."""
        from uuid import uuid4
        response = store_client.get(f'/api/v1/orders/{uuid4()}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestOrderFiltering:
    """Tests for filtering orders by status."""

    def test_filter_pending_orders(self, store_client, sample_order, db):
        """Filter by pending status."""
        response = store_client.get('/api/v1/orders/?status=pending')

        assert response.status_code == status.HTTP_200_OK
        order_statuses = [o['status'] for o in response.data['data']]
        assert all(s == 'pending' for s in order_statuses)

    def test_filter_accepted_orders(self, store_client, accepted_order):
        """Filter by accepted status."""
        response = store_client.get('/api/v1/orders/?status=accepted')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_delivered_orders(self, dealer_client, delivered_order):
        """Filter by delivered status."""
        response = dealer_client.get('/api/v1/orders/?status=delivered')

        assert response.status_code == status.HTTP_200_OK
