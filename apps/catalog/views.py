from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import EntityFileForm, EntityPhotoForm, PrintEntityForm
from .models import EntityFile, EntityPhoto, PrintEntity


def _get_entity(slug, org):
    return get_object_or_404(PrintEntity, slug=slug, organization=org)


@login_required
def entity_list(request):
    entities = PrintEntity.objects.filter(organization=request.org).prefetch_related("photos", "tags")

    category = request.GET.get("category", "")
    material = request.GET.get("material", "")
    favorite = request.GET.get("favorite", "")
    active = request.GET.get("active", "")

    if category:
        entities = entities.filter(category=category)
    if material:
        entities = entities.filter(material_type=material)
    if favorite == "1":
        entities = entities.filter(is_favorite=True)
    if active == "1":
        entities = entities.filter(is_active=True)
    elif active == "0":
        entities = entities.filter(is_active=False)

    return render(request, "catalog/entity_list.html", {
        "entities": entities,
        "categories": PrintEntity.CATEGORY_CHOICES,
        "materials": PrintEntity.MATERIAL_CHOICES,
        "filters": {"category": category, "material": material, "favorite": favorite, "active": active},
    })


@login_required
def entity_detail(request, slug):
    entity = _get_entity(slug, request.org)
    return render(request, "catalog/entity_detail.html", {
        "entity": entity,
        "photo_form": EntityPhotoForm(),
        "file_form": EntityFileForm(),
    })


@login_required
def entity_create(request):
    if request.method == "POST":
        form = PrintEntityForm(request.POST, organization=request.org)
        if form.is_valid():
            entity = form.save()
            messages.success(request, f"'{entity.title}' created. Add photos and files below.")
            return redirect("catalog:detail", slug=entity.slug)
    else:
        form = PrintEntityForm(organization=request.org)
    return render(request, "catalog/entity_form.html", {"form": form, "action": "Create"})


@login_required
def entity_edit(request, slug):
    entity = _get_entity(slug, request.org)
    if request.method == "POST":
        form = PrintEntityForm(request.POST, instance=entity, organization=request.org)
        if form.is_valid():
            form.save()
            messages.success(request, "Entity updated.")
            return redirect("catalog:detail", slug=entity.slug)
    else:
        form = PrintEntityForm(instance=entity, organization=request.org)
    return render(request, "catalog/entity_form.html", {"form": form, "entity": entity, "action": "Edit"})


@login_required
@require_POST
def entity_delete(request, slug):
    entity = _get_entity(slug, request.org)
    title = entity.title
    entity.delete()
    messages.success(request, f"'{title}' deleted.")
    return redirect("catalog:list")


@login_required
@require_POST
def toggle_favorite(request, slug):
    entity = _get_entity(slug, request.org)
    entity.is_favorite = not entity.is_favorite
    entity.save(update_fields=["is_favorite"])
    return render(request, "catalog/partials/favorite_btn.html", {"entity": entity})


@login_required
@require_POST
def toggle_active(request, slug):
    entity = _get_entity(slug, request.org)
    entity.is_active = not entity.is_active
    entity.save(update_fields=["is_active"])
    return render(request, "catalog/partials/active_toggle.html", {"entity": entity})


@login_required
@require_POST
def upload_photo(request, slug):
    entity = _get_entity(slug, request.org)
    form = EntityPhotoForm(request.POST, request.FILES)
    if form.is_valid():
        photo = form.save(commit=False)
        photo.entity = entity
        photo.order = entity.photos.count()
        photo.save()
    return render(request, "catalog/partials/photo_gallery.html", {"entity": entity})


@login_required
@require_POST
def delete_photo(request, slug, photo_id):
    entity = _get_entity(slug, request.org)
    photo = get_object_or_404(EntityPhoto, id=photo_id, entity=entity)
    was_primary = photo.is_primary
    photo.delete()
    if was_primary:
        first = entity.photos.first()
        if first:
            first.is_primary = True
            first.save(update_fields=["is_primary"])
    return render(request, "catalog/partials/photo_gallery.html", {"entity": entity})


@login_required
@require_POST
def set_primary_photo(request, slug, photo_id):
    entity = _get_entity(slug, request.org)
    entity.photos.update(is_primary=False)
    photo = get_object_or_404(EntityPhoto, id=photo_id, entity=entity)
    photo.is_primary = True
    photo.save(update_fields=["is_primary"])
    return render(request, "catalog/partials/photo_gallery.html", {"entity": entity})


@login_required
@require_POST
def upload_file(request, slug):
    entity = _get_entity(slug, request.org)
    form = EntityFileForm(request.POST, request.FILES)
    if form.is_valid():
        f = form.save(commit=False)
        f.entity = entity
        f.save()
    return render(request, "catalog/partials/file_list.html", {"entity": entity})


@login_required
@require_POST
def delete_file(request, slug, file_id):
    entity = _get_entity(slug, request.org)
    f = get_object_or_404(EntityFile, id=file_id, entity=entity)
    f.delete()
    return render(request, "catalog/partials/file_list.html", {"entity": entity})
