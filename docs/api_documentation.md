# API Documentation - Roofing Contractor Platform

## Overview

The Roofing Contractor Platform provides a comprehensive REST API for integrating with external systems, building custom applications, and automating business processes. This documentation covers all available endpoints, authentication methods, and integration patterns.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Webhooks](#webhooks)
5. [Rate Limiting](#rate-limiting)
6. [Error Handling](#error-handling)
7. [SDKs and Libraries](#sdks-and-libraries)
8. [Integration Examples](#integration-examples)

---

## Getting Started

### Base URL

```
Production: https://api.roofingplatform.com/v1/
Staging: https://api-staging.roofingplatform.com/v1/
```

### Content Types

- **Request**: `application/json`
- **Response**: `application/json`
- **File Uploads**: `multipart/form-data`

### API Versioning

The API uses semantic versioning:
- **v1**: Current stable version
- **Breaking Changes**: New major version
- **Backwards Compatible**: Minor/patch versions

---

## Authentication

### JWT Token Authentication

The API uses JSON Web Tokens (JWT) for authentication with optional Multi-Factor Authentication (MFA).

#### Login Flow

```bash
POST /api/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "manager",
    "mfa_required": true
  }
}
```

#### MFA Verification (if required)

```bash
POST /api/auth/verify-mfa/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "code": "123456",
  "method": "totp"
}
```

#### Using API Tokens

Include the JWT token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

#### Token Refresh

```bash
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "your_refresh_token"
}
```

### API Key Authentication (for integrations)

For server-to-server integrations, use API keys:

```bash
X-API-Key: your_api_key
X-API-Secret: your_api_secret
```

---

## API Endpoints

### Customers

#### List Customers
```http
GET /api/customers/customers/
```

**Parameters:**
- `search` (string): Search by name, email, or phone
- `page` (integer): Page number for pagination
- `page_size` (integer): Items per page (max 100)

**Response:**
```json
{
  "count": 25,
  "next": "http://api.example.com/api/customers/customers/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "phone": "+1234567890",
      "address": "123 Main St",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### Create Customer
```http
POST /api/customers/customers/
```

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane@example.com",
  "phone": "+1987654321",
  "address": "456 Oak Avenue",
  "city": "Springfield",
  "state": "IL",
  "zip_code": "62701",
  "roof_type": "asphalt_shingle",
  "roof_age_years": 15
}
```

#### Get Customer Details
```http
GET /api/customers/customers/{id}/
```

#### Update Customer
```http
PATCH /api/customers/customers/{id}/
```

#### Delete Customer
```http
DELETE /api/customers/customers/{id}/
```

### Quotes

#### List Quotes
```http
GET /api/quotes/quotes/
```

**Parameters:**
- `status` (string): Filter by status (draft, sent, viewed, accepted, declined)
- `customer` (integer): Filter by customer ID
- `date_from` (date): Filter quotes from date
- `date_to` (date): Filter quotes to date

#### Create Quote
```http
POST /api/quotes/quotes/
```

**Request Body:**
```json
{
  "customer": 1,
  "title": "Roof Replacement Quote",
  "project_address": "123 Main St",
  "project_type": "replacement",
  "description": "Complete roof replacement with premium materials",
  "valid_until": "2024-02-15",
  "items": [
    {
      "description": "Premium Asphalt Shingles",
      "quantity": 120,
      "unit": "sq_ft",
      "unit_price": 4.50,
      "category": "materials"
    },
    {
      "description": "Labor - Roof Replacement",
      "quantity": 3,
      "unit": "days",
      "unit_price": 800.00,
      "category": "labor"
    }
  ]
}
```

#### Send Quote to Customer
```http
POST /api/quotes/quotes/{id}/send_to_customer/
```

#### Accept Quote
```http
POST /api/quotes/quotes/{id}/accept/
```

**Request Body:**
```json
{
  "notes": "Looks good, please proceed"
}
```

#### Convert Quote to Job
```http
POST /api/quotes/quotes/{id}/convert_to_job/
```

### Jobs

#### List Jobs
```http
GET /api/jobs/jobs/
```

**Parameters:**
- `status` (string): Filter by status
- `technician` (integer): Filter by technician ID
- `date_from` (date): Start date filter
- `date_to` (date): End date filter
- `priority` (string): low, medium, high

#### Create Job
```http
POST /api/jobs/jobs/
```

**Request Body:**
```json
{
  "customer": 1,
  "title": "Emergency Roof Repair",
  "description": "Fix leaking roof section",
  "priority": "high",
  "scheduled_date": "2024-01-20",
  "scheduled_time": "09:00:00",
  "estimated_cost": 2500.00,
  "assigned_technicians": [2, 3]
}
```

#### Update Job Status
```http
POST /api/jobs/jobs/{id}/start/
POST /api/jobs/jobs/{id}/pause/
POST /api/jobs/jobs/{id}/resume/
POST /api/jobs/jobs/{id}/complete/
```

#### Add Job Notes
```http
POST /api/jobs/jobs/{id}/notes/
```

**Request Body:**
```json
{
  "note": "Customer requested additional work",
  "is_internal": false
}
```

#### Upload Job Photos
```http
POST /api/jobs/jobs/{id}/photos/
Content-Type: multipart/form-data

photo: <image_file>
caption: "Before repair"
```

### Inventory

#### List Inventory Items
```http
GET /api/inventory/items/
```

**Parameters:**
- `category` (string): Filter by category
- `stock_status` (string): low_stock, normal, out_of_stock
- `search` (string): Search by name or SKU

#### Create Inventory Item
```http
POST /api/inventory/items/
```

**Request Body:**
```json
{
  "name": "Premium Asphalt Shingles",
  "sku": "SHINGLE-PREMIUM-001",
  "category": "roofing_materials",
  "unit": "sq_ft",
  "current_stock": 1000,
  "minimum_stock": 100,
  "unit_cost": 2.50,
  "selling_price": 4.50,
  "location": "Warehouse A",
  "supplier": 1
}
```

#### Update Stock
```http
POST /api/inventory/items/{id}/update_stock/
```

**Request Body:**
```json
{
  "quantity_change": 500,
  "reason": "New shipment received",
  "reference": "PO-2024-001"
}
```

#### Low Stock Alerts
```http
GET /api/inventory/items/low_stock/
```

### Reports

#### Dashboard Data
```http
GET /api/reports/dashboard/
```

**Response:**
```json
{
  "metrics": {
    "total_jobs": 150,
    "active_jobs": 12,
    "monthly_revenue": 45000.00,
    "customer_satisfaction": 4.7
  },
  "recent_jobs": [...],
  "recent_quotes": [...],
  "alerts": [...]
}
```

#### Custom Reports
```http
POST /api/reports/reports/
```

**Request Body:**
```json
{
  "name": "Monthly Performance Report",
  "report_type": "job_status",
  "description": "Monthly job completion analysis",
  "parameters": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "is_scheduled": true,
  "frequency": "monthly",
  "recipients": ["manager@example.com"]
}
```

#### Chart Data
```http
GET /api/reports/charts/?type=job_status&days=30
```

### Users and Authentication

#### User Profile
```http
GET /api/accounts/profile/
PATCH /api/accounts/profile/
```

#### Change Password
```http
POST /api/accounts/change-password/
```

**Request Body:**
```json
{
  "old_password": "currentpassword",
  "new_password": "newsecurepassword"
}
```

#### MFA Setup
```http
GET /api/mfa/setup/
POST /api/mfa/setup/
```

**Setup Request:**
```json
{
  "method": "totp"
}
```

#### MFA Verification
```http
POST /api/mfa/verify/
```

**Request Body:**
```json
{
  "code": "123456",
  "method": "totp"
}
```

---

## Webhooks

### Webhook Configuration

Set up webhooks to receive real-time notifications about platform events.

#### Register Webhook
```http
POST /api/webhooks/webhooks/
```

**Request Body:**
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["job.completed", "quote.accepted"],
  "secret": "your_webhook_secret",
  "is_active": true
}
```

### Supported Events

#### Job Events
- `job.created` - New job created
- `job.started` - Job started by technician
- `job.completed` - Job marked as completed
- `job.cancelled` - Job cancelled
- `job.photo_uploaded` - New photo uploaded to job

#### Quote Events
- `quote.created` - New quote created
- `quote.sent` - Quote sent to customer
- `quote.viewed` - Customer viewed quote
- `quote.accepted` - Customer accepted quote
- `quote.declined` - Customer declined quote

#### Customer Events
- `customer.created` - New customer created
- `customer.updated` - Customer profile updated
- `customer.deleted` - Customer deleted

#### Inventory Events
- `inventory.low_stock` - Item reached low stock level
- `inventory.out_of_stock` - Item out of stock
- `inventory.stock_updated` - Stock level changed

### Webhook Payload Format

```json
{
  "event": "job.completed",
  "timestamp": "2024-01-15T14:30:00Z",
  "data": {
    "id": 123,
    "customer": {
      "id": 456,
      "name": "John Doe"
    },
    "title": "Roof Repair",
    "completed_at": "2024-01-15T14:30:00Z"
  },
  "signature": "sha256=..."
}
```

### Webhook Security

Webhooks include an HMAC signature for verification:

```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, f"sha256={expected_signature}")
```

---

## Rate Limiting

### Rate Limits

- **Authenticated Requests**: 1000 requests per hour
- **Anonymous Requests**: 100 requests per hour
- **File Uploads**: 50 uploads per hour
- **Webhook Deliveries**: 1000 deliveries per hour

### Rate Limit Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 3600
```

### Handling Rate Limits

When rate limited, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 3600

{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Try again in 3600 seconds.",
  "retry_after": 3600
}
```

---

## Error Handling

### HTTP Status Codes

- **200 OK**: Success
- **201 Created**: Resource created
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

### Error Response Format

```json
{
  "error": "validation_error",
  "message": "The request contains invalid data",
  "details": {
    "field_name": ["This field is required"],
    "email": ["Enter a valid email address"]
  }
}
```

### Common Error Codes

- `validation_error`: Invalid input data
- `authentication_error`: Invalid credentials
- `permission_denied`: Insufficient permissions
- `not_found`: Resource doesn't exist
- `rate_limit_exceeded`: Too many requests
- `server_error`: Internal server error

---

## SDKs and Libraries

### Official SDKs

#### Python SDK
```bash
pip install roofing-platform-sdk
```

```python
from roofing_platform import Client

client = Client(api_key='your_key', api_secret='your_secret')

# List customers
customers = client.customers.list()

# Create job
job = client.jobs.create({
    'customer': 1,
    'title': 'Emergency Repair',
    'priority': 'high'
})
```

#### JavaScript SDK
```bash
npm install @roofing-platform/sdk
```

```javascript
import { RoofingPlatform } from '@roofing-platform/sdk';

const client = new RoofingPlatform({
  apiKey: 'your_key',
  apiSecret: 'your_secret'
});

// Create quote
const quote = await client.quotes.create({
  customer: 1,
  title: 'Roof Replacement',
  items: [...]
});
```

#### PHP SDK
```bash
composer require roofing-platform/sdk
```

```php
use RoofingPlatform\Client;

$client = new Client('your_key', 'your_secret');

// Get job details
$job = $client->jobs()->get(123);
```

### Community Libraries

- **Go SDK**: `go get github.com/roofing-platform/go-sdk`
- **Ruby SDK**: `gem install roofing_platform`
- **Java SDK**: Maven/Gradle dependency available

---

## Integration Examples

### E-commerce Integration

```python
# Sync customer data from e-commerce platform
def sync_customers_from_shopify():
    shopify_customers = shopify_api.get_customers()

    for shopify_customer in shopify_customers:
        customer_data = {
            'first_name': shopify_customer['first_name'],
            'last_name': shopify_customer['last_name'],
            'email': shopify_customer['email'],
            'phone': shopify_customer.get('phone'),
            'address': shopify_customer.get('address1', ''),
        }

        # Check if customer exists
        existing = roofing_api.customers.list(search=customer_data['email'])
        if not existing:
            roofing_api.customers.create(customer_data)
```

### CRM Integration

```javascript
// Sync job updates to CRM
async function syncJobToCRM(jobId) {
    const job = await roofingAPI.jobs.get(jobId);

    await crmAPI.updateDeal(job.crm_deal_id, {
        status: job.status,
        completed_date: job.completed_at,
        revenue: job.actual_cost,
        notes: job.notes
    });
}

// Listen for job completion webhooks
app.post('/webhooks/roofing', (req, res) => {
    if (req.body.event === 'job.completed') {
        syncJobToCRM(req.body.data.id);
    }
    res.sendStatus(200);
});
```

### Accounting Software Integration

```python
# Export invoices to QuickBooks
def export_invoices_to_quickbooks():
    # Get completed jobs with invoices
    completed_jobs = roofing_api.jobs.list(
        status='completed',
        has_invoice=True,
        date_from='2024-01-01'
    )

    for job in completed_jobs:
        invoice_data = {
            'customer_id': job.customer.quickbooks_id,
            'date': job.completed_at.date(),
            'due_date': job.completed_at.date() + timedelta(days=30),
            'items': [
                {
                    'description': f"{job.title} - Labor",
                    'amount': job.labor_cost,
                    'tax_code': 'TAX'
                },
                {
                    'description': f"{job.title} - Materials",
                    'amount': job.material_cost,
                    'tax_code': 'TAX'
                }
            ]
        }

        quickbooks_api.create_invoice(invoice_data)
```

### Mobile App Integration

```javascript
// React Native mobile app
import { RoofingAPI } from '@roofing-platform/mobile-sdk';

class JobDetailsScreen extends Component {
    async componentDidMount() {
        const job = await RoofingAPI.jobs.get(this.props.jobId);
        this.setState({ job });
    }

    async startJob() {
        await RoofingAPI.jobs.start(this.state.job.id);
        // Refresh job data
        const updatedJob = await RoofingAPI.jobs.get(this.state.job.id);
        this.setState({ job: updatedJob });
    }

    async uploadPhoto(imageUri) {
        const formData = new FormData();
        formData.append('photo', {
            uri: imageUri,
            type: 'image/jpeg',
            name: 'job_photo.jpg'
        });

        await RoofingAPI.jobs.uploadPhoto(this.state.job.id, formData);
    }
}
```

---

## API Changelog

### Version 1.1 (Latest)
- Added webhook support for real-time notifications
- Enhanced filtering options for all list endpoints
- Added bulk operations for customer and job management
- Improved error messages and validation

### Version 1.0 (Initial Release)
- Complete REST API for all platform features
- JWT authentication with MFA support
- Comprehensive CRUD operations
- Rate limiting and security features

---

## Support and Resources

### Getting Help

- **Developer Portal**: https://developers.roofingplatform.com
- **API Documentation**: https://api.roofingplatform.com/docs
- **Community Forums**: https://community.roofingplatform.com
- **Support Email**: api-support@roofingplatform.com

### Rate Limits and Quotas

- **Free Tier**: 1,000 requests/month
- **Professional**: 100,000 requests/month
- **Enterprise**: Unlimited requests

### Best Practices

1. **Use appropriate authentication** for your use case
2. **Implement proper error handling** and retry logic
3. **Respect rate limits** and implement exponential backoff
4. **Use webhooks** for real-time data synchronization
5. **Cache frequently accessed data** to reduce API calls
6. **Validate data** before sending to the API
7. **Monitor API usage** and performance metrics

---

*This API documentation is regularly updated. Subscribe to our developer newsletter for the latest changes and new features.*
