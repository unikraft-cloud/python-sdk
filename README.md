# Unikraft Cloud Python SDK

The official Python SDK for the [Unikraft Cloud](https://unikraft.com) Platform and
control-plane APIs.

## Installation

```sh
pip install unikraft-cloud
```

## Usage

```python
import asyncio
import os

from unikraft_cloud import UnikraftCloud


async def main() -> None:
    async with UnikraftCloud(token=os.environ["UKC_TOKEN"]) as ukc:
        async for instance in ukc.instances.list(details=True):
            print(instance.metro, instance.name, instance.state)


asyncio.run(main())
```

## Licence

BSD-3-Clause. See [`LICENSE.md`](LICENSE.md).
