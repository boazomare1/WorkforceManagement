# 🍽️ Restaurant Management System - Postman Testing Guide

## 🚀 Quick Start

### 1. Import the Collection
- Open Postman
- Click "Import" 
- Select `restaurant_management_postman_collection.json`
- The collection will be imported with all 28 API endpoints organized by category

### 2. Set Environment Variables
The collection uses these global variables:
- `base_url`: `http://site1.local:8000`
- `access_token`: Automatically populated after successful login
- `current_user`: Current logged-in user email
- `user_role`: Current user's position/role

## 🔐 Authentication Testing

### Test User Credentials
| Role | Email | Password | Department | Permissions |
|------|-------|----------|------------|-------------|
| **Manager** | `manager@restaurant.com` | `manager123` | Management | Full access to all features |
| **Waiter** | `waiter@restaurant.com` | `waiter123` | Service | Order management, table bookings |
| **Chef** | `chef@restaurant.com` | `chef123` | Kitchen | Kitchen display, order processing |
| **Cashier** | `cashier@restaurant.com` | `cashier123` | Support | Payment processing, basic operations |

### Login Flow
1. **Start with any login request** (e.g., "1. Login - Manager User")
2. **Send the request** - it will automatically:
   - Save the access token to `{{access_token}}`
   - Save user info to `{{current_user}}` and `{{user_role}}`
   - Display success/error details in the console
3. **Use the saved token** for all subsequent authenticated requests

## 📋 Testing Strategy

### Phase 1: Authentication & Basic Access
1. **Test all login scenarios** - verify each user type can authenticate
2. **Test logout** - ensure proper session termination
3. **Test unauthenticated access** - verify public endpoints work without tokens

### Phase 2: Role-Based Access Control
1. **Login as Manager** - test high-privilege operations
2. **Login as Waiter** - test service-level operations
3. **Login as Chef** - test kitchen operations
4. **Login as Cashier** - test payment operations

### Phase 3: API Functionality
1. **Test each category** systematically
2. **Verify response structures** match expected format
3. **Test error handling** with invalid inputs
4. **Test edge cases** and boundary conditions

## 🧪 Test Categories

### 🔐 Authentication & User Management (6 APIs)
- **Login tests** for all user types
- **User info retrieval** with authentication
- **Logout functionality**

### 👥 Staff Management (3 APIs)
- **Get all staff** (requires authentication)
- **Get staff by ID** (requires authentication)
- **Get restaurant staff** (requires authentication)

### 🍽️ Menu Management (3 APIs)
- **Public endpoints** - no authentication required
- **Menu categories, items, popular items**

### 📋 Order Management (2 APIs)
- **Requires authentication**
- **Test with different user roles**

### 🍽️ Table Booking (2 APIs)
- **Public endpoints** - no authentication required
- **Test availability and booking retrieval**

### 💰 Payment & Tips (2 APIs)
- **Requires authentication**
- **Test tip distribution and advance eligibility**

### 🎯 Loyalty & Marketing (2 APIs)
- **Public endpoints** - no authentication required
- **Test loyalty rewards and promotions**

### 📊 Reports & Analytics (2 APIs)
- **Requires authentication**
- **Test with different user roles**

### 👤 Face Recognition (2 APIs)
- **Requires authentication**
- **Test staff face encodings and attendance**

### 🔧 Utility APIs (4 APIs)
- **Public endpoints** - no authentication required
- **Test system configuration data**

## 🔍 Testing Tips

### 1. **Console Monitoring**
- Open Postman Console (View → Show Postman Console)
- Watch for automatic token saving messages
- Monitor test results and error messages

### 2. **Response Validation**
- Check HTTP status codes (200, 403, 500, etc.)
- Verify response structure matches expected format
- Look for error messages in failed responses

### 3. **Authentication Testing**
- Test endpoints with and without valid tokens
- Verify role-based access control works
- Test token expiration scenarios

### 4. **Error Handling**
- Test with invalid user credentials
- Test with missing required parameters
- Test with malformed request data

## 🚨 Common Issues & Solutions

### Login Fails
- **Check Frappe server** is running (`http://site1.local:8000`)
- **Verify user exists** in the system
- **Check password** is set correctly

### 403 Forbidden Errors
- **User lacks permissions** for the endpoint
- **Token expired** or invalid
- **Role-based access** restrictions

### 500 Internal Server Errors
- **Check Frappe logs** for detailed error information
- **Verify API function** exists and is properly implemented
- **Check database** connectivity and permissions

## 📊 Expected Test Results

### ✅ **Should Pass (Public Endpoints)**
- Menu management APIs
- Table booking queries
- Loyalty and marketing APIs
- Utility configuration APIs

### 🔐 **Requires Authentication**
- Staff management APIs
- Order management APIs
- Reports and analytics
- Face recognition APIs

### 🎯 **Role-Based Access**
- **Manager**: Access to all endpoints
- **Waiter**: Service and order operations
- **Chef**: Kitchen and order processing
- **Cashier**: Payment and basic operations

## 🔄 Testing Workflow

1. **Import collection** into Postman
2. **Set base_url** to `http://site1.local:8000`
3. **Start with Manager login** to test full access
4. **Test each category** systematically
5. **Switch user roles** to test permissions
6. **Verify all endpoints** work as expected
7. **Document any issues** found during testing

## 📝 Test Results Template

```markdown
## Test Results - [Date]

### Authentication Tests
- [ ] Manager Login: ✅/❌
- [ ] Waiter Login: ✅/❌
- [ ] Chef Login: ✅/❌
- [ ] Cashier Login: ✅/❌

### API Category Tests
- [ ] Staff Management: ✅/❌
- [ ] Menu Management: ✅/❌
- [ ] Order Management: ✅/❌
- [ ] Table Booking: ✅/❌
- [ ] Payment & Tips: ✅/❌
- [ ] Loyalty & Marketing: ✅/❌
- [ ] Reports & Analytics: ✅/❌
- [ ] Face Recognition: ✅/❌
- [ ] Utility APIs: ✅/❌

### Issues Found
- [List any issues or unexpected behavior]

### Overall Status
- **Pass Rate**: XX%
- **Status**: Ready for Production / Needs Fixes
```

## 🎯 Success Criteria

The system is ready for production when:
- ✅ **All login tests pass** for all user types
- ✅ **Public endpoints** work without authentication
- ✅ **Protected endpoints** require valid authentication
- ✅ **Role-based access** works correctly
- ✅ **Response formats** are consistent
- ✅ **Error handling** is graceful
- ✅ **Performance** is acceptable (< 2s response time)

---

**Happy Testing! 🚀**

For support or questions, check the Frappe server logs or API documentation. 