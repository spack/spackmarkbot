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

from .github import github
from .gitlab import gitlab

# Get configuration from environment
GIT_REPO_PATH = os.environ.get("SMB_GIT_REPO_PATH")
GH_REPO = os.environ.get("SMB_GH_REPO")
GL_REPO = os.environ.get("SMB_GL_REPO")
PORT = os.environ.get("SMB_PORT")


async def main(request):
    # route request to github or gitlab submodule based on event type header
    if "x-github-event" in request.headers:
        await github(request)
    elif "x-gitlab-event" in request.headers:
        await gitlab(request)
    else:
        return web.Response(status=404)


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
