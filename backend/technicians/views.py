from rest_framework import generics, status, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from .models import TechnicianProfile, Skill, Certification, Crew
from .serializers import (
    TechnicianProfileSerializer,
    TechnicianProfileCreateSerializer,
    SkillSerializer,
    CertificationSerializer,
    CrewSerializer,
    CrewCreateUpdateSerializer
)
from accounts.permissions import ManagerAndAbove, TechnicianAndAbove


class TechnicianProfileListCreateView(generics.ListCreateAPIView):
    """
    List all technician profiles or create a new technician profile.
    Only managers and above can create technicians.
    """
    permission_classes = [TechnicianAndAbove]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TechnicianProfileCreateSerializer
        return TechnicianProfileSerializer

    def get_queryset(self):
        """
        Filter technicians based on user role.
        """
        user = self.request.user
        queryset = TechnicianProfile.objects.select_related('user').prefetch_related(
            'certifications__skill'
        )

        # Managers can see all technicians, technicians can only see themselves
        if user.is_technician and not (user.is_manager or user.is_owner or user.is_admin):
            return queryset.filter(user=user)
        return queryset

    def perform_create(self, serializer):
        # Only managers and above can create technician profiles
        if not (self.request.user.is_manager or self.request.user.is_owner or self.request.user.is_admin):
            raise permissions.PermissionDenied("Only managers and above can create technician profiles.")
        serializer.save()


class TechnicianProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a technician profile.
    """
    queryset = TechnicianProfile.objects.select_related('user').prefetch_related(
        'certifications__skill'
    )
    serializer_class = TechnicianProfileSerializer
    permission_classes = [TechnicianAndAbove]

    def get_queryset(self):
        """
        Filter based on user permissions.
        """
        user = self.request.user
        queryset = super().get_queryset()

        # Technicians can only access their own profile
        if user.is_technician and not (user.is_manager or user.is_owner or user.is_admin):
            return queryset.filter(user=user)
        return queryset


class SkillListCreateView(generics.ListCreateAPIView):
    """
    List all skills or create a new skill.
    """
    queryset = Skill.objects.filter(is_active=True)
    serializer_class = SkillSerializer
    permission_classes = [ManagerAndAbove]


class SkillDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a skill.
    """
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [ManagerAndAbove]


class CertificationListCreateView(generics.ListCreateAPIView):
    """
    List all certifications or create a new certification.
    """
    serializer_class = CertificationSerializer
    permission_classes = [TechnicianAndAbove]

    def get_queryset(self):
        """
        Filter certifications based on user role.
        """
        user = self.request.user
        queryset = Certification.objects.select_related('technician__user', 'skill')

        # Technicians can only see their own certifications
        if user.is_technician and not (user.is_manager or user.is_owner or user.is_admin):
            try:
                tech_profile = user.technician_profile
                return queryset.filter(technician=tech_profile)
            except TechnicianProfile.DoesNotExist:
                return queryset.none()
        return queryset

    def perform_create(self, serializer):
        user = self.request.user

        # Technicians can only create certifications for themselves
        if user.is_technician and not (user.is_manager or user.is_owner or user.is_admin):
            try:
                tech_profile = user.technician_profile
                serializer.save(technician=tech_profile)
            except TechnicianProfile.DoesNotExist:
                raise serializers.ValidationError("Technician profile not found.")
        else:
            serializer.save()


class CertificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a certification.
    """
    queryset = Certification.objects.select_related('technician__user', 'skill')
    serializer_class = CertificationSerializer
    permission_classes = [TechnicianAndAbove]

    def get_queryset(self):
        """
        Filter based on user permissions.
        """
        user = self.request.user
        queryset = super().get_queryset()

        # Technicians can only access their own certifications
        if user.is_technician and not (user.is_manager or user.is_owner or user.is_admin):
            try:
                tech_profile = user.technician_profile
                return queryset.filter(technician=tech_profile)
            except TechnicianProfile.DoesNotExist:
                return queryset.none()
        return queryset


class CrewListCreateView(generics.ListCreateAPIView):
    """
    List all crews or create a new crew.
    """
    queryset = Crew.objects.prefetch_related('members__user', 'leader__user', 'primary_skill')
    permission_classes = [ManagerAndAbove]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CrewCreateUpdateSerializer
        return CrewSerializer

    def perform_create(self, serializer):
        serializer.save()


class CrewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a crew.
    """
    queryset = Crew.objects.prefetch_related('members__user', 'leader__user', 'primary_skill')
    permission_classes = [ManagerAndAbove]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CrewCreateUpdateSerializer
        return CrewSerializer


class TechnicianAvailabilityView(APIView):
    """
    Get availability status of technicians.
    """
    permission_classes = [TechnicianAndAbove]

    def get(self, request):
        """Get list of available technicians"""
        available_technicians = TechnicianProfile.objects.filter(
            is_available=True,
            user__is_active=True
        ).select_related('user')

        serializer = TechnicianProfileSerializer(available_technicians, many=True)
        return Response(serializer.data)


class CrewSkillsView(APIView):
    """
    Get skills summary for crews.
    """
    permission_classes = [ManagerAndAbove]

    def get(self, request, crew_id=None):
        """Get skills summary for a specific crew or all crews"""
        if crew_id:
            crew = get_object_or_404(Crew, id=crew_id)
            skills_summary = crew.get_skills_summary()
            return Response({
                'crew_id': crew_id,
                'crew_name': crew.name,
                'skills_summary': skills_summary
            })
        else:
            crews = Crew.objects.filter(is_active=True)
            result = []
            for crew in crews:
                result.append({
                    'crew_id': crew.id,
                    'crew_name': crew.name,
                    'skills_summary': crew.get_skills_summary(),
                    'member_count': crew.member_count
                })
            return Response(result)
