# Tests for email formatting functionality

import pytest
from datetime import datetime
from unittest.mock import patch

from src.inventree_order_calculator.email_formatter import EmailFormatter
from src.inventree_order_calculator.models import OutputTables, CalculatedPart
from src.inventree_order_calculator.email_config import (
    EmailConfig, SMTPConfig, EmailRecipients
)

class TestEmailFormatter:
    """Test email formatting functionality"""
    
    @pytest.fixture
    def formatter(self):
        """Create email formatter instance"""
        return EmailFormatter()
    
    @pytest.fixture
    def sample_config(self):
        """Create sample email configuration"""
        smtp = SMTPConfig(
            host="smtp.test.com",
            port=587,
            username="test@test.com",
            password="testpass"
        )
        
        recipients = EmailRecipients(
            to=["recipient@test.com"]
        )
        
        return EmailConfig(
            smtp=smtp,
            sender_email="sender@test.com",
            recipients=recipients,
            include_parts_table=True,
            include_assemblies_table=True,
            include_summary=True
        )
    
    @pytest.fixture
    def sample_results(self):
        """Create sample calculation results"""
        # Create sample parts
        part1 = CalculatedPart(
            pk=1,
            name="Test Part 1",
            is_purchaseable=True,
            is_assembly=False,
            total_required=10.0,
            available=5.0,
            to_order=5.0,
            supplier_names=["Supplier A", "Supplier B"],
            is_optional=False
        )
        
        part2 = CalculatedPart(
            pk=2,
            name="Test Part 2",
            is_purchaseable=True,
            is_assembly=False,
            total_required=20.0,
            available=15.0,
            to_order=5.0,
            supplier_names=["Supplier C"],
            is_optional=True
        )
        
        # Create sample assemblies
        assembly1 = CalculatedPart(
            pk=3,
            name="Test Assembly 1",
            is_purchaseable=False,
            is_assembly=True,
            total_required=5.0,
            available=2.0,
            to_build=3.0,
            building=1.0,
            is_optional=False
        )
        
        return OutputTables(
            parts_to_order=[part1, part2],
            subassemblies_to_build=[assembly1],
            warnings=["Test warning message"]
        )
    
    def test_format_email_complete(self, formatter, sample_config, sample_results):
        """Test complete email formatting with all components"""
        content = formatter.format_email(
            results=sample_results,
            config=sample_config,
            preset_name="Test Preset"
        )
        
        assert 'html' in content
        assert 'text' in content
        
        # Check HTML content
        html = content['html']
        assert "Test Preset" in html
        assert "Test Part 1" in html
        assert "Test Part 2" in html
        assert "Test Assembly 1" in html
        assert "Test warning message" in html
        assert "Summary" in html
        
        # Check text content
        text = content['text']
        assert "Test Preset" in text
        assert "Test Part 1" in text
        assert "Test Part 2" in text
        assert "Test Assembly 1" in text
        assert "Test warning message" in text
        assert "SUMMARY" in text
    
    def test_format_email_no_parts(self, formatter, sample_config):
        """Test email formatting with no parts to order"""
        results = OutputTables(
            parts_to_order=[],
            subassemblies_to_build=[],
            warnings=[]
        )
        
        content = formatter.format_email(
            results=results,
            config=sample_config
        )
        
        html = content['html']
        text = content['text']
        
        assert "No parts need to be ordered" in html
        assert "No assemblies need to be built" in html
        assert "No parts need to be ordered" in text
        assert "No assemblies need to be built" in text
    
    def test_format_email_selective_inclusion(self, formatter, sample_results):
        """Test email formatting with selective component inclusion"""
        # Config with only parts table
        smtp = SMTPConfig(
            host="smtp.test.com",
            port=587,
            username="test@test.com",
            password="testpass"
        )
        
        recipients = EmailRecipients(
            to=["recipient@test.com"]
        )
        
        config = EmailConfig(
            smtp=smtp,
            sender_email="sender@test.com",
            recipients=recipients,
            include_parts_table=True,
            include_assemblies_table=False,
            include_summary=False
        )
        
        content = formatter.format_email(
            results=sample_results,
            config=config
        )
        
        html = content['html']
        text = content['text']
        
        # Should include parts but not assemblies or summary
        assert "Test Part 1" in html
        assert "Test Assembly 1" not in html
        assert "Summary" not in html
        
        assert "Test Part 1" in text
        assert "Test Assembly 1" not in text
        assert "SUMMARY" not in text
    
    def test_generate_summary(self, formatter, sample_results):
        """Test summary generation"""
        summary = formatter._generate_summary(sample_results)
        
        assert summary['parts_count'] == 2
        assert summary['assemblies_count'] == 1
        assert summary['total_parts_quantity'] == 10.0  # 5.0 + 5.0
        assert summary['total_assemblies_quantity'] == 3.0
        assert summary['has_warnings'] is True
        assert 'generation_time' in summary
    
    def test_format_parts_table_html(self, formatter, sample_results):
        """Test HTML parts table formatting"""
        html = formatter._format_parts_table_html(sample_results.parts_to_order)
        
        assert "<table" in html
        assert "Test Part 1" in html
        assert "Test Part 2" in html
        assert "Supplier A, Supplier B" in html
        assert "Supplier C" in html
        assert "(Optional)" in html  # For part 2
        assert "5.00" in html  # to_order quantities
    
    def test_format_assemblies_table_html(self, formatter, sample_results):
        """Test HTML assemblies table formatting"""
        html = formatter._format_assemblies_table_html(sample_results.subassemblies_to_build)
        
        assert "<table" in html
        assert "Test Assembly 1" in html
        assert "3.00" in html  # to_build quantity
        assert "1.00" in html  # building quantity
    
    def test_format_parts_table_text(self, formatter, sample_results):
        """Test text parts table formatting"""
        text = formatter._format_parts_table_text(sample_results.parts_to_order)
        
        assert "PARTS TO ORDER" in text
        assert "Test Part 1" in text
        assert "Test Part 2" in text
        assert "(Opt)" in text  # For optional part
        assert "5.00" in text  # to_order quantities
    
    def test_format_assemblies_table_text(self, formatter, sample_results):
        """Test text assemblies table formatting"""
        text = formatter._format_assemblies_table_text(sample_results.subassemblies_to_build)
        
        assert "ASSEMBLIES TO BUILD" in text
        assert "Test Assembly 1" in text
        assert "3.00" in text  # to_build quantity
    
    def test_format_empty_tables(self, formatter):
        """Test formatting of empty tables"""
        # HTML empty tables
        html_parts = formatter._format_parts_table_html([])
        html_assemblies = formatter._format_assemblies_table_html([])
        
        assert "No parts need to be ordered" in html_parts
        assert "No assemblies need to be built" in html_assemblies
        
        # Text empty tables
        text_parts = formatter._format_parts_table_text([])
        text_assemblies = formatter._format_assemblies_table_text([])
        
        assert "No parts need to be ordered" in text_parts
        assert "No assemblies need to be built" in text_assemblies
    
    @patch('src.inventree_order_calculator.email_formatter.datetime')
    def test_format_subject(self, mock_datetime, formatter):
        """Test subject line formatting"""
        # Mock datetime
        mock_now = datetime(2024, 1, 15, 14, 30, 0)
        mock_datetime.now.return_value = mock_now
        
        # Test basic template
        subject = formatter.format_subject(
            "InvenTree Order Report - {{date}}",
            preset_name="Test Preset"
        )

        assert "2024-01-15" in subject

        # Test template with preset
        subject = formatter.format_subject(
            "Report for {{preset}} - {{date}}",
            preset_name="Test Preset"
        )

        assert "Test Preset" in subject
        assert "2024-01-15" in subject
    
    def test_format_subject_error_handling(self, formatter):
        """Test subject formatting error handling"""
        # Template with undefined variable should trigger error handling
        subject = formatter.format_subject(
            "Invalid template {{ invalid_var }}",  # Use Jinja2 syntax
            preset_name="Test Preset"
        )

        # Should contain current date as fallback
        current_date = datetime.now().strftime('%Y-%m-%d')
        assert current_date in subject
        assert "InvenTree Order Report" in subject
    
    def test_html_email_structure(self, formatter, sample_config, sample_results):
        """Test HTML email structure and styling"""
        content = formatter.format_email(
            results=sample_results,
            config=sample_config,
            preset_name="Test Preset"
        )
        
        html = content['html']
        
        # Check HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "<style>" in html
        
        # Check CSS classes
        assert "header" in html
        assert "summary" in html
        assert "warning" in html
        assert "section" in html
        assert "footer" in html
        
        # Check table styling
        assert "border-collapse: collapse" in html
        assert "border: 1px solid #ddd" in html
    
    def test_text_email_structure(self, formatter, sample_config, sample_results):
        """Test text email structure"""
        content = formatter.format_email(
            results=sample_results,
            config=sample_config,
            preset_name="Test Preset"
        )
        
        text = content['text']
        
        # Check text structure
        assert "INVENTREE ORDER CALCULATOR REPORT" in text
        assert "=" * 50 in text
        assert "SUMMARY:" in text
        assert "WARNINGS:" in text
        assert "PARTS TO ORDER:" in text
        assert "ASSEMBLIES TO BUILD:" in text
        
        # Check table formatting
        assert "-" * 80 in text  # Table separators
