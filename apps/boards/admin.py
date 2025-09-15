from django.contrib import admin
from nested_admin import NestedTabularInline, NestedStackedInline, NestedModelAdmin
from .models import Board, List, Card, Membership

class CardInline(NestedTabularInline):
    model = Card
    extra = 0
    # fields = ('title', 'description', 'priority', 'due_date', 'order', 'created_at', 'updated_at')

class ListInline(NestedStackedInline):
    model = List
    extra = 0
    inlines = [CardInline]
    # fields = ('title', 'order', 'created_at', 'updated_at')

@admin.register(Board)
class BoardAdmin(NestedModelAdmin):
    list_display = ('title', 'owner', 'color', 'created_at', 'updated_at')
    list_filter = ('color', 'created_at', 'updated_at')
    search_fields = ('title', 'description')
    # prepopulated_fields = {'slug': ('title',)}  # You may need to add a slug field to your Board model
    autocomplete_fields = ['owner']
    raw_id_fields = ('owner',)
    date_hierarchy = 'created_at'
    ordering = ('created_at',)
    inlines = [ListInline]

@admin.register(List)
class ListAdmin(admin.ModelAdmin):
    list_display = ('title', 'board', 'order', 'created_at', 'updated_at')
    list_filter = ('board', 'created_at', 'updated_at')
    search_fields = ('title',)
    raw_id_fields = ('board',)
    date_hierarchy = 'created_at'
    ordering = ('board', 'order')

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('title', 'list', 'priority', 'due_date', 'order', 'created_at', 'updated_at')
    list_filter = ('list', 'priority', 'due_date', 'created_at', 'updated_at')
    search_fields = ('title', 'description')
    raw_id_fields = ('list', 'assignees')
    date_hierarchy = 'created_at'
    ordering = ('list', 'priority', 'order')

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'board', 'role', 'is_active', 'created_at', 'updated_at')
    list_filter = ('board', 'role', 'is_active', 'created_at', 'updated_at')
    search_fields = ('user__username', 'board__title')
    raw_id_fields = ('user', 'board', 'invited_by')
    date_hierarchy = 'created_at'
    ordering = ('board', 'role', 'created_at')
