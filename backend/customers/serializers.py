from rest_framework import serializers
from .models import Customer, CustomerAddress, CustomerCommunication


class CustomerAddressSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomerAddress model.
    """
    full_address = serializers.ReadOnlyField()

    class Meta:
        model = CustomerAddress
        fields = [
            'id', 'customer', 'address_type', 'street_address', 'apartment_unit',
            'city', 'state', 'postal_code', 'country', 'latitude', 'longitude',
            'is_primary', 'is_active', 'instructions', 'full_address',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate address data"""
        # Ensure postal code format is valid for US addresses
        if data.get('country', '').lower() in ['united states', 'us', 'usa']:
            postal_code = data.get('postal_code', '')
            if postal_code and not self._is_valid_us_postal_code(postal_code):
                raise serializers.ValidationError({
                    'postal_code': 'Invalid US postal code format. Use XXXXX or XXXXX-XXXX.'
                })
        return data

    def _is_valid_us_postal_code(self, postal_code):
        """Validate US postal code format"""
        import re
        # US ZIP code patterns: 12345 or 12345-6789
        pattern = r'^\d{5}(?:-\d{4})?$'
        return bool(re.match(pattern, postal_code))


class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for Customer model.
    """
    addresses = CustomerAddressSerializer(many=True, read_only=True)
    primary_address = CustomerAddressSerializer(read_only=True)
    total_jobs = serializers.ReadOnlyField()
    active_jobs = serializers.ReadOnlyField()
    completed_jobs = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number', 'alt_phone_number',
            'is_active', 'marketing_opt_in', 'notes', 'addresses', 'primary_address',
            'total_jobs', 'active_jobs', 'completed_jobs', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'addresses', 'primary_address', 'total_jobs', 'active_jobs', 'completed_jobs', 'created_at', 'updated_at']


class CustomerCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new customers.
    """
    addresses = CustomerAddressSerializer(many=True, required=False)

    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'alt_phone_number',
            'is_active', 'marketing_opt_in', 'notes', 'addresses'
        ]

    def create(self, validated_data):
        """Create customer with addresses"""
        addresses_data = validated_data.pop('addresses', [])
        customer = Customer.objects.create(**validated_data)

        # Create addresses
        for address_data in addresses_data:
            CustomerAddress.objects.create(customer=customer, **address_data)

        return customer

    def validate_email(self, value):
        """Check if email is already in use"""
        if Customer.objects.filter(email=value).exists():
            raise serializers.ValidationError("A customer with this email already exists.")
        return value


class CustomerCommunicationSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomerCommunication model.
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = CustomerCommunication
        fields = [
            'id', 'customer', 'customer_name', 'communication_type', 'subject',
            'message', 'contact_method', 'created_by', 'created_by_name',
            'requires_followup', 'followup_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer_name', 'created_by_name', 'created_at', 'updated_at']


class CustomerSearchSerializer(serializers.Serializer):
    """
    Serializer for customer search parameters.
    """
    query = serializers.CharField(required=False, allow_blank=True)
    search_type = serializers.ChoiceField(
        choices=['name', 'email', 'phone', 'address', 'all'],
        default='all'
    )
    is_active = serializers.BooleanField(required=False)
    has_jobs = serializers.BooleanField(required=False)


class CustomerListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for customer lists.
    """
    primary_address = serializers.SerializerMethodField()
    job_stats = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number',
            'is_active', 'primary_address', 'job_stats', 'created_at'
        ]

    def get_primary_address(self, obj):
        """Get primary address summary"""
        primary = obj.primary_address
        if primary:
            return {
                'street_address': primary.street_address,
                'city': primary.city,
                'state': primary.state,
                'postal_code': primary.postal_code
            }
        return None

    def get_job_stats(self, obj):
        """Get job statistics"""
        return {
            'total': obj.total_jobs,
            'active': obj.active_jobs,
            'completed': obj.completed_jobs
        }


class CustomerDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual customer view.
    """
    addresses = CustomerAddressSerializer(many=True, read_only=True)
    communications = CustomerCommunicationSerializer(many=True, read_only=True, source='communications.all')
    primary_address = CustomerAddressSerializer(read_only=True)
    recent_jobs = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number', 'alt_phone_number',
            'is_active', 'marketing_opt_in', 'notes', 'addresses', 'primary_address',
            'communications', 'recent_jobs', 'total_jobs', 'active_jobs', 'completed_jobs',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'communications', 'recent_jobs', 'total_jobs', 'active_jobs', 'completed_jobs', 'created_at', 'updated_at']

    def get_recent_jobs(self, obj):
        """Get recent jobs for this customer"""
        # This will be implemented when we create the jobs app
        # For now, return empty list
        return []
