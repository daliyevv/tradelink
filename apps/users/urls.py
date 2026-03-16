from django.urls import path

from .views import (
    SendOTPView,
    VerifyOTPView,
    CustomTokenRefreshView,
    LogoutView,
    ProfileView,
    UpdateProfileView,
)

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('auth/send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('auth/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    
    # Profile endpoints
    path('profile/me/', ProfileView.as_view(), name='profile_me'),
    path('profile/me/update/', UpdateProfileView.as_view(), name='update_profile_me'),
]
