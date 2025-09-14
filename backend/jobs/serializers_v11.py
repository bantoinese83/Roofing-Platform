from rest_framework import serializers
from .models import JobNote, JobHistory
from accounts.serializers import UserSerializer


class JobNoteSerializer(serializers.ModelSerializer):
    """Serializer for job notes and chat messages"""

    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    created_by_role = serializers.CharField(source='created_by.role', read_only=True)
    reply_count = serializers.ReadOnlyField()
    has_replies = serializers.ReadOnlyField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = JobNote
        fields = [
            'id', 'note_type', 'content', 'visibility', 'attachment', 'attachment_url',
            'attachment_name', 'created_by', 'created_by_name', 'created_by_role',
            'parent_note', 'read_by', 'is_pinned', 'reply_count', 'has_replies',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_by_name', 'created_by_role', 'reply_count', 'has_replies',
            'attachment_url', 'created_at', 'updated_at'
        ]

    def get_attachment_url(self, obj):
        """Get the full URL for the attachment"""
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return None

    def create(self, validated_data):
        """Set created_by to current user"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class JobNoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating job notes"""

    class Meta:
        model = JobNote
        fields = [
            'note_type', 'content', 'visibility', 'attachment', 'attachment_name',
            'parent_note', 'is_pinned'
        ]


class JobNoteThreadSerializer(serializers.ModelSerializer):
    """Serializer for job note threads (with replies)"""

    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    created_by_role = serializers.CharField(source='created_by.role', read_only=True)
    replies = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = JobNote
        fields = [
            'id', 'note_type', 'content', 'visibility', 'attachment', 'attachment_url',
            'attachment_name', 'created_by', 'created_by_name', 'created_by_role',
            'parent_note', 'replies', 'is_pinned', 'created_at', 'updated_at'
        ]

    def get_replies(self, obj):
        """Get all replies for this note"""
        if obj.replies.exists():
            return JobNoteThreadSerializer(obj.replies.all(), many=True, context=self.context).data
        return []

    def get_attachment_url(self, obj):
        """Get the full URL for the attachment"""
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return None


class JobHistorySerializer(serializers.ModelSerializer):
    """Serializer for job history/audit trail"""

    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    changed_by_role = serializers.CharField(source='changed_by.role', read_only=True)
    is_field_change = serializers.ReadOnlyField()
    is_asset_change = serializers.ReadOnlyField()
    is_communication = serializers.ReadOnlyField()

    class Meta:
        model = JobHistory
        fields = [
            'id', 'history_type', 'field_name', 'old_value', 'new_value', 'description',
            'related_photo', 'related_document', 'related_note', 'changed_by',
            'changed_by_name', 'changed_by_role', 'ip_address', 'user_agent',
            'is_field_change', 'is_asset_change', 'is_communication', 'created_at'
        ]
        read_only_fields = [
            'id', 'changed_by_name', 'changed_by_role', 'is_field_change',
            'is_asset_change', 'is_communication', 'created_at'
        ]


class JobHistoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating job history entries"""

    class Meta:
        model = JobHistory
        fields = [
            'history_type', 'field_name', 'old_value', 'new_value', 'description',
            'related_photo', 'related_document', 'related_note', 'ip_address', 'user_agent'
        ]

    def create(self, validated_data):
        """Set changed_by to current user"""
        validated_data['changed_by'] = self.context['request'].user
        return super().create(validated_data)
