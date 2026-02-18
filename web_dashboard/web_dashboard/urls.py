from django.contrib import admin
from django.urls import path
from journal.views import dashboard, session_detail

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('session/<int:session_id>/', session_detail, name='session_detail'),
]