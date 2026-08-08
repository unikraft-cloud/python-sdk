# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

from __future__ import annotations

from collections.abc import Mapping

from ..api.platform import models
from ..api.platform.users_gen import UsersApi
from ..core.fanout import MetroFailure, fanout_error, fanout_settled
from ..core.http import UNSET, TimeoutOption
from ..core.metro import MetroEndpoint, MetroScope
from ..core.resource import Resource, list_tagged
from ..core.session import Session
from ._shared import options, scoped

__all__ = ["Quotas", "Users"]

_KEY = "quotas"


class Quotas(models.Quotas):
    """One metro's quotas and usage, tagged with the metro that served it."""

    metro: str


class Users(Resource[UsersApi]):
    """Idiomatic client for the account's users and quotas."""

    noun = "user"

    def __init__(self, session: Session, scope: MetroScope) -> None:
        super().__init__(session, scope, UsersApi(session.platform))

    async def quotas(
        self,
        *,
        metros: MetroScope | None = None,
        headers: Mapping[str, str] | None = None,
        base_url: str | None = None,
        timeout: TimeoutOption = UNSET,
    ) -> list[Quotas]:
        """Quotas and usage for every metro in scope.

        Quotas are per-metro, so an account-wide view means asking each one and
        collecting the answers.

        .. code-block:: python

            for quota in await ukc.users.quotas():
                print(quota.metro, quota.used, quota.hard)
        """
        opts = scoped(options(headers, base_url, timeout), metros)
        endpoints = await self._endpoints(opts)

        async def per_metro(endpoint: MetroEndpoint) -> list[Quotas]:
            res = await self.api.get_user(**self._call(endpoint, opts))
            return list_tagged(res, _KEY, endpoint.metro, Quotas)

        if len(endpoints) == 1:
            return await per_metro(endpoints[0])

        outcomes = await fanout_settled(endpoints, per_metro)
        quotas: list[Quotas] = []
        failures: list[MetroFailure] = []
        for outcome in outcomes:
            if outcome.ok:
                quotas.extend(outcome.value)
            else:
                failures.append(MetroFailure(metro=outcome.endpoint.metro, error=outcome.error))
        if failures:
            error = fanout_error(len(endpoints), failures)
            # A partial answer is still an answer; carry what did arrive.
            error.results = list(quotas)
            raise error
        return quotas
