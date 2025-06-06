#!/usr/bin/env python3
"""
Debug script to test the actual app flow and see where the building calculation is failing.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_app_flow():
    """Test the actual app flow to debug the building calculation issue."""
    
    print("🔧 Testing Actual App Flow for Building Calculation")
    print("=" * 60)
    
    try:
        # Import required modules
        from inventree_order_calculator.config import AppConfig
        from inventree_order_calculator.api_client import ApiClient
        from inventree_order_calculator.calculator import OrderCalculator
        from inventree_order_calculator.models import BuildingCalculationMethod, InputPart
        
        print("✅ All modules imported successfully")
        
        # Load configuration
        config = AppConfig.load()
        print(f"✅ Configuration loaded")
        
        # Create API client
        api_client = ApiClient(url=config.inventree_url, token=config.inventree_api_token)
        print("✅ API client created")
        
        part_id = 2081
        
        # Test 1: Direct API client method
        print(f"\n🧪 Test 1: Direct get_legacy_building_quantity call")
        legacy_qty, warnings = api_client.get_legacy_building_quantity(part_id)
        print(f"   Result: {legacy_qty}")
        if warnings:
            for warning in warnings:
                print(f"   Warning: {warning}")
        
        # Test 2: get_part_data with OLD_GUI method
        print(f"\n🧪 Test 2: get_part_data call")
        part_data, part_warnings = api_client.get_part_data(part_id)
        if part_data:
            print(f"   Standard building field: {part_data.building}")
            print(f"   Total in stock: {part_data.total_in_stock}")
            print(f"   Required for build orders: {part_data.required_for_build_orders}")
        
        # Test 3: Calculator with OLD_GUI method
        print(f"\n🧪 Test 3: OrderCalculator with OLD_GUI method")
        calculator_old = OrderCalculator(api_client, building_method=BuildingCalculationMethod.OLD_GUI)
        print(f"   Calculator created with method: {calculator_old.building_method}")
        
        # Test the _get_part_data_with_building_method directly
        print(f"\n🧪 Test 4: _get_part_data_with_building_method call")
        part_data_with_method, method_warnings = calculator_old._get_part_data_with_building_method(part_id)
        if part_data_with_method:
            print(f"   Building quantity from method: {part_data_with_method.building}")
            print(f"   Total in stock: {part_data_with_method.total_in_stock}")
            print(f"   Available: {part_data_with_method.available}")
        if method_warnings:
            for warning in method_warnings:
                print(f"   Method warning: {warning}")
        
        # Test 5: Full calculator flow
        print(f"\n🧪 Test 5: Full calculator flow")
        input_parts = [InputPart(part_identifier=str(part_id), quantity_to_build=1.0)]
        result = calculator_old.calculate_orders(input_parts)
        
        # Find our part in the results
        part_found = None
        for part in result.parts_to_order + result.subassemblies_to_build:
            if getattr(part, 'pk', None) == part_id:
                part_found = part
                break
        
        if part_found:
            print(f"   ✅ Part found in results:")
            print(f"      Building: {getattr(part_found, 'building', 'N/A')}")
            print(f"      Available: {getattr(part_found, 'available', 'N/A')}")
            print(f"      To build: {getattr(part_found, 'to_build', 'N/A')}")
            print(f"      Total required: {getattr(part_found, 'total_required', 'N/A')}")
        else:
            print("   ❌ Part not found in results")
            print(f"   Parts to order: {len(result.parts_to_order)}")
            print(f"   Subassemblies to build: {len(result.subassemblies_to_build)}")
        
        # Test 6: Compare with NEW_GUI method
        print(f"\n🧪 Test 6: Compare with NEW_GUI method")
        calculator_new = OrderCalculator(api_client, building_method=BuildingCalculationMethod.NEW_GUI)
        result_new = calculator_new.calculate_orders(input_parts)
        
        part_found_new = None
        for part in result_new.parts_to_order + result_new.subassemblies_to_build:
            if getattr(part, 'pk', None) == part_id:
                part_found_new = part
                break
        
        if part_found_new:
            print(f"   ✅ Part found in NEW_GUI results:")
            print(f"      Building: {getattr(part_found_new, 'building', 'N/A')}")
            print(f"      Available: {getattr(part_found_new, 'available', 'N/A')}")
            print(f"      To build: {getattr(part_found_new, 'to_build', 'N/A')}")
        
        # Test 7: Check if the issue is in the calculator logic
        print(f"\n🧪 Test 7: Debug calculator internal logic")
        
        # Manually call the internal methods
        print("   Checking calculate_required_recursive...")
        required_dict = calculator_old.calculate_required_recursive(input_parts)
        
        if part_id in required_dict:
            part_info = required_dict[part_id]
            print(f"   Part {part_id} in required_dict:")
            print(f"      total_required: {getattr(part_info, 'total_required', 'N/A')}")
            print(f"      building: {getattr(part_info, 'building', 'N/A')}")
            print(f"      available: {getattr(part_info, 'available', 'N/A')}")
        else:
            print(f"   Part {part_id} NOT found in required_dict")
            print(f"   Keys in required_dict: {list(required_dict.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 App Flow Debug Script")
    print("=" * 60)
    
    success = test_app_flow()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Debug completed!")
    else:
        print("❌ Debug failed. Check output above for details.")
