from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from .models import Customer, CustomerAddress, CustomerCommunication
from .serializers import (
    CustomerSerializer,
    CustomerCreateSerializer,
    CustomerListSerializer,
    CustomerDetailSerializer,
    CustomerAddressSerializer,
    CustomerCommunicationSerializer,
    CustomerSearchSerializer
)
from accounts.permissions import TechnicianAndAbove


class CustomerListCreateView(generics.ListCreateAPIView):
    """
    List all customers or create a new customer.
    """
    permission_classes = [TechnicianAndAbove]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CustomerCreateSerializer
        return CustomerListSerializer

    def get_queryset(self):
        """
        Filter customers based on user permissions and search parameters.
        """
        queryset = Customer.objects.prefetch_related('addresses').select_related('created_by')

        # Search functionality
        search_query = self.request.query_params.get('search', '')
        search_type = self.request.query_params.get('search_type', 'all')

        if search_query:
            if search_type == 'name':
                queryset = queryset.filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query)
                )
            elif search_type == 'email':
                queryset = queryset.filter(email__icontains=search_query)
            elif search_type == 'phone':
                queryset = queryset.filter(
                    Q(phone_number__icontains=search_query) |
                    Q(alt_phone_number__icontains=search_query)
                )
            elif search_type == 'address':
                queryset = queryset.filter(
                    Q(addresses__street_address__icontains=search_query) |
                    Q(addresses__city__icontains=search_query) |
                    Q(addresses__state__icontains=search_query) |
                    Q(addresses__postal_code__icontains=search_query)
                ).distinct()
            else:  # search_type == 'all'
                queryset = queryset.filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(email__icontains=search_query) |
                    Q(phone_number__icontains=search_query) |
                    Q(alt_phone_number__icontains=search_query) |
                    Q(addresses__street_address__icontains=search_query) |
                    Q(addresses__city__icontains=search_query) |
                    Q(addresses__state__icontains=search_query) |
                    Q(addresses__postal_code__icontains=search_query)
                ).distinct()

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filter by job status
        has_jobs = self.request.query_params.get('has_jobs')
        if has_jobs is not None:
            if has_jobs.lower() == 'true':
                queryset = queryset.annotate(job_count=Count('jobs')).filter(job_count__gt=0)
            else:
                queryset = queryset.annotate(job_count=Count('jobs')).filter(job_count=0)

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Set the created_by field to the current user"""
        serializer.save(created_by=self.request.user)


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a customer.
    """
    queryset = Customer.objects.prefetch_related(
        'addresses', 'communications'
    ).select_related('created_by')
    serializer_class = CustomerDetailSerializer
    permission_classes = [TechnicianAndAbove]


class CustomerAddressListCreateView(generics.ListCreateAPIView):
    """
    List all addresses for a customer or create a new address.
    """
    serializer_class = CustomerAddressSerializer
    permission_classes = [TechnicianAndAbove]

    def get_queryset(self):
        """Filter addresses by customer"""
        customer_id = self.kwargs.get('customer_id')
        return CustomerAddress.objects.filter(customer_id=customer_id)

    def perform_create(self, serializer):
        """Set the customer for the new address"""
        customer_id = self.kwargs.get('customer_id')
        customer = get_object_or_404(Customer, id=customer_id)
        serializer.save(customer=customer)


class CustomerAddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a customer address.
    """
    serializer_class = CustomerAddressSerializer
    permission_classes = [TechnicianAndAbove]

    def get_queryset(self):
        """Filter addresses by customer"""
        customer_id = self.kwargs.get('customer_id')
        return CustomerAddress.objects.filter(customer_id=customer_id)


class CustomerCommunicationListCreateView(generics.ListCreateAPIView):
    """
    List all communications for a customer or create a new communication.
    """
    serializer_class = CustomerCommunicationSerializer
    permission_classes = [TechnicianAndAbove]

    def get_queryset(self):
        """Filter communications by customer"""
        customer_id = self.kwargs.get('customer_id')
        return CustomerCommunication.objects.filter(
            customer_id=customer_id
        ).select_related('created_by')

    def perform_create(self, serializer):
        """Set the customer and created_by for the new communication"""
        customer_id = self.kwargs.get('customer_id')
        customer = get_object_or_404(Customer, id=customer_id)
        serializer.save(customer=customer, created_by=self.request.user)


class CustomerCommunicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a customer communication.
    """
    serializer_class = CustomerCommunicationSerializer
    permission_classes = [TechnicianAndAbove]

    def get_queryset(self):
        """Filter communications by customer"""
        customer_id = self.kwargs.get('customer_id')
        return CustomerCommunication.objects.filter(customer_id=customer_id)


class CustomerSearchView(APIView):
    """
    Advanced customer search endpoint.
    """
    permission_classes = [TechnicianAndAbove]

    def post(self, request):
        """Perform advanced customer search"""
        serializer = CustomerSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        search_params = serializer.validated_data
        queryset = Customer.objects.prefetch_related('addresses').select_related('created_by')

        # Apply search filters
        query = search_params.get('query', '')
        search_type = search_params.get('search_type', 'all')

        if query:
            if search_type == 'name':
                queryset = queryset.filter(
                    Q(first_name__icontains=query) |
                    Q(last_name__icontains=query)
                )
            elif search_type == 'email':
                queryset = queryset.filter(email__icontains=query)
            elif search_type == 'phone':
                queryset = queryset.filter(
                    Q(phone_number__icontains=query) |
                    Q(alt_phone_number__icontains=query)
                )
            elif search_type == 'address':
                queryset = queryset.filter(
                    Q(addresses__street_address__icontains=query) |
                    Q(addresses__city__icontains=query) |
                    Q(addresses__state__icontains=query) |
                    Q(addresses__postal_code__icontains=query)
                ).distinct()
            else:  # search_type == 'all'
                queryset = queryset.filter(
                    Q(first_name__icontains=query) |
                    Q(last_name__icontains=query) |
                    Q(email__icontains=query) |
                    Q(phone_number__icontains=query) |
                    Q(alt_phone_number__icontains=query) |
                    Q(addresses__street_address__icontains=query) |
                    Q(addresses__city__icontains=query) |
                    Q(addresses__state__icontains=query) |
                    Q(addresses__postal_code__icontains=query)
                ).distinct()

        # Apply additional filters
        if 'is_active' in search_params:
            queryset = queryset.filter(is_active=search_params['is_active'])

        if 'has_jobs' in search_params:
            if search_params['has_jobs']:
                queryset = queryset.annotate(job_count=Count('jobs')).filter(job_count__gt=0)
            else:
                queryset = queryset.annotate(job_count=Count('jobs')).filter(job_count=0)

        # Serialize results
        results = CustomerListSerializer(queryset[:50], many=True)  # Limit to 50 results

        return Response({
            'count': queryset.count(),
            'results': results.data
        })


class CustomerStatsView(APIView):
    """
    Get customer statistics.
    """
    permission_classes = [TechnicianAndAbove]

    def get(self, request):
        """Get customer statistics"""
        total_customers = Customer.objects.count()
        active_customers = Customer.objects.filter(is_active=True).count()
        customers_with_jobs = Customer.objects.annotate(
            job_count=Count('jobs')
        ).filter(job_count__gt=0).count()

        # Recent customer additions (last 30 days)
        from django.utils import timezone
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        recent_customers = Customer.objects.filter(created_at__gte=thirty_days_ago).count()

        return Response({
            'total_customers': total_customers,
            'active_customers': active_customers,
            'customers_with_jobs': customers_with_jobs,
            'inactive_customers': total_customers - active_customers,
            'recent_customers': recent_customers
        })
