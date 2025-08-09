#!/bin/bash

# Restaurant Backend Quality Testing Suite
# =======================================

echo "🏪 RESTAURANT BACKEND QUALITY TESTING"
echo "======================================"
echo "Started at: $(date)"
echo ""

BASE_URL="http://site1.local:8000/api/method/restaurant_management.api"
TOTAL_TESTS=0
PASSED_TESTS=0

# Function to test API endpoint
test_api() {
    local name="$1"
    local endpoint="$2"
    local method="${3:-GET}"
    local data="$4"
    local params="$5"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    start_time=$(date +%s.%N)
    
    if [ "$method" = "GET" ]; then
        if [ -n "$params" ]; then
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$BASE_URL.$endpoint?$params")
        else
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$BASE_URL.$endpoint")
        fi
    else
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$BASE_URL.$endpoint")
    fi
    
    end_time=$(date +%s.%N)
    response_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0.000")
    
    # Extract HTTP status and body
    http_status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    body=$(echo "$response" | sed 's/HTTPSTATUS:[0-9]*$//')
    
    if [ "$http_status" = "200" ]; then
        # Check if response contains success or data
        if echo "$body" | grep -q '"success":true\|"data":\[\|"message"'; then
            PASSED_TESTS=$((PASSED_TESTS + 1))
            printf "✅ PASS | %-40s | %.3fs | Success\n" "$name" "$response_time"
        else
            printf "❌ FAIL | %-40s | %.3fs | No success/data in response\n" "$name" "$response_time"
        fi
    else
        printf "❌ FAIL | %-40s | %.3fs | HTTP %s\n" "$name" "$response_time" "$http_status"
    fi
}

# Test Utility APIs
echo "🔧 TESTING UTILITY APIs"
echo "==============================="
test_api "Utility: get_positions" "get_positions"
test_api "Utility: get_order_types" "get_order_types"
test_api "Utility: get_order_statuses" "get_order_statuses"
test_api "Utility: get_payment_methods" "get_payment_methods"
test_api "Utility: get_spice_levels" "get_spice_levels"
test_api "Utility: get_employment_statuses" "get_employment_statuses"
test_api "Utility: get_genders" "get_genders"
test_api "Utility: get_discount_types" "get_discount_types"

# Test Face Recognition APIs
echo ""
echo "👤 TESTING FACE RECOGNITION APIs"
echo "================================="
test_api "Face: get_restaurant_staff" "get_restaurant_staff"
test_api "Face: get_all_staff_face_encodings" "get_all_staff_face_encodings"
test_api "Face: sync_face_recognition_data" "sync_face_recognition_data"
test_api "Face: get_staff_shift_schedule" "get_staff_shift_schedule"

# Test Order Management APIs
echo ""
echo "🍽️ TESTING ORDER MANAGEMENT APIs"
echo "=================================="
test_api "Order: get_pricing_contexts" "get_pricing_contexts"
test_api "Order: get_dynamic_price" "get_dynamic_price" "GET" "" "item_name=Caesar%20Salad&pricing_context=vip_room"

# Test Table Booking APIs
echo ""
echo "🪑 TESTING TABLE BOOKING APIs"
echo "=============================="
test_api "Booking: get_available_tables" "get_available_tables" "POST" '{"booking_date":"2025-08-15","booking_time":"19:00","party_size":4}'
test_api "Booking: get_restaurant_layout" "get_restaurant_layout"

# Test Staff Management APIs
echo ""
echo "👥 TESTING STAFF MANAGEMENT APIs"
echo "================================="
test_api "Staff: check_advance_eligibility" "check_advance_eligibility_api" "GET" "" "staff_id=EMP001&amount=100"
test_api "Staff: get_staff_for_tip_selection" "get_staff_for_tip_selection"

# Test Customer Management APIs
echo ""
echo "🧑‍🤝‍🧑 TESTING CUSTOMER MANAGEMENT APIs"
echo "======================================="
test_api "Customer: get_loyalty_rewards" "get_loyalty_rewards"
test_api "Customer: get_feedback_analytics" "get_feedback_analytics"

# Test Kitchen Management APIs
echo ""
echo "🍳 TESTING KITCHEN MANAGEMENT APIs"
echo "==================================="
test_api "Kitchen: get_kitchen_display_orders" "get_kitchen_display_orders"

# Test Inventory Management APIs
echo ""
echo "📦 TESTING INVENTORY MANAGEMENT APIs"
echo "====================================="
test_api "Inventory: get_inventory_status" "get_inventory_status"
test_api "Inventory: get_inventory_valuation_report" "get_inventory_valuation_report"

# Test Reporting APIs
echo ""
echo "📊 TESTING REPORTING APIs"
echo "=========================="
test_api "Reports: get_daily_operations_report" "get_daily_operations_report"
test_api "Reports: get_weekly_performance_report" "get_weekly_performance_report"

# Test Marketing APIs
echo ""
echo "📢 TESTING MARKETING APIs"
echo "=========================="
test_api "Marketing: get_active_promotions" "get_active_promotions"
test_api "Marketing: get_campaign_analytics" "get_campaign_analytics" "POST" '{"campaign_id":"TEST001"}'

# Performance Tests
echo ""
echo "⚡ TESTING PERFORMANCE BENCHMARKS"
echo "=================================="

# Test critical endpoints 3 times each for average response time
for endpoint in "get_positions" "get_restaurant_staff" "get_daily_operations_report" "get_all_staff_face_encodings"; do
    total_time=0
    for i in {1..3}; do
        start_time=$(date +%s.%N)
        curl -s "$BASE_URL.$endpoint" > /dev/null
        end_time=$(date +%s.%N)
        time_diff=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0.000")
        total_time=$(echo "$total_time + $time_diff" | bc -l 2>/dev/null || echo "0.000")
    done
    
    avg_time=$(echo "scale=3; $total_time / 3" | bc -l 2>/dev/null || echo "0.000")
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    # Performance is good if under 2 seconds
    if (( $(echo "$avg_time < 2.000" | bc -l 2>/dev/null || echo "0") )); then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        printf "✅ PASS | %-40s | %.3fs | Fast response\n" "Performance: $endpoint" "$avg_time"
    else
        printf "❌ FAIL | %-40s | %.3fs | Slow response\n" "Performance: $endpoint" "$avg_time"
    fi
done

# Print Summary
echo ""
echo "=============================================="
echo "📋 TEST SUMMARY"
echo "=============================================="

if [ $TOTAL_TESTS -gt 0 ]; then
    pass_rate=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l 2>/dev/null || echo "0.0")
else
    pass_rate="0.0"
fi

echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $((TOTAL_TESTS - PASSED_TESTS))"
echo "Pass Rate: ${pass_rate}%"

if (( $(echo "$pass_rate >= 90.0" | bc -l 2>/dev/null || echo "0") )); then
    echo "🎉 EXCELLENT: Backend quality is exceptional!"
elif (( $(echo "$pass_rate >= 80.0" | bc -l 2>/dev/null || echo "0") )); then
    echo "✅ GOOD: Backend quality is solid"
elif (( $(echo "$pass_rate >= 70.0" | bc -l 2>/dev/null || echo "0") )); then
    echo "⚠️ FAIR: Backend needs some improvements"
else
    echo "❌ POOR: Backend requires significant fixes"
fi

echo ""
echo "Completed at: $(date)"