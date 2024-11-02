from django.contrib import admin

from borrowings_service.models import Borrowing


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    pass
