from django.urls import path
from . import views

app_name = 'exhibits'

urlpatterns = [
    # Entry flow (project/trade context)
    path(
        'projects/<int:project_pk>/trades/<int:trade_pk>/scope/open/',
        views.trade_scope_open,
        name='trade_scope_open',
    ),
    path(
        'projects/<int:project_pk>/trades/<int:trade_pk>/scope/pick/',
        views.template_picker,
        name='template_picker',
    ),
    path(
        'projects/<int:project_pk>/trades/<int:trade_pk>/scope/start/',
        views.exhibit_start,
        name='exhibit_start',
    ),

    # Editor
    path('<int:pk>/', views.exhibit_editor, name='editor'),

    # Section CRUD
    path('<int:pk>/sections/add/', views.section_add, name='section_add'),
    path('<int:pk>/sections/<int:section_pk>/rename/', views.section_rename, name='section_rename'),
    path('<int:pk>/sections/<int:section_pk>/delete/', views.section_delete, name='section_delete'),
    path('<int:pk>/sections/<int:section_pk>/move/', views.section_move, name='section_move'),

    # Item CRUD
    path('<int:pk>/sections/<int:section_pk>/items/add/', views.item_add, name='item_add'),
    path(
        '<int:pk>/sections/<int:section_pk>/items/<int:item_pk>/edit/',
        views.item_edit,
        name='item_edit',
    ),
    path(
        '<int:pk>/sections/<int:section_pk>/items/<int:item_pk>/delete/',
        views.item_delete,
        name='item_delete',
    ),

    # Item hierarchy
    path(
        '<int:pk>/sections/<int:section_pk>/items/<int:item_pk>/move/<str:direction>/',
        views.item_move,
        name='item_move',
    ),
    path(
        '<int:pk>/sections/<int:section_pk>/items/<int:item_pk>/indent/',
        views.item_indent,
        name='item_indent',
    ),
    path(
        '<int:pk>/sections/<int:section_pk>/items/<int:item_pk>/outdent/',
        views.item_outdent,
        name='item_outdent',
    ),

    # Exhibit-level actions
    path('<int:pk>/save-as-template/', views.exhibit_save_as_template, name='save_as_template'),
    path('<int:pk>/status/', views.exhibit_update_status, name='update_status'),
]
