from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.entity_list, name="list"),
    path("add/", views.entity_create, name="create"),
    path("<slug:slug>/", views.entity_detail, name="detail"),
    path("<slug:slug>/edit/", views.entity_edit, name="edit"),
    path("<slug:slug>/delete/", views.entity_delete, name="delete"),
    path("<slug:slug>/toggle-favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("<slug:slug>/toggle-active/", views.toggle_active, name="toggle_active"),
    path("<slug:slug>/photos/upload/", views.upload_photo, name="upload_photo"),
    path("<slug:slug>/photos/<int:photo_id>/delete/", views.delete_photo, name="delete_photo"),
    path("<slug:slug>/photos/<int:photo_id>/set-primary/", views.set_primary_photo, name="set_primary_photo"),
    path("<slug:slug>/files/upload/", views.upload_file, name="upload_file"),
    path("<slug:slug>/files/<int:file_id>/delete/", views.delete_file, name="delete_file"),
]
