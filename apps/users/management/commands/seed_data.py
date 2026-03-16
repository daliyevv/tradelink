"""
Management command to seed database with demo data for development.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear (to delete all data first)
"""

from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.products.models import Category, Product
from apps.dealers.models import DealerProfile
from apps.locations.models import Location

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with demo data for development'
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing data before seeding',
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        clear_data = options.get('clear', False)
        
        # Clear existing data if requested
        if clear_data:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            User.objects.all().delete()
            Category.objects.all().delete()
            Product.objects.all().delete()
            Location.objects.all().delete()
            DealerProfile.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Data cleared'))
        
        with transaction.atomic():
            # Create locations (Tashkent area)
            self.stdout.write(self.style.NOTICE('\n📍 Creating locations...'))
            locations = self._create_locations()
            
            # Create manufacturers
            self.stdout.write(self.style.NOTICE('\n👨‍🏭 Creating manufacturers...'))
            manufacturers = self._create_manufacturers()
            
            # Create dealers
            self.stdout.write(self.style.NOTICE('\n🚚 Creating dealers...'))
            dealers = self._create_dealers(locations)
            
            # Create store owners
            self.stdout.write(self.style.NOTICE('\n🏪 Creating store owners...'))
            stores = self._create_store_owners()
            
            # Create categories
            self.stdout.write(self.style.NOTICE('\n📂 Creating categories...'))
            categories = self._create_categories()
            
            # Create products
            self.stdout.write(self.style.NOTICE('\n📦 Creating products...'))
            products = self._create_products(manufacturers, categories)
            
            # Summary
            self.stdout.write(self.style.SUCCESS('\n✓ Seed data created successfully!'))
            self.stdout.write(self.style.SUCCESS(f'\n Summary:'))
            self.stdout.write(self.style.SUCCESS(f'  • Manufacturers: {len(manufacturers)}'))
            self.stdout.write(self.style.SUCCESS(f'  • Dealers: {len(dealers)}'))
            self.stdout.write(self.style.SUCCESS(f'  • Store Owners: {len(stores)}'))
            self.stdout.write(self.style.SUCCESS(f'  • Categories: {len(categories)}'))
            self.stdout.write(self.style.SUCCESS(f'  • Products: {len(products)}'))
            self.stdout.write(self.style.SUCCESS(f'  • Locations: {len(locations)}'))
    
    def _create_locations(self):
        """Create test locations in Tashkent area."""
        locations = []
        tashkent_areas = [
            ('Tashkent City', Decimal('41.3063'), Decimal('69.2788')),
            ('Chilonzor', Decimal('41.2995'), Decimal('69.2401')),
            ('Yunusabad', Decimal('41.3284'), Decimal('69.2401')),
            ('Mirabad', Decimal('41.3407'), Decimal('69.1906')),
            ('Shaykhontohur', Decimal('41.2897'), Decimal('69.1701')),
        ]
        
        for name, lat, lng in tashkent_areas:
            location, created = Location.objects.get_or_create(
                city=name,
                defaults={
                    'latitude': lat,
                    'longitude': lng,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  ✓ {name}')
            locations.append(location)
        
        return locations
    
    def _create_manufacturers(self):
        """Create manufacturer users."""
        manufacturers = []
        manufacturer_data = [
            ('+998901112222', 'Samsung Uzbekistan', 'Samsung'),
            ('+998901113333', 'Huawei Central Asia', 'Huawei'),
        ]
        
        for phone, full_name, company in manufacturer_data:
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'full_name': full_name,
                    'role': 'manufacturer',
                    'is_verified': True,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  ✓ {full_name}')
            manufacturers.append(user)
        
        return manufacturers
    
    def _create_dealers(self, locations):
        """Create dealer users with profiles."""
        dealers = []
        dealer_data = [
            ('+998902221111', 'Qora Diller 1', 'Qora Diller Kompaniyasi', 0),
            ('+998902222222', 'Qora Diller 2', 'Qora Diller 2 LLC', 1),
            ('+998902223333', 'Qora Diller 3', 'Qora Diller 3 AJ', 2),
        ]
        
        for phone, full_name, business_name, location_idx in dealer_data:
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'full_name': full_name,
                    'role': 'dealer',
                    'is_verified': True,
                    'is_active': True,
                }
            )
            
            # Create dealer profile
            profile, profile_created = DealerProfile.objects.get_or_create(
                user=user,
                defaults={
                    'business_name': business_name,
                    'location': locations[location_idx % len(locations)],
                    'coverage_radius': Decimal('15.5'),
                    'is_available': True,
                    'phone_number': phone,
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ {full_name} → {business_name}')
            dealers.append(user)
        
        return dealers
    
    def _create_store_owners(self):
        """Create store owner users."""
        stores = []
        store_data = [
            ('+998903331111', "Abdulloh's Shop"),
            ('+998903332222', 'Yasmin Store'),
            ('+998903333333', 'TashMart'),
            ('+998903334444', 'Bozor.uz'),
            ('+998903335555', 'Turli Mahsulotlar'),
        ]
        
        for phone, full_name in store_data:
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'full_name': full_name,
                    'role': 'store',
                    'is_verified': True,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  ✓ {full_name}')
            stores.append(user)
        
        return stores
    
    def _create_categories(self):
        """Create product categories."""
        categories = []
        category_data = [
            ('Oziq-Ovqat', 'oziq-ovqat', 'Tabiiy oziq-ovqat mahsulotlari'),
            ('Kiyim-Kechak', 'kiyim-kechak', "Erkaklar, ayollar va bolalar kiyimi"),
            ('Elektronika', 'elektronika', 'Mobil telefonlar, kompyuterlar, gadjetlar'),
        ]
        
        for name, slug, description in category_data:
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'description': description,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  ✓ {name}')
            categories.append(category)
        
        return categories
    
    def _create_products(self, manufacturers, categories):
        """Create sample products."""
        products = []
        product_data = [
            # Electronics
            ('Samsung Galaxy S24', 'samsung-galaxy-s24', categories[2], manufacturers[0], '5000.00', 100),
            ('Samsung Galaxy A15', 'samsung-galaxy-a15', categories[2], manufacturers[0], '2500.00', 150),
            ('Huawei Mate 60', 'huawei-mate-60', categories[2], manufacturers[1], '4200.00', 80),
            ('Huawei Nova 12', 'huawei-nova-12', categories[2], manufacturers[1], '2200.00', 120),
            
            # Clothing
            ('Erkak Koftai Qora', 'erkak-koftai-qora', categories[1], manufacturers[0], '150.00', 200),
            ('Ayol Elbisasi Qizil', 'ayol-elbisasi-qizil', categories[1], manufacturers[0], '200.00', 180),
            ('Bolalar Shirtka', 'bolalar-shirtka', categories[1], manufacturers[1], '80.00', 300),
            
            # Food
            ('Buqday Uni', 'buqday-uni', categories[0], manufacturers[0], '25.00', 500),
            ('Palitre Sut', 'palitre-sut', categories[0], manufacturers[1], '12.50', 400),
            ('Yog\'', 'yog', categories[0], manufacturers[1], '35.00', 250),
        ]
        
        for name, slug, category, manufacturer, price, stock in product_data:
            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'category': category,
                    'manufacturer': manufacturer,
                    'price': Decimal(price),
                    'stock': stock,
                    'description': f'{name} — {category.description}',
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  ✓ {name} ({category.name}) — {int(price):,} som')
            products.append(product)
        
        return products
