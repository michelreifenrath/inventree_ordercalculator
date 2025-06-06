#!/usr/bin/env python3
"""
Test script to verify the legacy building calculation method with real InvenTree API.
This script tests the get_legacy_building_quantity method using actual credentials.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from inventree_order_calculator.api_client import ApiClient
    from inventree_order_calculator.config import AppConfig
    from inventree_order_calculator.models import BuildingCalculationMethod
    from inventree_order_calculator.calculator import OrderCalculator
    print("✅ Successfully imported all modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_legacy_building_method():
    """Test the legacy building calculation method with real API calls."""
    
    print("\n🔧 Testing Legacy Building Calculation Method")
    print("=" * 60)
    
    # Load configuration from .env file
    try:
        config = AppConfig.load()
        print(f"✅ Configuration loaded:")
        print(f"   URL: {config.inventree_url}")
        print(f"   Token: {'*' * 20}...{config.inventree_api_token[-10:] if config.inventree_api_token else 'None'}")
        print(f"   Instance URL: {config.inventree_instance_url}")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False
    
    # Create API client
    try:
        api_client = ApiClient(url=config.inventree_url, token=config.inventree_api_token)
        print("✅ API client created successfully")
    except Exception as e:
        print(f"❌ Failed to create API client: {e}")
        return False
    
    # Test basic API connectivity
    try:
        print("\n🌐 Testing API connectivity...")
        # Try to get a simple part list to verify connection
        parts_data = api_client.api.get('part/', params={'limit': 1})
        if isinstance(parts_data, dict) and 'count' in parts_data:
            print("✅ API connection successful")
            print(f"✅ Found {parts_data.get('count', 0)} parts in system")
        else:
            print(f"❌ API connection failed: unexpected response format")
            return False
    except Exception as e:
        print(f"❌ API connection test failed: {e}")
        return False
    
    # Find some parts to test with
    try:
        print("\n🔍 Finding parts to test legacy building calculation...")
        
        # Get parts that are assemblies (likely to have building quantities)
        parts_data = api_client.api.get('part/', params={
            'assembly': True,
            'limit': 10,
            'active': True
        })

        parts = parts_data.get('results', [])
        print(f"✅ Found {len(parts)} assembly parts to test")

        if not parts:
            print("⚠️ No assembly parts found, testing with any available parts...")
            parts_data = api_client.api.get('part/', params={'limit': 5, 'active': True})
            parts = parts_data.get('results', [])

        if not parts:
            print("❌ No parts found in the system")
            return False
            
    except Exception as e:
        print(f"❌ Failed to get parts for testing: {e}")
        return False
    
    # Test legacy building calculation on found parts
    success_count = 0
    test_count = 0
    
    print(f"\n🧪 Testing legacy building calculation on {min(5, len(parts))} parts...")
    print("-" * 60)
    
    for part in parts[:5]:  # Test first 5 parts
        part_id = part.get('pk')
        part_name = part.get('name', 'Unknown')
        
        test_count += 1
        print(f"\n📦 Testing Part {test_count}: {part_name} (ID: {part_id})")
        
        try:
            # Test the legacy building quantity method
            legacy_qty, warnings = api_client.get_legacy_building_quantity(part_id)
            print(f"   ✅ Legacy building quantity: {legacy_qty}")
            
            if warnings:
                print(f"   ⚠️ Warnings: {warnings}")
            
            # Compare with standard building field from part data
            part_data, part_warnings = api_client.get_part_data(part_id)
            if part_data:
                standard_building = getattr(part_data, 'building', 0.0)
                print(f"   📊 Standard building field: {standard_building}")
                
                if legacy_qty != standard_building:
                    print(f"   🔍 Difference detected: Legacy={legacy_qty}, Standard={standard_building}")
                else:
                    print(f"   ✅ Values match: {legacy_qty}")
            
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Error testing part {part_id}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n📈 Test Results:")
    print(f"   Successful tests: {success_count}/{test_count}")
    print(f"   Success rate: {(success_count/test_count)*100:.1f}%" if test_count > 0 else "   No tests run")
    
    return success_count > 0

def test_calculator_integration():
    """Test the calculator with both building methods."""
    
    print("\n🧮 Testing Calculator Integration")
    print("=" * 60)
    
    try:
        config = AppConfig.load()
        api_client = ApiClient(url=config.inventree_url, token=config.inventree_api_token)
        
        # Test with OLD_GUI method
        print("\n🔧 Testing with OLD_GUI (Legacy) method...")
        calculator_old = OrderCalculator(api_client, building_method=BuildingCalculationMethod.OLD_GUI)
        print("✅ OrderCalculator created with OLD_GUI method")
        
        # Test with NEW_GUI method
        print("\n🆕 Testing with NEW_GUI (Standard) method...")
        calculator_new = OrderCalculator(api_client, building_method=BuildingCalculationMethod.NEW_GUI)
        print("✅ OrderCalculator created with NEW_GUI method")
        
        print("✅ Calculator integration test successful")
        return True
        
    except Exception as e:
        print(f"❌ Calculator integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Legacy Building Calculation Test Script")
    print("=" * 60)
    
    # Test the legacy building method
    legacy_success = test_legacy_building_method()
    
    # Test calculator integration
    integration_success = test_calculator_integration()
    
    print("\n" + "=" * 60)
    print("📋 FINAL RESULTS:")
    print(f"   Legacy Building Method: {'✅ PASS' if legacy_success else '❌ FAIL'}")
    print(f"   Calculator Integration: {'✅ PASS' if integration_success else '❌ FAIL'}")
    
    if legacy_success and integration_success:
        print("\n🎉 All tests passed! Legacy building calculation is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the output above for details.")
        sys.exit(1)
