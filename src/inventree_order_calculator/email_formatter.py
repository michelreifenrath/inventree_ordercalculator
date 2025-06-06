# Module: src/inventree_order_calculator/email_formatter.py
# Description: HTML email formatting for order calculator reports

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from jinja2 import Template, Environment, BaseLoader
from .models import OutputTables, CalculatedPart
from .email_config import EmailConfig

logger = logging.getLogger(__name__)

class EmailFormatter:
    """Formats order calculator results into HTML emails"""
    
    def __init__(self):
        self.env = Environment(loader=BaseLoader())
        
    def format_email(
        self, 
        results: OutputTables, 
        config: EmailConfig,
        preset_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Format calculation results into HTML and plain text email content
        
        Args:
            results: OutputTables containing calculation results
            config: EmailConfig for formatting preferences
            preset_name: Name of preset used for calculation
            
        Returns:
            Dict with 'html' and 'text' keys containing formatted content
        """
        try:
            # Generate summary statistics
            summary = self._generate_summary(results)
            
            # Format parts table
            parts_html = ""
            parts_text = ""
            if config.include_parts_table:
                parts_html = self._format_parts_table_html(results.parts_to_order)
                parts_text = self._format_parts_table_text(results.parts_to_order)

            # Format assemblies table
            assemblies_html = ""
            assemblies_text = ""
            if config.include_assemblies_table:
                assemblies_html = self._format_assemblies_table_html(results.subassemblies_to_build)
                assemblies_text = self._format_assemblies_table_text(results.subassemblies_to_build)
            
            # Generate HTML content
            html_content = self._generate_html_email(
                summary=summary if config.include_summary else None,
                parts_html=parts_html,
                assemblies_html=assemblies_html,
                preset_name=preset_name,
                warnings=results.warnings
            )
            
            # Generate plain text content
            text_content = self._generate_text_email(
                summary=summary if config.include_summary else None,
                parts_text=parts_text,
                assemblies_text=assemblies_text,
                preset_name=preset_name,
                warnings=results.warnings
            )
            
            return {
                'html': html_content,
                'text': text_content
            }
            
        except Exception as e:
            logger.error(f"Error formatting email content: {e}")
            raise

    def _generate_summary(self, results: OutputTables) -> Dict[str, Any]:
        """Generate summary statistics from results"""
        parts_count = len(results.parts_to_order) if results.parts_to_order else 0
        assemblies_count = len(results.subassemblies_to_build) if results.subassemblies_to_build else 0
        
        # Calculate total quantities
        total_parts_to_order = sum(
            part.to_order for part in results.parts_to_order
        ) if results.parts_to_order else 0
        
        total_assemblies_to_build = sum(
            assembly.to_build for assembly in results.subassemblies_to_build
        ) if results.subassemblies_to_build else 0
        
        return {
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'parts_count': parts_count,
            'assemblies_count': assemblies_count,
            'total_parts_quantity': total_parts_to_order,
            'total_assemblies_quantity': total_assemblies_to_build,
            'has_warnings': bool(results.warnings)
        }

    def _format_parts_table_html(self, parts: List[CalculatedPart]) -> str:
        """Format parts to order as HTML table"""
        if not parts:
            return "<p>No parts need to be ordered.</p>"
        
        html = """
        <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
            <thead>
                <tr style="background-color: #f5f5f5;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Part Name</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Part ID</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Needed</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Available</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">To Order</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Suppliers</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for part in parts:
            suppliers = ", ".join(part.supplier_names) if part.supplier_names else "N/A"
            optional_indicator = " (Optional)" if part.is_optional else ""
            
            html += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{part.name}{optional_indicator}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{part.pk}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{part.total_required:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{part.available:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right; font-weight: bold;">{part.to_order:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{suppliers}</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        return html

    def _format_assemblies_table_html(self, assemblies: List[CalculatedPart]) -> str:
        """Format assemblies to build as HTML table"""
        if not assemblies:
            return "<p>No assemblies need to be built.</p>"
        
        html = """
        <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
            <thead>
                <tr style="background-color: #f5f5f5;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Assembly Name</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Part ID</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Needed</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Available</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">To Build</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">In Production</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for assembly in assemblies:
            optional_indicator = " (Optional)" if assembly.is_optional else ""
            
            html += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{assembly.name}{optional_indicator}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{assembly.pk}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{assembly.total_required:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{assembly.available:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right; font-weight: bold;">{assembly.to_build:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{assembly.building:.2f}</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        return html

    def _format_parts_table_text(self, parts: List[CalculatedPart]) -> str:
        """Format parts to order as plain text table"""
        if not parts:
            return "No parts need to be ordered.\n"
        
        text = "\nPARTS TO ORDER:\n"
        text += "=" * 80 + "\n"
        text += f"{'Part Name':<30} {'ID':<8} {'Needed':<8} {'Available':<10} {'To Order':<10} {'Suppliers':<20}\n"
        text += "-" * 80 + "\n"
        
        for part in parts:
            suppliers = ", ".join(part.supplier_names) if part.supplier_names else "N/A"
            optional_indicator = " (Opt)" if part.is_optional else ""
            name_display = f"{part.name[:25]}{optional_indicator}"
            
            text += f"{name_display:<30} {part.pk:<8} {part.total_required:<8.2f} {part.available:<10.2f} {part.to_order:<10.2f} {suppliers[:20]:<20}\n"
        
        text += "\n"
        return text

    def _format_assemblies_table_text(self, assemblies: List[CalculatedPart]) -> str:
        """Format assemblies to build as plain text table"""
        if not assemblies:
            return "No assemblies need to be built.\n"
        
        text = "\nASSEMBLIES TO BUILD:\n"
        text += "=" * 80 + "\n"
        text += f"{'Assembly Name':<30} {'ID':<8} {'Needed':<8} {'Available':<10} {'To Build':<10} {'In Prod':<10}\n"
        text += "-" * 80 + "\n"
        
        for assembly in assemblies:
            optional_indicator = " (Opt)" if assembly.is_optional else ""
            name_display = f"{assembly.name[:25]}{optional_indicator}"
            
            text += f"{name_display:<30} {assembly.pk:<8} {assembly.total_required:<8.2f} {assembly.available:<10.2f} {assembly.to_build:<10.2f} {assembly.building:<10.2f}\n"
        
        text += "\n"
        return text

    def _generate_html_email(
        self, 
        summary: Optional[Dict[str, Any]], 
        parts_html: str, 
        assemblies_html: str,
        preset_name: Optional[str],
        warnings: List[str]
    ) -> str:
        """Generate complete HTML email content"""
        
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>InvenTree Order Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .summary { background-color: #ecf0f1; padding: 15px; margin: 20px 0; border-radius: 5px; }
        .warning { background-color: #f39c12; color: white; padding: 10px; margin: 10px 0; border-radius: 3px; }
        .section { margin: 30px 0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>InvenTree Order Calculator Report</h1>
        {% if preset_name %}
        <p>Generated from preset: <strong>{{ preset_name }}</strong></p>
        {% endif %}
    </div>
    
    {% if summary %}
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Generated:</strong> {{ summary.generation_time }}</p>
        <p><strong>Parts to Order:</strong> {{ summary.parts_count }} (Total Quantity: {{ summary.total_parts_quantity }})</p>
        <p><strong>Assemblies to Build:</strong> {{ summary.assemblies_count }} (Total Quantity: {{ summary.total_assemblies_quantity }})</p>
    </div>
    {% endif %}
    
    {% if warnings %}
    <div class="section">
        <h2>Warnings</h2>
        {% for warning in warnings %}
        <div class="warning">{{ warning }}</div>
        {% endfor %}
    </div>
    {% endif %}
    
    {% if parts_html %}
    <div class="section">
        <h2>Parts to Order</h2>
        {{ parts_html|safe }}
    </div>
    {% endif %}
    
    {% if assemblies_html %}
    <div class="section">
        <h2>Assemblies to Build</h2>
        {{ assemblies_html|safe }}
    </div>
    {% endif %}
    
    <div class="footer">
        <p>This report was automatically generated by InvenTree Order Calculator.</p>
    </div>
</body>
</html>
        """
        
        template = self.env.from_string(html_template)
        return template.render(
            summary=summary,
            parts_html=parts_html,
            assemblies_html=assemblies_html,
            preset_name=preset_name,
            warnings=warnings
        )

    def _generate_text_email(
        self, 
        summary: Optional[Dict[str, Any]], 
        parts_text: str, 
        assemblies_text: str,
        preset_name: Optional[str],
        warnings: List[str]
    ) -> str:
        """Generate complete plain text email content"""
        
        text = "INVENTREE ORDER CALCULATOR REPORT\n"
        text += "=" * 50 + "\n\n"
        
        if preset_name:
            text += f"Generated from preset: {preset_name}\n\n"
        
        if summary:
            text += "SUMMARY:\n"
            text += f"Generated: {summary['generation_time']}\n"
            text += f"Parts to Order: {summary['parts_count']} (Total Quantity: {summary['total_parts_quantity']})\n"
            text += f"Assemblies to Build: {summary['assemblies_count']} (Total Quantity: {summary['total_assemblies_quantity']})\n\n"
        
        if warnings:
            text += "WARNINGS:\n"
            for warning in warnings:
                text += f"- {warning}\n"
            text += "\n"
        
        if parts_text:
            text += parts_text
        
        if assemblies_text:
            text += assemblies_text
        
        text += "\n" + "=" * 50 + "\n"
        text += "This report was automatically generated by InvenTree Order Calculator.\n"
        
        return text

    def format_subject(self, template: str, preset_name: Optional[str] = None) -> str:
        """Format email subject line"""
        try:
            # Create environment with strict undefined behavior
            from jinja2 import Environment, StrictUndefined
            strict_env = Environment(undefined=StrictUndefined)
            template_obj = strict_env.from_string(template)
            return template_obj.render(
                date=datetime.now().strftime('%Y-%m-%d'),
                time=datetime.now().strftime('%H:%M'),
                preset=preset_name or "Manual"
            )
        except Exception as e:
            logger.error(f"Error formatting subject: {e}")
            return f"InvenTree Order Report - {datetime.now().strftime('%Y-%m-%d')}"
