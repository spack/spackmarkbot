# Copyright 2013-2021 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
import asyncio
from typing import Any

from gidgethub import routing
from gidgethub import sansio

from ..utils.git import git


class SpackmarkRouter(routing.Router):

    """
    Custom router to handle common interactions for spackmarkbot
    """

    async def dispatch(self, event: sansio.Event, *args: Any, **kwargs: Any) -> None:
        """Dispatch an event to all registered function(s)."""

        # for all endpoints, spackmark should not respond to himself!
        if "comment" in event.data and re.search(
            helpers.alias_regex, event.data["comment"]["user"]["login"]
        ):
            return

        found_callbacks = self.fetch(event)
        for callback in found_callbacks:
            await callback(event, *args, **kwargs)


router = SpackmarkRouter()
repo_lock = asyncio.Lock()


@router.register("pull_request", action="opened")
@router.register("pull_request", action="reopened")
@router.register("pull_request", action="synchronize")
async def sync_pr(event, gh, *arg, **kwargs):
    """Sync the git fork/branch referenced in a PR to GitLab."""
    pull_request = event.data["pull_request"]
    pull_request_id = pull_request["number"]
    await repo_lock.acquire()
    try:
        git(f"fetch github pull/{pull_request_id}/head")
        git(f"push gitlab FETCH_HEAD:refs/heads/pr-{pull_request_id}")
    finally:
        repo_lock.release()

@router.register("pull_request", action="closed")
async def remove_pr(event, gh, *arg, **kwargs):
    pull_request = event.data["pull_request"]
    pull_request_id = pull_request["number"]
    await repo_lock.acquire()
    try:
        git(f"push -d gitlab refs/heads/pr-{pull_request_id}")
    finally:
        repo_lock.release()
