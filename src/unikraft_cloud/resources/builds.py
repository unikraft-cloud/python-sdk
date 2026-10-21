# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Builds on the remote build service: a request names the sources, the
# outputs and a Kraftfile, or no Kraftfile to build the context's Dockerfile
# alone; the build runs on a builder in the caller's own account, and its
# progress can be followed from the start until it ends. The service is
# global, so no metro scope applies. Every source is a git repository or a
# tarball the builder fetches itself: a directory on this machine would need
# a buildkit session, which the service does not take yet.

from __future__ import annotations

import asyncio
import codecs
import contextlib
import json
from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import quote

from pydantic import PrivateAttr, TypeAdapter, ValidationError

from ..api.build import BuildsApi, models
from ..core.errors import UnikraftCloudError
from ..core.http import UNSET, TimeoutOption
from ..core.resource import check_spec
from ..core.session import Session

__all__ = [
    "LOGS_RETRY_BUDGET",
    "LOGS_RETRY_MAX",
    "LOGS_RETRY_MIN",
    "Build",
    "Builds",
    "git_source",
    "image_output",
    "kraftfile_from",
    "url_source",
]

#: The wait before the progress stream is asked for again, in seconds, which
#: doubles on every attempt in a row up to the cap and starts over once an
#: attempt brings a new event.
LOGS_RETRY_MIN = 0.25
LOGS_RETRY_MAX = 5.0
#: How many more times in a row the stream is asked for after an attempt got
#: no stream at all, because the service could not be reached or answered
#: with a 5xx, before :meth:`Builds.logs` gives up.
LOGS_RETRY_BUDGET = 5

# Named so tests can stand in for it and assert the backoff without waiting.
_sleep = asyncio.sleep

_EVENT = TypeAdapter(models.BuildEvent)
_NDJSON = "application/x-ndjson"


def git_source(
    url: str, ref: str | None = None, *, subdir: str | None = None, filename: str | None = None
) -> models.Source:
    """A source that is the git repository at `url`, checked out at `ref`.

    `ref` is a branch, a tag or a commit; omitted, it is the default branch.
    `subdir` narrows the source to a directory of the repository, and
    `filename` points the Kraftfile's source at a file, which defaults to
    ``Kraftfile``, or the ``dockerfile`` context at its Dockerfile. The
    builder clones the repository anonymously.
    """
    return models.Source(**_given(git=url, ref=ref, subdir=subdir, filename=filename))


def url_source(
    url: str, *, subdir: str | None = None, filename: str | None = None
) -> models.Source:
    """A source that is the tarball at `url`, which the builder fetches and unpacks."""
    return models.Source(**_given(url=url, subdir=subdir, filename=filename))


def kraftfile_from(source: models.Source) -> models.Kraftfile:
    """A Kraftfile the service reads out of `source`, from its `filename`.

    Relative paths in the file resolve inside the build context, not inside
    `source`. A `filename` is only valid on the Kraftfile's source and on the
    ``dockerfile`` context; any other context that names one is refused. To
    give the file inline instead, pass ``kraftfile=`` its YAML as a ``str``,
    or the parsed file as a ``dict``.
    """
    return source


def image_output(ref: str) -> models.BuildOutput:
    """An output that pushes the built image to `ref`, tag included, with the caller's token."""
    return models.BuildOutput(image=ref)


def _given(**fields: str | None) -> dict[str, str]:
    """The fields that were given, so a request carries no explicit nulls."""
    return {key: value for key, value in fields.items() if value is not None}


class Build(models.Build):
    """A build, with the operations that take its ID."""

    _builds: Builds = PrivateAttr()

    @classmethod
    def _of(cls, builds: Builds, build: models.Build) -> Build:
        found = cls.model_validate(build.model_dump(by_alias=True, exclude_unset=True))
        found._builds = builds
        return found

    @property
    def _ref(self) -> str:
        if not self.id:
            raise ValueError("This build has no ID, so nothing can be asked about it.")
        return self.id

    async def refresh(self, *, timeout: TimeoutOption = UNSET) -> Build:
        """The build as the service has it now."""
        return await self._builds.get(self._ref, timeout=timeout)

    def logs(self, *, timeout: TimeoutOption = UNSET) -> AsyncGenerator[models.BuildEvent, None]:
        """Follow the build's progress, see :meth:`Builds.logs`."""
        return self._builds.logs(self._ref, timeout=timeout)

    def plain_logs(self, *, timeout: TimeoutOption = UNSET) -> AsyncGenerator[str, None]:
        """Follow the build's progress as text, see :meth:`Builds.plain_logs`."""
        return self._builds.plain_logs(self._ref, timeout=timeout)

    async def cancel(self, *, timeout: TimeoutOption = UNSET) -> Build:
        """Cancel the build, see :meth:`Builds.cancel`."""
        return await self._builds.cancel(self._ref, timeout=timeout)

    async def delete(self, *, timeout: TimeoutOption = UNSET) -> None:
        """Delete the finished build, see :meth:`Builds.delete`."""
        await self._builds.delete(self._ref, timeout=timeout)


class Builds:
    """Builds on the build service, as exposed by ``ukc.builds``.

    The service is global, so ``builds`` hangs off ``ukc`` alone and not off
    a metro scope. Every source is a git repository or a tarball the builder
    fetches itself; a directory on this machine cannot be sent.

    .. code-block:: python

        from unikraft_cloud import git_source, image_output, kraftfile_from

        src = git_source("https://github.com/acme/app.git", "main", subdir="app")
        build = await ukc.builds.create(
            kraftfile=kraftfile_from(src),
            contexts={"context": src},
            output=[image_output("index.unikraft.io/acme/app:1.2.3")],
        )
        async for line in build.plain_logs():
            print(line, end="")
        build = await build.refresh()
    """

    def __init__(self, session: Session) -> None:
        #: The generated plumbing client every operation goes through.
        self.api = BuildsApi(session.build)

    async def create(self, *, timeout: TimeoutOption = UNSET, **spec: Any) -> Build:
        """Create a build from the properties the API describes; it runs whether or not followed.

        Without a ``kraftfile``, the build is the ``Dockerfile`` in the
        ``context`` on the ``base-compat:latest`` runtime, for ``x86_64``.
        A property the API does not describe is a ``TypeError``. The service
        refuses a request that uses a part of the API it does not support yet
        with the code ``unsupported``, and a tenant with as many builds
        running or waiting as it may with ``too_many_builds``; the code is
        ``err.errors[0].code``.
        """
        check_spec(spec, models.CreateBuildRequest, "build")
        request = models.CreateBuildRequest.model_validate(spec)
        return Build._of(self, await self.api.create_build(body=request, timeout=timeout))

    async def get(self, id: str, *, timeout: TimeoutOption = UNSET) -> Build:
        """A build by ID: its state, and its result or error once it has ended."""
        _check(id)
        return Build._of(self, await self.api.get_build(id, timeout=timeout))

    async def list(
        self,
        *,
        status: models.BuildStatus | None = None,
        limit: int | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> list[Build]:
        """The caller's builds, newest first, only those in `status` if given."""
        listed = await self.api.list_builds(status=status, limit=limit, timeout=timeout)
        return [Build._of(self, build) for build in listed.builds or []]

    async def cancel(self, id: str, *, timeout: TimeoutOption = UNSET) -> Build:
        """Cancel a build by ID.

        A waiting or running build becomes ``cancelled`` once buildkit has
        unwound, with its progress ending in an error of that code; a build
        that has already ended is left as it is.
        """
        _check(id)
        return Build._of(self, await self.api.cancel_build(id, timeout=timeout))

    async def delete(self, id: str, *, timeout: TimeoutOption = UNSET) -> None:
        """Delete an ended build by ID: its record and its progress.

        The images it pushed are left alone. A build still waiting or running
        is refused with a 409, the code ``conflict``: cancel it first.
        """
        _check(id)
        await self.api.delete_build(id, timeout=timeout)

    async def logs(
        self, id: str, *, timeout: TimeoutOption = UNSET
    ) -> AsyncGenerator[models.BuildEvent, None]:
        """Follow the progress of a build by ID, every event once, in order.

        The stream ends with the event that says how the build went: its
        ``result``, or its ``error``. The service replays the stream from the
        start on every request, so a stream cut before that event -- by the
        connection, by something between the service and the caller, or by
        `timeout` running out between two events -- is asked for again after
        a short and growing wait, and the events already yielded are skipped.
        A request that gets no stream from the service -- it answers with a
        5xx, or cannot be reached once it has answered before -- is made
        again up to five more times in a row, then given up on with the last
        error. A request the service refuses (a 4xx, such as a build that
        does not exist), an answer that is not a progress stream, an event
        that does not parse, or a service that has not answered at all yet,
        such as a wrong host, is raised at once. A failed build is not an
        error here but the last event, whose ``error`` is set.

        `timeout` bounds each wait for more of the stream, not the whole
        follow: a build quiet for longer is asked for again, which replays it.

        Close the iterator to stop early and release the connection at once,
        with ``contextlib.aclosing`` or its ``aclose()``.
        """
        _check(id)
        seen = 0  # the lines yielded so far, which a replay skips
        answered = False  # the service has answered once, so it is there
        failed = 0  # the attempts in a row that got no stream at all
        idle = 0  # the attempts in a row that brought no new event
        while True:
            yielded = 0
            try:
                async with contextlib.aclosing(self._follow(id, seen, timeout)) as events:
                    async for event in events:
                        yielded += 1
                        yield event
                        if _done(event):
                            return
                # The stream ended before its last event.
                answered, no_stream = True, False
            except _CutError:
                answered, no_stream = True, False
            except UnikraftCloudError as err:
                if err.status is not None and err.status >= 500:
                    answered = True  # The service is there, and could not answer.
                elif err.kind == "network" and answered and err.__cause__ is not None:
                    pass  # No answer from a service that answered before.
                else:
                    # Refused, even by an answer that broke off; not a stream;
                    # or a service that never answered. A closed client has no
                    # cause, and is not coming back.
                    raise
                no_stream = True
                failed += 1
                if failed > LOGS_RETRY_BUDGET:
                    raise type(err)(
                        f"Giving up on the progress stream after {failed} attempts: {err}",
                        kind=err.kind,
                        status=err.status,
                        errors=err.errors,
                        body=err.body,
                    ) from err
            seen += yielded
            if not no_stream:
                failed = 0
            if yielded > 0:
                idle = 0
            wait = min(LOGS_RETRY_MIN * 2**idle, LOGS_RETRY_MAX)
            if wait < LOGS_RETRY_MAX:
                idle += 1
            await _sleep(wait)

    async def _follow(
        self, id: str, seen: int, timeout: TimeoutOption
    ) -> AsyncGenerator[models.BuildEvent, None]:
        """Request the stream once, skipping its first `seen` lines.

        A last event is never skipped: a service that restarted replays a
        shorter stream that ends in an error. A stream that breaks off or
        ends mid-line once the service has answered was cut, and raises
        :class:`_CutError`.
        """
        chunks = self.api.stream_bytes(
            method="GET",
            path=f"/v1/builds/{quote(id, safe='')}/logs",
            headers={"accept": _NDJSON},
            timeout=timeout,
            media_type=_NDJSON,
        )
        buffer = b""
        line = 0
        try:
            async with contextlib.aclosing(chunks):
                async for chunk in chunks:
                    buffer += chunk
                    while (end := buffer.find(b"\n")) >= 0:
                        raw, buffer = buffer[:end].strip(), buffer[end + 1 :]
                        if not raw:
                            continue
                        line += 1
                        event = _parse(raw, line)
                        if line <= seen and not _done(event):
                            continue
                        yield event
                        if _done(event):
                            return
        except UnikraftCloudError as err:
            # A network error that carries a status failed in the body of a
            # stream the service had started; one without never got that far.
            if err.kind == "network" and err.status is not None and err.status < 300:
                raise _CutError from err
            raise
        if buffer.strip():
            raise _CutError

    async def plain_logs(
        self, id: str, *, timeout: TimeoutOption = UNSET
    ) -> AsyncGenerator[str, None]:
        """Follow the progress of a build by ID as text, as the service renders it.

        The text is the one ``docker buildx build --progress=plain`` prints,
        then a ``pushed <ref>@<digest>`` line per image the build pushed, or
        an ``error: ...`` line when it failed. The service renders the text
        again from the start on every request, so unlike :meth:`logs` this
        asks only once: a stream the service breaks off on its side ends the
        text with ``error: the stream ended before the build did: ask for it
        again``, and one cut on the way, or by `timeout` running out while
        waiting for more, is raised. Either way the build goes on, and :meth:`get`
        says whether it still runs.
        """
        _check(id)
        chunks = self.api.stream_bytes(
            method="GET",
            path=f"/v1/builds/{quote(id, safe='')}/logs",
            headers={"accept": "text/plain"},
            timeout=timeout,
            media_type="text/plain",
        )
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        async with contextlib.aclosing(chunks):
            async for chunk in chunks:
                if text := decoder.decode(chunk):
                    yield text
        if text := decoder.decode(b"", final=True):
            yield text


class _CutError(Exception):
    """The progress stream broke off or ended mid-line: it was cut."""


def _check(id: str) -> None:
    """Refuse an ID the request path would resolve away, or that would add a segment."""
    if id in ("", ".", "..") or "/" in id:
        raise ValueError(f"A build ID is one segment of a path; got {id!r}.")


def _done(event: models.BuildEvent) -> bool:
    return event.result is not None or event.error is not None


def _parse(raw: bytes, line: int) -> models.BuildEvent:
    """Decode one line of the stream, dropping the nulls buildkit leaves in its lists."""
    try:
        return _EVENT.validate_python(_without_nulls(json.loads(raw)))
    except (ValueError, ValidationError) as cause:
        raise UnikraftCloudError(
            f"Line {line} of the progress stream did not match the specification: {cause}",
            kind="parse",
            body=raw,
        ) from cause


def _without_nulls(data: Any) -> Any:
    """`data` with the nulls dropped from every list in it, however deep."""
    if isinstance(data, list):
        return [_without_nulls(item) for item in data if item is not None]
    if isinstance(data, dict):
        return {key: _without_nulls(value) for key, value in data.items()}
    return data
