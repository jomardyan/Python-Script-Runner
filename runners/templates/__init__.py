"""
Script Templates Module

Provides pre-built templates for common tasks:
- ETL pipelines
- API integrations
- File processing
- Data transformations
"""

try:
    from runners.templates.template_manager import TemplateManager
    __all__ = ["TemplateManager"]
except ImportError:
    __all__ = []
