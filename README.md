# Unikraft Cloud Python SDK

The official Python SDK for the [Unikraft Cloud](https://unikraft.com) Platform and
control-plane APIs.

It has two layers. The **idiomatic** layer is what you reach for: envelope-free results,
automatic pagination, chainable references, and multi-metro fan-out. The **plumbing**
layer underneath mirrors the OpenAPI specification exactly, and stays available for
anything the idiomatic layer does not cover yet.

The SDK is async-only.

## Installation

```sh
pip install unikraft-cloud
```

Requires Python 3.10 or newer.

## Quickstart

```python
import asyncio

from unikraft_cloud import UnikraftCloud


async def main() -> None:
    async with UnikraftCloud() as ukc:  # token from UKC_TOKEN
        instance = await ukc.metro("fra").instances.create(
            image="nginx:latest", memory_mb=256, autostart=True
        )
        print(instance.name, instance.uuid, instance.metro)


asyncio.run(main())
```

The client owns a connection pool, so close it when you are done — either with
`async with`, or by awaiting `ukc.aclose()`.

## Configuration

```python
ukc = UnikraftCloud(
    token="...",  # falls back to UKC_TOKEN
    metro="fra",  # falls back to UKC_METRO; omit to cover every metro
)
```

| Argument | Purpose |
| --- | --- |
| `token` | Bearer token. Falls back to `UKC_TOKEN`. |
| `metro` | Pin to one metro, or to a full `http(s)://` URL for a staging or self-hosted deployment. Falls back to `UKC_METRO`. |
| `metros` | The metros operations cover by default: `"all"`, one metro, or a list. |
| `base_url` | Explicit platform API base URL; overrides `metro`. |
| `control_plane_url` | Override the control-plane API base URL. |
| `headers` | Extra headers sent with every request. |
| `user_agent` | Override the default User-Agent. |
| `http` | An `httpx.AsyncClient` to send through. Supplying one makes its lifetime yours. |
| `transport` | An `httpx.AsyncBaseTransport`, chiefly for testing with `httpx.MockTransport`. |
| `trust_env` | Honour `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY`. Defaults to `True`. |
| `timeout` | Timeout for every request. The default bounds connecting but not reading, because `wait` operations block for as long as you asked. |

## Metros

The platform API is metro-scoped. By default the client is **account-wide**: reads ask
every metro the account can reach and merge the answers as they arrive, and each result
carries the metro it came from.

```python
# Every metro, merged as the pages arrive.
async for inst in ukc.instances.list(details=True):
    print(inst.metro, inst.name, inst.state)

# One metro. Because it is known, no lookup is needed.
await ukc.metro("fra").instances.get(name="web").suspend()

# Several metros, for one call or for a whole client.
async for inst in ukc.instances.list(metros=["fra", "dal"]):
    ...
scoped = ukc.metros(["fra", "dal"])

# What the account can reach, as the control plane reports it.
for endpoint in await ukc.available_metros():
    print(endpoint.metro, endpoint.base_url)
```

Naming metros is also how you skip metro discovery, which is otherwise one extra request
per client.

## References

A resource is addressed by `name` or `uuid` — one or the other, because the API validates
whichever field it is given.

```python
await ukc.instances.get(name="web")
await ukc.instances.get(uuid="550e8400-e29b-41d4-a716-446655440000")
```

A name is only unique **within** a metro, so the same name can exist in several. Add
`metro=` to say which you mean, which also saves a lookup:

```python
await ukc.instances.get(name="web", metro="fra")
```

Without it, and with more than one metro in scope, the SDK asks every metro. If the name
matches in several it raises `AmbiguousRefError` rather than picking one — with the
matches attached, so recovering costs no further requests:

```python
from unikraft_cloud import AmbiguousRefError

try:
    await ukc.instances.get(name="web")
except AmbiguousRefError as err:
    print(err.metros)  # ("fra", "dal")
    print([m.uuid for m in err.matches])
```

To act on all of them deliberately, use `each()`:

```python
await ukc.instances.each(name="web").suspend()  # in every metro that has one
```

Bulk operations take a sequence of references, as `Ref` objects or plain dicts:

```python
from unikraft_cloud import Ref

await ukc.instances.delete([Ref(uuid="a"), {"name": "b"}])
```

## Chainable handles

Single-resource operations return a **handle** rather than a coroutine, so they compose.
A handle is awaitable too, so awaiting one gives you the resource:

```python
inst = await ukc.instances.get(name="web")  # the instance
await ukc.instances.get(name="web").suspend()  # the suspend

logs = await (
    ukc.metro("fra")
    .instances.create(image="nginx:latest")
    .wait(state="running", timeout_seconds=30)
    .logs(offset=-4096)
)
```

Nothing is sent until a handle is awaited or an operation is chained onto it. With one
metro in scope, `get(name=...).suspend()` is a single request; when the scope spans
metros, the instance is located first so the operation reaches the metro that holds it.

A handle that is dropped without ever being awaited emits a `RuntimeWarning`: unlike a
forgotten `await` on a coroutine, nothing else would tell you no request was sent.

## Updating

Properties are keyword arguments. A value sets the property, `REMOVE` clears it, and
anything omitted is left alone — all in one request.

```python
from unikraft_cloud import REMOVE

await ukc.instances.get(name="web").update(memory_mb=512, vcpus=2, autokill=REMOVE)
```

When `set` is not what you mean — merging into a property, or removing individual members
— stage the operations and apply them together:

```python
await (
    ukc.instances.get(name="web")
    .edit()
    .set(memory_mb=512)
    .add(env={"LOG_LEVEL": "debug"}, tags=["prod"])
    .delete(env=["OLD_FLAG"])
    .apply()
)
```

`apply()` returns a handle, so the chain continues. For anything keyword arguments cannot
express, `patch()` takes the raw triples.

## Errors

Every failure is an `UnikraftCloudError`, so one `except` catches the lot. Its `kind`
says which layer failed (`"http"`, `"network"`, `"parse"` or `"fanout"`) and `status`
carries the HTTP status where there was one.

```python
from unikraft_cloud import NotFoundError, UnikraftCloudError

try:
    await ukc.instances.get(name="web")
except NotFoundError:
    ...
except UnikraftCloudError as err:
    print(err.kind, err.status, err.errors)
```

`AuthenticationError` (401/403), `NotFoundError` (404), `RateLimitError` (429) and
`ServerError` (5xx) are raised for the statuses they name, and all subclass
`UnikraftCloudError`.

A multi-metro operation that only partly succeeded raises `MetroFanoutError`. An
iteration yields everything the healthy metros returned *before* raising, so a partial
failure never costs you the whole answer; operations that cannot yield as they go attach
what did arrive to `err.results`.

```python
from unikraft_cloud import MetroFanoutError

try:
    async for inst in ukc.instances.list():
        ...
except MetroFanoutError as err:
    print([failure.metro for failure in err.failures])
```

## Resources

`instances`, `volumes`, `services`, `certificates` and `users` hang off any scope —
`ukc`, `ukc.metro("fra")` or `ukc.metros([...])`.

```python
await ukc.volumes.get(name="data").attach(to="web", at="/data")
await ukc.services.get(name="web").update(hard_limit=10)
await ukc.certificates.get(name="tls").update(chain=chain_pem, pkey=key_pem)

for quota in await ukc.users.quotas():
    print(quota.metro, quota.used, quota.hard)
```

## The plumbing layer

Every operation in the specification is available raw, returning the response envelope
untouched. Each client talks to exactly one metro, and a single call can be redirected
with `base_url=`.

```python
res = await ukc.api.platform.instances.get_instances(count=10)
print(res.status, res.op_time_us, res.data.instances)

await ukc.api.controlplane.metros.list_metros()

# Or per resource, alongside its idiomatic client.
await ukc.instances.api.get_instance_metrics(uuid=["..."])
```

It can also be used on its own, without the idiomatic layer:

```python
from unikraft_cloud import ApiClientConfig
from unikraft_cloud.api.platform import PlatformApi

api = PlatformApi(ApiClientConfig(base_url="https://api.fra.unikraft.cloud", token=token))
```

## Examples

- [`examples/quickstart.py`](examples/quickstart.py) — create, wait, read logs, list, suspend, delete
- [`examples/update.py`](examples/update.py) — patch objects and the staged editor
- [`examples/plumbing.py`](examples/plumbing.py) — the raw API on its own

## Development

The `api/platform` and `api/controlplane` packages are generated from the OpenAPI
specification by [`openapi-gen`](https://github.com/unikraft-cloud) using the templates in
[`templates/`](templates). Everything else is hand-written. Files ending in `_gen.py` are
never edited by hand.

```sh
make generate    # regenerate both plumbing clients from the specs
make lint        # ruff check + format --check
make typecheck   # mypy
make test        # pytest
```

The test suite runs entirely offline through `httpx.MockTransport`.

## Licence

BSD-3-Clause. See [`LICENSE.md`](LICENSE.md).
