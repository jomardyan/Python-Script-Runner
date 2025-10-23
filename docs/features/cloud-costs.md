# Cloud Cost Attribution

## Overview

Python Script Runner v7.0+ includes integrated cloud cost tracking for AWS, Azure, and Google Cloud Platform (GCP). Automatically attribute infrastructure costs to individual script executions for accurate chargeback and cost optimization.

## Why Cloud Cost Attribution?

- **FinOps Practices**: Enable showback and chargeback across teams
- **Budget Control**: Monitor spending per script/project/team
- **Optimization**: Identify expensive operations and optimize
- **Compliance**: Audit costs for SOC2, HIPAA, PCI-DSS compliance
- **Multi-Cloud**: Unified cost tracking across AWS, Azure, GCP

## Installation

```bash
pip install 'python-script-runner[cloud]'
```

## Quick Start

### AWS

```python
from runner import ScriptRunner

runner = ScriptRunner('my_script.py')
runner.enable_cost_tracking = True
runner.cost_tracking_provider = 'aws'

result = runner.run_script()

# View costs
print(f"💰 Estimated cost: ${result.estimated_cost:.4f}")
print(f"Cost breakdown: {result.cost_breakdown}")
```

### Azure

```python
runner = ScriptRunner('my_script.py')
runner.enable_cost_tracking = True
runner.cost_tracking_provider = 'azure'
runner.azure_subscription_id = 'your-subscription-id'

result = runner.run_script()
print(f"💰 Estimated cost: ¥{result.estimated_cost:.2f}")  # Or in your currency
```

### Google Cloud

```python
runner = ScriptRunner('my_script.py')
runner.enable_cost_tracking = True
runner.cost_tracking_provider = 'gcp'
runner.gcp_project_id = 'your-project-id'

result = runner.run_script()
print(f"💰 Estimated cost: ${result.estimated_cost:.4f}")
```

## Configuration

### Environment Variables

```bash
# AWS
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1

# Azure
export AZURE_SUBSCRIPTION_ID=your-subscription-id
export AZURE_TENANT_ID=your-tenant-id
export AZURE_CLIENT_ID=your-client-id
export AZURE_CLIENT_SECRET=your-client-secret

# GCP
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
export GOOGLE_CLOUD_PROJECT=your-project-id
```

### Programmatic Configuration

```python
from runner import CostTrackingConfig

config = CostTrackingConfig(
    enabled=True,
    provider='aws',
    track_compute=True,
    track_storage=True,
    track_network=True,
    track_database=True,
    cost_allocation_tags={
        'Environment': 'production',
        'Team': 'data-engineering',
        'Project': 'etl-pipeline',
        'CostCenter': '12345'
    },
    exclude_resources=['lambda'],  # Don't track Lambda costs
    include_resources=['ec2', 'rds', 's3']  # Focus on these
)

runner.cost_config = config
```

## Cost Tracking Components

### Compute

```
EC2 instances (AWS) / Virtual Machines (Azure) / Compute Engine (GCP)
- Hourly rate based on instance type
- On-demand vs Reserved Instance discounts
- CPU, memory utilization during execution
```

### Storage

```
S3 / Blob Storage / Cloud Storage
- Per GB-month rates
- Data transfer costs
- Request costs (GET, PUT, LIST)
```

### Network

```
Data transfer out to internet
- Egress bandwidth charges
- Inter-region transfer costs
- VPC peering costs
```

### Database

```
Managed databases and data warehouses
- RDS, DynamoDB (AWS) / Cosmos DB (Azure) / Cloud SQL (GCP)
- Query execution costs
- Storage and backup costs
```

## Real-World Examples

### Example 1: Cost-Aware ETL Pipeline

```python
from runner import ScriptRunner, CostTrackingConfig

config = CostTrackingConfig(
    enabled=True,
    provider='aws',
    track_compute=True,
    track_storage=True,
    cost_allocation_tags={
        'Environment': 'production',
        'Team': 'data-engineering',
        'Pipeline': 'daily-etl'
    }
)

runner = ScriptRunner('etl_pipeline.py')
runner.cost_config = config

result = runner.run_script()

print(f"""
ETL Pipeline Cost Report:
========================
Total Cost: ${result.estimated_cost:.4f}

Cost Breakdown:
- Compute (EC2): ${result.cost_breakdown['compute']:.4f}
- Storage (S3): ${result.cost_breakdown['storage']:.4f}
- Data Transfer: ${result.cost_breakdown['network']:.4f}
- Database (RDS): ${result.cost_breakdown['database']:.4f}

Tags Applied:
{result.cost_allocation_tags}
""")
```

### Example 2: Budget Monitoring

```python
from runner import ScriptRunner

BUDGET_PER_SCRIPT = 1.50  # Max $1.50 per run

runner = ScriptRunner('batch_processing.py')
runner.enable_cost_tracking = True

result = runner.run_script()

if result.estimated_cost > BUDGET_PER_SCRIPT:
    print(f"⚠️ BUDGET EXCEEDED!")
    print(f"Limit: ${BUDGET_PER_SCRIPT:.2f}")
    print(f"Actual: ${result.estimated_cost:.4f}")
    print(f"Overage: ${result.estimated_cost - BUDGET_PER_SCRIPT:.4f}")
    
    # Notify team or trigger optimization
    notify_team("Script exceeded cost budget")
else:
    print(f"✅ Within budget: ${result.estimated_cost:.4f}/${BUDGET_PER_SCRIPT:.2f}")
```

### Example 3: Multi-Cloud Cost Comparison

```python
from runner import ScriptRunner

# Run on AWS
runner_aws = ScriptRunner('my_script.py')
runner_aws.enable_cost_tracking = True
runner_aws.cost_tracking_provider = 'aws'
result_aws = runner_aws.run_script()

# Run on Azure
runner_azure = ScriptRunner('my_script.py')
runner_azure.enable_cost_tracking = True
runner_azure.cost_tracking_provider = 'azure'
result_azure = runner_azure.run_script()

# Run on GCP
runner_gcp = ScriptRunner('my_script.py')
runner_gcp.enable_cost_tracking = True
runner_gcp.cost_tracking_provider = 'gcp'
result_gcp = runner_gcp.run_script()

# Compare
print(f"""
Multi-Cloud Cost Comparison:
===========================
AWS:   ${result_aws.estimated_cost:.4f}
Azure: ${result_azure.estimated_cost:.4f}
GCP:   ${result_gcp.estimated_cost:.4f}

Cheapest: {min([('AWS', result_aws.estimated_cost), 
                  ('Azure', result_azure.estimated_cost), 
                  ('GCP', result_gcp.estimated_cost)], 
                 key=lambda x: x[1])[0]}
""")
```

## CI/CD Integration

### GitHub Actions

```yaml
- uses: jomardyan/python-script-runner@v1
  with:
    script-path: './scripts/my_script.py'
    enable-cost-tracking: true
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### GitLab CI

```yaml
my_job:
  extends: .psr_script_runner_with_costs
  variables:
    SCRIPT_PATH: ./scripts/my_script.py
    AWS_REGION: us-east-1
```

## Cost Optimization Tips

### 1. Use Reserved Instances

```python
# AWS
config.instance_type = 't3.medium'  # Use standard types
config.use_reserved_instances = True  # Leverage RIs

# Savings: ~30-70% vs on-demand
```

### 2. Batch Similar Operations

```python
# Instead of running script 100 times separately
for i in range(100):
    runner.run_script()

# Batch into single run with matrix execution
runner.matrix = {'item_id': list(range(100))}
runner.run_script()  # More efficient
```

### 3. Right-Size Compute

```python
# Use smallest instance that meets requirements
runner.cpu_cores = 2  # Not 8
runner.memory_mb = 2048  # Not 16384

# Monitor actual usage and adjust
```

### 4. Schedule Off-Peak Execution

```python
# Run non-urgent jobs during off-peak hours
from datetime import datetime

if datetime.now().hour >= 9 and datetime.now().hour < 17:
    print("Deferring to off-peak hours")
    schedule_for_later()
else:
    runner.run_script()
```

## Reporting and Analytics

### Cost Report Generation

```python
from runner.analytics import CostAnalytics

analytics = CostAnalytics()

# Daily report
report = analytics.generate_report(
    period='daily',
    group_by=['team', 'project'],
    filters={'environment': 'production'}
)

print(report.to_html())  # View in browser
```

### Trend Analysis

```python
# Week-over-week comparison
trends = analytics.analyze_trends(
    metric='estimated_cost',
    period='week',
    lookback_weeks=12
)

print(f"Cost trend: {trends.growth_percent}% {'📈' if trends.growing else '📉'}")
```

## Compliance and Audit

### Cost Tagging

```python
runner.cost_allocation_tags = {
    'CostCenter': '12345',
    'Team': 'platform',
    'Project': 'infrastructure',
    'Environment': 'production',
    'ChargebackCode': 'ENG-2024'
}

result = runner.run_script()
# Tags are applied to all resources during execution
```

### Audit Trail

```python
# Access cost audit logs
audit_logs = analytics.get_audit_logs(
    start_date='2024-01-01',
    end_date='2024-01-31',
    script_name='etl_pipeline.py'
)

# Export for compliance
audit_logs.export_to_csv('cost_audit_2024-01.csv')
```

## Troubleshooting

### Credentials Not Working

```python
# Verify AWS credentials
import boto3
try:
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    print(f"AWS Account: {identity['Account']}")
except Exception as e:
    print(f"❌ AWS credentials error: {e}")
```

### Costs Seem Too High

1. Check which resources are being tracked
2. Verify cost allocation tags are correct
3. Look for resource leaks (instances not terminating)
4. Check data transfer costs

### No Cost Data

1. Ensure APIs have permission to read cost/billing data
2. Wait 24 hours (initial delay for AWS/Azure/GCP billing data)
3. Check if resources were actually created/used
4. Enable debug logging for detailed error info

## Related Documentation

- [AWS Cost Allocation Tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html)
- [Azure Cost Management](https://learn.microsoft.com/en-us/azure/cost-management-billing/)
- [GCP Cost Management](https://cloud.google.com/cost-management)
- [FinOps Foundation](https://www.finops.org/)
