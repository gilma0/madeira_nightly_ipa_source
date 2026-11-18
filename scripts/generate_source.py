#!/usr/bin/env python3
"""Publish the nightly releases using version metadata from their actual IPAs."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import tempfile
from urllib.request import Request, urlopen
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "camhoc/Madeira"
NIGHTLY_ASSET = re.compile(r"Madeira[._ -]+Nightly(?:[._ -].*)?\.ipa", re.IGNORECASE)
CACHE_PATH = ROOT / "ipa-metadata.json"
USER_AGENT = "madeira-nightly-source"


def fetch_releases():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=100"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def read_ipa_metadata(ipa):
    with ZipFile(ipa) as archive:
        plists = []
        for name in archive.namelist():
            path = PurePosixPath(name)
            if (len(path.parts) == 3 and path.parts[0] == "Payload"
                    and path.parts[1].endswith(".app") and path.name == "Info.plist"):
                plists.append(name)
        if len(plists) != 1:
            raise ValueError("Expected one top-level app Info.plist in the IPA")
        info = plistlib.loads(archive.read(plists[0]))

    metadata = {
        "bundleIdentifier": info["CFBundleIdentifier"],
        "version": info["CFBundleShortVersionString"],
        "buildVersion": info["CFBundleVersion"],
        "minOSVersion": info["MinimumOSVersion"],
    }
    if not all(isinstance(value, str) and value.strip() for value in metadata.values()):
        raise ValueError("IPA has invalid app metadata")
    return metadata


def download_metadata(asset):
    print(f"Reading {asset['name']}", flush=True)
    expected_size = asset["size"]
    request = Request(asset["browser_download_url"], headers={"User-Agent": USER_AGENT})
    checksum = hashlib.sha256()
    size = 0
    with tempfile.TemporaryFile() as ipa:
        with urlopen(request, timeout=60) as response:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > expected_size:
                    raise ValueError(f"{asset['name']} exceeds its release asset size")
                checksum.update(chunk)
                ipa.write(chunk)
        if size != expected_size or f"sha256:{checksum.hexdigest()}" != asset["digest"]:
            raise ValueError(f"{asset['name']} does not match its release asset size or checksum")
        return read_ipa_metadata(ipa)


def build_source(config, releases, cached_metadata):
    app = {**config["app"], "iconURL": config["iconURL"]}
    versions = []
    metadata_cache = {}
    seen_versions = set()
    releases = sorted(releases, key=lambda release: release.get("published_at") or "", reverse=True)
    for release in releases:
        if release.get("draft") or not release.get("published_at"):
            continue
        asset = next((item for item in release["assets"]
                      if NIGHTLY_ASSET.fullmatch(item["name"])), None)
        if asset is None:
            continue

        digest = asset.get("digest") or ""
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
            raise ValueError(f"No SHA-256 digest for {asset['name']}")
        metadata = cached_metadata.get(digest) or download_metadata(asset)
        if metadata["bundleIdentifier"] != app["bundleIdentifier"]:
            raise ValueError(f"Unexpected bundle identifier in {asset['name']}")
        metadata_cache[digest] = metadata

        identity = (metadata["version"], metadata["buildVersion"])
        if identity in seen_versions:
            continue
        seen_versions.add(identity)
        versions.append({
            "version": metadata["version"],
            "buildVersion": metadata["buildVersion"],
            "marketingVersion": release["tag_name"].removeprefix("v"),
            "date": release["published_at"],
            "downloadURL": asset["browser_download_url"],
            "size": asset["size"],
            "minOSVersion": metadata["minOSVersion"],
        })

    if not versions:
        raise ValueError("No nightly IPAs found. Keeping the current source.")
    app["versions"] = versions
    source = {key: value for key, value in config.items() if key != "app"}
    return {**source, "apps": [app]}, metadata_cache


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    source, metadata_cache = build_source(config, fetch_releases(), cache)
    write_json(ROOT / "source.json", source)
    write_json(CACHE_PATH, metadata_cache)
    print(f"Published metadata for {len(source['apps'][0]['versions'])} nightly build(s)")


if __name__ == "__main__":
    main()
