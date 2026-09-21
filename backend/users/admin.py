from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User,OTP
from .forms import UserCreationForm, UserChangeForm


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    form = UserChangeForm
    add_form = UserCreationForm

    readonly_fields = ('created_at', 'updated_at',)

    list_display = (
        "email",
        "first_name",
        "last_name",
        "phone",
        "is_verified",
        "is_staff",
        "is_active",
    )

    search_fields = ("email", "phone")

    list_filter = (
        "is_verified",
        "is_staff",
        "is_active",
    )

    ordering = ("created_at",)

    fieldsets = (
        (
            "Personal information",
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "phone",
                )
            },
        ),
        (
            "Authentication",
            {
                "fields": ("password",)
            },
        ),
        (
            "Permissions",
            {
                "classes": ("collapse",),
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "phone",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

admin.site.register(OTP)