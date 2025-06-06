#!/usr/bin/env python3
"""
Simple test to debug the building calculation issue.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def simple_test():
    """Simple test to debug the issue."""

    print("🔧 Simple Building Calculation Test")
    print("=" * 50)

    try:
        import logging
        logging.basicConfig(level=logging.DEBUG)

        from inventree_order_calculator.config import AppConfig
        from inventree_order_calculator.api_client import ApiClient
        from inventree_order_calculator.calculator import OrderCalculator
        from inventree_order_calculator.models import BuildingCalculationMethod, InputPart
        
        # Load configuration
        config = AppConfig.load()
        api_client = ApiClient(url=config.inventree_url, token=config.inventree_api_token)
        
        part_id = 2081
        
        print(f"Testing part {part_id}...")
        
        # Test 1: Direct legacy method
        print("\n1. Direct legacy method:")
        legacy_qty, warnings = api_client.get_legacy_building_quantity(part_id)
        print(f"   Result: {legacy_qty}")
        
        # Test 2: Standard part data
        print("\n2. Standard part data:")
        part_data, part_warnings = api_client.get_part_data(part_id)
        if part_data:
            print(f"   Standard building: {part_data.building}")
            print(f"   Is assembly: {part_data.is_assembly}")
        
        # Test 3: Calculator method
        print("\n3. Calculator _get_part_data_with_building_method:")
        calculator = OrderCalculator(api_client, building_method=BuildingCalculationMethod.OLD_GUI)
        print(f"   Calculator building method: {calculator.building_method}")
        
        part_data_with_method, method_warnings = calculator._get_part_data_with_building_method(part_id)
        if part_data_with_method:
            print(f"   Building from method: {part_data_with_method.building}")
            print(f"   Is assembly: {part_data_with_method.is_assembly}")
        
        # Test 4: Full calculation
        print("\n4. Full calculation:")
        input_parts = [InputPart(part_identifier=str(part_id), quantity_to_build=1.0)]
        result = calculator.calculate_orders(input_parts)
        
        # Find the part in results
        found_part = None
        for part in result.parts_to_order + result.subassemblies_to_build:
            if getattr(part, 'pk', None) == part_id:
                found_part = part
                break
        
        if found_part:
            print(f"   Found in results:")
            print(f"   Building: {getattr(found_part, 'building', 'N/A')}")
            print(f"   Available: {getattr(found_part, 'available', 'N/A')}")
            print(f"   To build: {getattr(found_part, 'to_build', 'N/A')}")
        else:
            print("   Part not found in results")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    simple_test()
