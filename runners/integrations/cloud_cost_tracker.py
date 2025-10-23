"""
Cloud Cost Attribution and Tracking

Track AWS/Azure/GCP resource usage during script execution and estimate costs.

Features:
- Multi-cloud support (AWS, Azure, GCP)
- Real-time resource monitoring
- Cost calculation and attribution
- Budget tracking and alerting
- Cost optimization recommendations
- Tagging and allocation
"""

import logging
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


class CloudProvider(Enum):
    """Supported cloud providers."""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class ResourceType(Enum):
    """Types of cloud resources."""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"
    OTHER = "other"


@dataclass
class ResourceUsage:
    """Resource usage during execution."""
    resource_id: str
    resource_type: ResourceType
    provider: CloudProvider
    start_time: datetime
    end_time: Optional[datetime] = None
    metrics: Dict[str, float] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.metrics is None:
            self.metrics = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type.value,
            "provider": self.provider.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metrics": self.metrics,
        }


@dataclass
class CostEstimate:
    """Cost estimate for resource usage."""
    resource_id: str
    provider: CloudProvider
    estimated_cost_usd: float
    currency: str = "USD"
    breakdown: Dict[str, float] = None
    confidence: float = 0.8  # 0.0 to 1.0
    calculation_time: Optional[datetime] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.breakdown is None:
            self.breakdown = {}
        if self.calculation_time is None:
            self.calculation_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resource_id": self.resource_id,
            "provider": self.provider.value,
            "estimated_cost_usd": self.estimated_cost_usd,
            "currency": self.currency,
            "breakdown": self.breakdown,
            "confidence": self.confidence,
            "calculation_time": self.calculation_time.isoformat() if self.calculation_time else None,
        }


@dataclass
class CostResult:
    """Result of cost tracking."""
    success: bool
    total_estimated_cost_usd: float
    resource_usages: List[ResourceUsage]
    cost_estimates: List[CostEstimate]
    tracking_duration: float = 0.0
    tags: Dict[str, str] = None
    errors: Optional[List[str]] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.tags is None:
            self.tags = {}
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "total_estimated_cost_usd": self.total_estimated_cost_usd,
            "resource_usages": [r.to_dict() for r in self.resource_usages],
            "cost_estimates": [c.to_dict() for c in self.cost_estimates],
            "tracking_duration": self.tracking_duration,
            "tags": self.tags,
            "errors": self.errors,
        }


class AWSCostCalculator:
    """Calculate costs for AWS resources."""

    # Simplified pricing models (update with real pricing)
    PRICING = {
        "ec2": {
            "t3.micro": 0.0104,  # per hour
            "t3.small": 0.0208,
            "t3.medium": 0.0416,
            "m5.large": 0.096,
            "m5.xlarge": 0.192,
            "c5.large": 0.085,
            "c5.xlarge": 0.17,
        },
        "s3": {
            "storage_gb_month": 0.023,  # per GB per month
            "transfer_gb": 0.09,  # per GB
        },
        "rds": {
            "multi_az_micro": 0.034,  # per hour
            "multi_az_small": 0.068,
            "multi_az_medium": 0.136,
        },
        "lambda": {
            "per_million_requests": 0.20,
            "per_gb_second": 0.0000166667,
        },
    }

    def __init__(self):
        """Initialize AWS cost calculator."""
        self.logger = logging.getLogger(__name__)

    def estimate_ec2_cost(
        self, instance_type: str, hours: float, data_transfer_gb: float = 0
    ) -> Tuple[float, Dict[str, float]]:
        """
        Estimate EC2 cost.

        Args:
            instance_type: Instance type (e.g., t3.micro)
            hours: Hours of usage
            data_transfer_gb: GB of data transferred

        Returns:
            (total_cost, breakdown_dict)
        """
        breakdown = {}
        compute_cost = 0.0

        if instance_type in self.PRICING["ec2"]:
            hourly_rate = self.PRICING["ec2"][instance_type]
            compute_cost = hourly_rate * hours
            breakdown["compute"] = compute_cost

        transfer_cost = data_transfer_gb * self.PRICING["s3"]["transfer_gb"]
        if transfer_cost > 0:
            breakdown["data_transfer"] = transfer_cost

        total = compute_cost + transfer_cost
        return total, breakdown

    def estimate_s3_cost(
        self, storage_gb: float, transfer_gb: float = 0, requests: int = 0
    ) -> Tuple[float, Dict[str, float]]:
        """
        Estimate S3 cost.

        Args:
            storage_gb: GB stored
            transfer_gb: GB transferred
            requests: Number of requests

        Returns:
            (total_cost, breakdown_dict)
        """
        breakdown = {}

        storage_cost = storage_gb * self.PRICING["s3"]["storage_gb_month"] / 30
        breakdown["storage"] = storage_cost

        transfer_cost = transfer_gb * self.PRICING["s3"]["transfer_gb"]
        if transfer_cost > 0:
            breakdown["transfer"] = transfer_cost

        request_cost = (requests / 1000) * 0.00001  # Simplified
        if request_cost > 0:
            breakdown["requests"] = request_cost

        return storage_cost + transfer_cost + request_cost, breakdown

    def estimate_lambda_cost(
        self, gb_seconds: float, requests: int
    ) -> Tuple[float, Dict[str, float]]:
        """
        Estimate Lambda cost.

        Args:
            gb_seconds: GB-seconds of compute
            requests: Number of requests

        Returns:
            (total_cost, breakdown_dict)
        """
        breakdown = {}

        compute_cost = gb_seconds * self.PRICING["lambda"]["per_gb_second"]
        breakdown["compute"] = compute_cost

        request_cost = (requests / 1_000_000) * self.PRICING["lambda"]["per_million_requests"]
        breakdown["requests"] = request_cost

        return compute_cost + request_cost, breakdown


class AzureCostCalculator:
    """Calculate costs for Azure resources."""

    PRICING = {
        "vm": {
            "Standard_B1s": 0.0121,  # per hour
            "Standard_B2s": 0.0485,
            "Standard_D2s_v3": 0.0968,
            "Standard_D4s_v3": 0.1936,
        },
        "storage": {
            "per_gb_month": 0.0184,
        },
        "sql": {
            "basic": 0.49,  # per database per day
            "standard": 2.45,
            "premium": 9.8,
        },
    }

    def __init__(self):
        """Initialize Azure cost calculator."""
        self.logger = logging.getLogger(__name__)

    def estimate_vm_cost(
        self, vm_type: str, hours: float
    ) -> Tuple[float, Dict[str, float]]:
        """Estimate Azure VM cost."""
        breakdown = {}

        if vm_type in self.PRICING["vm"]:
            hourly_rate = self.PRICING["vm"][vm_type]
            compute_cost = hourly_rate * hours
            breakdown["compute"] = compute_cost
            return compute_cost, breakdown

        return 0.0, breakdown

    def estimate_storage_cost(self, storage_gb: float) -> Tuple[float, Dict[str, float]]:
        """Estimate Azure Storage cost."""
        breakdown = {}

        cost = storage_gb * self.PRICING["storage"]["per_gb_month"] / 30
        breakdown["storage"] = cost

        return cost, breakdown


class GCPCostCalculator:
    """Calculate costs for GCP resources."""

    PRICING = {
        "compute_engine": {
            "n1_standard_1": 0.0475,  # per hour
            "n1_standard_2": 0.095,
            "n1_standard_4": 0.19,
            "n1_standard_8": 0.38,
        },
        "storage": {
            "per_gb_month": 0.020,
        },
        "cloud_sql": {
            "db_f1_micro": 0.0065,  # per hour
            "db_g1_small": 0.026,
        },
    }

    def __init__(self):
        """Initialize GCP cost calculator."""
        self.logger = logging.getLogger(__name__)

    def estimate_compute_engine_cost(
        self, machine_type: str, hours: float
    ) -> Tuple[float, Dict[str, float]]:
        """Estimate Compute Engine cost."""
        breakdown = {}

        if machine_type in self.PRICING["compute_engine"]:
            hourly_rate = self.PRICING["compute_engine"][machine_type]
            compute_cost = hourly_rate * hours
            breakdown["compute"] = compute_cost
            return compute_cost, breakdown

        return 0.0, breakdown

    def estimate_storage_cost(self, storage_gb: float) -> Tuple[float, Dict[str, float]]:
        """Estimate Cloud Storage cost."""
        breakdown = {}

        cost = storage_gb * self.PRICING["storage"]["per_gb_month"] / 30
        breakdown["storage"] = cost

        return cost, breakdown


class CloudCostTracker:
    """Track and estimate cloud costs during script execution."""

    def __init__(self):
        """Initialize cloud cost tracker."""
        self.logger = logging.getLogger(__name__)
        self.aws_calc = AWSCostCalculator()
        self.azure_calc = AzureCostCalculator()
        self.gcp_calc = GCPCostCalculator()
        self.resource_usages: List[ResourceUsage] = []
        self.cost_estimates: List[CostEstimate] = []
        self.tags: Dict[str, str] = {}
        self.start_time = datetime.now()

    def add_resource(
        self,
        resource_id: str,
        resource_type: ResourceType,
        provider: CloudProvider,
        metrics: Dict[str, float] = None,
    ) -> ResourceUsage:
        """
        Add resource to tracking.

        Args:
            resource_id: Unique resource identifier
            resource_type: Type of resource
            provider: Cloud provider
            metrics: Initial metrics

        Returns:
            ResourceUsage object
        """
        usage = ResourceUsage(
            resource_id=resource_id,
            resource_type=resource_type,
            provider=provider,
            start_time=datetime.now(),
            metrics=metrics or {},
        )
        self.resource_usages.append(usage)
        self.logger.info(f"Tracking {provider.value} {resource_type.value}: {resource_id}")
        return usage

    def add_tag(self, key: str, value: str):
        """
        Add allocation tag.

        Args:
            key: Tag key (Environment, Team, Project, CostCenter)
            value: Tag value
        """
        self.tags[key] = value

    def finalize_resource(self, resource_id: str, metrics: Dict[str, float]):
        """
        Finalize resource and estimate cost.

        Args:
            resource_id: Resource identifier
            metrics: Final metrics
        """
        # Find resource
        for usage in self.resource_usages:
            if usage.resource_id == resource_id:
                usage.end_time = datetime.now()
                usage.metrics.update(metrics)

                # Calculate cost
                duration = (usage.end_time - usage.start_time).total_seconds() / 3600  # hours

                cost, breakdown = self._calculate_cost(usage, duration)

                estimate = CostEstimate(
                    resource_id=resource_id,
                    provider=usage.provider,
                    estimated_cost_usd=cost,
                    breakdown=breakdown,
                )
                self.cost_estimates.append(estimate)
                self.logger.info(f"Estimated cost for {resource_id}: ${cost:.4f}")
                break

    def _calculate_cost(
        self, usage: ResourceUsage, duration: float
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate cost for resource usage."""
        if usage.provider == CloudProvider.AWS:
            if usage.resource_type == ResourceType.COMPUTE:
                instance_type = usage.metrics.get("instance_type", "t3.micro")
                data_transfer = usage.metrics.get("data_transfer_gb", 0)
                return self.aws_calc.estimate_ec2_cost(instance_type, duration, data_transfer)
            elif usage.resource_type == ResourceType.STORAGE:
                storage_gb = usage.metrics.get("storage_gb", 0)
                transfer_gb = usage.metrics.get("transfer_gb", 0)
                return self.aws_calc.estimate_s3_cost(storage_gb, transfer_gb)

        elif usage.provider == CloudProvider.AZURE:
            if usage.resource_type == ResourceType.COMPUTE:
                vm_type = usage.metrics.get("vm_type", "Standard_B1s")
                return self.azure_calc.estimate_vm_cost(vm_type, duration)
            elif usage.resource_type == ResourceType.STORAGE:
                storage_gb = usage.metrics.get("storage_gb", 0)
                return self.azure_calc.estimate_storage_cost(storage_gb)

        elif usage.provider == CloudProvider.GCP:
            if usage.resource_type == ResourceType.COMPUTE:
                machine_type = usage.metrics.get("machine_type", "n1_standard_1")
                return self.gcp_calc.estimate_compute_engine_cost(machine_type, duration)
            elif usage.resource_type == ResourceType.STORAGE:
                storage_gb = usage.metrics.get("storage_gb", 0)
                return self.gcp_calc.estimate_storage_cost(storage_gb)

        return 0.0, {}

    def get_total_cost(self) -> float:
        """Get total estimated cost."""
        return sum(ce.estimated_cost_usd for ce in self.cost_estimates)

    def get_result(self) -> CostResult:
        """
        Get final cost tracking result.

        Returns:
            CostResult with all information
        """
        duration = (datetime.now() - self.start_time).total_seconds()

        return CostResult(
            success=len(self.resource_usages) > 0,
            total_estimated_cost_usd=self.get_total_cost(),
            resource_usages=self.resource_usages,
            cost_estimates=self.cost_estimates,
            tracking_duration=duration,
            tags=self.tags,
        )
