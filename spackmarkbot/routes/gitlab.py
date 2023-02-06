# Copyright 2013-2021 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
import os
import re
from typing import Any

from gidgetlab import routing
from gidgetlab import sansio

GH_REPO = os.environ.get("SMB_GH_REPO")
GH_CHECK_NAME = os.environ.get("SMB_GH_CHECK_NAME")


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

        found_callbacks = []
        try:
            found_callbacks.extend(self._shallow_routes[event.event])
        except KeyError:
            pass
        try:
            details = self._deep_routes[event.event]
        except KeyError:
            pass
        else:
            for data_key, data_values in details.items():
                if data_key in event.object_attributes:
                    event_value = event.object_attributes[data_key]
                    if event_value in data_values:
                        found_callbacks.extend(data_values[event_value])
        for callback in found_callbacks:
            await callback(event, *args, **kwargs)


router = SpackmarkRouter()

# set owner & repo values from config
owner = re.search("(?<=\:)[^\/]*", GH_REPO, re.IGNORECASE).group()
repo = re.search("(?<=\/)[^.]*", GH_REPO, re.IGNORECASE).group()


@router.register("Pipeline Hook", status="pending")
@router.register("Pipeline Hook", status="running")
@router.register("Pipeline Hook", status="success")
@router.register("Pipeline Hook", status="failed")
async def opened_issue(event, gh, gl, *arg, **kwargs):
    """Relay status of a GitLab pipeline back to GitHub."""
    # get ref from event
    ref = event.data["object_attributes"]["sha"]

    # get status from event
    ci_status = event.data["object_attributes"]["status"]

    # construct upload payload
    payload = {
        "name": GH_CHECK_NAME,
        "head_sha": ref,
    }

    if ci_status == "pending":
        payload["status"] = "queued"
    elif ci_status == "running":
        payload["status"] = "in_progress"
    elif ci_status == "success":
        payload["status"] = "completed"
        payload["conclusion"] = "success"
    else:
        payload["status"] = "completed"
        payload["conclusion"] = "failure"

    # get a list of the checks on a commit
    url = f"/repos/{owner}/{repo}/commits/{ref}/check-runs"
    data = await gh.getitem(url)

    # search for existing check with GH_CHECK_NAME
    check_id = None
    for check in data["check_runs"]:
        if check["name"] == GH_CHECK_NAME:
            check_id = check["id"]
            break

    if check_id is None:
        url = f"/repos/{owner}/{repo}/check-runs"
        await gh.post(url, data=payload)
    else:
        url = f"/repos/{owner}/{repo}/check-runs/{check_id}"
        await gh.patch(url, data=payload)
