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
| `metro` | The metro operations default to, or a full `http(s)://` URL for a staging or self-hosted deployment. Falls back to `UKC_METRO`. A code leaves the other metros reachable with `ukc.metro(...)`; a URL pins the client to that endpoint, and naming another metro then raises. |
| `metros` | The metros operations cover by default: `"all"`, one metro, or a list. Creating a resource needs exactly one, so name a metro somewhere when you create. |
| `base_url` | Explicit platform API base URL. It settles where requests go, so it overrides `metro` and `UKC_METRO` alike, and pins the client to that one endpoint. |
| `control_plane_url` | Override the control-plane API base URL. |
| `headers` | Extra headers sent with every request. |
| `user_agent` | Override the default User-Agent. |
| `http` | An `httpx.AsyncClient` to send through. Supplying one makes its lifetime yours. |
| `transport` | An `httpx.AsyncBaseTransport`, chiefly for testing with `httpx.MockTransport`. |
| `trust_env` | Honour `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY`. Defaults to `True`. |
| `timeout` | Timeout for every request. Omitted, an injected `http` client keeps its own; otherwise the default bounds connecting but not reading, because `wait` operations block for as long as you asked. |

## Metros

The platform API is metro-scoped. By default the client is **account-wide**: reads ask
every metro the account can reach and merge the answers as they arrive, and each result
carries the metro it came from.

```python
# Every metro, merged as the pages arrive. Await the listing instead for a list.
async for inst in ukc.instances.list(details=True):
    print(inst.metro, inst.name, inst.state)
every = await ukc.instances.list(details=True)  # one pass each: call list() again for more

# One metro. Because it is known, no lookup is needed.
await ukc.metro("fra").instances.get(name="web").suspend()

# Several metros, for one call or for a whole client.
async for inst in ukc.instances.list(metros=["fra", "dal"]):
    ...
scoped = ukc.metros(["fra", "dal"])

# A listing you stop reading holds a page of every metro, so close it.
async with ukc.instances.list() as listing:
    async for inst in listing:
        break

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

Bulk operations take a sequence of references, as `Ref` objects, plain dicts, or names:

```python
from unikraft_cloud import Ref

await ukc.instances.delete([Ref(uuid="a"), {"name": "b"}, "web"])
```

An operation the API could only carry out in part raises, naming what failed. What did
succeed is on `err.results`, so a partial failure costs nothing already done:

```python
from unikraft_cloud import NotFoundError

try:
    await ukc.instances.delete(["web", "gone"])
except NotFoundError as err:
    print([deleted.name for deleted in err.results])  # ["web"]
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

A handle is awaitable but is not a coroutine, so `asyncio.gather(...)` takes one while
`asyncio.create_task(...)` does not; wrap it in `asyncio.ensure_future(...)` for a task.

## Updating

Properties are keyword arguments. A value sets the property, `REMOVE` clears it out, and
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

`AuthenticationError` (401/403), `NotFoundError` (404), `AlreadyExistsError` (409),
`RateLimitError` (429) and `ServerError` (5xx) are raised for the statuses they name, and
all subclass `UnikraftCloudError`. The API reports some failures inside an otherwise-200
envelope, per item; those carry the API's own code on `err.errors[n].code` and are raised
with the status that says the same thing.

Two failures are caught before anything is sent, and are not `UnikraftCloudError`: a
property the resource does not have is a `TypeError`, and a request missing a field the
specification requires -- a service group without its `services`, an instance's `volumes`
entry without its `at` -- is pydantic's `ValidationError`.

A `wait()` that runs out of time raises `WaitTimeoutError`, which is also a builtin
`TimeoutError`, and carries the state the API last saw, with the instances it named on
`err.errors` -- so a `create()` whose wait lapsed still hands over the instance it made:

```python
try:
    await ukc.instances.get(name="web").wait(state="running", timeout_seconds=30)
except TimeoutError as err:
    print(err.state)  # e.g. "starting"
```

A `create()` whose instance stopped instead of running -- a node could not pull its
image, say -- raises `InstanceStoppedError`. The instance is read back so the error
carries the decoded reason, and every instance read back carries the same decoding as
its `stop`:

```python
from unikraft_cloud import InstanceStoppedError, PlatformStopCode

fra = ukc.metro("fra")
try:
    await fra.instances.create(image="org/app:latest", autostart=True, timeout_s=30)
except InstanceStoppedError as err:
    print(err.stop)  # e.g. "platform stop: image pull failed"
    if err.stop and err.stop.platform_code == PlatformStopCode.IMAGE_PULL_FAILED:
        await fra.instances.get(uuid=err.instance.uuid).delete()
```

When the API attaches a warning to an answer -- a deprecated field, say -- the SDK
issues it as a Python `UnikraftCloudWarning`, so the standard `warnings` filters
apply.

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

`instances`, `images`, `volumes`, `services`, `certificates` and `users` hang off any
scope — `ukc`, `ukc.metro("fra")` or `ukc.metros([...])`.

Creating one takes the properties the API describes as keyword arguments, and a property
it does not have is a `TypeError` rather than a field the server quietly ignores.

```python
await ukc.volumes.get(name="data").attach(to="web", at="/data")
await ukc.services.get(name="web").update(hard_limit=10)
await ukc.certificates.get(name="tls").update(chain=chain_pem, pkey=key_pem)

for quota in await ukc.users.quotas():
    print(quota.metro, quota.used, quota.hard)
```

### Instances

Beyond the operations above, instances can be addressed by their tags, deleted with a wait
and a retry while busy, and asked why they stopped:

```python
# Every instance in scope carrying all of the tags, however many; nothing matched is an
# empty set, so a cleanup can run again.
await ukc.instances.each(tags=["batch", "job=42"]).delete(missing_ok=True)
async for inst in ukc.instances.list(tags=["batch"], details=True):
    ...

# Wait for the deletion (-1 for as long as the platform allows), forgive an instance
# that is already gone, and keep trying while something still holds on to it. The read
# timeout is stretched to outlast the wait only when no `timeout` was given.
await fra.instances.get(name="relay").delete(timeout_seconds=60, missing_ok=True, retry_busy=20)

from unikraft_cloud import StopReason

inst = await fra.instances.get(name="web")
if inst.state == "stopped":
    print(inst.describe_stop())  # e.g. "kernel crash: out of memory (ENOMEM)"
    if inst.stop and inst.stop.reason & StopReason.KERNEL:
        print(inst.stop.kernel_code)
```

### Images

The metros report what their nodes have cached; the registry says what a node can pull.
`find` and `exists` ask the control plane, which answers from the registry itself, and
read a reference as the CLI does: a registry host in front is ignored, a bare name is in
the `official` namespace, and no tag means `latest`.

```python
for image in await ukc.images.list():
    print(image.metro, image.url, image.size_in_bytes)

if not await ukc.images.exists("org/app:1.2.3"):
    build_and_push("org/app:1.2.3")
found = await ukc.images.find("org/app@sha256:...")  # a tag of that digest, or None
```

## The sandbox plugin

A plugin is a helper loaded into an instance beside its workload, and reached through the
instance on the metro that runs it. The sandbox plugin runs commands and moves files
inside an instance; `sandbox()` on an instance handle is its client, and nothing is sent
until it is used.

```python
from unikraft_cloud import ExecTimeoutError

fra = ukc.metro("fra")
inst = await fra.instances.create(
    image="org/app:latest",
    memory_mb=1024,
    plugins=[{"name": "sandbox", "image": "plugins/sandbox:latest", "config": {}}],
    autostart=True,
    timeout_s=60,
)
sb = fra.instances.get(uuid=inst.uuid).sandbox()
await sb.wait_ready(timeout=60)  # until the plugin answers; PluginNotReadyError otherwise

# A shell line, or an argument vector run without a shell. The exit code is reported, not
# raised; output is collected, and handed over as it arrives if you ask.
result = await sb.exec("make test", cwd="/app", on_output=lambda chunk: print(chunk.data))
result = await sb.exec(["python", "-c", "print('no quoting needed')"])
print(result.exit_code, result.stdout, result.stderr)

# A timeout interrupts the command and waits for it to end; with a grace period a command
# that ignores the interrupt is given up on, and the error carries it for you to signal.
try:
    await sb.exec("./long-build", timeout=600, wait_delay=10, forget=True)
except ExecTimeoutError as err:
    await err.command.signal("KILL")

# Start, feed, follow and finish a command yourself.
cmd = await sb.run("sort")
await cmd.feed_stdin(b"b\na\n")
await cmd.close_stdin()
async for chunk in cmd.stream():  # until the command ends
    ...
code = await cmd.wait(timeout=30)  # None while it still runs
await cmd.delete()  # once it has ended

# Files move in chunks, so no request size limit applies; a download lands whole or not
# at all.
await sb.fs.write("/app/config.json", data, parents=True)
await sb.fs.upload_file("./bundle.tar", "/app/")
async for piece in sb.fs.stream("/app/out.bin"):
    ...
await sb.fs.read_to("/app/out.bin", "./out.bin")
```

`ExecResult.exit_code` is negative for a command a signal ended: `-2` after the
interrupt a timeout sends. A command left behind when `exec` fails or is cancelled keeps
running in the sandbox, for you to signal or forget. `PluginNotReadyError` and
`ExecTimeoutError` are `UnikraftCloudError` and builtin `TimeoutError` both, like
`WaitTimeoutError`.

Any other plugin is addressed the same way: `plugin("name")` on an instance handle resolves
its route once, and `.client(SomeApi)` builds a client there. The sandbox plumbing is
`ukc.api.plugins.sandbox.for_instance(uuid)`, and the generated clients it wraps come from
the `unikraft-cloud-plugin-sandbox-api` package.

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

# An operation that streams events yields each as it arrives.
async for event in ukc.api.platform.audit.subscribe_audit_events(tags=["prod"]):
    print(event.type, event.object.uuid if event.object else None)

# An operation that answers with bytes returns them with their status and headers.
raw = await ukc.api.plugins.sandbox.for_instance(instance_uuid).commands.get_raw_command_log(
    command_uuid, "stdout", range="bytes=0-1023"
)
print(raw.status, raw.byte_range, raw.total_size, raw.content)
```

It can also be used on its own, without the idiomatic layer:

```python
from unikraft_cloud import ApiClientConfig
from unikraft_cloud.api.platform import PlatformApi

config = ApiClientConfig(base_url="https://api.fra.unikraft.cloud", token=token)
async with PlatformApi(config) as api:
    res = await api.instances.get_instances(count=10)
```

## Examples

- [`examples/quickstart.py`](examples/quickstart.py) — create, wait, read logs, list, suspend, delete
- [`examples/update.py`](examples/update.py) — patch objects and the staged editor
- [`examples/sandbox.py`](examples/sandbox.py) — run commands and move files through the sandbox plugin
- [`examples/plumbing.py`](examples/plumbing.py) — the raw API on its own

## Development

The `api/platform` and `api/controlplane` packages are generated from the OpenAPI
specification by [`openapi-gen`](https://github.com/unikraft-cloud) using the templates in
[`templates/`](templates). The sandbox plugin's plumbing is generated elsewhere, by
[plugin-sdk](https://github.com/unikraft-cloud/plugin-sdk) from the plugin's own
specification, and installed as the `unikraft-cloud-plugin-sandbox-api` package.
Everything else is hand-written. Files ending in `_gen.py` are never edited by hand.

The templates tell request models from response models by name, after the TypeSpec
convention `<Verb><Resource>Request*`, and by use: a schema whose name contains
`Request` and not `Response` keeps the fields the specification requires, and so does a
schema that only requests reach -- through request bodies and the models they name,
however deep -- so a request missing a required field fails at construction. A schema
that any response reaches has every field optional, so a partial response always parses,
and a `Request`-named schema that a response also carries fails to parse when the server
leaves a required field out.

```sh
make generate    # regenerate the platform and control-plane plumbing from the specs
make lint        # ruff check + format --check
make typecheck   # mypy
make test        # pytest
```

The test suite runs entirely offline through `httpx.MockTransport`.

## Licence

BSD-3-Clause. See [`LICENSE.md`](LICENSE.md).
