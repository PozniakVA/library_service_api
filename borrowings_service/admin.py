from django.contrib import admin

from borrowings_service.models import Borrowings


@admin.register(Borrowings)
class BorrowingsAdmin(admin.ModelAdmin):
    pass
