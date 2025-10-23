#!/usr/bin/env python3
"""
ETL Pipeline Template

This template demonstrates a production-grade ETL workflow with:
- Data extraction from multiple sources
- Transformation with error handling
- Load into target system
- Comprehensive logging and metrics

Customize by replacing {{SOURCE}}, {{TRANSFORM}}, and {{TARGET}} placeholders.
"""

import sys
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ETLPipeline:
    """Production-grade ETL pipeline with error handling and metrics."""
    
    def __init__(self, config_file: str = "config.yaml"):
        """Initialize pipeline with configuration."""
        self.config = self._load_config(config_file)
        self.metrics = {
            'start_time': datetime.now(),
            'records_extracted': 0,
            'records_transformed': 0,
            'records_loaded': 0,
            'errors': []
        }
        logger.info("ETL Pipeline initialized")
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            import yaml
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Config file not found, using defaults: {e}")
            return {
                'source': {'type': '{{SOURCE}}', 'path': 'input_data.csv'},
                'transform': {'{{TRANSFORM}}': True},
                'target': {'type': '{{TARGET}}', 'connection': 'default'}
            }
    
    def extract(self) -> List[Dict[str, Any]]:
        """
        Extract data from source.
        
        Implement your extraction logic here. Example:
        - Read CSV files
        - Query databases
        - Call REST APIs
        """
        logger.info("Starting data extraction...")
        try:
            source_config = self.config.get('source', {})
            source_type = source_config.get('type', 'csv')
            
            if source_type == 'csv':
                import pandas as pd
                data = pd.read_csv(source_config.get('path', 'input.csv'))
                records = data.to_dict('records')
            else:
                logger.warning(f"Unknown source type: {source_type}, using sample data")
                records = [
                    {'id': 1, 'name': 'Sample 1', 'value': 100},
                    {'id': 2, 'name': 'Sample 2', 'value': 200},
                ]
            
            self.metrics['records_extracted'] = len(records)
            logger.info(f"Extracted {len(records)} records")
            return records
        
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            self.metrics['errors'].append(str(e))
            raise
    
    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform extracted data.
        
        Implement your transformation logic here. Example:
        - Data cleaning and validation
        - Enrichment and calculations
        - Deduplication
        """
        logger.info("Starting data transformation...")
        try:
            transformed = []
            
            for record in records:
                # Example transformations
                try:
                    transformed_record = {
                        **record,
                        'processed_at': datetime.now().isoformat(),
                        'record_valid': True
                    }
                    
                    # Add custom transformations here
                    if 'value' in transformed_record:
                        transformed_record['value_doubled'] = transformed_record['value'] * 2
                    
                    transformed.append(transformed_record)
                except Exception as record_error:
                    logger.warning(f"Failed to transform record {record}: {record_error}")
                    self.metrics['errors'].append(f"Transform error: {record_error}")
            
            self.metrics['records_transformed'] = len(transformed)
            logger.info(f"Transformed {len(transformed)} records")
            return transformed
        
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            self.metrics['errors'].append(str(e))
            raise
    
    def load(self, records: List[Dict[str, Any]]) -> None:
        """
        Load transformed data to target system.
        
        Implement your load logic here. Example:
        - Write to CSV/Parquet
        - Insert into database
        - Call REST APIs
        - Write to data warehouse
        """
        logger.info("Starting data load...")
        try:
            target_config = self.config.get('target', {})
            target_type = target_config.get('type', 'csv')
            
            if target_type == 'csv':
                import pandas as pd
                df = pd.DataFrame(records)
                output_path = target_config.get('path', 'output.csv')
                df.to_csv(output_path, index=False)
                logger.info(f"Loaded {len(records)} records to {output_path}")
            
            elif target_type == 'json':
                output_path = target_config.get('path', 'output.json')
                with open(output_path, 'w') as f:
                    json.dump(records, f, indent=2)
                logger.info(f"Loaded {len(records)} records to {output_path}")
            
            else:
                logger.warning(f"Unknown target type: {target_type}, defaulting to JSON")
                with open('output.json', 'w') as f:
                    json.dump(records, f, indent=2)
            
            self.metrics['records_loaded'] = len(records)
        
        except Exception as e:
            logger.error(f"Load failed: {e}")
            self.metrics['errors'].append(str(e))
            raise
    
    def run(self) -> Dict[str, Any]:
        """Execute the complete ETL pipeline."""
        logger.info("=" * 60)
        logger.info("ETL PIPELINE STARTING")
        logger.info("=" * 60)
        
        try:
            # Extract
            extracted_data = self.extract()
            
            # Transform
            transformed_data = self.transform(extracted_data)
            
            # Load
            self.load(transformed_data)
            
            # Finalize metrics
            self.metrics['end_time'] = datetime.now()
            self.metrics['duration_seconds'] = (
                self.metrics['end_time'] - self.metrics['start_time']
            ).total_seconds()
            self.metrics['status'] = 'SUCCESS'
            
            logger.info("=" * 60)
            logger.info("ETL PIPELINE COMPLETED SUCCESSFULLY")
            logger.info(f"Metrics: {json.dumps(self.metrics, default=str, indent=2)}")
            logger.info("=" * 60)
            
            return self.metrics
        
        except Exception as e:
            self.metrics['status'] = 'FAILED'
            self.metrics['end_time'] = datetime.now()
            logger.error(f"Pipeline execution failed: {e}")
            raise


def main():
    """Main entry point."""
    try:
        pipeline = ETLPipeline()
        metrics = pipeline.run()
        
        # Exit with status code
        return 0 if metrics.get('status') == 'SUCCESS' else 1
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
