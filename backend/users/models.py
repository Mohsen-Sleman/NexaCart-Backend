from django.db import models
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin,BaseUserManager
from django.utils.translation import gettext_lazy as _



class UserManager(BaseUserManager) :
    def create_user(self,email,first_name,last_name,password=None,**extra_fields) :
        """
        Creates and saves a regular User with the given email, first_name, last_name and password.
        Raises ValueError if email is missing or already registered.
        """
        email = self.normalize_email(email)
        if not email : 
            raise ValueError('A valid email address must be provided.')
        
        if self.model.objects.filter(email=email).exists() : 
            raise ValueError('This email address is already registered.')
        
        user = self.model(email=email,first_name=first_name,last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
        
    def create_superuser(self,email,first_name,last_name,password=None,**extra_fields) :

        extra_fields.setdefault('is_staff',True)
        extra_fields.setdefault('is_superuser',True)
        extra_fields.setdefault('is_verified',True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email,first_name,last_name,password,**extra_fields)



class User(AbstractBaseUser,PermissionsMixin) :

    email = models.EmailField(unique=True, max_length=200)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=50,blank=True,null=True,unique=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/',blank=True,null=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name','last_name',]

    def __str__(self):
        return self.email

class OTP(models.Model):
    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = 'email_verification', _('Email Verification')
        PASSWORD_RESET = 'password_reset', _('Password Reset')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    purpose = models.CharField(max_length=30, choices=Purpose.choices, default=Purpose.EMAIL_VERIFICATION)
    otp_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

