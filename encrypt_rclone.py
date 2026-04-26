#!/usr/bin/env python3
"""
encrypt_rclone.py — rclone config ko encrypt karo aur repo mein commit karo.

HOW TO USE:
  1. Apna rclone.conf update karo (nayi Mega account add karo etc.)
  2. Is script ko repo root se chalao:
       python encrypt_rclone.py
  3. Password dalo (same jo GitHub Secret RCLONE_CONFIG_PASSWORD mein hai)
  4. Script automatically encrypt karke commit aur push kar dega

FIRST TIME SETUP:
  1. GitHub mein ek Secret banao: Settings → Secrets → New repository secret
     Name:  RCLONE_CONFIG_PASSWORD
     Value: koi bhi strong password (e.g. myS3cur3P@ss2024)
  2. Yeh password yaad rakho — isi se encrypt/decrypt hoga

ADDING NEW MEGA ACCOUNT (no Secret changes needed):
  1. rclone config chalao locally, nayi remote add karo
  2. phir yeh script chalao — bas itna kaafi hai
"""

import os
import sys
import subprocess
import getpass
from pathlib import Path

REPO_ROOT      = Path(__file__).parent
RCLONE_CONF    = RCLONE_CONF    = Path.home() / "AppData" / "Roaming" / "rclone" / "rclone.conf"
ENCRYPTED_FILE = REPO_ROOT / "rclone.conf.enc"


def encrypt_config(password: str) -> bool:
    if not RCLONE_CONF.exists():
        print(f"❌ rclone.conf not found at: {RCLONE_CONF}")
        print(f"   Pehle 'rclone config' chalao aur remotes setup karo.")
        return False

    cmd = [
        "openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "600000",
        "-in",  str(RCLONE_CONF),
        "-out", str(ENCRYPTED_FILE),
        "-pass", f"pass:{password}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Encryption failed:\n{result.stderr}")
        return False

    print(f"✅ Encrypted → {ENCRYPTED_FILE}")
    return True


def verify_decrypt(password: str) -> bool:
    """Encrypt ke baad verify karo ke decrypt bhi kaam karta hai."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".conf", delete=False) as tmp:
        tmp_path = tmp.name

    cmd = [
        "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "600000",
        "-in",  str(ENCRYPTED_FILE),
        "-out", tmp_path,
        "-pass", f"pass:{password}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(tmp_path)

    if result.returncode != 0:
        print(f"❌ Decrypt verify failed — wrong password? {result.stderr}")
        return False

    print("✅ Decrypt verify passed — encryption is correct.")
    return True


def git_commit_push() -> bool:
    os.chdir(REPO_ROOT)

    # Check if git repo
    if not (REPO_ROOT / ".git").exists():
        print("⚠️ Git repo nahi mila — manually commit karo: git add rclone.conf.enc && git commit -m 'update rclone config' && git push")
        return False

    cmds = [
        ["git", "add", "rclone.conf.enc"],
        ["git", "commit", "-m", "🔐 Update encrypted rclone config"],
        ["git", "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # commit may fail if no changes — that's OK
            if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                print("ℹ️ No changes to commit — config already up to date.")
                return True
            print(f"❌ Git command failed: {' '.join(cmd)}\n{result.stderr}")
            return False
        print(f"✅ {' '.join(cmd[:2])}")

    return True


def check_openssl():
    result = subprocess.run(["openssl", "version"], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ openssl nahi mila! Install karo:")
        print("   Windows: https://slproweb.com/products/Win32OpenSSL.html")
        print("   Mac:     brew install openssl")
        print("   Linux:   sudo apt install openssl")
        sys.exit(1)


def main():
    print("=" * 50)
    print("  rclone Config Encrypt & Push Tool")
    print("=" * 50)
    print(f"\n📂 Repo:        {REPO_ROOT}")
    print(f"📄 Source conf: {RCLONE_CONF}")
    print(f"🔐 Output:      {ENCRYPTED_FILE}\n")

    check_openssl()

    if not RCLONE_CONF.exists():
        print(f"❌ rclone.conf not found at {RCLONE_CONF}")
        print("   Pehle 'rclone config' se remotes setup karo.")
        sys.exit(1)

    # Show current remotes
    result = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        print(f"📡 Current remotes in rclone.conf:")
        for r in result.stdout.strip().splitlines():
            print(f"   • {r}")
        print()

    password = getpass.getpass("🔑 Enter encryption password (same as GitHub Secret RCLONE_CONFIG_PASSWORD): ")
    if not password:
        print("❌ Password khali nahi ho sakta!")
        sys.exit(1)

    confirm = getpass.getpass("🔑 Confirm password: ")
    if password != confirm:
        print("❌ Passwords match nahi karte!")
        sys.exit(1)

    print("\n⚙️ Encrypting...")
    if not encrypt_config(password):
        sys.exit(1)

    print("🔍 Verifying decrypt...")
    if not verify_decrypt(password):
        sys.exit(1)

    print("\n📤 Committing and pushing to GitHub...")
    git_commit_push()

    print("\n" + "=" * 50)
    print("✅ Done! rclone.conf.enc is now in your repo.")
    print("   GitHub Actions will decrypt it automatically.")
    print("\n📌 REMINDER: GitHub Secret 'RCLONE_CONFIG_PASSWORD' must")
    print("   match the password you just used.")
    print("=" * 50)


if __name__ == "__main__":
    main()
