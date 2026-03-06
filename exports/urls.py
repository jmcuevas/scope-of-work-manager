from django.urls import path

from . import views

app_name = 'exports'

urlpatterns = [
    path('exhibit/<int:pk>/pdf/', views.exhibit_pdf_download, name='exhibit_pdf'),
]
