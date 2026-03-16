from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.db.models import Prefetch
from math import radians, cos, sin, asin, sqrt

from utils.permissions import IsDealer
from utils.responses import success_response, error_response
from .models import DealerProfile
from .serializers import (
    DealerProfileListSerializer,
    DealerProfileDetailSerializer,
    DealerProfileUpdateSerializer,
    DealerLocationUpdateSerializer,
    DealerAvailabilitySerializer,
)


class DealerProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for dealer profile management.
    
    Endpoints:
    - GET /api/v1/dealers/ — List all active dealers (paginated)
    - GET /api/v1/dealers/{id}/ — Get dealer details
    - GET /api/v1/dealers/nearby/ — Find nearby dealers with distance
    - PATCH /api/v1/dealers/me/ — Update own profile (IsDealer)
    - POST /api/v1/dealers/me/location/ — Update GPS location
    - POST /api/v1/dealers/me/toggle-availability/ — Toggle online status
    
    RBAC Test Matrix:
    Action                   | Unauthenticated | Dealer | Store Owner | Other Dealer
    ----------------------- | --------------- | ------ | ----------- | ----
    GET list                | 401             | 200    | 200         | 200
    GET retrieve            | 401             | 200    | 200         | 200
    GET nearby              | 401             | 200*   | 200*        | 200*
    GET me                  | 401             | 200    | 403         | 403
    PATCH me                | 401             | 200    | 403         | 403
    POST location           | 401             | 200    | 403         | 403
    POST toggle-availability| 401             | 200    | 403         | 403
    
    * Nearby dealers endpoint needs authentication
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['company_name', 'bio', 'user__full_name']
    ordering_fields = ['rating', 'created_at']
    ordering = ['-rating']
    pagination_class = None  # Can be changed to PageNumberPagination

    def get_queryset(self):
        """Build optimized queryset with select_related and prefetch_related."""
        return DealerProfile.objects.filter(is_available=True).select_related(
            'user'
        ).prefetch_related(
            Prefetch('manufacturers')
        ).order_by('-rating')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return DealerProfileListSerializer
        elif self.action == 'nearby':
            return DealerProfileListSerializer
        elif self.action == 'update_location':
            return DealerLocationUpdateSerializer
        elif self.action == 'toggle_availability':
            return DealerAvailabilitySerializer
        elif self.action in ['update', 'partial_update']:
            return DealerProfileUpdateSerializer
        return DealerProfileDetailSerializer

    def list(self, request, *args, **kwargs):
        """List all active dealers."""
        response = super().list(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message='Dillerlar ro\'yxati',
            status_code=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        """Get dealer profile details."""
        dealer = self.get_object()
        serializer = self.get_serializer(dealer)
        return success_response(
            data=serializer.data,
            message='Diller profili',
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='nearby')
    def nearby(self, request):
        """
        Find nearby dealers based on GPS coordinates and optional radius.
        Results cached for 5 minutes per (lat, lng, radius) combination.
        
        Query Parameters:
        - lat (required): Latitude
        - lng (required): Longitude
        - radius_km (optional, default=10): Search radius in kilometers
        
        Returns: Dealers sorted by distance with distance_km field
        
        Example:
        GET /api/v1/dealers/nearby/?lat=41.3&lng=69.2&radius_km=15
        """
        latitude = request.query_params.get('lat')
        longitude = request.query_params.get('lng')
        radius_km = request.query_params.get('radius_km', 10)

        # Validate parameters
        if not latitude or not longitude:
            return error_response(
                errors={'lat': 'lat missing', 'lng': 'lng missing'},
                message='Latitude va longitude talab qilinadi',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            latitude = float(latitude)
            longitude = float(longitude)
            radius_km = float(radius_km)
        except ValueError:
            return error_response(
                errors={'error': 'lat, lng, va radius_km raqamlar bo\'lishi kerak'},
                message='Noto\'g\'ri parametr formati',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate coordinates
        if not (-90 <= latitude <= 90):
            return error_response(
                errors={'lat': 'Latitude must be between -90 and 90'},
                message='Noto\'g\'ri latitude',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        if not (-180 <= longitude <= 180):
            return error_response(
                errors={'lng': 'Longitude must be between -180 and 180'},
                message='Noto\'g\'ri longitude',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Create cache key from coordinates (rounded to 2 decimals for grouping)
        cache_key = f'nearby_dealers_{round(latitude, 2)}_{round(longitude, 2)}_{round(radius_km, 1)}'
        
        # Try to get from cache (5 minutes = 300 seconds)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return success_response(
                data=cached_data,
                message=f'{len(cached_data)} ta diller topildi (cached)',
                status_code=status.HTTP_200_OK
            )

        # Calculate distance using Haversine formula and filter dealers
        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate the great circle distance between two points on the earth (in kilometers)"""
            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
            dlon = lon2 - lon1 
            dlat = lat2 - lat1 
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a)) 
            r = 6371  # Radius of earth in kilometers
            return c * r

        # Get all active dealers with optimized query
        dealers = DealerProfile.objects.filter(is_available=True).select_related('user')
        dealers_with_distance = []
        
        for dealer in dealers:
            if dealer.latitude is not None and dealer.longitude is not None:
                distance = haversine_distance(latitude, longitude, dealer.latitude, dealer.longitude)
                if distance <= radius_km:
                    dealers_with_distance.append({
                        'dealer': dealer,
                        'distance_km': distance
                    })
        
        # Sort by distance
        dealers_with_distance.sort(key=lambda x: x['distance_km'])

        if not dealers_with_distance:
            # Cache empty result for 5 minutes
            cache.set(cache_key, [], 300)
            return success_response(
                data=[],
                message=f'{radius_km}km ichida diller topilmadi',
                status_code=status.HTTP_200_OK
            )

        # Serialize dealers
        dealers_list = [item['dealer'] for item in dealers_with_distance]
        serializer = DealerProfileListSerializer(dealers_list, many=True, context={'request': request})
        
        # Add distance to each dealer's data
        for i, dealer_data in enumerate(serializer.data):
            dealer_data['distance_km'] = dealers_with_distance[i]['distance_km']

        data = serializer.data
        
        # Cache for 5 minutes (300 seconds)
        cache.set(cache_key, data, 300)

        return success_response(
            data=data,
            message=f'{len(dealers_with_distance)} ta diller topildi',
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def my_profile(self, request):
        """
        GET /api/v1/dealers/me/ — Get current user's dealer profile
        PATCH /api/v1/dealers/me/ — Update current user's dealer profile
        Requires: IsDealer permission
        """
        # Check if user is a dealer
        if request.user.role != 'dealer':
            return error_response(
                message='Faqat dillerlar bu amaldan foydalana oladi',
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Get or create dealer profile
        dealer = get_object_or_404(DealerProfile, user=request.user)

        if request.method == 'GET':
            serializer = DealerProfileDetailSerializer(dealer, context={'request': request})
            return success_response(
                data=serializer.data,
                message='Sizning diller profili',
                status_code=status.HTTP_200_OK
            )

        elif request.method == 'PATCH':
            serializer = DealerProfileUpdateSerializer(
                dealer,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            if not serializer.is_valid():
                return error_response(
                    errors=serializer.errors,
                    message='Profil yangilanishida xato',
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            dealer = serializer.save()
            output_serializer = DealerProfileDetailSerializer(dealer, context={'request': request})
            return success_response(
                data=output_serializer.data,
                message='Profil muvaffaqiyatli yangilandi',
                status_code=status.HTTP_200_OK
            )

    @action(detail=False, methods=['post'], url_path='me/location')
    def update_location(self, request):
        """
        Update current dealer's GPS location.
        
        POST /api/v1/dealers/me/location/
        
        Request:
        {
            "latitude": 41.2995,
            "longitude": 69.2401
        }
        
        Response: Updated dealer profile with location_coords
        """
        # Check if user is a dealer
        if request.user.role != 'dealer':
            return error_response(
                message='Faqat dillerlar bu amaldan foydalana oladi',
                status_code=status.HTTP_403_FORBIDDEN
            )

        dealer = get_object_or_404(DealerProfile, user=request.user)

        serializer = DealerLocationUpdateSerializer(
            dealer,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Lokatsiya yangilanishida xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        dealer = serializer.save()
        output_serializer = DealerProfileDetailSerializer(dealer, context={'request': request})
        return success_response(
            data=output_serializer.data,
            message='Lokatsiya muvaffaqiyatli yangilandi',
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='me/toggle-availability')
    def toggle_availability(self, request):
        """
        Toggle dealer online/offline status.
        
        POST /api/v1/dealers/me/toggle-availability/
        
        Request: {} (empty body) - toggles current status
        or
        {
            "is_available": true/false
        }
        
        Response: Updated availability status
        """
        # Check if user is a dealer
        if request.user.role != 'dealer':
            return error_response(
                message='Faqat dillerlar bu amaldan foydalana oladi',
                status_code=status.HTTP_403_FORBIDDEN
            )

        dealer = get_object_or_404(DealerProfile, user=request.user)

        # Toggle availability if not specified in request
        if 'is_available' in request.data:
            dealer.is_available = request.data.get('is_available', False)
        else:
            dealer.is_available = not dealer.is_available

        dealer.save()

        serializer = DealerAvailabilitySerializer(dealer)
        status_text = 'Faol' if dealer.is_available else 'Nofaol'
        
        return success_response(
            data=serializer.data,
            message=f'Siz {status_text} holatga o\'ttingiz',
            status_code=status.HTTP_200_OK
        )
