#!/usr/bin/env python3
"""
File Processing Template

Demonstrates batch file processing with:
- Directory traversal and filtering
- Progress tracking
- Error recovery and logging
- File type detection
- Metrics collection
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    """Metrics for file processing operations"""
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    bytes_processed: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def duration_seconds(self) -> float:
        """Calculate processing duration."""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def throughput_mbps(self) -> float:
        """Calculate throughput in MB/s."""
        if self.duration_seconds > 0:
            return (self.bytes_processed / (1024 * 1024)) / self.duration_seconds
        return 0.0


class FileProcessor:
    """Batch file processor with progress tracking and error recovery."""
    
    def __init__(self, source_dir: str, pattern: str = "*"):
        """
        Initialize file processor.
        
        Args:
            source_dir: Directory containing files to process
            pattern: Glob pattern for file filtering (e.g., "*.txt", "*.csv")
        """
        self.source_dir = Path(source_dir)
        self.pattern = pattern
        self.metrics = ProcessingMetrics()
        self.errors = []
    
    def find_files(self, recursive: bool = False) -> List[Path]:
        """
        Find files matching the pattern.
        
        Args:
            recursive: If True, search subdirectories
        
        Returns:
            List of file paths
        """
        if recursive:
            files = list(self.source_dir.rglob(self.pattern))
        else:
            files = list(self.source_dir.glob(self.pattern))
        
        logger.info(f"Found {len(files)} files matching '{self.pattern}'")
        return sorted(files)
    
    def process_files(self, processor_func: Callable[[Path], bool],
                      recursive: bool = False,
                      skip_extensions: Optional[List[str]] = None) -> ProcessingMetrics:
        """
        Process files with custom function.
        
        Args:
            processor_func: Function to call for each file, returns True if successful
            recursive: Search subdirectories
            skip_extensions: File extensions to skip (e.g., ['.tmp', '.bak'])
        
        Returns:
            Processing metrics
        """
        skip_extensions = skip_extensions or []
        
        self.metrics.start_time = time.time()
        files = self.find_files(recursive=recursive)
        self.metrics.total_files = len(files)
        
        for idx, file_path in enumerate(files, 1):
            try:
                # Check skip extensions
                if file_path.suffix in skip_extensions:
                    logger.debug(f"Skipping {file_path}")
                    self.metrics.skipped_files += 1
                    continue
                
                # Log progress
                progress = f"[{idx}/{self.metrics.total_files}]"
                logger.info(f"{progress} Processing: {file_path.name}")
                
                # Process file
                if processor_func(file_path):
                    self.metrics.processed_files += 1
                    self.metrics.bytes_processed += file_path.stat().st_size
                else:
                    self.metrics.failed_files += 1
            
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self.metrics.failed_files += 1
                self.errors.append(str(e))
        
        self.metrics.end_time = time.time()
        
        # Log summary
        self._log_summary()
        return self.metrics
    
    def _log_summary(self) -> None:
        """Log processing summary."""
        logger.info("=" * 60)
        logger.info("FILE PROCESSING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Files: {self.metrics.total_files}")
        logger.info(f"Processed: {self.metrics.processed_files}")
        logger.info(f"Failed: {self.metrics.failed_files}")
        logger.info(f"Skipped: {self.metrics.skipped_files}")
        logger.info(f"Bytes Processed: {self.metrics.bytes_processed:,}")
        logger.info(f"Duration: {self.metrics.duration_seconds:.2f}s")
        logger.info(f"Throughput: {self.metrics.throughput_mbps:.2f} MB/s")
        
        if self.errors:
            logger.info(f"Errors ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10 errors
                logger.info(f"  - {error}")
        
        logger.info("=" * 60)


def process_line_by_line(file_path: Path) -> bool:
    """
    Example processor: Process file line by line.
    
    Replace this with your actual processing logic.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            line_count = sum(1 for _ in f)
        logger.debug(f"  Lines: {line_count}")
        return True
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main entry point."""
    try:
        # Configure file processor
        source_dir = "{{SOURCE_DIR}}"  # Replace with actual directory
        pattern = "{{PATTERN}}"          # Replace with file pattern (e.g., "*.txt")
        
        processor = FileProcessor(source_dir, pattern=pattern)
        
        # Process files
        metrics = processor.process_files(
            processor_func=process_line_by_line,
            recursive=True,
            skip_extensions=['.tmp', '.bak']
        )
        
        # Return exit code based on success
        return 0 if metrics.failed_files == 0 else 1
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
