#!/usr/bin/env python3
"""
Data Transformation Template

Demonstrates common data operations:
- Loading and exploring data
- Cleaning and validation
- Transformation and enrichment
- Aggregation and statistics
- Output generation
"""

import sys
import logging
import json
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataTransformer:
    """Data transformation pipeline with validation and metrics."""
    
    def __init__(self, input_file: str):
        """Initialize with input data file."""
        self.input_file = input_file
        self.df = None
        self.metrics = {
            'input_rows': 0,
            'output_rows': 0,
            'transformations_applied': [],
            'errors': []
        }
    
    def load_data(self) -> bool:
        """Load data from file."""
        try:
            import pandas as pd
            
            logger.info(f"Loading data from {self.input_file}")
            
            if self.input_file.endswith('.csv'):
                self.df = pd.read_csv(self.input_file)
            elif self.input_file.endswith('.json'):
                self.df = pd.read_json(self.input_file)
            elif self.input_file.endswith('.xlsx'):
                self.df = pd.read_excel(self.input_file)
            else:
                logger.error(f"Unsupported file format: {self.input_file}")
                return False
            
            self.metrics['input_rows'] = len(self.df)
            logger.info(f"Loaded {len(self.df)} rows, {len(self.df.columns)} columns")
            logger.info(f"Columns: {', '.join(self.df.columns)}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            self.metrics['errors'].append(str(e))
            return False
    
    def explore_data(self) -> None:
        """Display data summary and statistics."""
        if self.df is None:
            logger.warning("No data loaded")
            return
        
        logger.info("=" * 60)
        logger.info("DATA EXPLORATION")
        logger.info("=" * 60)
        
        logger.info("\nData Types:")
        logger.info(str(self.df.dtypes))
        
        logger.info("\nBasic Statistics:")
        logger.info(str(self.df.describe()))
        
        logger.info("\nMissing Values:")
        logger.info(str(self.df.isnull().sum()))
        
        logger.info("\nDuplicate Rows:")
        logger.info(f"  {self.df.duplicated().sum()}")
    
    def clean_data(self) -> None:
        """Apply data cleaning operations."""
        if self.df is None:
            return
        
        try:
            import pandas as pd
            import numpy as np
            
            logger.info("Cleaning data...")
            
            # Remove duplicates
            before_dedup = len(self.df)
            self.df = self.df.drop_duplicates()
            after_dedup = len(self.df)
            
            if before_dedup > after_dedup:
                removed = before_dedup - after_dedup
                logger.info(f"  Removed {removed} duplicate rows")
                self.metrics['transformations_applied'].append(f"remove_duplicates: {removed}")
            
            # Handle missing values
            missing_before = self.df.isnull().sum().sum()
            self.df = self.df.fillna(method='bfill').fillna(method='ffill')
            missing_after = self.df.isnull().sum().sum()
            
            if missing_before > 0:
                logger.info(f"  Filled {missing_before - missing_after} missing values")
                self.metrics['transformations_applied'].append(f"fill_missing: {missing_before - missing_after}")
            
            # Convert data types (example)
            for col in self.df.columns:
                if self.df[col].dtype == 'object':
                    try:
                        self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
                    except (ValueError, TypeError):
                        pass
            
            logger.info("Data cleaning completed")
        
        except Exception as e:
            logger.error(f"Error during cleaning: {e}")
            self.metrics['errors'].append(str(e))
    
    def transform_data(self) -> None:
        """Apply custom transformations ({{TRANSFORMATIONS}})."""
        if self.df is None:
            return
        
        try:
            logger.info("Applying transformations...")
            
            # Example transformations - customize as needed
            
            # 1. Add computed columns
            if 'value' in self.df.columns:
                self.df['value_doubled'] = self.df['value'] * 2
                self.metrics['transformations_applied'].append("add_computed_column: value_doubled")
            
            # 2. Create categories (if applicable)
            if 'timestamp' in self.df.columns:
                try:
                    self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
                    self.df['date'] = self.df['timestamp'].dt.date
                    self.metrics['transformations_applied'].append("extract_date_from_timestamp")
                except (ValueError, TypeError):
                    pass
            
            # 3. Text transformations
            for col in self.df.select_dtypes(include=['object']).columns:
                if col != 'date':  # Skip date column
                    self.df[col] = self.df[col].str.strip().str.lower()
            
            logger.info("Transformations completed")
        
        except Exception as e:
            logger.error(f"Error during transformation: {e}")
            self.metrics['errors'].append(str(e))
    
    def aggregate_data(self) -> None:
        """Generate aggregated statistics."""
        if self.df is None:
            return
        
        try:
            logger.info("Generating aggregations...")
            
            # Example: Group by first column and calculate statistics
            if len(self.df.columns) > 0:
                group_col = self.df.columns[0]
                numeric_cols = self.df.select_dtypes(include=['number']).columns
                
                if len(numeric_cols) > 0:
                    aggregations = self.df.groupby(group_col)[numeric_cols].agg(['sum', 'mean', 'count'])
                    logger.info(f"\nAggregations by {group_col}:")
                    logger.info(str(aggregations))
        
        except Exception as e:
            logger.error(f"Error during aggregation: {e}")
            self.metrics['errors'].append(str(e))
    
    def save_data(self, output_file: str) -> bool:
        """Save transformed data to file."""
        if self.df is None:
            logger.error("No data to save")
            return False
        
        try:
            logger.info(f"Saving data to {output_file}")
            
            if output_file.endswith('.csv'):
                self.df.to_csv(output_file, index=False)
            elif output_file.endswith('.json'):
                self.df.to_json(output_file, orient='records', indent=2)
            elif output_file.endswith('.xlsx'):
                self.df.to_excel(output_file, index=False)
            else:
                logger.error(f"Unsupported output format: {output_file}")
                return False
            
            self.metrics['output_rows'] = len(self.df)
            logger.info(f"Saved {len(self.df)} rows to {output_file}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            self.metrics['errors'].append(str(e))
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get transformation metrics."""
        return self.metrics


def main():
    """Main entry point."""
    try:
        # Configure input/output
        input_file = "{{INPUT_FILE}}"      # Replace with input file path
        output_file = "{{OUTPUT_FILE}}"    # Replace with output file path
        
        # Create transformer
        transformer = DataTransformer(input_file)
        
        # Execute pipeline
        if not transformer.load_data():
            return 1
        
        transformer.explore_data()
        transformer.clean_data()
        transformer.transform_data()
        transformer.aggregate_data()
        
        if not transformer.save_data(output_file):
            return 1
        
        # Print metrics
        logger.info("=" * 60)
        logger.info("TRANSFORMATION METRICS")
        logger.info("=" * 60)
        metrics = transformer.get_metrics()
        logger.info(json.dumps(metrics, indent=2))
        
        return 0 if not metrics['errors'] else 1
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
