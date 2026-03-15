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
    path(
        '<int:pk>/sections/<int:section_pk>/items/<int:item_pk>/accept-ai/',
        views.item_accept_ai,
        name='item_accept_ai',
    ),
    path(
        '<int:pk>/sections/<int:section_pk>/items/<int:item_pk>/reject-ai/',
        views.item_reject_ai,
        name='item_reject_ai',
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
    path(
        '<int:pk>/sections/<int:section_pk>/items/<int:item_pk>/insert-below/',
        views.item_insert_below,
        name='item_insert_below',
    ),

    # Exhibit-level actions
    path('<int:pk>/pending-banner/', views.pending_banner, name='pending_banner'),
    path('<int:pk>/accept-all-pending/', views.accept_all_pending_view, name='accept_all_pending'),
    path('<int:pk>/reject-all-pending/', views.reject_all_pending_view, name='reject_all_pending'),
    path('<int:pk>/save-as-template/', views.exhibit_save_as_template, name='save_as_template'),
    path('<int:pk>/status/', views.exhibit_update_status, name='update_status'),
    path('<int:pk>/generate-scope/', views.exhibit_generate_scope, name='generate_scope'),
    path('<int:pk>/sections/<int:section_pk>/items/generate/', views.item_generate, name='item_generate'),
    path('<int:pk>/sections/<int:section_pk>/items/add-gap/', views.add_gap_item, name='add_gap_item'),
    path('<int:pk>/notes/<int:note_pk>/to-scope-item/', views.note_to_scope_item, name='note_to_scope_item'),

    # AI panel
    path('<int:pk>/ai-panel/', views.ai_panel, name='ai_panel'),
    path('<int:pk>/check-completeness/', views.exhibit_check_completeness, name='check_completeness'),

    # Section list (GET refresh endpoint)
    path('<int:pk>/sections/', views.section_list, name='section_list'),

    # AI chat overlay
    path('<int:pk>/chat/', views.ai_chat, name='ai_chat'),
    path('<int:pk>/chat/send/', views.ai_chat_send, name='ai_chat_send'),
    path(
        '<int:pk>/sections/<int:section_pk>/items/<int:item_pk>/rewrite/',
        views.item_rewrite,
        name='item_rewrite',
    ),
    path(
        '<int:pk>/sections/<int:section_pk>/items/<int:item_pk>/expand/',
        views.item_expand,
        name='item_expand',
    ),
]
