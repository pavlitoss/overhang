from django.db import models
from django.utils.text import slugify

from apps.accounts.models import Organization


def entity_photo_path(instance, filename):
    return f"{instance.entity.organization.slug}/entities/{instance.entity.slug}/{filename}"


def entity_file_path(instance, filename):
    return f"{instance.entity.organization.slug}/models/{instance.entity.slug}/{filename}"


class Tag(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ("organization", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class PrintEntity(models.Model):
    CATEGORY_MINIATURE = "miniature"
    CATEGORY_FUNCTIONAL = "functional"
    CATEGORY_DECORATIVE = "decorative"
    CATEGORY_COSPLAY = "cosplay"
    CATEGORY_OTHER = "other"
    CATEGORY_CHOICES = [
        (CATEGORY_MINIATURE, "Miniature"),
        (CATEGORY_FUNCTIONAL, "Functional"),
        (CATEGORY_DECORATIVE, "Decorative"),
        (CATEGORY_COSPLAY, "Cosplay"),
        (CATEGORY_OTHER, "Other"),
    ]

    MATERIAL_CHOICES = [
        ("PLA", "PLA"),
        ("PETG", "PETG"),
        ("TPU", "TPU"),
        ("ABS", "ABS"),
        ("ASA", "ASA"),
        ("other", "Other"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="entities")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    tags = models.ManyToManyField(Tag, blank=True, related_name="entities")
    estimated_weight_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    estimated_print_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    support_required = models.BooleanField(default=False)
    material_type = models.CharField(max_length=10, choices=MATERIAL_CHOICES, default="PLA")
    # preferred_color FK to FilamentSpool added in Phase 4
    is_active = models.BooleanField(default=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while PrintEntity.objects.filter(organization=self.organization, slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def primary_photo(self):
        return self.photos.filter(is_primary=True).first() or self.photos.first()


class EntityPhoto(models.Model):
    entity = models.ForeignKey(PrintEntity, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=entity_photo_path)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def save(self, *args, **kwargs):
        if not self.pk and not self.entity.photos.exists():
            self.is_primary = True
        super().save(*args, **kwargs)


class EntityFile(models.Model):
    FILE_TYPE_CHOICES = [
        ("stl", "STL"),
        ("3mf", "3MF"),
        ("obj", "OBJ"),
    ]
    EXTENSION_MAP = {"stl": "stl", "3mf": "3mf", "obj": "obj"}

    entity = models.ForeignKey(PrintEntity, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to=entity_file_path)
    file_type = models.CharField(max_length=5, choices=FILE_TYPE_CHOICES)
    label = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.label or self.file_type} — {self.entity.title}"
