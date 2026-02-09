#!/usr/bin/env python3
"""
MCP Tools Testing Script

Test your custom tools before deploying to production.
"""

import sys
sys.path.insert(0, '/home/bashar/odoo18')

from dotenv import load_dotenv
load_dotenv()

from odoo_mcp_server import ODOO
from custom_tools import (
    advanced_lead_search, AdvancedLeadSearchInput,
    analyze_sales_performance, SalesPerformanceInput,
    create_automated_task, AutoTaskInput,
    recommend_products, ProductRecommendationInput
)


def print_test_header(test_name):
    """Print test header"""
    print("\n" + "="*70)
    print(f"  TEST: {test_name}")
    print("="*70)


def test_advanced_lead_search():
    """Test advanced lead search"""
    print_test_header("Advanced Lead Search")

    try:
        result = advanced_lead_search(AdvancedLeadSearchInput(
            min_probability=50,
            max_probability=100,
            min_revenue=1000,
            limit=5
        ))

        print(f"✅ Found {result['count']} leads")
        print(f"   Total expected revenue: ${result['total_expected_revenue']:,.2f}")
        print("\n   Top leads:")
        for lead in result['leads'][:3]:
            print(f"   - {lead['name']}: {lead['probability']}% / ${lead.get('expected_revenue', 0):,.2f}")

        return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_sales_performance():
    """Test sales performance analysis"""
    print_test_header("Sales Performance Analysis")

    try:
        result = analyze_sales_performance(SalesPerformanceInput(
            date_from="2026-01-01",
            date_to="2026-12-31"
        ))

        metrics = result['metrics']
        print(f"✅ Analysis complete")
        print(f"   Total leads: {metrics['total_leads']}")
        print(f"   Won leads: {metrics['won_leads']}")
        print(f"   Win rate: {metrics['win_rate_percent']}%")
        print(f"   Total revenue: ${metrics['total_revenue']:,.2f}")
        print(f"   Avg deal size: ${metrics['average_deal_size']:,.2f}")

        return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_automated_task():
    """Test automated task creation"""
    print_test_header("Automated Task Creation")

    try:
        # First, get a lead to test with
        leads = ODOO.search_read("crm.lead", [], ["id"], limit=1)

        if not leads:
            print("⚠️  No leads found to test with")
            return False

        lead_id = leads[0]["id"]

        result = create_automated_task(AutoTaskInput(
            lead_id=lead_id,
            task_type="follow_up",
            days_from_now=7
        ))

        print(f"✅ Task created successfully")
        print(f"   Activity ID: {result['activity_id']}")
        print(f"   Lead: {result['lead_name']}")
        print(f"   Type: {result['task_type']}")
        print(f"   Deadline: {result['deadline']}")

        return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_product_recommendations():
    """Test product recommendations"""
    print_test_header("Product Recommendations")

    try:
        # Get a customer to test with
        customers = ODOO.search_read("res.partner", [["customer_rank", ">", 0]], ["id"], limit=1)

        if not customers:
            print("⚠️  No customers found to test with")
            return False

        customer_id = customers[0]["id"]

        result = recommend_products(ProductRecommendationInput(
            customer_id=customer_id,
            limit=5
        ))

        print(f"✅ Found {result['count']} product recommendations")
        print(f"   Based on: {result['based_on']}")
        print("\n   Recommended products:")
        for product in result['recommendations'][:3]:
            print(f"   - {product['name']}: ${product['list_price']}")

        return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*20 + "MCP TOOLS TEST SUITE" + " "*28 + "║")
    print("╚" + "═"*68 + "╝")

    tests = [
        ("Advanced Lead Search", test_advanced_lead_search),
        ("Sales Performance", test_sales_performance),
        ("Automated Task Creation", test_automated_task),
        ("Product Recommendations", test_product_recommendations)
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results.append((name, False))

    # Print summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}  {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
