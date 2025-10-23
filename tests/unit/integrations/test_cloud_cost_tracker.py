"""Unit tests for Cloud Cost Attribution & Tracking."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runners.integrations.cloud_cost_tracker import (
    CloudCostTracker, CloudProvider, ResourceType, ResourceUsage,
    CostEstimate, CostResult, AWSCostCalculator, AzureCostCalculator,
    GCPCostCalculator
)


class TestCloudProvider:
    """Test CloudProvider enumeration."""
    
    def test_cloud_provider_values(self):
        """Test CloudProvider enum values."""
        assert CloudProvider.AWS.value == 'aws'
        assert CloudProvider.AZURE.value == 'azure'
        assert CloudProvider.GCP.value == 'gcp'


class TestResourceUsage:
    """Test ResourceUsage data class."""
    
    def test_create_resource_usage(self):
        """Test creating a ResourceUsage object."""
        usage = ResourceUsage(
            resource_id='i-1234567890abcdef0',
            resource_type='COMPUTE',
            provider='AWS',
            start_time=datetime.now(),
            end_time=datetime.now(),
            metrics={'instance_type': 't3.medium', 'region': 'us-east-1'}
        )
        assert usage.resource_id == 'i-1234567890abcdef0'
        assert usage.resource_type == 'COMPUTE'


class TestCostEstimate:
    """Test CostEstimate data class."""
    
    def test_create_cost_estimate(self):
        """Test creating a CostEstimate object."""
        estimate = CostEstimate(
            resource_id='i-1234567890abcdef0',
            provider='AWS',
            estimated_cost_usd=10.50,
            currency='USD',
            breakdown={'compute': 8.00, 'storage': 2.50}
        )
        assert estimate.resource_id == 'i-1234567890abcdef0'
        assert estimate.estimated_cost_usd == 10.50


class TestAWSCostCalculator:
    """Test AWS cost calculations."""
    
    def test_calculator_creation(self):
        """Test creating an AWSCostCalculator."""
        calculator = AWSCostCalculator()
        assert calculator is not None
    
    def test_ec2_cost_estimation(self):
        """Test EC2 instance cost estimation."""
        calculator = AWSCostCalculator()
        cost = calculator.estimate_ec2_cost(
            instance_type='t3.medium',
            region='us-east-1',
            hours=1
        )
        
        assert isinstance(cost, float)
        assert cost > 0
    
    def test_s3_cost_estimation(self):
        """Test S3 storage cost estimation."""
        calculator = AWSCostCalculator()
        cost = calculator.estimate_s3_cost(
            storage_gb=100,
            region='us-east-1'
        )
        
        assert isinstance(cost, float)
        assert cost > 0
    
    def test_lambda_cost_estimation(self):
        """Test Lambda function cost estimation."""
        calculator = AWSCostCalculator()
        cost = calculator.estimate_lambda_cost(
            executions=1000,
            duration_ms=1000,
            memory_mb=256
        )
        
        assert isinstance(cost, float)
        assert cost > 0


class TestAzureCostCalculator:
    """Test Azure cost calculations."""
    
    def test_calculator_creation(self):
        """Test creating an AzureCostCalculator."""
        calculator = AzureCostCalculator()
        assert calculator is not None
    
    def test_vm_cost_estimation(self):
        """Test Virtual Machine cost estimation."""
        calculator = AzureCostCalculator()
        cost = calculator.estimate_vm_cost(
            vm_size='Standard_D2s_v3',
            hours=1
        )
        
        assert isinstance(cost, float)
        assert cost > 0


class TestGCPCostCalculator:
    """Test GCP cost calculations."""
    
    def test_calculator_creation(self):
        """Test creating a GCPCostCalculator."""
        calculator = GCPCostCalculator()
        assert calculator is not None
    
    def test_compute_engine_cost(self):
        """Test Compute Engine cost estimation."""
        calculator = GCPCostCalculator()
        cost = calculator.estimate_compute_engine_cost(
            machine_type='n1-standard-1',
            region='us-central1',
            hours=1
        )
        
        assert isinstance(cost, float)
        assert cost > 0


class TestCloudCostTracker:
    """Test CloudCostTracker main functionality."""
    
    def test_tracker_creation(self):
        """Test creating a CloudCostTracker."""
        tracker = CloudCostTracker()
        assert tracker is not None
    
    def test_add_resource(self):
        """Test adding a resource to tracker."""
        tracker = CloudCostTracker()
        tracker.add_resource(
            resource_id='i-1234567890abcdef0',
            resource_type='COMPUTE',
            provider='AWS',
            metrics={'instance_type': 't3.medium', 'region': 'us-east-1'}
        )
        
        # Resource should be tracked
        assert len(tracker.resources) > 0
    
    def test_add_tag(self):
        """Test adding tags for cost allocation."""
        tracker = CloudCostTracker()
        tracker.add_tag('project', 'data-pipeline')
        tracker.add_tag('environment', 'production')
        
        assert tracker.tags['project'] == 'data-pipeline'
        assert tracker.tags['environment'] == 'production'
    
    def test_finalize_resource(self):
        """Test finalizing resource tracking."""
        tracker = CloudCostTracker()
        tracker.add_resource(
            resource_id='i-1234567890abcdef0',
            resource_type='COMPUTE',
            provider='AWS',
            metrics={'instance_type': 't3.medium', 'hours': 1}
        )
        
        # Finalize should calculate costs
        tracker.finalize_resource('i-1234567890abcdef0')
        
        # Result should have cost estimates
        result = tracker.get_result()
        assert result.success
    
    def test_get_total_cost(self):
        """Test getting total cost."""
        tracker = CloudCostTracker()
        tracker.add_resource(
            resource_id='i-1234567890abcdef0',
            resource_type='COMPUTE',
            provider='AWS',
            metrics={'instance_type': 't3.medium', 'hours': 1}
        )
        
        # Get total before finalizing
        total = tracker.get_total_cost()
        
        # Should return a float
        assert isinstance(total, float)
    
    def test_multi_provider_tracking(self):
        """Test tracking resources across multiple clouds."""
        tracker = CloudCostTracker()
        
        # Add AWS resource
        tracker.add_resource(
            resource_id='aws-resource',
            resource_type='COMPUTE',
            provider='AWS',
            metrics={'instance_type': 't3.medium', 'hours': 1}
        )
        
        # Add Azure resource
        tracker.add_resource(
            resource_id='azure-resource',
            resource_type='COMPUTE',
            provider='AZURE',
            metrics={'vm_size': 'Standard_D2s_v3', 'hours': 1}
        )
        
        # Add GCP resource
        tracker.add_resource(
            resource_id='gcp-resource',
            resource_type='COMPUTE',
            provider='GCP',
            metrics={'machine_type': 'n1-standard-1', 'hours': 1}
        )
        
        result = tracker.get_result()
        assert result.success
        assert len(result.resource_usages) >= 3


class TestCostResult:
    """Test CostResult data class."""
    
    def test_cost_result_creation(self):
        """Test creating a CostResult."""
        result = CostResult(
            success=True,
            total_estimated_cost_usd=50.00,
            resource_usages=[],
            cost_estimates=[],
            tags={'project': 'test'}
        )
        
        assert result.success
        assert result.total_estimated_cost_usd == 50.00


class TestCostTrackerIntegration:
    """Integration tests for cost tracking."""
    
    def test_complete_tracking_workflow(self):
        """Test complete cost tracking workflow."""
        tracker = CloudCostTracker()
        
        # Add resources
        tracker.add_resource(
            resource_id='resource-1',
            resource_type='COMPUTE',
            provider='AWS',
            metrics={'instance_type': 't3.micro', 'hours': 2}
        )
        
        # Add tags
        tracker.add_tag('environment', 'test')
        tracker.add_tag('project', 'demo')
        
        # Finalize
        tracker.finalize_resource('resource-1')
        
        # Get results
        result = tracker.get_result()
        
        assert result.success
        assert result.total_estimated_cost_usd > 0
        assert result.tags['environment'] == 'test'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
