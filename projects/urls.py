from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list, name='list'),
    path('new/', views.project_create, name='create'),
    path('<int:pk>/', views.project_dashboard, name='dashboard'),
    path('<int:pk>/edit/', views.project_edit, name='edit'),
]
