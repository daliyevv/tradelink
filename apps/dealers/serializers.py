from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import DealerProfile

User = get_user_model()


class ManufacturerSimpleSerializer(serializers.ModelSerializer):
    """
    Simple manufacturer serializer for dealer partnerships.
    """

    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'phone', 'full_name', 'role', 'role_display']
        read_only_fields = ['id']


class DealerProfileListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for dealer list view.
    Includes distance_km field for nearby queries.
    """

    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = DealerProfile
        fields = [
            'id',
            'user',
            'user_phone',
            'user_name',
            'company_name',
            'coverage_radius_km',
            'is_available',
            'rating',
            'distance_km',
        ]
        read_only_fields = ['id', 'user']

    def get_distance_km(self, obj):
        """
        Return distance in km if available in context.
        Populated by nearby view's annotate(distance_km=...).
        """
        if hasattr(obj, 'distance_km'):
            return float(obj.distance_km)
        return None


class DealerProfileDetailSerializer(serializers.ModelSerializer):
    """
    Full dealer profile serializer with all relationships.
    """

    user = serializers.StringRelatedField(read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    manufacturers = ManufacturerSimpleSerializer(many=True, read_only=True)
    location_coords = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = DealerProfile
        fields = [
            'id',
            'user',
            'user_phone',
            'user_email',
            'user_avatar',
            'company_name',
            'location_coords',
            'coverage_radius_km',
            'manufacturers',
            'is_available',
            'bio',
            'rating',
            'created_at',
            'updated_at',
            'distance_km',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'rating']

    def get_user_avatar(self, obj):
        """Return absolute URL for user avatar."""
        if obj.user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
            return obj.user.avatar.url
        return None

    def get_location_coords(self, obj):
        """Return location as GeoJSON Point."""
        if obj.location:
            return {
                'type': 'Point',
                'coordinates': [obj.location.x, obj.location.y]
            }
        return None

    def get_distance_km(self, obj):
        """Return distance in km if available in context."""
        if hasattr(obj, 'distance_km'):
            return float(obj.distance_km)
        return None


class DealerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating dealer profile.
    """

    location_coords = serializers.SerializerMethodField()

    class Meta:
        model = DealerProfile
        fields = [
            'company_name',
            'coverage_radius_km',
            'is_available',
            'bio',
            'location_coords',
        ]

    def get_location_coords(self, obj):
        """Return location as GeoJSON Point."""
        if obj.location:
            return {
                'type': 'Point',
                'coordinates': [obj.location.x, obj.location.y]
            }
        return None


class DealerLocationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating dealer GPS location.
    Expects GeoJSON Point format: {"type": "Point", "coordinates": [lng, lat]}
    """

    latitude = serializers.FloatField(write_only=True)
    longitude = serializers.FloatField(write_only=True)
    location_coords = serializers.SerializerMethodField()

    class Meta:
        model = DealerProfile
        fields = ['latitude', 'longitude', 'location_coords']

    def get_location_coords(self, obj):
        """Return location as GeoJSON Point."""
        if obj.location:
            return {
                'type': 'Point',
                'coordinates': [obj.location.x, obj.location.y]
            }
        return None

    def validate(self, data):
        """Validate coordinates are within valid range."""
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if latitude is not None and longitude is not None:
            if not (-90 <= latitude <= 90):
                raise serializers.ValidationError(
                    {'latitude': 'Latitude must be between -90 and 90'}
                )
            if not (-180 <= longitude <= 180):
                raise serializers.ValidationError(
                    {'longitude': 'Longitude must be between -180 and 180'}
                )

        return data

    def create(self, validated_data):
        """Not used - update only."""
        pass

    def update(self, instance, validated_data):
        """Update dealer location from coordinates."""
        latitude = validated_data.pop('latitude', None)
        longitude = validated_data.pop('longitude', None)

        if latitude is not None and longitude is not None:
            from django.contrib.gis.geos import Point
            instance.location = Point(longitude, latitude, srid=4326)

        return super().update(instance, validated_data)


class DealerAvailabilitySerializer(serializers.ModelSerializer):
    """
    Serializer for toggling dealer availability status.
    """

    class Meta:
        model = DealerProfile
        fields = ['is_available']
