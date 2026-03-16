"""
API Testing Guide for TradeLink

This guide helps you test the API endpoints during development.
"""

# ===========================
# Testing with Swagger UI
# ===========================

"""
The easiest way to test during development:

1. Start the server:
   python manage.py runserver

2. Navigate to Swagger UI:
   http://localhost:8000/api/docs/

3. Click "Authorize" button (top right)

4. Enter token in the dialog:
   Bearer <your_access_token>

5. Try endpoints interactively

Benefits:
- No command line needed
- See request/response format
- Try different filters
- Built-in documentation
"""

# ===========================
# Testing with curl
# ===========================

"""
Command line testing:

1. Test without authentication (public endpoints):
   curl -X GET http://localhost:8000/api/v1/categories/

2. Get token (login):
   curl -X POST http://localhost:8000/api/v1/auth/verify-otp/ \\
     -H "Content-Type: application/json" \\
     -d '{
       "phone": "+998901234567",
       "otp": "123456"
     }'
   
   Save the "access" token from response

3. Use token in API calls:
   curl -X GET http://localhost:8000/api/v1/products/ \\
     -H "Authorization: Bearer <access_token>"

4. Filter results:
   curl -X GET "http://localhost:8000/api/v1/products/?search=samsung" \\
     -H "Authorization: Bearer <access_token>"

5. Create resource:
   curl -X POST http://localhost:8000/api/v1/products/ \\
     -H "Content-Type: application/json" \\
     -H "Authorization: Bearer <access_token>" \\
     -d '{
       "name": "Samsung A53",
       "description": "New phone",
       "price": 300.00,
       "stock": 50,
       "unit": "dona",
       "min_order_qty": 5
     }'

6. Update resource:
   curl -X PATCH http://localhost:8000/api/v1/products/{id}/ \\
     -H "Content-Type: application/json" \\
     -H "Authorization: Bearer <access_token>" \\
     -d '{"price": 280.00}'

7. Delete resource:
   curl -X DELETE http://localhost:8000/api/v1/products/{id}/ \\
     -H "Authorization: Bearer <access_token>"

8. Refresh token:
   curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \\
     -H "Content-Type: application/json" \\
     -d '{"refresh": "<refresh_token>"}'
"""

# ===========================
# Testing with Python requests
# ===========================

"""
In a Python script:

import requests
import json

BASE_URL = 'http://localhost:8000/api/v1'

# 1. Login
login_data = {
    'phone': '+998901234567',
    'otp': '123456'
}
resp = requests.post(f'{BASE_URL}/auth/verify-otp/', json=login_data)
tokens = resp.json()['data']
access_token = tokens['access']
refresh_token = tokens['refresh']

print(f"Logged in. Access token: {access_token[:20]}...")

# 2. Prepare headers
headers = {'Authorization': f'Bearer {access_token}'}

# 3. List products
resp = requests.get(f'{BASE_URL}/products/', headers=headers)
products = resp.json()
print(f"Found {products['data']['count']} products")
print(f"First product: {products['data']['results'][0]}")

# 4. Search products
resp = requests.get(
    f'{BASE_URL}/products/',
    headers=headers,
    params={'search': 'samsung', 'ordering': '-price'}
)
search_results = resp.json()['data']['results']
print(f"Search found {len(search_results)} products")

# 5. Get single product
product_id = products['data']['results'][0]['id']
resp = requests.get(f'{BASE_URL}/products/{product_id}/', headers=headers)
product = resp.json()['data']
print(f"Product details: {json.dumps(product, indent=2)}")

# 6. Create product
product_data = {
    'name': 'New Product',
    'description': 'Description here',
    'price': '100.00',
    'stock': 50,
    'unit': 'dona',
    'min_order_qty': 5,
    'category': 'category-uuid'
}
resp = requests.post(f'{BASE_URL}/products/', json=product_data, headers=headers)
if resp.status_code == 201:
    new_product = resp.json()['data']
    print(f"Created product: {new_product['id']}")
else:
    errors = resp.json()['errors']
    print(f"Error creating product: {errors}")

# 7. Update product
update_data = {'price': '120.00'}
resp = requests.patch(
    f'{BASE_URL}/products/{product_id}/',
    json=update_data,
    headers=headers
)
updated_product = resp.json()['data']
print(f"Updated price to {updated_product['price']}")

# 8. Delete product
resp = requests.delete(f'{BASE_URL}/products/{product_id}/', headers=headers)
if resp.status_code == 204:
    print("Product deleted")

# 9. Refresh token
refresh_data = {'refresh': refresh_token}
resp = requests.post(f'{BASE_URL}/auth/token/refresh/', json=refresh_data)
new_tokens = resp.json()['data']
new_access_token = new_tokens['access']
print(f"Token refreshed")

# 10. Logout (blacklist token)
logout_data = {'refresh': refresh_token}
resp = requests.post(f'{BASE_URL}/auth/logout/', json=logout_data, headers=headers)
print("Logged out")
"""

# ===========================
# Testing with Postman
# ===========================

"""
Using Postman (GUI tool):

1. Download and install Postman: https://www.postman.com/downloads/

2. Create a new collection "TradeLink"

3. Create a new environment with variables:
   - base_url: http://localhost:8000/api/v1
   - access_token: (leave empty, will fill after login)
   - refresh_token: (leave empty, will fill after login)

4. Create requests:

   a) Login (POST):
      URL: {{base_url}}/auth/verify-otp/
      Body (JSON):
      {
        "phone": "+998901234567",
        "otp": "123456"
      }
      
      In Tests tab, add script to save token:
      var jsonData = pm.response.json();
      pm.environment.set("access_token", jsonData.data.access);
      pm.environment.set("refresh_token", jsonData.data.refresh);

   b) Get Products (GET):
      URL: {{base_url}}/products/
      Header: 
        Authorization: Bearer {{access_token}}
      
      Params:
        Key: page, Value: 1
        Key: search, Value: samsung

   c) Create Product (POST):
      URL: {{base_url}}/products/
      Header:
        Authorization: Bearer {{access_token}}
        Content-Type: application/json
      Body (JSON):
      {
        "name": "Product Name",
        "description": "Description",
        "price": "100.00",
        "stock": 50,
        "unit": "dona",
        "min_order_qty": 5,
        "category": "category-id"
      }

5. Run requests and view responses

6. Use Postman's auto-complete for API exploration
"""

# ===========================
# Common HTTP Status Codes
# ===========================

"""
200 OK              ✓ Request successful, resource returned
201 Created         ✓ Resource created successfully
204 No Content      ✓ Request successful, no content (DELETE)
400 Bad Request     ✗ Invalid request (validation error)
401 Unauthorized    ✗ Token missing or invalid
403 Forbidden       ✗ No permission for this action
404 Not Found       ✗ Resource doesn't exist
429 Too Many        ✗ Rate limit exceeded
500 Server Error    ✗ Server error (bug in backend)

Always check status_code before using response.json()
"""

# ===========================
# End-to-End Test Scenario
# ===========================

"""
Test the complete user journey:

1. User Registration
   POST /api/v1/auth/register/
   Body: {"phone": "+998901234567", "full_name": "Test User", "role": "store"}
   Expected: {"success": true, "data": {...}, "message": "OTP yuborildi"}

2. OTP Verification (login)
   POST /api/v1/auth/verify-otp/
   Body: {"phone": "+998901234567", "otp": "123456"}
   Expected: {"success": true, "data": {"access": "...", "refresh": "..."}}
   Save tokens

3. Get Categories
   GET /api/v1/categories/
   Header: Authorization: Bearer {access_token}
   Expected: List of product categories

4. Search Products
   GET /api/v1/products/?search=phone&category={category_id}
   Header: Authorization: Bearer {access_token}
   Expected: Filtered products list

5. Get Single Product
   GET /api/v1/products/{product_id}/
   Header: Authorization: Bearer {access_token}
   Expected: Product details

6. Add to Cart
   POST /api/v1/cart/items/
   Header: Authorization: Bearer {access_token}
   Body: {"product": "{product_id}", "quantity": 2}
   Expected: {"success": true, "data": {...}, "message": "..."}

7. Checkout (Create Order)
   POST /api/v1/cart/checkout/
   Header: Authorization: Bearer {access_token}
   Body: {"delivery_address": "...", "delivery_location": {"lat": ..., "lng": ...}}
   Expected: Order created, cart cleared

8. Get My Orders
   GET /api/v1/orders/
   Header: Authorization: Bearer {access_token}
   Expected: List of user's orders

9. Refresh Token (when expires)
   POST /api/v1/auth/token/refresh/
   Body: {"refresh": "{refresh_token}"}
   Expected: New access token

10. Logout
    POST /api/v1/auth/logout/
    Header: Authorization: Bearer {access_token}
    Body: {"refresh": "{refresh_token}"}
    Expected: {"success": true, ...}

If everything returns 200/201 with success: true, the API is working!
"""

# ===========================
# Debugging Tips
# ===========================

"""
1. Check server logs:
   Look at Django console output for errors
   
2. Check response status:
   Even if response looks wrong, first check status_code
   
3. Verify token is correct:
   JWT tokens are long strings starting with "eyJ..."
   
4. Use same token for all requests:
   Don't get a new token for every request
   
5. Check CORS settings:
   If requests from frontend fail with CORS error,
   verify CORS_ALLOWED_ORIGINS in .env
   
6. Enable debug mode in development:
   DEBUG=True in .env shows detailed error pages
   
7. Check database connections:
   python manage.py dbshell
   to verify database is accessible
   
8. Test with curl first:
   Before building GUI, test API with curl
   to isolate frontend/backend issues
"""
