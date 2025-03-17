# Case Study Single Cell RNA-Seq App

Case Study for a DIY scRNASeq data analysis platform

The following components are required

1. Django / PostgreSQL Database and Webserver
2. Streamlit Frontend Application
3. Bioinformatics Pipeline Steps
4. AWS CDK for automated Cloud Deployment


## AWS CDK Infrastructure for scRNA-seq Analysis Platform

This directory contains the AWS Cloud Development Kit (CDK) implementation for deploying the single-cell RNA sequencing (scRNA-seq) analysis platform infrastructure to AWS.

### Architecture Overview

The infrastructure consists of several stacks that work together to provide a scalable, secure environment for processing and visualizing scRNA-seq data:

![Architecture Diagram](docs/architecture.png)

#### Stack Components

1. **Network Stack** - Creates the VPC, subnets, security groups, and network ACLs
2. **PostgreSQL Stack** - Provisions the RDS PostgreSQL database
3. **Django API Stack** - Deploys the Django backend service
4. **Pipeline Stack** - Sets up data processing pipeline components
5. **UI Stack** - Deploys the user interface application

### Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.8+
- AWS CDK Toolkit (`npm install -g aws-cdk`)
- Docker (for building container images)

### Configuration

Configuration settings are stored in:
- `assets/cdk_config.yaml` - Main configuration parameters
- `assets/policies.json` - IAM policies

## Deployment

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Update Configuration (if needed)

Edit `assets/cdk_config.yaml` to set appropriate values for your environment.

#### 3. Synthesize CloudFormation Templates

```bash
cdk synth
```

#### 4. Deploy the Stacks

```bash
cdk deploy --all
```

## Stack Details

### Network Stack (`AlCaseScrnaseqStackNetwork`)

Creates the networking foundation:
- VPC with public and private subnets
- Security groups for different components
- Network ACLs to control traffic flow
- VPC endpoints for AWS services
- ECS cluster for container services
- Service discovery namespace

### PostgreSQL Stack (`AlCaseScrnaseqStackPG`)

Provisions the PostgreSQL database:
- RDS PostgreSQL instance (v16.3)
- Database credentials stored in AWS Secrets Manager
- Securely placed in a private subnet

### Django Stack (`AlCaseScrnaseqStackDjango`)

Deploys the backend API service:
- Django application running in Fargate container
- Environment configuration from S3
- Database initialization script
- Health checks
- Service discovery registration

### Pipeline Stack (`AlCaseScrnaseqStackPipeline`)

Sets up the data processing pipeline:
- FASTQ registration service (processes raw sequencing files)
- Raw data processing service (runs CellRanger analysis)
- Integration service (combines and analyzes datasets)
- S3 event notifications to trigger pipeline steps
- Lambda functions to orchestrate ECS tasks

### UI Stack (`AlCaseScrnaseqStackUI`)

Deploys the user interface:
- React frontend application
- Nginx for serving static content and routing
- Connected to backend API via service discovery

## Security Features

- Private subnets for sensitive components
- Least-privilege IAM policies
- Security groups that restrict traffic flow
- VPC endpoints to avoid public internet for AWS services
- Secrets managed via AWS Secrets Manager

## Development

### Adding a New Stack

1. Create a new Python file in the `awscdk` directory
2. Define your stack class extending `Stack`
3. Add the stack to `app.py`

### Updating Dependencies

If you modify dependencies between stacks, update the `add_dependency()` calls in `app.py`.

## Cleanup

To remove all deployed resources:

```bash
cdk destroy --all
```

## Notes

- The Django application communicates with the PostgreSQL database through the private subnet
- The UI application communicates with the Django API using service discovery
- Data processing happens in isolated containers with ephemeral storage
- Pipeline components are triggered automatically by S3 events