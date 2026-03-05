from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list, name='list'),
    path('new/', views.project_create, name='create'),
    path('<int:pk>/', views.project_dashboard, name='dashboard'),
    path('<int:pk>/edit/', views.project_edit, name='edit'),
    path('<int:pk>/import/', views.trade_import, name='trade_import'),
    path('<int:pk>/trades/add/', views.trade_add, name='trade_add'),
    path('<int:pk>/trades/<int:trade_pk>/status/', views.trade_update_status, name='trade_update_status'),
    path('<int:pk>/trades/<int:trade_pk>/assign/', views.trade_update_assign, name='trade_update_assign'),
]
