from django.contrib import admin

from .models import EntityFile, EntityPhoto, PrintEntity, Tag


class EntityPhotoInline(admin.TabularInline):
    model = EntityPhoto
    extra = 0


class EntityFileInline(admin.TabularInline):
    model = EntityFile
    extra = 0


@admin.register(PrintEntity)
class PrintEntityAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "category", "material_type", "is_active", "is_favorite", "created_at")
    list_filter = ("organization", "category", "material_type", "is_active", "is_favorite")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [EntityPhotoInline, EntityFileInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "organization")
    list_filter = ("organization",)
