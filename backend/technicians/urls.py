from django.urls import path
from . import views

app_name = 'technicians'

urlpatterns = [
    # Technician profiles
    path('technicians/', views.TechnicianProfileListCreateView.as_view(), name='technician-list-create'),
    path('technicians/<int:pk>/', views.TechnicianProfileDetailView.as_view(), name='technician-detail'),

    # Skills
    path('skills/', views.SkillListCreateView.as_view(), name='skill-list-create'),
    path('skills/<int:pk>/', views.SkillDetailView.as_view(), name='skill-detail'),

    # Certifications
    path('certifications/', views.CertificationListCreateView.as_view(), name='certification-list-create'),
    path('certifications/<int:pk>/', views.CertificationDetailView.as_view(), name='certification-detail'),

    # Crews
    path('crews/', views.CrewListCreateView.as_view(), name='crew-list-create'),
    path('crews/<int:pk>/', views.CrewDetailView.as_view(), name='crew-detail'),

    # Utility endpoints
    path('availability/', views.TechnicianAvailabilityView.as_view(), name='technician-availability'),
    path('crew-skills/', views.CrewSkillsView.as_view(), name='crew-skills'),
    path('crew-skills/<int:crew_id>/', views.CrewSkillsView.as_view(), name='crew-skills-detail'),
]
