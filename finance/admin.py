from django.contrib import admin
from .models import Category, CategoryKeyword, FinancialRecordType


class CategoryKeywordInline(admin.TabularInline):
    model = CategoryKeyword
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'record_type')
    list_filter = ('record_type',)
    search_fields = ('name',)
    inlines = [CategoryKeywordInline]


@admin.register(CategoryKeyword)
class CategoryKeywordAdmin(admin.ModelAdmin):
    list_display = ('id', 'keyword', 'category')
    list_filter = ('category__record_type', 'category')
    search_fields = ('keyword', 'category__name')


@admin.register(FinancialRecordType)
class FinancialRecordTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'behavior')
    search_fields = ('name',)
