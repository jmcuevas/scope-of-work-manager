from django.urls import path

from . import views

app_name = 'notes'

urlpatterns = [
    # Sidebar: note list + add (scoped to an exhibit)
    path('exhibit/<int:exhibit_pk>/notes/', views.note_list, name='note_list'),
    path('exhibit/<int:exhibit_pk>/notes/add/', views.note_add, name='note_add'),

    # Note actions (scoped to note pk)
    path('notes/<int:pk>/resolve/', views.note_resolve, name='note_resolve'),
    path('notes/<int:pk>/edit/', views.note_edit, name='note_edit'),

    # Project-level open notes
    path('projects/<int:project_pk>/open-notes/', views.open_questions, name='open_notes'),
    path('projects/<int:project_pk>/open-notes/add/', views.note_add_project, name='note_add_project'),
]
