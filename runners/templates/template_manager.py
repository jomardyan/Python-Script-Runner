"""
Script Template Manager

Provides pre-built templates for common scripting tasks with embedded best practices.
Supports CLI scaffolding to quickly create new scripts from templates.
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging


logger = logging.getLogger(__name__)


@dataclass
class TemplateMetadata:
    """Metadata for a script template"""
    name: str
    category: str  # etl, api, file_processing, data_transform, etc.
    description: str
    author: str
    version: str
    tags: List[str]
    dependencies: List[str]
    difficulty: str  # beginner, intermediate, advanced
    estimated_time_minutes: int


class TemplateManager:
    """
    Manages script templates for rapid development and best practices.
    
    Features:
    - Pre-built templates for common tasks
    - Template discovery and filtering
    - Scaffold new scripts from templates
    - Embedded documentation and examples
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize TemplateManager.
        
        Args:
            templates_dir: Path to templates directory. If None, uses default location.
        """
        if templates_dir is None:
            # Default to runners/templates directory
            templates_dir = os.path.join(
                os.path.dirname(__file__), 
                '..'
            )
        
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, TemplateMetadata] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Discover and load all available templates."""
        try:
            # Look for template.json files in subdirectories
            for template_dir in self.templates_dir.glob('**/template.json'):
                try:
                    with open(template_dir, 'r') as f:
                        metadata_dict = json.load(f)
                    
                    metadata = TemplateMetadata(**metadata_dict)
                    self.templates[metadata.name] = metadata
                    logger.debug(f"Loaded template: {metadata.name}")
                except Exception as e:
                    logger.warning(f"Failed to load template from {template_dir}: {e}")
        except Exception as e:
            logger.error(f"Error discovering templates: {e}")
    
    def list_templates(self, category: Optional[str] = None, 
                       difficulty: Optional[str] = None,
                       tags: Optional[List[str]] = None) -> List[TemplateMetadata]:
        """
        List available templates with optional filtering.
        
        Args:
            category: Filter by category (e.g., 'etl', 'api')
            difficulty: Filter by difficulty level
            tags: Filter by tags (matches any tag)
        
        Returns:
            List of matching template metadata
        """
        results = list(self.templates.values())
        
        if category:
            results = [t for t in results if t.category == category]
        
        if difficulty:
            results = [t for t in results if t.difficulty == difficulty]
        
        if tags:
            results = [
                t for t in results 
                if any(tag in t.tags for tag in tags)
            ]
        
        return sorted(results, key=lambda x: x.name)
    
    def get_template(self, template_name: str) -> Optional[TemplateMetadata]:
        """Get template metadata by name."""
        return self.templates.get(template_name)
    
    def scaffold(self, template_name: str, output_path: str, 
                 replacements: Optional[Dict[str, str]] = None) -> bool:
        """
        Create a new script from a template.
        
        Args:
            template_name: Name of the template to use
            output_path: Path where to create the new script
            replacements: Dict of placeholder replacements (e.g., {'{{PROJECT}}': 'my_project'})
        
        Returns:
            True if successful, False otherwise
        """
        metadata = self.get_template(template_name)
        if not metadata:
            logger.error(f"Template not found: {template_name}")
            return False
        
        try:
            template_source = self.templates_dir / template_name / 'script.py'
            if not template_source.exists():
                logger.error(f"Template script not found: {template_source}")
                return False
            
            # Read template content
            with open(template_source, 'r') as f:
                content = f.read()
            
            # Apply replacements
            if replacements:
                for placeholder, value in replacements.items():
                    content = content.replace(placeholder, value)
            
            # Write output
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                f.write(content)
            
            logger.info(f"Created script from template '{template_name}': {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error scaffolding template: {e}")
            return False
    
    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive template information including docstring and examples.
        
        Args:
            template_name: Name of the template
        
        Returns:
            Dict with metadata and additional info, or None if not found
        """
        metadata = self.get_template(template_name)
        if not metadata:
            return None
        
        result = {"metadata": asdict(metadata)}
        
        try:
            # Try to get README if it exists
            readme_path = self.templates_dir / template_name / 'README.md'
            if readme_path.exists():
                with open(readme_path, 'r') as f:
                    result['readme'] = f.read()
            
            # Try to get example config if it exists
            example_config = self.templates_dir / template_name / 'example_config.yaml'
            if example_config.exists():
                with open(example_config, 'r') as f:
                    result['example_config'] = f.read()
        
        except Exception as e:
            logger.warning(f"Error reading template supplementary files: {e}")
        
        return result
    
    def add_custom_template(self, template_name: str, 
                           script_content: str,
                           metadata: TemplateMetadata) -> bool:
        """
        Add a custom template to the manager.
        
        Args:
            template_name: Name for the template
            script_content: Python script content
            metadata: Template metadata
        
        Returns:
            True if successful, False otherwise
        """
        try:
            template_dir = self.templates_dir / template_name
            template_dir.mkdir(parents=True, exist_ok=True)
            
            # Write script
            script_path = template_dir / 'script.py'
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Write metadata
            metadata_path = template_dir / 'template.json'
            with open(metadata_path, 'w') as f:
                json.dump(asdict(metadata), f, indent=2)
            
            # Reload templates
            self._load_templates()
            logger.info(f"Added custom template: {template_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding custom template: {e}")
            return False


def create_template_scaffolding() -> None:
    """Create default template directory structure with examples."""
    templates_base = Path(__file__).parent
    
    # This function is called during package initialization to set up examples
    pass
