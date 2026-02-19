from django.urls import path
from journal import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('session/<int:session_id>/chart-data/', views.session_chart_data, name='session_chart_data'),
]