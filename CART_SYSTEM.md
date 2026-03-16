# Cart System Implementation

## Overview
Complete shopping cart system for TradeLink with cart management, item tracking, and dealer selection.

## Models Created

### Cart Model (`apps/cart/models.py`)
- **Fields:**
  - `id`: UUID primary key
  - `owner`: OneToOneField(User) - Cart owner
  - `dealer`: ForeignKey(DealerProfile) - Selected delivery dealer (nullable)
  - `created_at`: DateTimeField (auto_now_add)
  - `updated_at`: DateTimeField (auto_now)

- **Properties:**
  - `total_price`: Sum of (quantity × price_snapshot) for all items
  - `total_items`: Sum of all item quantities
  - `is_empty`: Boolean indicating if cart has no items

- **Signal:** Auto-creates Cart when User is created

### CartItem Model (`apps/cart/models.py`)
- **Fields:**
  - `id`: UUID primary key
  - `cart`: ForeignKey(Cart)
  - `product`: ForeignKey(Product)
  - `quantity`: PositiveIntegerField (min 1)
  - `price_snapshot`: DecimalField - Product price at time of adding
  - `added_at`: DateTimeField (auto_now_add)
  - `updated_at`: DateTimeField (auto_now)

- **Constraints:**
  - Unique constraint on (cart, product)
  
- **Property:**
  - `subtotal`: quantity × price_snapshot

## API Endpoints

### 1. GET `/api/v1/cart/`
Retrieve current cart with all items, totals, and dealer info.

**Response:**
```json
{
  "id": "uuid",
  "total_items": 5,
  "total_price": 50000.00,
  "items": [
    {
      "id": "uuid",
      "product_id": "uuid",
      "product_name": "Mahsulot",
      "quantity": 2,
      "price_snapshot": 10000.00,
      "subtotal": 20000.00
    }
  ],
  "dealer": {
    "id": "uuid",
    "company_name": "Diller Co.",
    "coverage_radius_km": 15.0
  },
  "is_empty": false
}
```

### 2. POST `/api/v1/cart/items/`
Add item to cart.

**Request:**
```json
{
  "product_id": "uuid",
  "quantity": 2
}
```

**Validations:**
- Product must be active (`is_active=True`)
- Quantity ≥ product's `min_order_qty`
- Quantity ≤ product's available `stock`
- If dealer selected: product must be from dealer's manufacturers
- If product already in cart: quantity is added to existing

### 3. PATCH `/api/v1/cart/items/{id}/`
Update item quantity.

**Request:**
```json
{
  "quantity": 5
}
```

**Validations:**
- Quantity ≥ product's `min_order_qty`
- Quantity ≤ product's available `stock`

### 4. DELETE `/api/v1/cart/items/{id}/`
Remove item from cart.

### 5. POST `/api/v1/cart/select-dealer/`
Select delivery dealer for cart.

**Request:**
```json
{
  "dealer_id": "uuid"
}
```

**Validations:**
- Dealer must be available (`is_available=True`)
- If cart has items: all products must be from dealer's manufacturers

### 6. DELETE `/api/v1/cart/`
Clear all items from cart and remove dealer selection.

## Files Created/Modified

### New Files
- `apps/cart/models.py` - Cart and CartItem models with signals
- `apps/cart/views.py` - CartViewSet with all endpoints
- `apps/cart/serializers.py` - Serializers for all operations
- `apps/cart/permissions.py` - IsCartOwner permission
- `apps/cart/migrations/0001_initial.py` - Initial migration
- `apps/cart/admin.py` - Django admin interface

### Modified Files
- `apps/cart/urls.py` - Added router configuration

## Key Features

1. **Automatic Cart Creation**
   - Cart automatically created for each user via signals
   - OneToOne relationship ensures single cart per user

2. **Price Snapshots**
   - Product price captured at time of adding to cart
   - Historical price tracking for cart items

3. **Inventory Validation**
   - Real-time stock checking
   - Minimum order quantity enforcement
   - Product availability status verification

4. **Dealer Management**
   - Selectable delivery dealer per cart
   - Manufacturer-dealer validation
   - Automatic validation when selecting dealer

5. **Atomic Transactions**
   - Cart operations wrapped in database transactions
   - Data integrity guaranteed

## Admin Interface

- **Cart Admin:**
  - List carts with totals and dealer info
  - View cart items inline
  - Search by owner
  - Filter by dealer and date

- **CartItem Admin:**
  - View all cart items
  - Filter by cart owner
  - Read-only for data integrity
  - Grouped inline in Cart admin

## Business Logic

1. **Dealer Validation:**
   - When dealer is selected, all items must be from dealer's manufacturers
   - When adding item with dealer selected, item's manufacturer must be in dealer's list
   - When dealer removed, no validation needed

2. **Price Snapshots:**
   - Prices frozen when items added to cart
   - Prevents price changes affecting existing carts
   - Historical record for auditing

3. **Cart Persistence:**
   - Cart persists across sessions
   - Dealer selection persists
   - Items persist indefinitely unless cleared

## Database
- SQLite (development)
- PostgreSQL (production)
- Tables: `cart_cart`, `cart_cartitem`

## Permissions
- All endpoints require `IsAuthenticated`
- Cart operations automatically scoped to `request.user`
- No explicit permission checks needed (via OneToOne relationship)

## Testing Endpoints

```bash
# Get cart
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/v1/cart/

# Add item
curl -X POST -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "UUID", "quantity": 2}' \
  http://localhost:8000/api/v1/cart/items/

# Update item quantity
curl -X PATCH -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 5}' \
  http://localhost:8000/api/v1/cart/items/ITEM_ID/

# Remove item
curl -X DELETE -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/cart/items/ITEM_ID/

# Select dealer
curl -X POST -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dealer_id": "UUID"}' \
  http://localhost:8000/api/v1/cart/select-dealer/

# Clear cart
curl -X DELETE -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/cart/
```

## Migration Status
✓ Migrations created: `apps/cart/migrations/0001_initial.py`
✓ Migrations applied: `Applying cart.0001_initial... OK`
✓ Database tables created: `cart_cart`, `cart_cartitem`
