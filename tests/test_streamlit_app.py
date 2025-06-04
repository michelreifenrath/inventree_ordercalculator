"""
Unit tests for Streamlit app display functions

Tests the format_parts_to_order_for_display and format_assemblies_to_build_for_display
functions, specifically focusing on the new Optional column implementation.
"""

import pytest
import pandas as pd
from unittest.mock import Mock
from src.inventree_order_calculator.streamlit_app import (
    format_parts_to_order_for_display,
    format_assemblies_to_build_for_display
)
from src.inventree_order_calculator.models import CalculatedPart


class TestFormatPartsToOrderForDisplay:
    """Test cases for format_parts_to_order_for_display function with Optional column."""
    
    def test_format_parts_to_order_includes_optional_column_true(self):
        """Test that format_parts_to_order_for_display includes Optional column when part is optional."""
        # Arrange
        optional_part = CalculatedPart(
            pk=123,
            name="Optional Resistor",
            is_purchaseable=True,
            is_assembly=False,
            total_required=5.0,
            total_in_stock=2.0,
            available=2.0,
            to_order=3.0,
            is_optional=True  # This should appear in the Optional column
        )
        
        parts = [optional_part]
        app_config = None
        show_consumables = True
        
        # Act
        df = format_parts_to_order_for_display(parts, app_config, show_consumables)
        
        # Assert
        assert not df.empty
        assert "Optional" in df.columns
        assert df.iloc[0]["Optional"] == True  # Use == instead of is for pandas boolean
        assert df.iloc[0]["Part ID"] == 123
        assert df.iloc[0]["Needed"] == 5.0
        assert df.iloc[0]["To Order"] == 3.0
    
    def test_format_parts_to_order_includes_optional_column_false(self):
        """Test that format_parts_to_order_for_display includes Optional column when part is required."""
        # Arrange
        required_part = CalculatedPart(
            pk=456,
            name="Required Capacitor",
            is_purchaseable=True,
            is_assembly=False,
            total_required=10.0,
            total_in_stock=5.0,
            available=5.0,
            to_order=5.0,
            is_optional=False  # This should appear in the Optional column
        )
        
        parts = [required_part]
        app_config = None
        show_consumables = True
        
        # Act
        df = format_parts_to_order_for_display(parts, app_config, show_consumables)
        
        # Assert
        assert not df.empty
        assert "Optional" in df.columns
        assert df.iloc[0]["Optional"] == False  # Use == instead of is for pandas boolean
        assert df.iloc[0]["Part ID"] == 456
        assert df.iloc[0]["Needed"] == 10.0
        assert df.iloc[0]["To Order"] == 5.0
    
    def test_format_parts_to_order_optional_column_positioning(self):
        """Test that Optional column is positioned after Part ID and before Needed."""
        # Arrange
        part = CalculatedPart(
            pk=789,
            name="Test Part",
            is_purchaseable=True,
            is_assembly=False,
            total_required=1.0,
            to_order=1.0,
            is_optional=True
        )
        
        parts = [part]
        app_config = None
        show_consumables = True
        
        # Act
        df = format_parts_to_order_for_display(parts, app_config, show_consumables)
        
        # Assert
        columns = list(df.columns)
        part_id_index = columns.index("Part ID")
        optional_index = columns.index("Optional")
        needed_index = columns.index("Needed")
        
        assert optional_index == part_id_index + 1  # Optional should be right after Part ID
        assert optional_index < needed_index  # Optional should be before Needed
    
    def test_format_parts_to_order_mixed_optional_required_parts(self):
        """Test that format_parts_to_order_for_display handles mixed optional and required parts."""
        # Arrange
        required_part = CalculatedPart(
            pk=111,
            name="Required Part",
            is_purchaseable=True,
            is_assembly=False,
            total_required=2.0,
            to_order=2.0,
            is_optional=False
        )
        
        optional_part = CalculatedPart(
            pk=222,
            name="Optional Part",
            is_purchaseable=True,
            is_assembly=False,
            total_required=3.0,
            to_order=3.0,
            is_optional=True
        )
        
        parts = [required_part, optional_part]
        app_config = None
        show_consumables = True
        
        # Act
        df = format_parts_to_order_for_display(parts, app_config, show_consumables)
        
        # Assert
        assert len(df) == 2
        assert "Optional" in df.columns
        
        # Check first part (required)
        required_row = df[df["Part ID"] == 111].iloc[0]
        assert required_row["Optional"] == False  # Use == instead of is for pandas boolean

        # Check second part (optional)
        optional_row = df[df["Part ID"] == 222].iloc[0]
        assert optional_row["Optional"] == True  # Use == instead of is for pandas boolean
    
    def test_format_parts_to_order_empty_list(self):
        """Test that format_parts_to_order_for_display handles empty parts list."""
        # Arrange
        parts = []
        app_config = None
        show_consumables = True

        # Act
        df = format_parts_to_order_for_display(parts, app_config, show_consumables)

        # Assert
        assert df.empty

    def test_format_parts_to_order_show_optional_parts_true(self):
        """Test that optional parts are included when show_optional_parts=True."""
        # Arrange
        required_part = CalculatedPart(
            pk=100, name="Required Part", is_purchaseable=True, is_assembly=False,
            total_required=10.0, to_order=5.0, is_optional=False
        )
        optional_part = CalculatedPart(
            pk=200, name="Optional Part", is_purchaseable=True, is_assembly=False,
            total_required=5.0, to_order=3.0, is_optional=True
        )

        parts = [required_part, optional_part]
        app_config = None
        show_consumables = True
        show_optional_parts = True

        # Act
        df = format_parts_to_order_for_display(parts, app_config, show_consumables, show_optional_parts)

        # Assert
        assert len(df) == 2  # Both parts should be included
        part_ids = df["Part ID"].tolist()
        assert 100 in part_ids
        assert 200 in part_ids

    def test_format_parts_to_order_show_optional_parts_false(self):
        """Test that optional parts are excluded when show_optional_parts=False."""
        # Arrange
        required_part = CalculatedPart(
            pk=100, name="Required Part", is_purchaseable=True, is_assembly=False,
            total_required=10.0, to_order=5.0, is_optional=False
        )
        optional_part = CalculatedPart(
            pk=200, name="Optional Part", is_purchaseable=True, is_assembly=False,
            total_required=5.0, to_order=3.0, is_optional=True
        )

        parts = [required_part, optional_part]
        app_config = None
        show_consumables = True
        show_optional_parts = False

        # Act
        df = format_parts_to_order_for_display(parts, app_config, show_consumables, show_optional_parts)

        # Assert
        assert len(df) == 1  # Only required part should be included
        assert df.iloc[0]["Part ID"] == 100
        assert df.iloc[0]["Optional"] == False

    def test_format_parts_to_order_combined_filtering_consumables_and_optional(self):
        """Test combined filtering of consumables and optional parts."""
        # Arrange
        required_part = CalculatedPart(
            pk=100, name="Required Part", is_purchaseable=True, is_assembly=False,
            total_required=10.0, to_order=5.0, is_optional=False, is_consumable=False
        )
        optional_part = CalculatedPart(
            pk=200, name="Optional Part", is_purchaseable=True, is_assembly=False,
            total_required=5.0, to_order=3.0, is_optional=True, is_consumable=False
        )
        consumable_part = CalculatedPart(
            pk=300, name="Consumable Part", is_purchaseable=True, is_assembly=False,
            total_required=2.0, to_order=2.0, is_optional=False, is_consumable=True
        )
        optional_consumable_part = CalculatedPart(
            pk=400, name="Optional Consumable Part", is_purchaseable=True, is_assembly=False,
            total_required=1.0, to_order=1.0, is_optional=True, is_consumable=True
        )

        parts = [required_part, optional_part, consumable_part, optional_consumable_part]
        app_config = None
        show_consumables = False  # Hide consumables
        show_optional_parts = False  # Hide optional parts

        # Act
        df = format_parts_to_order_for_display(parts, app_config, show_consumables, show_optional_parts)

        # Assert
        assert len(df) == 1  # Only required, non-consumable part should be included
        assert df.iloc[0]["Part ID"] == 100


class TestFormatAssembliesToBuildForDisplay:
    """Test cases for format_assemblies_to_build_for_display function with Optional column."""
    
    def test_format_assemblies_to_build_includes_optional_column_true(self):
        """Test that format_assemblies_to_build_for_display includes Optional column when assembly is optional."""
        # Arrange
        optional_assembly = CalculatedPart(
            pk=333,
            name="Optional Subassembly",
            is_purchaseable=False,
            is_assembly=True,
            total_required=2.0,
            total_in_stock=0.0,
            available=0.0,
            to_build=2.0,
            is_optional=True  # This should appear in the Optional column
        )
        
        assemblies = [optional_assembly]
        app_config = None
        show_consumables = True
        
        # Act
        df = format_assemblies_to_build_for_display(assemblies, app_config, show_consumables)
        
        # Assert
        assert not df.empty
        assert "Optional" in df.columns
        assert df.iloc[0]["Optional"] == True  # Use == instead of is for pandas boolean
        assert df.iloc[0]["Part ID"] == 333
        assert df.iloc[0]["Needed"] == 2.0
        assert df.iloc[0]["To Build"] == 2.0
    
    def test_format_assemblies_to_build_includes_optional_column_false(self):
        """Test that format_assemblies_to_build_for_display includes Optional column when assembly is required."""
        # Arrange
        required_assembly = CalculatedPart(
            pk=444,
            name="Required Subassembly",
            is_purchaseable=False,
            is_assembly=True,
            total_required=1.0,
            total_in_stock=0.0,
            available=0.0,
            to_build=1.0,
            is_optional=False  # This should appear in the Optional column
        )
        
        assemblies = [required_assembly]
        app_config = None
        show_consumables = True
        
        # Act
        df = format_assemblies_to_build_for_display(assemblies, app_config, show_consumables)
        
        # Assert
        assert not df.empty
        assert "Optional" in df.columns
        assert df.iloc[0]["Optional"] == False  # Use == instead of is for pandas boolean
        assert df.iloc[0]["Part ID"] == 444
        assert df.iloc[0]["Needed"] == 1.0
        assert df.iloc[0]["To Build"] == 1.0
    
    def test_format_assemblies_to_build_optional_column_positioning(self):
        """Test that Optional column is positioned after Part ID and before Needed."""
        # Arrange
        assembly = CalculatedPart(
            pk=555,
            name="Test Assembly",
            is_purchaseable=False,
            is_assembly=True,
            total_required=1.0,
            to_build=1.0,
            is_optional=True
        )
        
        assemblies = [assembly]
        app_config = None
        show_consumables = True
        
        # Act
        df = format_assemblies_to_build_for_display(assemblies, app_config, show_consumables)
        
        # Assert
        columns = list(df.columns)
        part_id_index = columns.index("Part ID")
        optional_index = columns.index("Optional")
        needed_index = columns.index("Needed")
        
        assert optional_index == part_id_index + 1  # Optional should be right after Part ID
        assert optional_index < needed_index  # Optional should be before Needed
    
    def test_format_assemblies_to_build_mixed_optional_required_assemblies(self):
        """Test that format_assemblies_to_build_for_display handles mixed optional and required assemblies."""
        # Arrange
        required_assembly = CalculatedPart(
            pk=666,
            name="Required Assembly",
            is_purchaseable=False,
            is_assembly=True,
            total_required=1.0,
            to_build=1.0,
            is_optional=False
        )
        
        optional_assembly = CalculatedPart(
            pk=777,
            name="Optional Assembly",
            is_purchaseable=False,
            is_assembly=True,
            total_required=2.0,
            to_build=2.0,
            is_optional=True
        )
        
        assemblies = [required_assembly, optional_assembly]
        app_config = None
        show_consumables = True
        
        # Act
        df = format_assemblies_to_build_for_display(assemblies, app_config, show_consumables)
        
        # Assert
        assert len(df) == 2
        assert "Optional" in df.columns
        
        # Check first assembly (required)
        required_row = df[df["Part ID"] == 666].iloc[0]
        assert required_row["Optional"] == False  # Use == instead of is for pandas boolean

        # Check second assembly (optional)
        optional_row = df[df["Part ID"] == 777].iloc[0]
        assert optional_row["Optional"] == True  # Use == instead of is for pandas boolean
    
    def test_format_assemblies_to_build_empty_list(self):
        """Test that format_assemblies_to_build_for_display handles empty assemblies list."""
        # Arrange
        assemblies = []
        app_config = None
        show_consumables = True

        # Act
        df = format_assemblies_to_build_for_display(assemblies, app_config, show_consumables)

        # Assert
        assert df.empty

    def test_format_assemblies_to_build_show_optional_parts_true(self):
        """Test that optional assemblies are included when show_optional_parts=True."""
        # Arrange
        required_assembly = CalculatedPart(
            pk=500, name="Required Assembly", is_purchaseable=False, is_assembly=True,
            total_required=2.0, to_build=1.0, is_optional=False
        )
        optional_assembly = CalculatedPart(
            pk=600, name="Optional Assembly", is_purchaseable=False, is_assembly=True,
            total_required=1.0, to_build=1.0, is_optional=True
        )

        assemblies = [required_assembly, optional_assembly]
        app_config = None
        show_consumables = True
        show_optional_parts = True

        # Act
        df = format_assemblies_to_build_for_display(assemblies, app_config, show_consumables, show_optional_parts)

        # Assert
        assert len(df) == 2  # Both assemblies should be included
        part_ids = df["Part ID"].tolist()
        assert 500 in part_ids
        assert 600 in part_ids

    def test_format_assemblies_to_build_show_optional_parts_false(self):
        """Test that optional assemblies are excluded when show_optional_parts=False."""
        # Arrange
        required_assembly = CalculatedPart(
            pk=500, name="Required Assembly", is_purchaseable=False, is_assembly=True,
            total_required=2.0, to_build=1.0, is_optional=False
        )
        optional_assembly = CalculatedPart(
            pk=600, name="Optional Assembly", is_purchaseable=False, is_assembly=True,
            total_required=1.0, to_build=1.0, is_optional=True
        )

        assemblies = [required_assembly, optional_assembly]
        app_config = None
        show_consumables = True
        show_optional_parts = False

        # Act
        df = format_assemblies_to_build_for_display(assemblies, app_config, show_consumables, show_optional_parts)

        # Assert
        assert len(df) == 1  # Only required assembly should be included
        assert df.iloc[0]["Part ID"] == 500
        assert df.iloc[0]["Optional"] == False

    def test_format_assemblies_to_build_combined_filtering_consumables_and_optional(self):
        """Test combined filtering of consumables and optional assemblies."""
        # Arrange
        required_assembly = CalculatedPart(
            pk=500, name="Required Assembly", is_purchaseable=False, is_assembly=True,
            total_required=2.0, to_build=1.0, is_optional=False, is_consumable=False
        )
        optional_assembly = CalculatedPart(
            pk=600, name="Optional Assembly", is_purchaseable=False, is_assembly=True,
            total_required=1.0, to_build=1.0, is_optional=True, is_consumable=False
        )
        consumable_assembly = CalculatedPart(
            pk=700, name="Consumable Assembly", is_purchaseable=False, is_assembly=True,
            total_required=1.0, to_build=1.0, is_optional=False, is_consumable=True
        )
        optional_consumable_assembly = CalculatedPart(
            pk=800, name="Optional Consumable Assembly", is_purchaseable=False, is_assembly=True,
            total_required=1.0, to_build=1.0, is_optional=True, is_consumable=True
        )

        assemblies = [required_assembly, optional_assembly, consumable_assembly, optional_consumable_assembly]
        app_config = None
        show_consumables = False  # Hide consumables
        show_optional_parts = False  # Hide optional parts

        # Act
        df = format_assemblies_to_build_for_display(assemblies, app_config, show_consumables, show_optional_parts)

        # Assert
        assert len(df) == 1  # Only required, non-consumable assembly should be included
        assert df.iloc[0]["Part ID"] == 500
