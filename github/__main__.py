# Copyright 2013-2021 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import asyncio
import importlib
import os
import sys
import traceback

import aiohttp
from aiohttp import web
from gidgethub import aiohttp as gh_aiohttp
from gidgethub import routing
from gidgethub import sansio

from .auth import authenticate_installation
from .routes import router
from .utils import git

# Get configuration from environment
GIT_REPO_PATH = os.environ.get("SMB_GIT_REPO_PATH")
GH_REPO = os.environ.get("SMB_GH_REPO")
GH_SECRET = os.environ.get("SMB_GH_SECRET")
GH_REQUESTER = os.environ.get("SMB_GH_REQUESTER")
GL_REPO = os.environ.get("SMB_GL_REPO")
PORT = os.environ.get("SMB_PORT")


async def main(request):
    try:
        # read the GitHub webhook payload
        body = await request.read()

        event = sansio.Event.from_http(request.headers, body, secret=GH_SECRET)
        print("GH delivery ID", event.delivery_id, file=sys.stderr)

        # extract installation_id from request
        installation_id = event.data["installation"]["id"]

        # retrieve GitHub authentication token
        token = await authenticate_installation(installation_id)

        dispatch_kwargs = {
            "token": token,
        }

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, GH_REQUESTER, oauth_token=token)

            # call the appropriate callback for the event
            await router.dispatch(event, gh, session=session, **dispatch_kwargs)

        # return a "Success"
        return web.Response(status=200)

    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        return web.Response(status=500)


if __name__ == "__main__":
    print("Initializing Spackmarkbot ...")
    print("Configuring Git Repository ...")
    if not os.path.exists(GIT_REPO_PATH):
        os.makedirs(GIT_REPO_PATH)
        git("init")
        git(f"remote add github {GH_REPO}")
        git(f"remote add gitlab {GL_REPO}")

    print("Starting Web Server...")
    app = web.Application()
    app.router.add_post("/", main)
    if PORT is not None:
        PORT = int(PORT)

    web.run_app(app, port=PORT)
