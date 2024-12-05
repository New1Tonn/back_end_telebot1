from django.contrib import admin
from .models import Car, UserProfile, User

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('make', 'model', 'year', 'price')
    search_fields = ('make', 'model')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_phone_number', 'get_email')
    search_fields = ('user__username', 'user__email')

    def get_phone_number(self, obj):
        return obj.user.phone_number
    get_phone_number.short_description = 'Phone Number'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'