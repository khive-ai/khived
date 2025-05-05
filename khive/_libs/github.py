import os
from pathlib import Path

import requests


class GithubUtils:

    @staticmethod
    def download_github_repo(
        owner: str,
        repo: str,
        ref: str = "main",
        dest_dir: str | None = None,
        token: str | None = None,
        timeout: int = 30,
    ) -> Path:
        """Download a GitHub repository as a zip file. return the path to the zip file."""
        # Build API request
        api = f"https://api.github.com/repos/{owner}/{repo}/zipball/{ref}"
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        dest_dir = dest_dir or os.getcwd()
        os.makedirs(dest_dir, exist_ok=True)
        archive_path = os.path.join(dest_dir, f"{repo}-{ref}.zip")

        with requests.get(
            api,
            headers=headers,
            stream=True,
            timeout=timeout,
            allow_redirects=True,
        ) as r:
            r.raise_for_status()
            with open(archive_path, "wb") as fp:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        fp.write(chunk)

        return Path(archive_path)
