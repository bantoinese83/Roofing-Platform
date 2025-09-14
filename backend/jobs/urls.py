from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Job management
    path('', views.JobListCreateView.as_view(), name='job-list-create'),
    path('<int:pk>/', views.JobDetailView.as_view(), name='job-detail'),

    # Job media
    path('<int:job_id>/photos/', views.JobPhotoListCreateView.as_view(), name='job-photos'),
    path('<int:job_id>/documents/', views.JobDocumentListCreateView.as_view(), name='job-documents'),

    # Calendar and scheduling
    path('calendar/', views.JobCalendarView.as_view(), name='job-calendar'),

    # Technician endpoints
    path('technician/today/', views.TechnicianJobsView.as_view(), name='technician-jobs'),
    path('<int:job_id>/status/', views.JobStatusUpdateView.as_view(), name='job-status-update'),
]