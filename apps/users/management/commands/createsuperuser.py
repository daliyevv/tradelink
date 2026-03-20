"""
Custom createsuperuser management command.

Handles custom User model fields including phone and role.
Superusers are created with 'manufacturer' role by default.

Usage:
    python manage.py createsuperuser
    python manage.py createsuperuser --phone=+998901234567 --full-name="Admin User" --password=admin123
"""

from django.contrib.auth.management.commands.createsuperuser import Command as BaseCommand
from django.core.management import CommandError
from django.contrib.auth import get_user_model
import getpass

User = get_user_model()


class Command(BaseCommand):
    """
    Custom createsuperuser command for custom User model.
    """

    def add_arguments(self, parser):
        """Add custom arguments for phone and role."""
        parser.add_argument(
            '--phone',
            dest='phone',
            default=None,
            help='Superuser phone number (format: +998XXXXXXXXX)'
        )
        parser.add_argument(
            '--full-name',
            dest='full_name',
            default=None,
            help='Superuser full name'
        )
        parser.add_argument(
            '--password',
            dest='password',
            default=None,
            help='Superuser password (if omitted, will be prompted)'
        )

    def handle(self, *app_labels, **options):
        """
        Main command handler.
        """
        phone = options.get('phone')
        full_name = options.get('full_name')
        password = options.get('password')
        interactive = options.get('interactive', True)

        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING('⚠️  Superuser already exists!\n')
            )

        # Interactive mode
        if interactive:
            self.stdout.write(
                self.style.WARNING(
                    '\n🔑 Creating Superuser (Admin Account)\n'
                    '====================================\n'
                )
            )

            # Phone
            if not phone:
                while True:
                    phone = input('Phone number (format: +998XXXXXXXXX): ').strip()
                    if phone and phone.startswith('+998') and len(phone) == 13:
                        break
                    self.stdout.write(
                        self.style.ERROR('❌ Invalid format. Must be: +998XXXXXXXXX (13 digits)')
                    )

            # Full name
            if not full_name:
                while True:
                    full_name = input('Full name: ').strip()
                    if full_name:
                        break
                    self.stdout.write(
                        self.style.ERROR('❌ Full name cannot be empty')
                    )

            # Password
            if not password:
                while True:
                    password = getpass.getpass('Password: ')
                    if not password:
                        self.stdout.write(
                            self.style.ERROR('❌ Password cannot be empty')
                        )
                        continue

                    confirm_password = getpass.getpass('Confirm password: ')
                    if password == confirm_password:
                        break

                    self.stdout.write(
                        self.style.ERROR('❌ Passwords do not match')
                    )

            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('✓ Creating superuser...'))
            self.stdout.write('='*50 + '\n')

        # Non-interactive mode (all must be provided)
        else:
            if not phone or not full_name or not password:
                raise CommandError(
                    'In non-interactive mode, you must provide: --phone, --full-name, --password'
                )

        # Validate phone format
        if not phone or not phone.startswith('+998') or len(phone) != 13:
            raise CommandError('Invalid phone format. Must be: +998XXXXXXXXX')

        # Check if user exists
        if User.objects.filter(phone=phone).exists():
            raise CommandError(f'User with phone {phone} already exists')

        # Create superuser
        try:
            user = User.objects.create_superuser(
                phone=phone,
                full_name=full_name,
                password=password,
                email=f'admin-{phone}@azizdali.uz',
                is_verified=True,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Superuser created successfully!\n'
                    f'   Phone: {phone}\n'
                    f'   Name: {full_name}\n'
                    f'   Role: Ishlab chiqaruvchi (Manufacturer)\n'
                    f'   Admin URL: https://api.azizdali.uz/admin\n'
                )
            )

            return

        except Exception as e:
            raise CommandError(f'Failed to create superuser: {str(e)}')
