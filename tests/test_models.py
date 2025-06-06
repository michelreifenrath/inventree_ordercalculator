"""
Unit tests for data models in models.py

Tests the BomItemData and CalculatedPart classes, specifically focusing on
the new is_optional field implementation for BOM optional column feature.
"""

import pytest
from src.inventree_order_calculator.models import (
    BomItemData,
    CalculatedPart,
    PartData,
    BuildingCalculationMethod
)


class TestBomItemData:
    """Test cases for BomItemData class with is_optional field."""
    
    def test_bom_item_data_default_is_optional_false(self):
        """Test that BomItemData.is_optional defaults to False."""
        bom_item = BomItemData(
            sub_part=123,
            quantity=2.0,
            is_consumable=False
        )
        
        # Should have is_optional field with default value False
        assert hasattr(bom_item, 'is_optional')
        assert bom_item.is_optional is False
    
    def test_bom_item_data_is_optional_true(self):
        """Test that BomItemData.is_optional can be set to True."""
        bom_item = BomItemData(
            sub_part=456,
            quantity=1.5,
            is_consumable=True,
            is_optional=True
        )
        
        assert bom_item.is_optional is True
        assert bom_item.sub_part == 456
        assert bom_item.quantity == 1.5
        assert bom_item.is_consumable is True
    
    def test_bom_item_data_is_optional_false_explicit(self):
        """Test that BomItemData.is_optional can be explicitly set to False."""
        bom_item = BomItemData(
            sub_part=789,
            quantity=3.0,
            is_consumable=False,
            is_optional=False
        )
        
        assert bom_item.is_optional is False
        assert bom_item.sub_part == 789
        assert bom_item.quantity == 3.0
        assert bom_item.is_consumable is False
    
    def test_bom_item_data_is_optional_type_validation(self):
        """Test that BomItemData.is_optional accepts boolean values."""
        # Test with True
        bom_item_true = BomItemData(
            sub_part=100,
            quantity=1.0,
            is_optional=True
        )
        assert isinstance(bom_item_true.is_optional, bool)
        assert bom_item_true.is_optional is True
        
        # Test with False
        bom_item_false = BomItemData(
            sub_part=200,
            quantity=2.0,
            is_optional=False
        )
        assert isinstance(bom_item_false.is_optional, bool)
        assert bom_item_false.is_optional is False


class TestCalculatedPart:
    """Test cases for CalculatedPart class with is_optional field."""
    
    def test_calculated_part_default_is_optional_false(self):
        """Test that CalculatedPart.is_optional defaults to False."""
        calculated_part = CalculatedPart(
            pk=123,
            name="Test Part",
            is_purchaseable=True,
            is_assembly=False
        )
        
        # Should have is_optional field with default value False
        assert hasattr(calculated_part, 'is_optional')
        assert calculated_part.is_optional is False
    
    def test_calculated_part_is_optional_true(self):
        """Test that CalculatedPart.is_optional can be set to True."""
        calculated_part = CalculatedPart(
            pk=456,
            name="Optional Assembly",
            is_purchaseable=False,
            is_assembly=True,
            is_optional=True
        )
        
        assert calculated_part.is_optional is True
        assert calculated_part.pk == 456
        assert calculated_part.name == "Optional Assembly"
        assert calculated_part.is_assembly is True
    
    def test_calculated_part_is_optional_false_explicit(self):
        """Test that CalculatedPart.is_optional can be explicitly set to False."""
        calculated_part = CalculatedPart(
            pk=789,
            name="Required Part",
            is_purchaseable=True,
            is_assembly=False,
            is_optional=False
        )
        
        assert calculated_part.is_optional is False
        assert calculated_part.pk == 789
        assert calculated_part.name == "Required Part"
        assert calculated_part.is_purchaseable is True
    
    def test_calculated_part_inherits_from_part_data(self):
        """Test that CalculatedPart still properly inherits from PartData."""
        calculated_part = CalculatedPart(
            pk=999,
            name="Inherited Part",
            is_purchaseable=True,
            is_assembly=False,
            total_in_stock=10.0,
            is_optional=True
        )
        
        # Test PartData fields are accessible
        assert calculated_part.pk == 999
        assert calculated_part.name == "Inherited Part"
        assert calculated_part.is_purchaseable is True
        assert calculated_part.is_assembly is False
        assert calculated_part.total_in_stock == 10.0
        
        # Test CalculatedPart specific fields
        assert calculated_part.total_required == 0.0
        assert calculated_part.available == 0.0
        assert calculated_part.to_order == 0.0
        assert calculated_part.to_build == 0.0
        assert calculated_part.is_optional is True
    
    def test_calculated_part_is_optional_type_validation(self):
        """Test that CalculatedPart.is_optional accepts boolean values."""
        # Test with True
        part_true = CalculatedPart(
            pk=100,
            name="Optional Part",
            is_purchaseable=True,
            is_assembly=False,
            is_optional=True
        )
        assert isinstance(part_true.is_optional, bool)
        assert part_true.is_optional is True
        
        # Test with False
        part_false = CalculatedPart(
            pk=200,
            name="Required Part",
            is_purchaseable=True,
            is_assembly=False,
            is_optional=False
        )
        assert isinstance(part_false.is_optional, bool)
        assert part_false.is_optional is False


class TestOptionalFieldIntegration:
    """Integration tests for is_optional field across models."""
    
    def test_bom_item_to_calculated_part_optional_propagation(self):
        """Test that optional status can be propagated from BomItemData to CalculatedPart."""
        # Create a BOM item with optional=True
        bom_item = BomItemData(
            sub_part=555,
            quantity=2.0,
            is_consumable=False,
            is_optional=True
        )
        
        # Create a CalculatedPart that would represent this BOM item
        calculated_part = CalculatedPart(
            pk=555,
            name="Optional Component",
            is_purchaseable=True,
            is_assembly=False,
            is_optional=bom_item.is_optional  # Propagate optional status
        )
        
        assert bom_item.is_optional is True
        assert calculated_part.is_optional is True
        assert bom_item.is_optional == calculated_part.is_optional
    
    def test_mixed_optional_required_parts(self):
        """Test handling of mixed optional and required parts."""
        # Required BOM item
        required_bom = BomItemData(
            sub_part=111,
            quantity=1.0,
            is_optional=False
        )
        
        # Optional BOM item
        optional_bom = BomItemData(
            sub_part=222,
            quantity=1.0,
            is_optional=True
        )
        
        # Corresponding calculated parts
        required_part = CalculatedPart(
            pk=111,
            name="Required Component",
            is_purchaseable=True,
            is_assembly=False,
            is_optional=required_bom.is_optional
        )
        
        optional_part = CalculatedPart(
            pk=222,
            name="Optional Component",
            is_purchaseable=True,
            is_assembly=False,
            is_optional=optional_bom.is_optional
        )
        
        assert required_bom.is_optional is False
        assert optional_bom.is_optional is True
        assert required_part.is_optional is False
        assert optional_part.is_optional is True


class TestBuildingCalculationMethod:
    """Test cases for BuildingCalculationMethod enum."""

    def test_building_calculation_method_values(self):
        """Test that BuildingCalculationMethod has correct enum values."""
        assert BuildingCalculationMethod.NEW_GUI.value == "new_gui"
        assert BuildingCalculationMethod.OLD_GUI.value == "old_gui"

    def test_building_calculation_method_enum_members(self):
        """Test that BuildingCalculationMethod has expected members."""
        members = list(BuildingCalculationMethod)
        assert len(members) == 2
        assert BuildingCalculationMethod.NEW_GUI in members
        assert BuildingCalculationMethod.OLD_GUI in members

    def test_building_calculation_method_string_representation(self):
        """Test string representation of BuildingCalculationMethod enum."""
        assert str(BuildingCalculationMethod.NEW_GUI) == "BuildingCalculationMethod.NEW_GUI"
        assert str(BuildingCalculationMethod.OLD_GUI) == "BuildingCalculationMethod.OLD_GUI"

    def test_building_calculation_method_comparison(self):
        """Test comparison operations with BuildingCalculationMethod enum."""
        assert BuildingCalculationMethod.NEW_GUI == BuildingCalculationMethod.NEW_GUI
        assert BuildingCalculationMethod.OLD_GUI == BuildingCalculationMethod.OLD_GUI
        assert BuildingCalculationMethod.NEW_GUI != BuildingCalculationMethod.OLD_GUI

    def test_building_calculation_method_from_value(self):
        """Test creating BuildingCalculationMethod from string values."""
        new_gui_method = BuildingCalculationMethod("new_gui")
        old_gui_method = BuildingCalculationMethod("old_gui")

        assert new_gui_method == BuildingCalculationMethod.NEW_GUI
        assert old_gui_method == BuildingCalculationMethod.OLD_GUI

    def test_building_calculation_method_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            BuildingCalculationMethod("invalid_method")
