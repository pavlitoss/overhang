from django import forms

from .models import EntityFile, EntityPhoto, PrintEntity, Tag


class PrintEntityForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        label="Tags",
        widget=forms.TextInput(attrs={"placeholder": "dragon, fantasy, figurine"}),
    )

    class Meta:
        model = PrintEntity
        fields = [
            "title",
            "description",
            "category",
            "material_type",
            "estimated_weight_g",
            "estimated_print_hours",
            "support_required",
            "is_active",
            "is_favorite",
        ]

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization")
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(
                self.instance.tags.values_list("name", flat=True)
            )

    def save(self, commit=True):
        entity = super().save(commit=False)
        entity.organization = self.organization
        if commit:
            entity.save()
            self._save_tags(entity)
        return entity

    def _save_tags(self, entity):
        raw = self.cleaned_data.get("tags_input", "")
        names = [t.strip().lower() for t in raw.split(",") if t.strip()]
        tags = []
        for name in names:
            tag, _ = Tag.objects.get_or_create(organization=entity.organization, name=name)
            tags.append(tag)
        entity.tags.set(tags)


class EntityPhotoForm(forms.ModelForm):
    class Meta:
        model = EntityPhoto
        fields = ["image"]


class EntityFileForm(forms.ModelForm):
    class Meta:
        model = EntityFile
        fields = ["file", "file_type", "label"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file_type"].required = False
        self.fields["label"].required = False

    def clean(self):
        cleaned = super().clean()
        file = cleaned.get("file")
        if file and not cleaned.get("file_type"):
            ext = file.name.rsplit(".", 1)[-1].lower()
            if ext in EntityFile.EXTENSION_MAP:
                cleaned["file_type"] = EntityFile.EXTENSION_MAP[ext]
            else:
                self.add_error("file_type", "Could not detect file type. Please select it manually.")
        return cleaned
