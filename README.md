# Unikraft Cloud Python SDK

This repository contains an auto-generated Go SDK which interfaces with
[Unikraft Cloud](https://unikraft.cloud) based on the public
[OpenAPI](https://github.com/unikraft-cloud/openapi) specification.

> **Get started with Unikraft Cloud Today**
>
> Sign up at https://console.unikraft.cloud/signup

## Quickstart

```python
#!/usr/bin/env python3
"""
List Instances Example

This example demonstrates how to use the Unikraft Cloud Platform SDK to list instances.

Usage:
    python list_instances.py

Environment Variables:
    UKC_TOKEN: Your Unikraft Cloud API token (required)
    UKC_METRO: The metro URL (optional, defaults to fra0.kraft.cloud)

Example:
    export UKC_TOKEN="your-api-token-here"
    export UKC_METRO="https://api.fra0.kraft.cloud"
    python list_instances.py
"""

import os
import sys
from unikraft_cloud_platform import AuthenticatedClient
from unikraft_cloud_platform.models import Instance
from unikraft_cloud_platform.models.get_instances_response import GetInstancesResponse
from unikraft_cloud_platform.api.instances import get_instances
from unikraft_cloud_platform.types import Response


def main():
    # Read configuration from environment variables
    token = os.getenv("UKC_TOKEN")
    base_url = os.getenv("UKC_METRO", "https://api.fra0.kraft.cloud")
    
    if not token:
        print("Error: UKC_TOKEN environment variable is required", file=sys.stderr)
        print("Please set your API token: export UKC_TOKEN='your-token-here'", file=sys.stderr)
        sys.exit(1)
    
    client = AuthenticatedClient(
        base_url=base_url,
        token=token,
    )

    # List all instances (empty body means get all instances)
    with client as client:
        response: Response[GetInstancesResponse] = get_instances.sync_detailed(
            client=client,
            body=[],  # Empty list to get all instances
            details=True
        )

        # Check if the request was successful
        if response.status_code == 200 and response.parsed:
            instances_response = response.parsed
            
            # Check if we have data and instances
            if instances_response.data and instances_response.data.instances:
                print(f"Found {len(instances_response.data.instances)} instances:")
                print("-" * 50)
                
                for instance in instances_response.data.instances:
                    print(f"Name: {instance.name}")
                    print(f"UUID: {instance.uuid}")
                    print(f"State: {instance.state}")
                    print(f"Created: {instance.created_at}")
                    if instance.private_fqdn:
                        print(f"Private FQDN: {instance.private_fqdn}")
                    print("-" * 50)
            else:
                print("No instances found.")
        else:
            print(f"Failed to retrieve instances. Status code: {response.status_code}")
            if response.parsed and response.parsed.message:
                print(f"Error message: {response.parsed.message}")
            if response.parsed and response.parsed.errors:
                for error in response.parsed.errors:
                    print(f"Error: {error}")


if __name__ == "__main__":
    main()
```
