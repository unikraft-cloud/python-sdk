# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

from __future__ import annotations

# `Certificates.list` shadows the builtin inside that class body, so annotations
# there spell the builtin out.
import builtins
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel

from ..api.platform import models
from ..api.platform.certificates_gen import CertificatesApi
from ..core.fanout import fanout
from ..core.handle import HandleSteps, Located, MetroTarget, ResourceHandle
from ..core.handle_set import HandleSet
from ..core.http import UNSET, CallOptions, TimeoutOption
from ..core.metro import MetroEndpoint, MetroScope
from ..core.pagination import paginate
from ..core.resource import MetroGroup, Resource, ScopeOptions, first_tagged, list_tagged
from ..core.response import Ref, RefLike, describe_ref, or_absent, to_refs
from ..core.session import Session
from ._shared import at_metro, filter_of, options, ref_dict, resolved, scoped, tag_first

__all__ = [
    "Certificate",
    "CertificateHandle",
    "CertificateSet",
    "Certificates",
    "DeletedCertificate",
]

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)
V = TypeVar("V")

_KEY = "certificates"
_NOUN = "certificate"


class Certificate(models.Certificate):
    """A TLS certificate, tagged with the metro that served it."""

    metro: str


class DeletedCertificate(models.DeleteCertificatesResponseDeletedCertificate):
    """What a delete reported, tagged with the metro that served it."""

    metro: str


class CertificateHandle(ResourceHandle[T]):
    """A chainable reference to one certificate in one metro."""

    def __init__(self, certificates: Certificates, steps: HandleSteps[T]) -> None:
        super().__init__(steps)
        self._certificates = certificates

    def refresh(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> CertificateHandle[Certificate]:
        """Re-read the certificate's full details."""
        opts = options(headers, base_url, timeout)
        return self._then(lambda target: self._certificates.read(target, opts))

    def delete(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> CertificateHandle[DeletedCertificate]:
        """Delete the certificate."""
        opts = options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> DeletedCertificate:
            body = [models.NameOrUUID.model_validate(ref_dict(target.ref))]
            res = await self._certificates.api.delete_certificates(
                body=body, **at_metro(target, opts)
            )
            return tag_first(res, _KEY, target, DeletedCertificate, _NOUN)

        return self._then(run)

    def update(
        self,
        *,
        chain: str,
        pkey: str,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> CertificateHandle[Certificate]:
        """Replace the certificate's chain and private key.

        Unlike the other resources, a certificate is not updated property by
        property: the API takes the new material as a whole.
        """
        opts = options(headers, base_url, timeout)

        async def run(target: MetroTarget) -> Certificate:
            body = [
                models.UpdateCertificatesRequestItem.model_validate(
                    {**ref_dict(target.ref), "chain": chain, "pkey": pkey}
                )
            ]
            res = await self._certificates.api.update_certificates(
                body=body, **at_metro(target, opts)
            )
            return tag_first(res, _KEY, target, Certificate, _NOUN)

        return self._then(run)

    def _then(self, fetch: Callable[[MetroTarget], Awaitable[V]]) -> CertificateHandle[V]:
        return CertificateHandle(self._certificates, self._chained(fetch))


class CertificateSet(HandleSet["CertificateHandle[Certificate]", Certificate]):
    """Every certificate matching one reference, one per metro that holds it."""

    async def refresh(self, **opts: Any) -> list[Certificate]:
        """Re-read every match's full details."""
        return await self._map(lambda handle: handle.refresh(**opts))

    async def delete(self, **opts: Any) -> list[DeletedCertificate]:
        """Delete every match."""
        return await self._map(lambda handle: handle.delete(**opts))

    async def update(self, **opts: Any) -> list[Certificate]:
        """Replace the material on every match."""
        return await self._map(lambda handle: handle.update(**opts))


class Certificates(Resource[CertificatesApi]):
    """Idiomatic client for Unikraft Cloud TLS certificates."""

    noun = _NOUN

    def __init__(self, session: Session, scope: MetroScope) -> None:
        super().__init__(session, scope, CertificatesApi(session.platform))

    def create(
        self,
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
        **spec: Any,
    ) -> CertificateHandle[Certificate]:
        """Create a certificate and return a handle to it."""
        opts = scoped(options(headers, base_url, timeout), metros)
        body = models.CreateCertificateRequest.model_validate(spec)

        async def created() -> Located[Certificate]:
            endpoint = await self._one_endpoint("Creating a certificate", opts)
            res = await self.api.create_certificate(body=body, **self._call(endpoint, opts))
            certificate = first_tagged(res, _KEY, endpoint.metro, Certificate, _NOUN)
            ref = Ref(uuid=certificate.uuid) if certificate.uuid else Ref(name=certificate.name)
            target = MetroTarget(metro=endpoint.metro, base_url=endpoint.base_url, ref=ref)
            return Located(target=target, value=certificate)

        return CertificateHandle(
            self,
            HandleSteps(
                locate=created,
                fetch=lambda target: self.read(target, opts),
                what="the certificate being created",
            ),
        )

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
    ) -> CertificateHandle[Certificate]:
        """Reference a single certificate by ``name`` or ``uuid``."""
        ref = Ref(uuid=uuid, name=name, metro=metro)
        opts = scoped(options(headers, base_url, timeout), metros)
        return CertificateHandle(
            self,
            HandleSteps(
                locate=lambda: self._locate(
                    ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
                ),
                fetch=lambda target: self.read(target, opts),
                what=f"certificate {describe_ref(ref)}",
            ),
        )

    def each(
        self,
        *,
        uuid: str | None = None,
        name: str | None = None,
        metro: str | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> CertificateSet:
        """Reference every certificate matching a name -- one per metro."""
        ref = Ref(uuid=uuid, name=name, metro=metro)
        opts = scoped(options(headers, base_url, timeout), metros)

        async def locate() -> builtins.list[CertificateHandle[Certificate]]:
            located = await self._locate_all(
                ref, opts, lambda endpoint: self._find(endpoint, ref, opts)
            )
            return [
                CertificateHandle(
                    self,
                    HandleSteps(
                        locate=resolved(hit),
                        fetch=lambda target: self.read(target, opts),
                        what=f"certificate {describe_ref(ref)}",
                    ),
                )
                for hit in located
            ]

        return CertificateSet(locate)

    def list(
        self,
        *,
        details: bool | None = None,
        page_size: int | None = None,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> AsyncIterator[Certificate]:
        """Lazily iterate every certificate in scope, merging the metros."""
        opts = scoped(options(headers, base_url, timeout), metros)

        async def merged() -> AsyncIterator[Certificate]:
            endpoints = await self._endpoints(opts)

            def per_metro(endpoint: MetroEndpoint) -> AsyncIterator[Certificate]:
                async def fetch_page(count: int, start: str | None) -> builtins.list[Certificate]:
                    res = await self.api.get_certificates(
                        count=count,
                        from_=start,
                        details=details,
                        **self._call(endpoint, opts),
                    )
                    return list_tagged(res, _KEY, endpoint.metro, Certificate)

                return paginate(fetch_page, lambda cert: cert.uuid, page_size)

            async for certificate in fanout(endpoints, per_metro):
                yield certificate

        return merged()

    async def delete(
        self,
        refs: RefLike | Sequence[RefLike],
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> builtins.list[DeletedCertificate]:
        """Delete one or more certificates."""
        opts = scoped(options(headers, base_url, timeout), metros)

        def call(group: MetroGroup) -> Awaitable[BaseModel]:
            body = [models.NameOrUUID.model_validate(ref_dict(ref)) for ref in group.refs]
            return self.api.delete_certificates(body=body, **self._call(group.endpoint, opts))

        return await self._bulk(refs, opts, DeletedCertificate, call)

    async def read(self, target: MetroTarget, opts: CallOptions) -> Certificate:
        """Read one certificate's full details from the metro it was located in."""
        uuid, name = filter_of(target.ref)
        res = await self.api.get_certificates(
            uuid=uuid, name=name, details=True, **self._call(target, opts)
        )
        return tag_first(res, _KEY, target, Certificate, _NOUN)

    async def _find(
        self, endpoint: MetroEndpoint, ref: Ref, opts: ScopeOptions
    ) -> Certificate | None:
        async def lookup() -> Certificate | None:
            uuid, name = filter_of(ref)
            res = await self.api.get_certificates(
                uuid=uuid, name=name, details=True, **self._call(endpoint, opts)
            )
            entries = list_tagged(res, _KEY, endpoint.metro, Certificate)
            return entries[0] if entries else None

        return await or_absent(lookup())

    async def _bulk(
        self,
        refs: RefLike | Sequence[RefLike],
        opts: ScopeOptions,
        cls: type[M],
        each: Callable[[MetroGroup], Awaitable[BaseModel]],
    ) -> builtins.list[M]:
        groups = await self._group_by_metro(
            to_refs(refs), opts, lambda endpoint, ref: self._find(endpoint, ref, opts)
        )

        async def run(group: MetroGroup) -> builtins.list[M]:
            return list_tagged(await each(group), _KEY, group.endpoint.metro, cls)

        return await self._run_groups(groups, run)
