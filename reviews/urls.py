from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('exhibits/<int:exhibit_pk>/review/run/', views.run_review, name='run'),
    path('exhibits/<int:exhibit_pk>/review/items/<int:item_pk>/respond/', views.review_item_respond, name='item_respond'),
]
