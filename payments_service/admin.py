from django.contrib import admin

from payments_service.models import Payments


@admin.register(Payments)
class BorrowingsAdmin(admin.ModelAdmin):
    pass
