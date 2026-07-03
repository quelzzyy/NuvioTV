"""NuvioTV Fork Manager — one small window for the whole workflow.

Run with:  py scripts\nuvio-manager.py   (or double-click nuvio-manager.bat)

Buttons:
  - Push My Changes ....... commit + push everything you changed to your fork
  - Sync Official Updates . merge the latest official NuvioTV code into your branch
  - Publish Release ....... trigger the Beta Release workflow on GitHub
  - Pull Latest ........... fetch the version-bump commit CI pushes after a release

Publishing needs a GitHub token the first time (Settings section explains).
Everything else works with plain git.
"""

import json
import re
import subprocess
import threading
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

REPO_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / ".nuvio_manager_config.json"
GITHUB_OWNER = "quelzzyy"
GITHUB_REPO = "NuvioTV"
BRANCH = "my-features"
UPSTREAM_REF = "upstream/main"
ACTIONS_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/beta-release.yml"
API_BASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

BG = "#16161d"
FG = "#e8e8f0"
ACCENT = "#7c6cff"
MUTED = "#9a9ab0"


def run_git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def current_version() -> str:
    try:
        gradle = (REPO_DIR / "app" / "build.gradle.kts").read_text(encoding="utf-8")
        match = re.search(r'versionName\s*=\s*"([^"]+)"', gradle)
        return match.group(1) if match else "?"
    except Exception:
        return "?"


def suggest_next_version(version: str) -> str:
    # 0.7.13-beta.1 -> 0.7.13-beta.2 ; 0.7.14-beta -> 0.7.14-beta.1
    match = re.match(r"^(.*\.)(\d+)$", version)
    if match and "-" in version:
        return f"{match.group(1)}{int(match.group(2)) + 1}"
    return f"{version}.1"


def github_json(url: str, token: str | None = None, payload: dict | None = None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "nuvio-manager"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode()
        return json.loads(body) if body.strip() else {}


class ManagerApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("NuvioTV Fork Manager")
        self.root.geometry("720x640")
        self.root.configure(bg=BG)
        self.config = load_config()
        self.busy = False
        self._build_ui()
        self.refresh()

    # ---------- UI ----------

    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Head.TLabel", font=("Segoe UI", 15, "bold"), foreground=FG)
        style.configure(
            "Big.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8)
        )
        style.map(
            "Big.TButton",
            background=[("!disabled", ACCENT), ("disabled", "#3a3a4a")],
            foreground=[("!disabled", "white"), ("disabled", "#777")],
        )
        style.configure("TEntry", fieldbackground="#24242e", foreground=FG)

        pad = {"padx": 16, "pady": 4}
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="NuvioTV Fork Manager", style="Head.TLabel").pack(
            anchor="w", padx=16, pady=(14, 2)
        )
        self.status_label = ttk.Label(main, text="Loading status…", style="Muted.TLabel")
        self.status_label.pack(anchor="w", **pad)

        # --- Push section ---
        push = ttk.Frame(main)
        push.pack(fill="x", **pad)
        ttk.Label(push, text="1 · Push my changes to GitHub").pack(anchor="w")
        row = ttk.Frame(push)
        row.pack(fill="x", pady=4)
        self.msg_entry = ttk.Entry(row)
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.msg_entry.insert(0, "Update my features")
        self.push_btn = ttk.Button(
            row, text="Push My Changes", style="Big.TButton", command=self.do_push
        )
        self.push_btn.pack(side="right")

        # --- Sync section ---
        sync = ttk.Frame(main)
        sync.pack(fill="x", **pad)
        ttk.Label(sync, text="2 · Get the latest official NuvioTV updates").pack(anchor="w")
        row = ttk.Frame(sync)
        row.pack(fill="x", pady=4)
        self.sync_info = ttk.Label(row, text="", style="Muted.TLabel")
        self.sync_info.pack(side="left")
        self.sync_btn = ttk.Button(
            row, text="Sync Official Updates", style="Big.TButton", command=self.do_sync
        )
        self.sync_btn.pack(side="right")

        # --- Release section ---
        rel = ttk.Frame(main)
        rel.pack(fill="x", **pad)
        ttk.Label(rel, text="3 · Publish a release (updates your TV)").pack(anchor="w")
        row = ttk.Frame(rel)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Version:").pack(side="left")
        self.version_entry = ttk.Entry(row, width=18)
        self.version_entry.pack(side="left", padx=8)
        self.release_btn = ttk.Button(
            row, text="Publish Release", style="Big.TButton", command=self.do_release
        )
        self.release_btn.pack(side="right")
        self.pull_btn = ttk.Button(
            row, text="Pull Latest", command=self.do_pull
        )
        self.pull_btn.pack(side="right", padx=8)

        # --- Settings ---
        settings = ttk.Frame(main)
        settings.pack(fill="x", **pad)
        row = ttk.Frame(settings)
        row.pack(fill="x")
        ttk.Label(row, text="GitHub token:", style="Muted.TLabel").pack(side="left")
        self.token_entry = ttk.Entry(row, show="*", width=30)
        self.token_entry.pack(side="left", padx=8)
        if self.config.get("token"):
            self.token_entry.insert(0, self.config["token"])
        ttk.Button(row, text="Save", command=self.save_token).pack(side="left")
        ttk.Button(row, text="Refresh Status", command=self.refresh).pack(side="right")
        ttk.Label(
            settings,
            text=(
                "Token is only needed for Publish Release. Create one at "
                "github.com/settings/tokens (classic, scopes: repo + workflow)."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        # --- Log ---
        self.log_box = tk.Text(
            main,
            height=14,
            bg="#0e0e14",
            fg="#c9c9dd",
            insertbackground=FG,
            relief="flat",
            font=("Consolas", 9),
            state="disabled",
            wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, padx=16, pady=(8, 14))

    # ---------- helpers ----------

    def log(self, text: str) -> None:
        def _append() -> None:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", text.rstrip() + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.root.after(0, _append)

    def set_busy(self, busy: bool) -> None:
        def _apply() -> None:
            self.busy = busy
            state = "disabled" if busy else "normal"
            for btn in (self.push_btn, self.sync_btn, self.release_btn, self.pull_btn):
                btn.configure(state=state)

        self.root.after(0, _apply)

    def run_async(self, fn) -> None:
        if self.busy:
            return
        self.set_busy(True)

        def wrapper() -> None:
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 - surface everything to the log
                self.log(f"ERROR: {exc}")
            finally:
                self.set_busy(False)
                self.root.after(0, self._refresh_status_labels)

        threading.Thread(target=wrapper, daemon=True).start()

    # ---------- status ----------

    def refresh(self) -> None:
        self.run_async(self._refresh_full)

    def _refresh_full(self) -> None:
        self.log("Checking status…")
        run_git("fetch", "upstream", "--quiet")
        run_git("fetch", "origin", "--quiet")
        self.root.after(0, self._refresh_status_labels)
        # Latest release on the fork (public API, no token needed)
        try:
            release = github_json(f"{API_BASE}/releases/latest")
            self.log(
                f"Latest published release: {release.get('tag_name', 'none')}"
            )
        except urllib.error.HTTPError:
            self.log("Latest published release: none yet")
        except Exception:
            pass
        self.log("Ready.")

    def _refresh_status_labels(self) -> None:
        version = current_version()
        changes = run_git("status", "--porcelain").stdout.strip()
        change_count = len(changes.splitlines()) if changes else 0
        behind = run_git("rev-list", "--count", f"{BRANCH}..{UPSTREAM_REF}").stdout.strip() or "?"
        unpushed = run_git("rev-list", "--count", f"origin/{BRANCH}..{BRANCH}").stdout.strip() or "?"
        self.status_label.configure(
            text=(
                f"App version: {version}   ·   Unsaved changes: {change_count}   ·   "
                f"Commits not pushed: {unpushed}   ·   Official updates waiting: {behind}"
            )
        )
        self.sync_info.configure(
            text=f"{behind} official update(s) available"
            if behind not in ("0", "?")
            else "You are up to date with the official app"
        )
        if not self.version_entry.get().strip():
            self.version_entry.insert(0, suggest_next_version(version))

    # ---------- actions ----------

    def do_push(self) -> None:
        message = self.msg_entry.get().strip()
        if not message:
            messagebox.showwarning("Message needed", "Write a short note about what you changed.")
            return
        self.run_async(lambda: self._push(message))

    def _push(self, message: str) -> None:
        if not run_git("status", "--porcelain").stdout.strip():
            unpushed = run_git("rev-list", "--count", f"origin/{BRANCH}..{BRANCH}").stdout.strip()
            if unpushed not in ("0", ""):
                self.log("No new changes, but pushing earlier commits…")
                result = run_git("push", "origin", BRANCH)
                self.log(result.stderr or result.stdout or "Pushed.")
            else:
                self.log("Nothing to push — no changes found.")
            return
        self.log(f'Committing: "{message}"')
        run_git("add", "-A")
        commit = run_git("commit", "-m", message)
        self.log(commit.stdout.strip() or commit.stderr.strip())
        self.log("Pushing to your fork…")
        push = run_git("push", "origin", BRANCH)
        if push.returncode == 0:
            self.log("✔ Pushed! It will be in your next release.")
        else:
            self.log(f"Push failed:\n{push.stderr}")

    def do_sync(self) -> None:
        self.run_async(self._sync)

    def _sync(self) -> None:
        if run_git("status", "--porcelain").stdout.strip():
            self.log("You have unsaved changes — push them first, then sync.")
            return
        self.log("Fetching the official repo…")
        run_git("fetch", "upstream", "--tags")
        behind = run_git("rev-list", "--count", f"{BRANCH}..{UPSTREAM_REF}").stdout.strip()
        if behind == "0":
            self.log("✔ Already up to date with the official app.")
            return
        self.log(f"Merging {behind} official commit(s)…")
        merge = run_git("merge", UPSTREAM_REF, "--no-edit")
        if merge.returncode != 0:
            conflicted = run_git("diff", "--name-only", "--diff-filter=U").stdout.strip()
            run_git("merge", "--abort")
            self.log("✘ Merge conflict! The official update touches the same code as your features.")
            self.log(f"Conflicting files:\n{conflicted}")
            self.log("Nothing was changed. Ask Claude to 'sync upstream and fix the conflict'.")
            return
        self.log("Merged. Pushing to your fork…")
        push = run_git("push", "origin", BRANCH)
        if push.returncode == 0:
            self.log("✔ Synced! Publish a release to get it on your TV.")
        else:
            self.log(f"Push failed:\n{push.stderr}")

    def do_release(self) -> None:
        version = self.version_entry.get().strip()
        if not re.match(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$", version):
            messagebox.showwarning(
                "Version format",
                "Version must look like 0.7.13-beta.2 (three numbers, then a suffix).",
            )
            return
        token = self.config.get("token", "").strip()
        if not token:
            self.log("No GitHub token saved — opening the release page in your browser instead.")
            self.log(f"Fill in: branch {BRANCH}, release_mode publish, version {version}")
            webbrowser.open(ACTIONS_URL)
            return
        if not messagebox.askyesno(
            "Publish release",
            f"Build and publish version {version}?\n\nTakes about 15 minutes. "
            "Your TV will offer the update automatically once it finishes.",
        ):
            return
        self.run_async(lambda: self._release(version, token))

    def _release(self, version: str, token: str) -> None:
        self.log(f"Starting release {version} on GitHub…")
        try:
            github_json(
                f"{API_BASE}/actions/workflows/beta-release.yml/dispatches",
                token=token,
                payload={
                    "ref": BRANCH,
                    "inputs": {"release_mode": "publish", "version": version},
                },
            )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            self.log(f"✘ GitHub refused ({exc.code}): {detail}")
            self.log("Check the token has 'repo' and 'workflow' scopes.")
            return
        self.log("✔ Release build started! It takes ~15 minutes.")
        self.log("When it finishes, click 'Pull Latest' to sync the version bump.")
        self.log(f"Watch progress: {ACTIONS_URL}")

    def do_pull(self) -> None:
        self.run_async(self._pull)

    def _pull(self) -> None:
        self.log("Pulling latest from your fork…")
        result = run_git("pull", "origin", BRANCH)
        self.log(result.stdout.strip() or result.stderr.strip())

    def save_token(self) -> None:
        self.config["token"] = self.token_entry.get().strip()
        save_config(self.config)
        self.log("Token saved (kept only on this PC, never uploaded).")

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    ManagerApp().run()
