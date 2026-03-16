# Generated migration for User and OTPCode models

from django.db import migrations, models
import django.db.models.deletion
import django.contrib.auth.models
import django.core.validators
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('is_staff', models.BooleanField(default=False, help_text='Can access Django admin')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('phone', models.CharField(help_text='Format: +998XXXXXXXXX (Uzbekistan)', max_length=13, unique=True, validators=[django.core.validators.RegexValidator(code='invalid_phone', message='Phone must be in format +998XXXXXXXXX', regex='^\\+998\\d{9}$')])),
                ('email', models.EmailField(blank=True, help_text='Optional, but must be unique if provided', max_length=254, null=True, unique=True)),
                ('full_name', models.CharField(max_length=150)),
                ('role', models.CharField(choices=[('manufacturer', 'Ishlab chiqaruvchi'), ('dealer', 'Diller'), ('store', "Do'kon egasi")], help_text='User role determines permissions', max_length=20)),
                ('avatar', models.ImageField(blank=True, help_text='User profile picture', null=True, upload_to='avatars/')),
                ('is_verified', models.BooleanField(default=False, help_text='True if phone verified via OTP')),
                ('is_active', models.BooleanField(default=True, help_text='Set to False to soft-delete user')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
                'db_table': 'users_user',
                'ordering': ['-created_at'],
            },
            bases=(django.contrib.auth.models.AbstractBaseUser, models.Model),
        ),
        migrations.CreateModel(
            name='OTPCode',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(help_text='6-digit OTP code', max_length=6)),
                ('expires_at', models.DateTimeField(help_text='When OTP expires')),
                ('is_used', models.BooleanField(default=False, help_text='True if OTP was successfully verified')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(help_text='User this OTP belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='otp_codes', to='users.user')),
            ],
            options={
                'verbose_name': 'OTP Code',
                'verbose_name_plural': 'OTP Codes',
                'db_table': 'users_otpcode',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['phone'], name='users_user_phone_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='users_user_email_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['role'], name='users_user_role_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['-created_at'], name='users_user_created_at_idx'),
        ),
        migrations.AddIndex(
            model_name='otpcode',
            index=models.Index(fields=['user', 'is_used'], name='users_otpcode_user_is_used_idx'),
        ),
        migrations.AddIndex(
            model_name='otpcode',
            index=models.Index(fields=['code'], name='users_otpcode_code_idx'),
        ),
        migrations.AddIndex(
            model_name='otpcode',
            index=models.Index(fields=['expires_at'], name='users_otpcode_expires_at_idx'),
        ),
    ]
