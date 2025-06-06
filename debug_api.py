#!/usr/bin/env python3
"""
Debug script to test the InvenTree API connection and StockItem access.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_basic_api():
    """Test basic API functionality."""
    print("🔧 Testing Basic API Functionality")
    print("=" * 50)
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from inventree_order_calculator.config import AppConfig
        print("✅ Config import successful")
        
        from inventree_order_calculator.api_client import ApiClient
        print("✅ ApiClient import successful")
        
        # Test inventree-api imports
        try:
            from inventree.api import InvenTreeAPI
            from inventree.part import Part
            from inventree.stock import StockItem
            print("✅ InvenTree API imports successful")
        except ImportError as e:
            print(f"❌ InvenTree API import failed: {e}")
            return False
        
        # Load config
        print("\n🔧 Loading configuration...")
        config = AppConfig.load()
        print(f"✅ URL: {config.inventree_url}")
        print(f"✅ Token: {'*' * 20}...{config.inventree_api_token[-10:]}")
        
        # Create API client
        print("\n🌐 Creating API client...")
        api_client = ApiClient(url=config.inventree_url, token=config.inventree_api_token)
        print("✅ API client created")
        
        # Test direct InvenTree API connection
        print("\n🔗 Testing direct InvenTree API connection...")
        api = InvenTreeAPI(config.inventree_url, token=config.inventree_api_token)
        print("✅ Direct API connection created")
        
        # Test basic API call
        print("\n📋 Testing basic API call...")
        # The InvenTree API returns data directly, not a response object
        data = api.get('part/', params={'limit': 1})
        print(f"✅ API call successful")
        print(f"✅ Found {data.get('count', 0)} parts in system")

        # Get a part to test with
        results = data.get('results', [])
        if results:
            test_part = results[0]
            part_id = test_part.get('pk')
            part_name = test_part.get('name', 'Unknown')
            print(f"✅ Test part: {part_name} (ID: {part_id})")

            # Test StockItem.list
            print(f"\n📦 Testing StockItem.list for part {part_id}...")
            try:
                stock_items = StockItem.list(api, part=part_id)
                print(f"✅ Found {len(stock_items) if stock_items else 0} stock items")

                if stock_items:
                    for i, item in enumerate(stock_items[:3]):  # Show first 3
                        print(f"   Stock item {i+1}:")
                        print(f"     - Has _data: {hasattr(item, '_data')}")
                        print(f"     - Has quantity attr: {hasattr(item, 'quantity')}")

                        if hasattr(item, '_data') and item._data:
                            print(f"     - _data keys: {list(item._data.keys())}")
                            print(f"     - _data quantity: {item._data.get('quantity')}")

                        if hasattr(item, 'quantity'):
                            print(f"     - Direct quantity: {item.quantity}")

                # Test with is_building=True filter
                print(f"\n🏗️ Testing StockItem.list with is_building=True...")
                building_items = StockItem.list(api, part=part_id, is_building=True)
                print(f"✅ Found {len(building_items) if building_items else 0} building stock items")

                if building_items:
                    for i, item in enumerate(building_items[:3]):
                        print(f"   Building item {i+1}:")
                        if hasattr(item, '_data') and item._data:
                            print(f"     - _data quantity: {item._data.get('quantity')}")
                        if hasattr(item, 'quantity'):
                            print(f"     - Direct quantity: {item.quantity}")

            except Exception as e:
                print(f"❌ StockItem.list failed: {e}")
                import traceback
                traceback.print_exc()
                return False

            return True
        else:
            print("⚠️ No parts found to test with")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_legacy_method():
    """Test the legacy building quantity method."""
    print("\n🔧 Testing Legacy Building Quantity Method")
    print("=" * 50)
    
    try:
        from inventree_order_calculator.config import AppConfig
        from inventree_order_calculator.api_client import ApiClient
        
        config = AppConfig.load()
        api_client = ApiClient(url=config.inventree_url, token=config.inventree_api_token)
        
        # Test with multiple parts to find ones with building quantities
        data = api_client.api.get('part/', params={'limit': 20, 'assembly': True})
        parts = data.get('results', [])

        if parts:
            print(f"🔍 Testing legacy method on {len(parts)} assembly parts...")

            for i, test_part in enumerate(parts[:10]):  # Test first 10 parts
                part_id = test_part.get('pk')
                part_name = test_part.get('name', 'Unknown')
                building_field = test_part.get('building', 0)

                print(f"\n📦 Part {i+1}: {part_name} (ID: {part_id})")
                print(f"   Standard building field: {building_field}")

                # Test the legacy method
                legacy_qty, warnings = api_client.get_legacy_building_quantity(part_id)
                print(f"   Legacy building quantity: {legacy_qty}")

                if warnings:
                    print("   ⚠️ Warnings:")
                    for warning in warnings:
                        print(f"     - {warning}")

                # Compare methods
                if legacy_qty != building_field:
                    print(f"   🔍 DIFFERENCE: Legacy={legacy_qty}, Standard={building_field}")
                else:
                    print(f"   ✅ Values match: {legacy_qty}")

                # If we found a part with building quantities, test more thoroughly
                if legacy_qty > 0 or building_field > 0:
                    print(f"   🎯 Found part with building quantities - testing stock items...")

                    # Get stock items directly to see what's happening
                    from inventree.stock import StockItem
                    stock_items = StockItem.list(api_client.api, part=part_id, is_building=True)
                    print(f"   📊 Stock items with is_building=True: {len(stock_items) if stock_items else 0}")

                    if stock_items:
                        total_manual = 0.0
                        for j, item in enumerate(stock_items):
                            qty = getattr(item, 'quantity', 0)
                            is_building = getattr(item, 'is_building', False)
                            print(f"     Item {j+1}: quantity={qty}, is_building={is_building}")
                            total_manual += float(qty)
                        print(f"   🧮 Manual calculation: {total_manual}")

            return True
        else:
            print("⚠️ No parts found to test with")
            return True
            
    except Exception as e:
        print(f"❌ Legacy method test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 InvenTree API Debug Script")
    print("=" * 50)
    
    # Test basic API functionality
    basic_success = test_basic_api()
    
    if basic_success:
        # Test legacy method
        legacy_success = test_legacy_method()
    else:
        legacy_success = False
    
    print("\n" + "=" * 50)
    print("📋 RESULTS:")
    print(f"   Basic API: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"   Legacy Method: {'✅ PASS' if legacy_success else '❌ FAIL'}")
    
    if basic_success and legacy_success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed.")
