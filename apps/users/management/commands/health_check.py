"""
Management command to check system health and dependencies.

Usage:
    python manage.py health_check

Checks:
    - Database connection
    - Redis connection
    - Required environment variables
    - Media and static files directories
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Check system health and dependencies'
    
    def handle(self, *args, **options):
        """Execute health checks."""
        self.stdout.write(self.style.SUCCESS('\n🔍 TradeLink Health Check\n'))
        
        checks = [
            ('Database Connection', self._check_database),
            ('Redis Connection', self._check_redis),
            ('Required Environment Variables', self._check_env_vars),
            ('Media Directory', self._check_media_dir),
            ('Static Files Directory', self._check_static_dir),
        ]
        
        results = []
        for check_name, check_func in checks:
            try:
                status = check_func()
                results.append((check_name, status))
                icon = '✓' if status else '✗'
                line_style = self.style.SUCCESS if status else self.style.ERROR
                self.stdout.write(line_style(f'{icon} {check_name}'))
            except Exception as e:
                results.append((check_name, False))
                self.stdout.write(self.style.ERROR(f'✗ {check_name}: {str(e)}'))
        
        # Summary
        passed = sum(1 for _, status in results if status)
        total = len(results)
        
        self.stdout.write('\n' + '='*50)
        if passed == total:
            self.stdout.write(self.style.SUCCESS(f'\n✓ All checks passed ({passed}/{total})\n'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠ {total - passed} check(s) failed ({passed}/{total})\n'))
    
    def _check_database(self):
        """Check database connection."""
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return True
        except Exception as e:
            self.stdout.write(f'    Error: {str(e)}')
            return False
    
    def _check_redis(self):
        """Check Redis connection."""
        try:
            import redis
            redis_url = settings.CACHES.get('default', {}).get('LOCATION', '')
            if not redis_url:
                self.stdout.write('    Redis not configured (optional)')
                return True
            
            r = redis.from_url(redis_url)
            r.ping()
            return True
        except ImportError:
            self.stdout.write('    redis-py not installed (optional)')
            return True
        except Exception as e:
            self.stdout.write(f'    Error: {str(e)}')
            return False
    
    def _check_env_vars(self):
        """Check required environment variables."""
        required_vars = [
            'SECRET_KEY',
            'DEBUG',
            'DB_ENGINE',
        ]
        
        missing = []
        for var in required_vars:
            if not os.environ.get(var):
                missing.append(var)
        
        if missing:
            self.stdout.write(f'    Missing: {", ".join(missing)}')
            return False
        return True
    
    def _check_media_dir(self):
        """Check media directory exists."""
        media_root = settings.MEDIA_ROOT
        if not isinstance(media_root, str):
            media_root = str(media_root)
        
        if os.path.exists(media_root):
            return True
        
        try:
            os.makedirs(media_root, exist_ok=True)
            self.stdout.write(f'    Created: {media_root}')
            return True
        except Exception as e:
            self.stdout.write(f'    Error creating directory: {str(e)}')
            return False
    
    def _check_static_dir(self):
        """Check static files directory exists."""
        static_root = settings.STATIC_ROOT
        if not static_root:
            self.stdout.write('    STATIC_ROOT not configured')
            return True
        
        if not isinstance(static_root, str):
            static_root = str(static_root)
        
        if os.path.exists(static_root) or os.environ.get('DEBUG') == 'True':
            return True
        
        self.stdout.write(f'    Note: Run "python manage.py collectstatic" for production')
        return True
