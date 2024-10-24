from django.contrib import admin

from payments_service.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    pass
