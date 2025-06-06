#!/usr/bin/env python3
"""
Test script to verify the legacy building calculation method specifically for part 2081.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_part_2081():
    """Test the legacy building calculation method specifically for part 2081."""
    
    print("🔧 Testing Legacy Building Calculation for Part 2081")
    print("=" * 60)
    
    try:
        # Import required modules
        from inventree_order_calculator.config import AppConfig
        from inventree_order_calculator.api_client import ApiClient
        from inventree_order_calculator.calculator import OrderCalculator
        from inventree_order_calculator.models import BuildingCalculationMethod, InputPart
        from inventree.stock import StockItem
        
        print("✅ All modules imported successfully")
        
        # Load configuration
        config = AppConfig.load()
        print(f"✅ Configuration loaded:")
        print(f"   URL: {config.inventree_url}")
        print(f"   Token: {'*' * 20}...{config.inventree_api_token[-10:]}")
        
        # Create API client
        api_client = ApiClient(url=config.inventree_url, token=config.inventree_api_token)
        print("✅ API client created")
        
        part_id = 2081
        
        # Get part information
        print(f"\n📦 Getting information for part {part_id}...")
        part_data, part_warnings = api_client.get_part_data(part_id)
        
        if part_data:
            print(f"✅ Part found: {part_data.name}")
            print(f"   - Is Assembly: {part_data.is_assembly}")
            print(f"   - Is Purchaseable: {part_data.is_purchaseable}")
            print(f"   - Total in Stock: {part_data.total_in_stock}")
            print(f"   - Standard Building Field: {part_data.building}")
            print(f"   - Required for Build Orders: {part_data.required_for_build_orders}")
            print(f"   - Required for Sales Orders: {part_data.required_for_sales_orders}")
        else:
            print(f"❌ Part {part_id} not found")
            if part_warnings:
                for warning in part_warnings:
                    print(f"   Warning: {warning}")
            return False
        
        # Test legacy building calculation
        print(f"\n🏗️ Testing legacy building calculation for part {part_id}...")
        legacy_qty, warnings = api_client.get_legacy_building_quantity(part_id)
        print(f"✅ Legacy building quantity: {legacy_qty}")
        
        if warnings:
            print("⚠️ Warnings from legacy method:")
            for warning in warnings:
                print(f"   - {warning}")
        
        # Compare with standard building field
        standard_building = part_data.building
        print(f"📊 Standard building field: {standard_building}")
        
        if legacy_qty != standard_building:
            print(f"🔍 DIFFERENCE DETECTED:")
            print(f"   Legacy method: {legacy_qty}")
            print(f"   Standard field: {standard_building}")
            print(f"   Difference: {abs(legacy_qty - standard_building)}")
        else:
            print(f"✅ Values match: {legacy_qty}")
        
        # Get detailed stock item information
        print(f"\n📋 Analyzing stock items for part {part_id}...")
        
        # Get all stock items for this part
        all_stock_items = StockItem.list(api_client.api, part=part_id)
        print(f"📊 Total stock items: {len(all_stock_items) if all_stock_items else 0}")
        
        if all_stock_items:
            total_quantity = 0.0
            building_quantity = 0.0
            
            for i, item in enumerate(all_stock_items):
                quantity = getattr(item, 'quantity', 0)
                is_building = getattr(item, 'is_building', False)
                status = getattr(item, 'status', 'Unknown')
                location = getattr(item, 'location_name', 'No location')
                
                print(f"   Item {i+1}: qty={quantity}, is_building={is_building}, status={status}, location={location}")
                
                total_quantity += float(quantity)
                if is_building:
                    building_quantity += float(quantity)
        
        # Debug: Try different approaches to find building stock items
        print(f"\n🔍 DEBUGGING: Different ways to find building stock items...")

        # Method 1: Our current approach
        building_stock_items = StockItem.list(api_client.api, part=part_id, is_building=True)
        print(f"Method 1 - StockItem.list(api, part={part_id}, is_building=True): {len(building_stock_items) if building_stock_items else 0} items")

        # Method 2: Direct API call to stock endpoint
        try:
            stock_api_response = api_client.api.get('stock/', params={'part': part_id, 'is_building': True})
            # Handle both dict and list responses
            if isinstance(stock_api_response, dict):
                stock_items_direct = stock_api_response.get('results', [])
            else:
                stock_items_direct = stock_api_response if stock_api_response else []
            print(f"Method 2 - Direct API /stock/?part={part_id}&is_building=true: {len(stock_items_direct)} items")

            if stock_items_direct:
                for i, item in enumerate(stock_items_direct):
                    if isinstance(item, dict):
                        print(f"   Direct API item {i+1}: qty={item.get('quantity')}, is_building={item.get('is_building')}, status={item.get('status')}")
                    else:
                        print(f"   Direct API item {i+1}: {item}")
        except Exception as e:
            print(f"Method 2 failed: {e}")

        # Method 3: Get all stock items and filter manually
        try:
            all_stock_api = api_client.api.get('stock/', params={'part': part_id})
            # Handle both dict and list responses
            if isinstance(all_stock_api, dict):
                all_stock_items_direct = all_stock_api.get('results', [])
            else:
                all_stock_items_direct = all_stock_api if all_stock_api else []

            building_items_manual = []
            for item in all_stock_items_direct:
                if isinstance(item, dict) and item.get('is_building', False):
                    building_items_manual.append(item)

            print(f"Method 3 - Manual filter from all stock items: {len(building_items_manual)} items")

            if building_items_manual:
                for i, item in enumerate(building_items_manual):
                    print(f"   Manual filter item {i+1}: qty={item.get('quantity')}, is_building={item.get('is_building')}, status={item.get('status')}")
        except Exception as e:
            print(f"Method 3 failed: {e}")

        # Method 4: Check build orders for this part (try different status values)
        try:
            # Try without status filter first
            build_orders = api_client.api.get('build/', params={'part': part_id})
            if isinstance(build_orders, dict):
                build_orders_list = build_orders.get('results', [])
            else:
                build_orders_list = build_orders if build_orders else []
            print(f"Method 4a - All build orders for part {part_id}: {len(build_orders_list)} orders")

            # Try with numeric status codes
            for status_code in [10, 20, 30]:  # Common InvenTree status codes
                try:
                    build_orders_status = api_client.api.get('build/', params={'part': part_id, 'status': status_code})
                    if isinstance(build_orders_status, dict):
                        orders_list = build_orders_status.get('results', [])
                    else:
                        orders_list = build_orders_status if build_orders_status else []
                    print(f"Method 4b - Build orders with status {status_code}: {len(orders_list)} orders")
                except:
                    pass

            total_building_from_orders = 0
            for i, order in enumerate(build_orders_list):
                if isinstance(order, dict):
                    quantity = order.get('quantity', 0)
                    completed = order.get('completed', 0)
                    remaining = quantity - completed
                    status = order.get('status_text', order.get('status', 'Unknown'))
                    print(f"   Build order {i+1}: total={quantity}, completed={completed}, remaining={remaining}, status={status}")
                    if remaining > 0:
                        total_building_from_orders += remaining

            print(f"   Total remaining from build orders: {total_building_from_orders}")
        except Exception as e:
            print(f"Method 4 failed: {e}")

        # Method 5: Check the part's in_production field directly
        try:
            part_detail = api_client.api.get(f'part/{part_id}/')
            if isinstance(part_detail, dict):
                in_production = part_detail.get('in_production', 0)
                building_field = part_detail.get('building', 0)
                print(f"Method 5 - Part fields: in_production={in_production}, building={building_field}")
            else:
                print(f"Method 5 - Unexpected response format: {type(part_detail)}")
        except Exception as e:
            print(f"Method 5 failed: {e}")

        if building_stock_items:
            manual_building_total = 0.0
            for i, item in enumerate(building_stock_items):
                quantity = getattr(item, 'quantity', 0)
                status = getattr(item, 'status', 'Unknown')
                build_order = getattr(item, 'build', None)

                print(f"   Building item {i+1}: qty={quantity}, status={status}, build_order={build_order}")
                manual_building_total += float(quantity)

            print(f"🧮 Manual calculation of building items: {manual_building_total}")

            if manual_building_total != legacy_qty:
                print(f"⚠️ Discrepancy in manual vs legacy calculation:")
                print(f"   Manual: {manual_building_total}")
                print(f"   Legacy method: {legacy_qty}")
        
        # Test with calculator using both methods
        print(f"\n🧮 Testing with OrderCalculator...")
        
        # Test with OLD_GUI method
        calculator_old = OrderCalculator(api_client, building_method=BuildingCalculationMethod.OLD_GUI)
        input_parts = [InputPart(part_identifier=str(part_id), quantity_to_build=1.0)]
        
        print(f"🔧 Testing with OLD_GUI method...")
        result_old = calculator_old.calculate_orders(input_parts)
        
        # Find our part in the results
        part_found_old = None
        for part in result_old.parts_to_order + result_old.subassemblies_to_build:
            if getattr(part, 'pk', None) == part_id:
                part_found_old = part
                break
        
        if part_found_old:
            print(f"   ✅ Part found in OLD_GUI results:")
            print(f"      Building quantity used: {getattr(part_found_old, 'building', 'N/A')}")
            print(f"      Available: {getattr(part_found_old, 'available', 'N/A')}")
            print(f"      To build/order: {getattr(part_found_old, 'to_build', getattr(part_found_old, 'to_order', 'N/A'))}")
        
        # Test with NEW_GUI method
        calculator_new = OrderCalculator(api_client, building_method=BuildingCalculationMethod.NEW_GUI)
        
        print(f"🆕 Testing with NEW_GUI method...")
        result_new = calculator_new.calculate_orders(input_parts)
        
        # Find our part in the results
        part_found_new = None
        for part in result_new.parts_to_order + result_new.subassemblies_to_build:
            if getattr(part, 'pk', None) == part_id:
                part_found_new = part
                break
        
        if part_found_new:
            print(f"   ✅ Part found in NEW_GUI results:")
            print(f"      Building quantity used: {getattr(part_found_new, 'building', 'N/A')}")
            print(f"      Available: {getattr(part_found_new, 'available', 'N/A')}")
            print(f"      To build/order: {getattr(part_found_new, 'to_build', getattr(part_found_new, 'to_order', 'N/A'))}")
        
        # Compare results
        if part_found_old and part_found_new:
            old_building = getattr(part_found_old, 'building', 0)
            new_building = getattr(part_found_new, 'building', 0)
            
            if old_building != new_building:
                print(f"\n🔍 CALCULATOR DIFFERENCE DETECTED:")
                print(f"   OLD_GUI building: {old_building}")
                print(f"   NEW_GUI building: {new_building}")
                print(f"   Difference: {abs(old_building - new_building)}")
            else:
                print(f"\n✅ Calculator results match: {old_building}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Part 2081 Legacy Building Calculation Test")
    print("=" * 60)
    
    success = test_part_2081()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("❌ Test failed. Check output above for details.")
