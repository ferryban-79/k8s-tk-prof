#!/usr/bin/env python3
"""
update_links.py — Input_Links folder ko GitHub repo mein sync karo.

HOW TO USE:
  Apni local Input_Links/ folder mein nayi .txt files rakh do,
  phir bas yeh chalao:
      python update_links.py

  Script khud:
    ✅ GitHub se current files list karegi
    ✅ Nayi/updated files upload karegi
    ✅ Jo local mein nahi hain unhe GitHub se delete karegi

FIRST TIME SETUP:
  1. GitHub Personal Access Token banao:
     GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
     Permissions: repo (full)
  2. Neeche GITHUB_TOKEN, REPO_OWNER, REPO_NAME fill karo
     Ya environment variables set karo (recommended for security):
       Windows: set GITHUB_TOKEN=ghp_xxxx
       Mac/Linux: export GITHUB_TOKEN=ghp_xxxx

SAFE TO RUN:
  - Roz multiple baar run karo — GitHub API rate limit 5000 req/hour hai
  - 5-10 files × 2 calls each = 10-20 calls — bilkul safe
  - Sirf changed files upload hoti hain (SHA check se)
"""

import os
import sys
import json
import base64
import hashlib
import glob
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ 'requests' package nahi mila. Install karo:")
    print("   pip install requests")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# CONFIG — Yahan apni details bharo
# Ya environment variables use karo (zyada safe)
# ─────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")          # ghp_xxxxxxxxxxxx
REPO_OWNER   = os.environ.get("GITHUB_OWNER", "")          # aapka GitHub username
REPO_NAME    = os.environ.get("GITHUB_REPO",  "")          # repo ka naam
BRANCH       = os.environ.get("GITHUB_BRANCH", "main")     # branch (usually main or master)
REMOTE_DIR   = "Input_Links"                                # GitHub mein folder path

# Local folder — script ke sath waale directory mein Input_Links/
LOCAL_DIR = Path(__file__).parent / "Input_Links"
# ─────────────────────────────────────────────────────────────


def get_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }


def validate_config():
    errors = []
    if not GITHUB_TOKEN:
        errors.append("GITHUB_TOKEN — GitHub Personal Access Token set nahi hai")
    if not REPO_OWNER:
        errors.append("GITHUB_OWNER — aapka GitHub username set nahi hai")
    if not REPO_NAME:
        errors.append("GITHUB_REPO — repo name set nahi hai")
    if errors:
        print("❌ Configuration missing:")
        for e in errors:
            print(f"   • {e}")
        print("\n   Environment variables set karo:")
        print("     Windows:")
        print("       set GITHUB_TOKEN=ghp_your_token_here")
        print("       set GITHUB_OWNER=your_username")
        print("       set GITHUB_REPO=your_repo_name")
        print("     Mac/Linux:")
        print("       export GITHUB_TOKEN=ghp_your_token_here")
        print("       export GITHUB_OWNER=your_username")
        print("       export GITHUB_REPO=your_repo_name")
        sys.exit(1)


def get_remote_files() -> dict:
    """GitHub se Input_Links/ mein existing files ki list aur SHA lao."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{REMOTE_DIR}"
    params = {"ref": BRANCH}
    resp = requests.get(url, headers=get_headers(), params=params)

    if resp.status_code == 404:
        # Folder exist nahi karta — pehli baar
        return {}
    if resp.status_code != 200:
        print(f"❌ GitHub API error ({resp.status_code}): {resp.text[:200]}")
        sys.exit(1)

    files = {}
    for item in resp.json():
        if item["type"] == "file" and item["name"].endswith(".txt"):
            files[item["name"]] = item["sha"]
    return files


def file_sha(content_bytes: bytes) -> str:
    """GitHub ki tarah SHA calculate karo (blob sha)."""
    header = f"blob {len(content_bytes)}\0".encode()
    return hashlib.sha1(header + content_bytes).hexdigest()


def upload_file(filename: str, content_bytes: bytes, existing_sha: str = None):
    """File upload ya update karo GitHub par."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{REMOTE_DIR}/{filename}"
    data = {
        "message": f"🔄 Update Input_Links/{filename}",
        "content": base64.b64encode(content_bytes).decode(),
        "branch":  BRANCH,
    }
    if existing_sha:
        data["sha"] = existing_sha  # update ke liye existing SHA chahiye

    resp = requests.put(url, headers=get_headers(), data=json.dumps(data))
    if resp.status_code in (200, 201):
        action = "Updated" if existing_sha else "Uploaded"
        print(f"   ✅ {action}: {filename}")
        return True
    else:
        print(f"   ❌ Failed ({resp.status_code}): {filename} — {resp.text[:150]}")
        return False


def delete_file(filename: str, sha: str):
    """GitHub se file delete karo."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{REMOTE_DIR}/{filename}"
    data = {
        "message": f"🗑️ Remove Input_Links/{filename}",
        "sha":     sha,
        "branch":  BRANCH,
    }
    resp = requests.delete(url, headers=get_headers(), data=json.dumps(data))
    if resp.status_code == 200:
        print(f"   🗑️ Deleted: {filename}")
        return True
    else:
        print(f"   ❌ Delete failed ({resp.status_code}): {filename} — {resp.text[:150]}")
        return False


def main():
    print("=" * 55)
    print("  Input_Links GitHub Sync Tool")
    print("=" * 55)

    validate_config()

    if not LOCAL_DIR.exists():
        print(f"❌ Local folder not found: {LOCAL_DIR}")
        print(f"   Create it and add your .txt files there.")
        sys.exit(1)

    local_files = {f.name: f for f in LOCAL_DIR.glob("*.txt")}

    if not local_files:
        print(f"⚠️ No .txt files found in {LOCAL_DIR}")
        sys.exit(0)

    print(f"\n📂 Local files  ({len(local_files)}): {', '.join(sorted(local_files.keys()))}")
    print(f"🔗 Repo: https://github.com/{REPO_OWNER}/{REPO_NAME}/tree/{BRANCH}/{REMOTE_DIR}")
    print(f"\n⬇️  Fetching current GitHub state...")

    remote_files = get_remote_files()
    print(f"   GitHub files ({len(remote_files)}): {', '.join(sorted(remote_files.keys())) or 'none'}")

    # ── Uploads: new files OR changed files ──
    to_upload   = []
    to_skip     = []
    for name, path in local_files.items():
        content = path.read_bytes()
        local_computed_sha = file_sha(content)
        remote_sha = remote_files.get(name)

        if remote_sha is None:
            to_upload.append(("new", name, content, None))
        elif remote_sha != local_computed_sha:
            to_upload.append(("update", name, content, remote_sha))
        else:
            to_skip.append(name)

    # ── Deletions: files on GitHub that aren't local anymore ──
    to_delete = [(name, sha) for name, sha in remote_files.items() if name not in local_files]

    # ── Summary ──
    print(f"\n📊 Plan:")
    print(f"   ⬆️  Upload/Update : {len(to_upload)} files")
    print(f"   ⏭️  Skip (same)   : {len(to_skip)} files")
    print(f"   🗑️  Delete        : {len(to_delete)} files")

    if not to_upload and not to_delete:
        print("\n✅ Everything is already up to date!")
        return

    print()
    confirm = input("Proceed? (y/n): ").strip().lower()
    if confirm != "y":
        print("❌ Cancelled.")
        return

    print("\n⬆️  Uploading...")
    upload_ok, upload_fail = 0, 0
    for action, name, content, sha in to_upload:
        if upload_file(name, content, sha):
            upload_ok += 1
        else:
            upload_fail += 1

    print("\n🗑️  Deleting old files...")
    delete_ok, delete_fail = 0, 0
    for name, sha in to_delete:
        if delete_file(name, sha):
            delete_ok += 1
        else:
            delete_fail += 1

    print("\n" + "=" * 55)
    print(f"✅ Done!")
    print(f"   Uploaded/Updated : {upload_ok}  |  Failed: {upload_fail}")
    print(f"   Deleted          : {delete_ok}  |  Failed: {delete_fail}")
    print(f"\n🔗 Check: https://github.com/{REPO_OWNER}/{REPO_NAME}/tree/{BRANCH}/{REMOTE_DIR}")
    print("=" * 55)


if __name__ == "__main__":
    main()
