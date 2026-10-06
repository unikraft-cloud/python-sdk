# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Instance templates: a snapshotted instance that new ones are cloned from. The
# platform prepares a template as a side effect of cloning it, so preparing one
# here creates a stopped clone and deletes it again; the templates themselves
# are instances in the `template` state, read through the instances API.

from __future__ import annotations

import asyncio

# `Templates.list` shadows the builtin inside that class body, so annotations
# there spell the builtin out.
import builtins
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any, Literal, TypeVar, overload

import httpx
from pydantic import BaseModel

from ..api.platform import models
from ..api.platform.instances_gen import InstancesApi
from ..core.errors import NotFoundError
from ..core.fanout import MetroFanoutError, fanout, fanout_collect
from ..core.handle import HandleSteps, Located, MetroTarget, ResourceHandle
from ..core.handle_set import HandleSet
from ..core.http import UNSET, CallOptions, TimeoutOption, Unset, comma_separated
from ..core.metro import MetroEndpoint, MetroScope
from ..core.pagination import Listing, paginate
from ..core.resource import (
    MetroGroup,
    Resource,
    ScopeOptions,
    check_spec,
    list_tagged,
    refs_matching,
)
from ..core.response import Ref, RefLike, describe_ref, matched_entries, or_absent
from ..core.session import Session
from ._shared import (
    at_metro,
    filter_of,
    filters_for,
    options,
    ref_dict,
    resolved,
    scoped,
    tag_first,
)
from .instances import Instance, InstanceHandle, Instances, _ref_of

__all__ = [
    "DeletedTemplate",
    "Template",
    "TemplateHandle",
    "TemplateSet",
    "Templates",
]

T = TypeVar("T")
V = TypeVar("V")

#: Templates are instances in the ``template`` state, and the API reports them
#: under the same payload key as instances.
_KEY = "instances"
_NOUN = "template"
#: How long `prepare` waits for a prepared template to be listed when the
#: caller set no preparation timeout, and how it paces its reads.
_PREPARE_WAIT_SECONDS = 300.0
_PREPARE_POLL_INTERVAL = 0.5
_PREPARE_POLL_MAX_INTERVAL = 3.0

# Named so tests can stand in for it and assert the backoff without waiting.
_sleep = asyncio.sleep


def _within(timeout: float | httpx.Timeout | None, seconds: float) -> httpx.Timeout:
    """The client's timeout with its read bounded by ``seconds``, a second at least."""
    current = timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)
    read = seconds if current.read is None else min(current.read, seconds)
    return httpx.Timeout(
        connect=current.connect, read=max(read, 1.0), write=current.write, pool=current.pool
    )


class Template(models.Instance):
    """An instance template, tagged with the metro that holds it."""

    metro: str


class DeletedTemplate(models.DeleteTemplateInstancesResponseTemplateInstance):
    """What a delete reported, tagged with the metro that served it."""

    metro: str


class TemplateHandle(ResourceHandle[T]):
    """A chainable reference to one template in one metro.

    .. code-block:: python

        tpl = await ukc.templates.get(name="worker")
        web = await ukc.templates.get(name="worker").clone(name="web")
        await ukc.templates.get(name="worker").delete()
    """

    def __init__(self, templates: Templates, steps: HandleSteps[T]) -> None:
        super().__init__(steps)
        self._templates = templates

    def refresh(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> TemplateHandle[Template]:
        """Re-read the template's full details."""
        opts = self._options(headers, base_url, timeout)
        return self._then(lambda target: self._templates.read(target, opts), opts)

    @overload
    def delete(
        self,
        *,
        missing_ok: Literal[False] = False,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> TemplateHandle[DeletedTemplate]: ...

    @overload
    def delete(
        self,
        *,
        missing_ok: Literal[True],
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> TemplateHandle[DeletedTemplate | None]: ...

    def delete(
        self,
        *,
        missing_ok: bool = False,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> TemplateHandle[Any]:
        """Delete the template.

        With ``missing_ok`` a template that is not there resolves to ``None``
        instead of raising :class:`NotFoundError`. Instances cloned from it are
        left alone: they carry their own copy of the snapshot.
        """
        opts = self._options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> DeletedTemplate | None:
            body = [models.NameOrUUID.model_validate(ref_dict(target.ref))]
            try:
                res = await self._templates.api.delete_template_instances(
                    body=body, **at_metro(target, opts)
                )
                return tag_first(res, _KEY, target, DeletedTemplate, _NOUN)
            except NotFoundError as err:
                # The API losing the template is forgiven; a route that is not there is not.
                if not missing_ok or not err.absent:
                    raise
                return None

        steps = self._chained(run, opts)
        if missing_ok:
            steps = replace(steps, absent=lambda: None)
        return TemplateHandle(self._templates, steps)

    def clone(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
        **spec: Any,
    ) -> InstanceHandle[Instance]:
        """Create an instance from this template and return a handle to it.

        The clone is created in the metro that holds the template. ``spec``
        takes what an instance create takes, apart from ``image`` and
        ``template``, which the template already settles: attach ``roms`` for
        per-instance data, ``volumes`` for scratch space, ``schedules``, and
        so on.

        .. code-block:: python

            job = await ukc.templates.get(name="worker").clone(
                roms=[{"name": "job", "at": "/mnt/job", "files": [...]}],
                features=["delete-on-stop"],
            )
        """
        # The clone's own create does its validation and locate step; this
        # handle only supplies the metro and the reference of the template.
        self._consumed = True
        for settled in ("image", "template"):
            if settled in spec:
                raise TypeError(
                    f"`{settled}` is settled by the template a clone is made from; "
                    "drop it from the clone's properties."
                )
        # Checked here, when called, so a misspelled property is a TypeError at
        # once rather than when the handle is awaited, as it is for a create.
        check_spec(spec, models.CreateInstanceRequest, "instance")
        opts = self._options(headers, base_url, timeout)
        instances = self._templates.instances

        async def created() -> Located[Instance]:
            target = await self._next()
            # The clone goes where the template was found: an endpoint discovery
            # reported, which the metro's code alone would not rebuild.
            made = instances.create(
                template=ref_dict(target.ref),
                metros=target.metro,
                headers=opts.get("headers"),
                base_url=opts.get("base_url", target.base_url),
                timeout=opts.get("timeout", UNSET),
                **spec,
            )
            located = await made.resolve()
            if "base_url" not in opts:
                # Sent to a base URL, the create names its metro by it; the
                # metro is the one the template was found in.
                located = replace(located, metro=target.metro)
            return Located(target=located)

        return InstanceHandle(
            instances,
            HandleSteps(
                locate=created,
                fetch=lambda target: instances.read(target, opts),
                what=f"the instance cloned from {self._steps.what}",
                options=opts,
            ),
        )

    def _then(
        self, fetch: Callable[[MetroTarget], Awaitable[V]], opts: CallOptions
    ) -> TemplateHandle[V]:
        """Chain another operation onto this handle."""
        return TemplateHandle(self._templates, self._chained(fetch, opts))


class TemplateSet(HandleSet["TemplateHandle[Template]", Template]):
    """Every template matching one reference, or carrying some tags.

    .. code-block:: python

        await ukc.templates.each(tags=["app=web"]).delete(missing_ok=True)
    """

    async def refresh(self, **opts: Any) -> list[Template]:
        """Re-read every match's full details."""
        return await self._map(lambda handle: handle.refresh(**opts))

    async def delete(self, **opts: Any) -> list[DeletedTemplate]:
        """Delete every match.

        With ``missing_ok``, a match already gone is left out, and a reference
        that matches nothing deletes nothing rather than raising.
        """
        if opts.get("missing_ok") and await self._absent():
            return []
        try:
            deleted = await self._map(lambda handle: handle.delete(**opts))
        except MetroFanoutError as err:
            # The matches already gone are no result of the metros that did delete.
            err.results = [item for item in err.results if item is not None]
            raise
        return [item for item in deleted if item is not None]


class Templates(Resource[InstancesApi]):
    """Idiomatic client for instance templates.

    A template is a snapshotted instance that new instances are cloned from.
    :meth:`prepare` makes one from an ordinary instance specification;
    :meth:`TemplateHandle.clone` stamps instances out of it.
    """

    noun = _NOUN
    key = _KEY

    def __init__(self, session: Session, scope: MetroScope, instances: Instances) -> None:
        super().__init__(session, scope, InstancesApi(session.platform))
        #: The scope's instance client, which clones are created through.
        self.instances = instances

    async def prepare(
        self,
        name: str,
        *,
        create_args: Mapping[str, Any],
        autokill_ms: int | None = None,
        prepare_timeout_seconds: int | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> Template:
        """Make sure a template exists, preparing it from ``create_args`` when it does not.

        ``create_args`` describes the instance that becomes the template, with
        the properties an instance create takes, save that the API types it as
        an instance: its image, or a plugin's, is a plain reference rather than
        an object with a pull policy or credentials, and ``gpus`` is the list
        an instance reports rather than a count. The instance's guest writes
        ``1`` to ``/uk/libukp/template_instance`` once its own initialisation
        is done, and that write takes the snapshot. The call blocks until
        then: for ``prepare_timeout_seconds`` at most when it is positive, and
        otherwise for the bound the platform sets, with the template awaited
        for five minutes at most. A template that already exists is read and
        returned, and nothing else is sent. Like a create, this targets the
        one metro the scope names, where the template is looked for and
        prepared.

        The platform prepares a template as a side effect of cloning it, so this
        creates one stopped clone and deletes it again once the template is
        listed. Should the template never be listed, the clone is left in place
        for inspection and :class:`NotFoundError` is raised. ``autokill_ms``
        deletes the template once nothing has cloned it for that long.

        .. code-block:: python

            tpl = await ukc.metro("fra").templates.prepare(
                "worker-v3",
                create_args={"image": "org/worker:v3", "memory_mb": 1024},
            )
        """
        check_spec(create_args, models.CreateInstanceRequest, "template's source instance")
        # The seed would go to one metro, so that is where the template is
        # looked for: one listed elsewhere is not the one a clone here would use.
        where = (
            await self._one_endpoint(
                "Preparing a template", scoped(options(headers, base_url, timeout), metros)
            )
        ).metro
        # A template that exists needs no seed: one read says so.
        try:
            return await self.get(
                name=name, metros=where, headers=headers, base_url=base_url, timeout=timeout
            )
        except NotFoundError as err:
            # Only its absence is a reason to seed; a route that is not there is not.
            if not err.absent:
                raise
        template: dict[str, Any] = {
            "name": name,
            "prepare": True,
            "create_args": dict(create_args),
        }
        if autokill_ms is not None:
            template["autokill"] = {"time_ms": autokill_ms}
        if prepare_timeout_seconds is not None:
            template["prepare_timeout_s"] = prepare_timeout_seconds
        # The seed carries the source's tags, so one that outlives a failed
        # preparation is still found by whatever cleans the deployment up.
        tags = create_args.get("tags")
        # The create knows it prepares a template, and holds the connection
        # for as long as the platform may take.
        seed = self.instances.create(
            template=template,
            autostart=False,
            metros=where,
            headers=headers,
            base_url=base_url,
            timeout=timeout,
            **({"tags": list(tags)} if tags else {}),
        )
        target = await seed.resolve()
        # The create answers as soon as the clone exists; the template it was
        # prepared from can take a moment longer to be listed. Wait for it
        # before removing the seed clone, so the preparation is never cut short.
        prepared = await self._await_prepared(
            name,
            deadline_seconds=(
                prepare_timeout_seconds
                if prepare_timeout_seconds is not None and prepare_timeout_seconds > 0
                else _PREPARE_WAIT_SECONDS
            ),
            metros=where,
            headers=headers,
            base_url=base_url,
            timeout=timeout,
        )
        await self.instances.get(uuid=target.ref.uuid, name=target.ref.name, metros=where).delete(
            missing_ok=True, headers=headers, base_url=base_url, timeout=timeout
        )
        return prepared

    async def _await_prepared(
        self,
        name: str,
        *,
        deadline_seconds: float,
        metros: MetroScope | None,
        headers: Mapping[str, str] | None,
        base_url: str | None,
        timeout: TimeoutOption,
    ) -> Template:
        """Read the template once it is listed, retrying with backoff until the deadline.

        Each read is bounded by what is left of the deadline, so a read that
        stalls cannot outlive it, and a route that is not there is not waited out.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + deadline_seconds
        interval = _PREPARE_POLL_INTERVAL
        while True:
            remaining = deadline - loop.time()
            bounded = (
                _within(self._session.platform.timeout, remaining)
                if isinstance(timeout, Unset)
                else timeout
            )
            try:
                return await self.get(
                    name=name, metros=metros, headers=headers, base_url=base_url, timeout=bounded
                )
            except NotFoundError as err:
                if not err.absent:
                    raise
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise
            await _sleep(min(interval, remaining))
            interval = min(interval * 2, _PREPARE_POLL_MAX_INTERVAL)

    def get(
        self,
        *,
        uuid: str | None = None,
        name: str | None = None,
        metro: str | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> TemplateHandle[Template]:
        """Reference a single template by ``name`` or ``uuid``."""
        ref = Ref(uuid=uuid, name=name, metro=metro)
        call = options(headers, base_url, timeout)
        opts = scoped(call, metros)
        return TemplateHandle(
            self,
            HandleSteps(
                locate=lambda: self._locate(
                    ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
                ),
                fetch=lambda target: self.read(target, opts),
                what=f"template {describe_ref(ref)}",
                options=call,
                lookup=True,
            ),
        )

    def each(
        self,
        *,
        uuid: str | None = None,
        name: str | None = None,
        tags: Sequence[str] | None = None,
        metro: str | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> TemplateSet:
        """Reference every template matching a name, or every one carrying some tags."""
        call = options(headers, base_url, timeout)
        opts = scoped(call, metros)
        if tags is not None:
            if uuid is not None or name is not None or metro is not None:
                raise TypeError(
                    "`tags` selects templates on its own: drop `uuid`, `name` and `metro`, "
                    "or narrow the metros with `metros`."
                )
            return self._tagged(list(tags), call, opts)
        ref = Ref(uuid=uuid, name=name, metro=metro)

        async def locate() -> builtins.list[TemplateHandle[Template]]:
            located = await self._locate_all(
                ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
            )
            return [
                self._found(hit, f"template {describe_ref(ref)}", call, opts) for hit in located
            ]

        return TemplateSet(locate, f"template {describe_ref(ref)}")

    def _tagged(
        self, tags: builtins.list[str], call: CallOptions, opts: ScopeOptions
    ) -> TemplateSet:
        if not tags:
            raise TypeError(
                "`tags` needs at least one tag: none at all would select every template."
            )
        what = f"templates tagged {', '.join(tags)}"

        async def in_metro(endpoint: MetroEndpoint) -> builtins.list[Located[Template]]:
            found = self._pages(endpoint, opts, details=True, tags=tags, page_size=None)
            return [
                Located(
                    target=MetroTarget(
                        metro=endpoint.metro, base_url=endpoint.base_url, ref=_ref_of(tpl)
                    ),
                    value=tpl,
                )
                async for tpl in found
            ]

        async def locate() -> builtins.list[TemplateHandle[Template]]:
            endpoints = await self._endpoints(opts)
            if len(endpoints) == 1:
                hits = await in_metro(endpoints[0])
            else:
                try:
                    hits = await fanout_collect(endpoints, in_metro)
                except MetroFanoutError as err:
                    # What did arrive is reported as templates, as every other
                    # partial answer is, not as the located matches built here.
                    err.results = [hit.value for hit in err.results]
                    raise
            return [self._found(hit, what, call, opts) for hit in hits]

        return TemplateSet(locate, what)

    def _found(
        self, hit: Located[Template], what: str, call: CallOptions, opts: ScopeOptions
    ) -> TemplateHandle[Template]:
        return TemplateHandle(
            self,
            HandleSteps(
                locate=resolved(hit),
                fetch=lambda target: self.read(target, opts),
                what=what,
                located=True,
                options=call,
            ),
        )

    def list(
        self,
        *,
        details: bool | None = None,
        tags: Sequence[str] | None = None,
        page_size: int | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> Listing[Template]:
        """Lazily iterate every template in scope, or await it for a list."""
        opts = scoped(options(headers, base_url, timeout), metros)

        async def merged() -> AsyncIterator[Template]:
            endpoints = await self._endpoints(opts)

            def per_metro(endpoint: MetroEndpoint) -> AsyncIterator[Template]:
                return self._pages(endpoint, opts, details=details, tags=tags, page_size=page_size)

            async for template in fanout(endpoints, per_metro):
                yield template

        return Listing(merged())

    def _pages(
        self,
        endpoint: MetroEndpoint,
        opts: ScopeOptions,
        *,
        details: bool | None,
        tags: Sequence[str] | None,
        page_size: int | None,
    ) -> AsyncIterator[Template]:
        async def fetch_page(count: int, start: str | None) -> builtins.list[Template]:
            res = await self.api.get_template_instances(
                count=count,
                from_=start,
                details=details,
                tags=comma_separated(tags),
                **self._call(endpoint, opts),
            )
            return list_tagged(res, _KEY, endpoint.metro, Template)

        return paginate(fetch_page, lambda tpl: tpl.uuid, page_size)

    async def delete(
        self,
        refs: RefLike | Sequence[RefLike],
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> builtins.list[DeletedTemplate]:
        """Delete one or more templates."""
        opts = scoped(options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [models.NameOrUUID.model_validate(ref_dict(ref)) for ref in group.refs]
            return self.api.delete_template_instances(body=body, **self._call(group.endpoint, opts))

        return await self._bulk(refs, opts, DeletedTemplate, call)

    async def read(self, target: MetroTarget, opts: CallOptions) -> Template:
        """Read one template's full details from the metro it was located in."""
        uuid, name = filter_of(target.ref)
        res = await self.api.get_template_instances(
            uuid=uuid, name=name, details=True, **self._call(target, opts)
        )
        return tag_first(res, _KEY, target, Template, _NOUN)

    async def _find(self, endpoint: MetroEndpoint, ref: Ref, opts: ScopeOptions) -> Template | None:
        async def lookup() -> Template | None:
            uuid, name = filter_of(ref)
            res = await self.api.get_template_instances(
                uuid=uuid, name=name, details=True, **self._call(endpoint, opts)
            )
            entries = list_tagged(res, _KEY, endpoint.metro, Template)
            return entries[0] if entries else None

        return await or_absent(lookup())

    async def _match(
        self, endpoint: MetroEndpoint, refs: Sequence[Ref], opts: ScopeOptions
    ) -> builtins.list[Ref]:
        async def lookup() -> builtins.list[Ref]:
            uuid, name = filters_for(refs)
            res = await self.api.get_template_instances(
                uuid=uuid, name=name, **self._call(endpoint, opts)
            )
            return refs_matching(refs, matched_entries(res, _KEY))

        return await or_absent(lookup()) or []
