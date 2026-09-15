# This file is part of NeuraSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# NeuraSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with NeuraSelf-UwU. If not, see <https://www.gnu.org/licenses/>.


"""
Author: Routo
NeuraSelf-UwU - https://github.com/routo-loop/neura-self
"""



import asyncio
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from datetime import datetime
from importlib.metadata import distributions, version, PackageNotFoundError

import core.state as state
from utils import proxy_manager
from utils.platform import is_termux

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
    from rich.prompt import Confirm, Prompt
    from rich.table import Table
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "rich"], capture_output=True)
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
    from rich.prompt import Confirm, Prompt
    from rich.table import Table

console = Console()
SETUP_LOG = os.path.join(state.DATA_DIR, "setup.log")
DEFAULT_PASSWORD = "neuraself_default_password_change_me"
REQUIRED_VERSION_SUFFIX = "+g20ae80b3"

class NeuraSetupEngine:
    def __init__(self):
        self._log_lines = []
        self._ready = False

    def _write_log(self, level, message):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level}] {message}"
        self._log_lines.append(line)
        if not os.path.exists(state.DATA_DIR):
            os.makedirs(state.DATA_DIR, exist_ok=True)
        try:
            with open(SETUP_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def _console_log(self, level, message):
        styles = {
            "ok": "[green]✓[/green]",
            "warn": "[yellow]![/yellow]",
            "error": "[red]✗[/red]",
            "info": "[dim]•[/dim]",
        }
        prefix = styles.get(level, "[dim]•[/dim]")
        console.print(f"{prefix} {message}")
        self._write_log(level.upper(), message)

    def check_python(self):
        major, minor = sys.version_info[:2]
        if major < 3 or (major == 3 and minor < 10):
            self._console_log("error", f"python 3.10+ required (found {major}.{minor})")
            console.print("\n[bold]Please install Python 3.10 or newer:[/bold]")
            console.print("  - Windows: https://www.python.org/downloads/  (ensure 'Add Python to PATH' is checked)")
            console.print("  - macOS:   brew install python@3.11")
            console.print("  - Linux:   sudo apt install python3.11  (or use your package manager)")
            return False
        self._console_log("ok", f"python {major}.{minor} found")
        return True

    def check_git(self):
        git_path = shutil.which("git")
        if git_path:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                ver = result.stdout.strip().split()[-1]
                self._console_log("ok", f"git {ver} found")
                return True
        self._console_log("warn", "git not found – skipping (not required in this environment)")
        return True

    def ensure_directories(self):
        for path in (state.CONFIG_DIR, state.DATA_DIR):
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                self._console_log("ok", f"created {path}")
        return True

    def ensure_config_files(self):
        accounts_path = os.path.join(state.CONFIG_DIR, "accounts.json")
        if not os.path.exists(accounts_path):
            with open(accounts_path, "w", encoding="utf-8") as f:
                json.dump({"accounts": []}, f, indent=4)
            self._console_log("ok", "created config/accounts.json")

        proxies_path = os.path.join(state.CONFIG_DIR, "proxies.json")
        if not os.path.exists(proxies_path):
            with open(proxies_path, "w", encoding="utf-8") as f:
                json.dump({"proxies": []}, f, indent=4)
            self._console_log("ok", "created config/proxies.json")

        auth_path = os.path.join(state.CONFIG_DIR, "auth.json")
        if not os.path.exists(auth_path):
            with open(auth_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "username": "admin",
                        "password": DEFAULT_PASSWORD,
                        "secret_key": secrets.token_hex(32),
                    },
                    f,
                    indent=4,
                )
            self._console_log("warn", "default dashboard password set – change it in config/auth.json")

        settings_path = os.path.join(state.CONFIG_DIR, "settings.json")
        if not os.path.exists(settings_path):
            default_settings = {
                "core": {"monitor_bot_id": "408785106942164992"},
                "commands": {},
                "gambling": {"bet_strategy": "flat", "max_bet": 100000},
            }
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=4)
            self._console_log("ok", "created default config/settings.json")
        return True

    def _read_requirements(self):
        needed = []
        if not os.path.exists("requirements.txt"):
            return needed
        content = ""
        for enc in ("utf-8", "utf-16", "utf-8-sig"):
            try:
                with open("requirements.txt", "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeError, OSError):
                continue
        for line in content.splitlines():
            line = line.strip().replace("\x00", "")
            if line and not line.startswith("#"):
                pkg = line.split("@")[0].split("==")[0].strip()
                needed.append((pkg, line))
        heavy = [("numpy", "numpy"), ("pillow", "pillow"), ("onnxruntime", "onnxruntime")]
        for p, full in heavy:
            if not any(p == x[0] for x in needed):
                needed.append((p, full))
        return needed

    def _installed_packages(self):
        try:
            return {dist.metadata["Name"].lower().replace("-", "_") for dist in distributions()}
        except ImportError:
            import pkg_resources
            return {p.key.replace("-", "_") for p in pkg_resources.working_set}

    def _discord_self_ok(self):
        try:
            ver = version("discord.py-self")
            return ver.endswith(REQUIRED_VERSION_SUFFIX)
        except PackageNotFoundError:
            return False

    def _package_import_ok(self, name):
        import_map = {
            "flask": "flask",
            "requests": "requests",
            "aiohttp": "aiohttp",
            "rich": "rich",
            "plyer": "plyer",
            "playsound3": "playsound3",
            "aiohttp-socks": "aiohttp_socks",
            "aiohttp_socks": "aiohttp_socks",
            "numpy": "numpy",
            "pillow": "PIL",
            "onnxruntime": "onnxruntime",
        }
        key = name.lower().replace("-", "_")
        if key in ("discord_py_self", "discord.py-self"):
            return self._discord_self_ok()
        mod = import_map.get(name) or import_map.get(key)
        if mod:
            try:
                __import__(mod)
                return True
            except ImportError:
                return False
        return None

    def _install_discord_self(self):
        py_bin = sys.executable
        cmd = [
            py_bin,
            "-m",
            "pip",
            "install",
            "git+https://github.com/dolfies/discord.py-self@20ae80b398ec83fa272f0a96812140e14868c88",
            "--force-reinstall",
            "--no-cache-dir",
        ]
        process = subprocess.Popen(cmd, stdout=None, stderr=None)
        process.wait()
        if process.returncode != 0:
            self._console_log("error", "discord.py-self installation failed")
            return False
        self._console_log("ok", "discord.py-self installed correctly")
        return True

    def run_bootstrap(self):
        self._console_log("info", "checking dependencies...")
        py_bin = sys.executable
        needed = self._read_requirements()
        installed = self._installed_packages()
        to_install = []

        for name, full in needed:
            import_ok = self._package_import_ok(name)
            if import_ok is True:
                self._console_log("ok", f"{name} found")
                continue
            if import_ok is None and name.lower().replace("-", "_") in installed:
                self._console_log("ok", f"{name} found")
                continue
            to_install.append((name, full))

        if not to_install:
            self._console_log("ok", "all requirements already installed")
            return True

        mobile = is_termux()
        if mobile:
            self._console_log("info", "termux detected – preparing mobile packages")
            subprocess.run(["pkg", "update", "-y"], stdout=None, stderr=None)
            
            env = os.environ.copy()
            env["DEBIAN_FRONTEND"] = "noninteractive"
            subprocess.run(
                ["pkg", "upgrade", "-y", "-o", "Dpkg::Options::=--force-confold"],
                stdout=None, stderr=None, env=env
            )

        pkg_map = {
            "numpy": "python-numpy",
            "pillow": "python-pillow",
            "onnxruntime": "python-onnxruntime"
        }
        failed = []

        for name, full in to_install:
            installed_ok = False
            for attempt in range(2):
                try:
                    if mobile and name in pkg_map:
                        pkg_cmd = ["pkg", "install", pkg_map[name], "-y"]
                        result = subprocess.run(pkg_cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            installed_ok = True
                            self._console_log("ok", f"{name} installed via pkg")
                            break
                        else:
                            self._console_log("warn", f"{name} not found in pkg, falling back to pip")
                    # pip fallback
                    self._console_log("info", f"installing {name} with pip...")
                    result = subprocess.run([py_bin, "-m", "pip", "install", full, "--no-cache-dir"], capture_output=True, text=True)
                    if result.returncode == 0:
                        installed_ok = True
                        self._console_log("ok", f"{name} installed via pip")
                        break
                    else:
                        self._console_log("warn", f"{name} install failed on attempt {attempt+1}, retrying...")
                        time.sleep(2)
                except Exception as e:
                    self._console_log("warn", f"{name} install exception: {e}, retrying...")
                    time.sleep(2)
            if not installed_ok:
                failed.append(name)
                self._console_log("error", f"{name} install failed after retries")

        if failed:
            self._console_log("error", f"some packages failed: {', '.join(failed)}")
            if any("discord" in p for p in failed):
                self._console_log("info", "attempting targeted install for discord.py-self...")
                if not self._install_discord_self():
                    return False
            return False
        return True

    def verify_imports(self):
        modules = ["discord", "flask", "rich", "aiohttp", "aiohttp_socks", "requests", "numpy", "PIL"]
        missing = []
        for mod in modules:
            try:
                __import__(mod)
            except ImportError:
                missing.append(mod)
        if not self._discord_self_ok():
            missing.append("discord.py-self (correct version)")
        if missing:
            self._console_log("error", f"import check failed: {', '.join(missing)}")
            return False
        self._console_log("ok", "all critical imports verified")
        return True

    def run_full_setup(self, force_bootstrap=False):
        self._write_log("INFO", "setup started")
        self._console_log("info", "running full setup...")
        if not self.check_python():
            return False
        self.check_git()
        self.ensure_directories()
        self.ensure_config_files()
        if force_bootstrap or not self.environment_healthy():
            if not self._discord_self_ok():
                self._console_log("info", "discord.py-self missing or incorrect – installing...")
                if not self._install_discord_self():
                    self._console_log("error", "discord.py-self installation failed")
                    return False
            if not self.run_bootstrap():
                self._console_log("error", "bootstrap failed – check data/setup.log")
                return False
            if not self.verify_imports():
                self._console_log("error", "imports still failing after bootstrap")
                return False
        else:
            self._console_log("ok", "environment already healthy – skipping reinstall")
        self._console_log("ok", "setup complete")
        return True

    def environment_healthy(self):
        return self.check_python() and self.verify_imports()

    def load_accounts(self):
        return proxy_manager.load_accounts()

    def save_accounts(self, accounts):
        proxy_manager.save_accounts(accounts)
        proxy_manager.sync_proxy_assignments()

    def load_proxies(self):
        return proxy_manager.load_proxies()

    def save_proxies(self, proxies):
        proxy_manager.save_proxies(proxies)

    def remove_proxy(self, proxy_id):
        proxy_manager.remove_proxy(proxy_id)

    async def verify_token(self, token, channel_ids=None, proxy_url=None, proxy_auth=None):
        if not token or "." not in token:
            return False, "invalid format", []
        import discord
        client = discord.Client(proxy=proxy_url, proxy_auth=proxy_auth)
        result = {"valid": False, "user": None, "channels": []}

        @client.event
        async def on_ready():
            result["valid"] = True
            name = (
                f"{client.user.name}#{client.user.discriminator}"
                if client.user.discriminator != "0"
                else client.user.name
            )
            result["user"] = name
            if channel_ids:
                for cid in channel_ids:
                    try:
                        ch = client.get_channel(int(cid))
                        if ch:
                            result["channels"].append(cid)
                    except Exception:
                        pass
            await client.close()

        try:
            await asyncio.wait_for(client.start(token), timeout=30)
        except asyncio.TimeoutError:
            await client.close()
            return False, "timeout", []
        except discord.LoginFailure:
            return False, "invalid token", []
        except Exception as e:
            return False, f"error: {str(e)}", []

        return result["valid"], result["user"], result["channels"]

    def parse_proxy_line(self, line):
        return proxy_manager.parse_proxy_line(line)

    def bulk_import_proxies(self, text):
        return proxy_manager.bulk_import(text)

    async def test_proxy(self, proxy):
        return await proxy_manager.test_proxy(proxy)

    async def test_all_proxies(self):
        return await proxy_manager.test_all_proxies()

    def auto_assign_proxies(self):
        return proxy_manager.auto_assign()

    def resolve_account_proxy(self, account):
        return proxy_manager.resolve_account_proxy(account)
