import os
from split_settings.tools import include

# Determine environment and include appropriate settings
env = os.getenv('ENVIRONMENT', 'development')

if env == 'production':
    include('production.py')
else:
    include('development.py')
