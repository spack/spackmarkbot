# Copyright 2013-2021 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import subprocess
import os

# get configuration from environment.
GIT_REPO_PATH = os.environ.get("SMB_GIT_REPO_PATH")

def git(args):
    """Executes a git command on the host system."""
    result = subprocess.run(
        ["git", "-C", f"{GIT_REPO_PATH}"] + args.split(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True
    )
    return result
