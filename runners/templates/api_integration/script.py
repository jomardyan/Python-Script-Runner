#!/usr/bin/env python3
"""
REST API Integration Template

Demonstrates best practices for:
- API authentication (API key, OAuth, Bearer token)
- Rate limiting and backoff
- Retry logic with exponential backoff
- Error handling and validation
- Response parsing and validation
"""

import sys
import logging
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API Configuration"""
    base_url: str
    api_key: Optional[str] = None
    auth_type: str = "none"  # none, api_key, bearer, basic
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 0.5


class APIClient:
    """Resilient REST API client with rate limiting and retries."""
    
    def __init__(self, config: APIConfig):
        """Initialize API client with configuration."""
        self.config = config
        self.session = self._create_session()
        self.metrics = {
            'requests_sent': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'retries_performed': 0,
            'total_duration_seconds': 0.0
        }
    
    def _create_session(self) -> requests.Session:
        """Create a session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'User-Agent': 'PythonScriptRunner/1.0'
        })
        
        # Add authentication
        self._add_auth(session)
        
        return session
    
    def _add_auth(self, session: requests.Session) -> None:
        """Add authentication headers based on config."""
        if self.config.auth_type == "api_key" and self.config.api_key:
            session.headers.update({
                'X-API-Key': self.config.api_key
            })
        elif self.config.auth_type == "bearer" and self.config.api_key:
            session.headers.update({
                'Authorization': f'Bearer {self.config.api_key}'
            })
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        GET request with error handling.
        
        Args:
            endpoint: API endpoint (appended to base_url)
            params: Query parameters
        
        Returns:
            Response JSON or None on error
        """
        url = f"{self.config.base_url}/{endpoint}"
        try:
            logger.info(f"GET {url}")
            start_time = time.time()
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.timeout
            )
            
            duration = time.time() - start_time
            self.metrics['requests_sent'] += 1
            self.metrics['total_duration_seconds'] += duration
            
            response.raise_for_status()
            self.metrics['requests_successful'] += 1
            
            logger.info(f"Response: {response.status_code} ({duration:.2f}s)")
            return response.json()
        
        except requests.exceptions.RequestException as e:
            self.metrics['requests_failed'] += 1
            logger.error(f"API request failed: {e}")
            return None
    
    def post(self, endpoint: str, data: Optional[Dict] = None, 
             json_data: Optional[Dict] = None) -> Optional[Dict]:
        """
        POST request with error handling.
        
        Args:
            endpoint: API endpoint
            data: Form data
            json_data: JSON payload
        
        Returns:
            Response JSON or None on error
        """
        url = f"{self.config.base_url}/{endpoint}"
        try:
            logger.info(f"POST {url}")
            start_time = time.time()
            
            response = self.session.post(
                url,
                data=data,
                json=json_data,
                timeout=self.config.timeout
            )
            
            duration = time.time() - start_time
            self.metrics['requests_sent'] += 1
            self.metrics['total_duration_seconds'] += duration
            
            response.raise_for_status()
            self.metrics['requests_successful'] += 1
            
            logger.info(f"Response: {response.status_code} ({duration:.2f}s)")
            return response.json() if response.text else None
        
        except requests.exceptions.RequestException as e:
            self.metrics['requests_failed'] += 1
            logger.error(f"API request failed: {e}")
            return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get request metrics."""
        return self.metrics


def main():
    """Main entry point."""
    try:
        # Configure API client
        config = APIConfig(
            base_url="{{BASE_URL}}",  # Replace with actual API URL
            api_key="{{API_KEY}}",     # Replace with actual API key
            auth_type="api_key"
        )
        
        client = APIClient(config)
        
        # Example: Fetch data
        logger.info("Fetching data from API...")
        result = client.get("{{ENDPOINT}}")  # Replace with actual endpoint
        
        if result:
            logger.info(f"Success: {json.dumps(result, indent=2)}")
        else:
            logger.error("Failed to fetch data")
            return 1
        
        # Print metrics
        logger.info(f"Metrics: {json.dumps(client.get_metrics(), indent=2)}")
        return 0
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
