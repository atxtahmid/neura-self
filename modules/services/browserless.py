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

Browserless captcha service for NeuraSelf.
Runs the full OwO hCaptcha flow inside a remote Chromium browser
with the NoneCap extension installed.
"""

import os
import json
import asyncio
import aiohttp


class BrowserlessService:
    def __init__(self, bot, api_key, site_key):
        self.bot = bot
        self.api_key = api_key or os.getenv("BROWSERLESS_TOKEN", "")
        self.site_key = site_key
        self.extension_name = "nonecap"
        self.ws_endpoint = "wss://production-sfo.browserless.io/chromium/playwright"
        self.oauth_url = (
            "https://discord.com/api/v9/oauth2/authorize"
            "?client_id=408785106942164992"
            "&response_type=code"
            "&redirect_uri=https://owobot.com/api/auth/discord/redirect"
            "&scope=identify guilds"
        )
        self.captcha_url = "https://owobot.com/captcha"

    async def get_balance(self):
        return 999

    async def solve_hcaptcha(self, retries=3):
        return None

    async def solve_full_flow(self, discord_token, retries=3):
        if not self.api_key:
            self.bot.log("ERROR", "Browserless: BROWSERLESS_TOKEN is not set.")
            return False

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.bot.log("ERROR", "Browserless: playwright not installed. Run `pip install playwright`.")
            return False

        launch_opts = json.dumps({
            "extensions": [self.extension_name],
            "stealth": True,
            "blockAds": True,
        })
        ws_url = f"{self.ws_endpoint}?token={self.api_key}&launch={launch_opts}"

        for attempt in range(retries):
            browser = None
            try:
                self.bot.log("SYS", f"Browserless: Attempt {attempt + 1}/{retries}")
                async with async_playwright() as p:
                    browser = await p.chromium.connect(ws_url, timeout=60000)
                    context = await browser.new_context()
                    page = await context.new_page()

                    async def add_auth(route):
                        headers = route.request.headers.copy()
                        headers["authorization"] = discord_token
                        await route.continue_(headers=headers)

                    await page.route("**/discord.com/api/**", add_auth)
                    await page.route("**/owobot.com/api/**", add_auth)

                    self.bot.log("SYS", "Browserless: Authorizing Discord OAuth...")
                    await page.goto(self.oauth_url, wait_until="networkidle", timeout=60000)
                    await asyncio.sleep(2)

                    self.bot.log("SYS", "Browserless: Opening captcha page...")
                    await page.goto(self.captcha_url, wait_until="networkidle", timeout=60000)

                    self.bot.log("SYS", "Browserless: Waiting for NoneCap to solve hCaptcha...")
                    token = None
                    for _ in range(60):
                        await asyncio.sleep(2)
                        try:
                            token = await page.evaluate("""() => {
                                const ta = document.querySelector('textarea[name="h-captcha-response"]');
                                if (ta && ta.value && ta.value.length > 20) return ta.value;
                                const inp = document.querySelector('input[name="h-captcha-response"]');
                                if (inp && inp.value && inp.value.length > 20) return inp.value;
                                if (window.hcaptcha && window.hcaptcha.getResponse) {
                                    try {
                                        const r = window.hcaptcha.getResponse();
                                        if (r && r.length > 20) return r;
                                    } catch(e) {}
                                }
                                return null;
                            }""")
                        except Exception:
                            token = None
                        if token:
                            break

                    try:
                        await context.close()
                    except Exception:
                        pass
                    try:
                        await browser.close()
                    except Exception:
                        pass
                    browser = None

                    if token:
                        self.bot.log("SUCCESS", "Browserless: hCaptcha solved, submitting to OwO...")
                        if await self._verify_with_owo(token):
                            return True
                        else:
                            self.bot.log("ERROR", "Browserless: OwO rejected the token, retrying...")
                    else:
                        self.bot.log("WARN", "Browserless: No hCaptcha token detected, retrying...")

            except Exception as e:
                self.bot.log("ERROR", f"Browserless attempt {attempt + 1} failed: {e}")
                try:
                    if browser:
                        await browser.close()
                except Exception:
                    pass
                if attempt < retries - 1:
                    await asyncio.sleep(5)

        return False

    async def _verify_with_owo(self, token):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://owobot.com/api/captcha/verify",
                    json={"token": token},
                    headers={
                        "Referer": "https://owobot.com/captcha",
                        "Origin": "https://owobot.com",
                        "Accept": "application/json, text/plain, */*",
                        "Content-Type": "application/json",
                    }
                ) as resp:
                    if resp.status == 200:
                        self.bot.log("SUCCESS", "Browserless: OwO verification succeeded!")
                        return True
                    err = await resp.text()
                    self.bot.log("ERROR", f"Browserless verify failed ({resp.status}): {err}")
                    return False
        except Exception as e:
            self.bot.log("ERROR", f"Browserless verify exception: {e}")
            return False
