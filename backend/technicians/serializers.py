from rest_framework import serializers
from django.utils import timezone
from .models import TechnicianProfile, Skill, Certification, Crew


class SkillSerializer(serializers.ModelSerializer):
    """
    Serializer for Skill model.
    """
    class Meta:
        model = Skill
        fields = ['id', 'name', 'description', 'category', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CertificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Certification model.
    """
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    skill_category = serializers.CharField(source='skill.category', read_only=True)
    technician_name = serializers.CharField(source='technician.full_name', read_only=True)
    is_expired = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()

    class Meta:
        model = Certification
        fields = [
            'id', 'technician', 'technician_name', 'skill', 'skill_name', 'skill_category',
            'certification_number', 'issued_date', 'expiry_date', 'is_verified',
            'verification_document', 'notes', 'is_expired', 'days_until_expiry',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_expired', 'days_until_expiry', 'created_at', 'updated_at']


class TechnicianProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for TechnicianProfile model.
    """
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    skills_list = serializers.ReadOnlyField()

    class Meta:
        model = TechnicianProfile
        fields = [
            'id', 'user_id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'role', 'employee_id', 'hourly_rate',
            'emergency_contact_name', 'emergency_contact_phone',
            'license_number', 'license_expiry', 'max_daily_hours',
            'preferred_start_time', 'is_available', 'certifications',
            'skills_list', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_id', 'created_at', 'updated_at']


class TechnicianProfileCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating technician profiles.
    """
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = TechnicianProfile
        fields = [
            'email', 'first_name', 'last_name', 'phone_number',
            'employee_id', 'hourly_rate', 'emergency_contact_name',
            'emergency_contact_phone', 'license_number', 'license_expiry',
            'max_daily_hours', 'preferred_start_time', 'is_available'
        ]

    def create(self, validated_data):
        # Extract user data
        user_data = {
            'email': validated_data.pop('email'),
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'username': validated_data['email'],  # Use email as username
            'phone_number': validated_data.pop('phone_number', ''),
            'role': 'technician'
        }

        # Create user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(**user_data)

        # Create technician profile
        technician_profile = TechnicianProfile.objects.create(user=user, **validated_data)
        return technician_profile


class CrewSerializer(serializers.ModelSerializer):
    """
    Serializer for Crew model.
    """
    leader_name = serializers.CharField(source='leader.full_name', read_only=True)
    member_count = serializers.ReadOnlyField()
    primary_skill_name = serializers.CharField(source='primary_skill.name', read_only=True)
    members = TechnicianProfileSerializer(many=True, read_only=True)
    skills_summary = serializers.ReadOnlyField()

    class Meta:
        model = Crew
        fields = [
            'id', 'name', 'description', 'leader', 'leader_name',
            'members', 'member_count', 'is_active', 'primary_skill',
            'primary_skill_name', 'max_concurrent_jobs', 'contact_phone',
            'notes', 'skills_summary', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'member_count', 'skills_summary', 'created_at', 'updated_at']

    def validate_leader(self, value):
        """Ensure leader is a technician profile"""
        if value and not hasattr(value, 'user'):
            raise serializers.ValidationError("Leader must be a valid technician profile.")
        return value

    def validate_members(self, value):
        """Ensure all members are technician profiles"""
        for member in value:
            if not hasattr(member, 'user'):
                raise serializers.ValidationError("All members must be valid technician profiles.")
        return value


class CrewCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating crews.
    """
    class Meta:
        model = Crew
        fields = [
            'name', 'description', 'leader', 'members', 'is_active',
            'primary_skill', 'max_concurrent_jobs', 'contact_phone', 'notes'
        ]

    def validate_leader(self, value):
        """Ensure leader is a technician profile"""
        if value and not hasattr(value, 'user'):
            raise serializers.ValidationError("Leader must be a valid technician profile.")
        return value

    def validate_members(self, value):
        """Ensure all members are technician profiles"""
        for member in value:
            if not hasattr(member, 'user'):
                raise serializers.ValidationError("All members must be valid technician profiles.")
        return value
