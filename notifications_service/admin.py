from django.contrib import admin

from notifications_service.models import Chat


@admin.register(Chat)
class BorrowingsAdmin(admin.ModelAdmin):
    pass
