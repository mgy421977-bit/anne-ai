"""CLI entry points for ANNE Dropbox integration."""

from __future__ import annotations

import argparse
from pathlib import Path

from anne.cloud.dropbox import DropboxConfig, DropboxKnowledgeAdapter


def authorize() -> None:
    """Authorize the local ANNE runtime against Dropbox."""

    result = DropboxKnowledgeAdapter.authorize(DropboxConfig.from_env())
    print(f"Dropbox authorized: {result['account_id']}")
    print(f"Credential: {result['token_path']}")


def pull() -> None:
    """Pull matching Dropbox files into a local ANNE knowledge directory."""

    parser = argparse.ArgumentParser(description="Pull files from ANNE's Dropbox knowledge root")
    parser.add_argument("query", help="Filename/path text to search for")
    parser.add_argument(
        "--destination",
        default="./anne-cloud",
        help="Local destination directory (default: ./anne-cloud)",
    )
    args = parser.parse_args()

    adapter = DropboxKnowledgeAdapter.connect()
    paths = adapter.pull(args.query, Path(args.destination))
    if not paths:
        print("No matching Dropbox files found.")
        return
    for path in paths:
        print(path)


if __name__ == "__main__":
    pull()
