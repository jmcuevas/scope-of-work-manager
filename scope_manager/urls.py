from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='projects:list'), name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('projects/', include('projects.urls', namespace='projects')),
    path('exhibits/', include('exhibits.urls', namespace='exhibits')),
    path('exports/', include('exports.urls', namespace='exports')),
    path('notes/', include('notes.urls', namespace='notes')),
]
