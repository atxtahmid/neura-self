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

BrowserUse captcha service for NeuraSelf.
Runs the full OwO hCaptcha flow inside a remote Chromium browser
via BrowserUse Cloud API.
"""

import os
import asyncio
import aiohttp


class BrowserUseService:

    def __init__(self, bot, api_key, site_key):
        self.bot = bot
        self.api_key = api_key or os.getenv("BROWSER_USE_API_KEY", "")
        self.site_key = site_key
        self.base_url = "https://api.browser-use.com/api/v4"
        self.oauth_url = "https://discord.com/api/v9/oauth2/authorize?client_id=408785106942164992&response_type=code&redirect_uri=https://owobot.com/api/auth/discord/redirect&scope=identify guilds"
        self.captcha_url = "https://owobot.com/captcha"

    async def get_balance(self):
        return 999

    async def solve_hcaptcha(self, retries=3):
        return None

    def _still_solving(self):
        # Returns True if the security cog is still waiting for a solve.
        # When the DM "verified" message arrives, security.py sets this to False.
        return getattr(self.bot, '_solving_captcha', True)

    async def _create_browser(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url + "/browsers",
                headers={
                    "X-Browser-Use-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={"proxyCountryCode": "us"},
            ) as resp:
                if resp.status not in (200, 201):
                    err = await resp.text()
                    self.bot.log("ERROR", "BrowserUse: Failed to create browser: " + str(resp.status) + " - " + err)
                    return None, None
                data = await resp.json()
                return data.get("id"), data.get("cdpUrl")

    async def _stop_browser(self, session_id):
        try:
            async with aiohttp.ClientSession() as session:
                await session.patch(
                    self.base_url + "/browsers/" + session_id,
                    headers={
                        "X-Browser-Use-API-Key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={"action": "stop"},
                )
        except Exception:
            pass

    async def solve_full_flow(self, discord_token, retries=3):
        if not self.api_key:
            self.bot.log("ERROR", "BrowserUse: BROWSER_USE_API_KEY is not set.")
            return False

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.bot.log("ERROR", "BrowserUse: playwright not installed.")
            return False

        for attempt in range(retries):
            # --- If the DM already arrived, stop retrying entirely ---
            if not self._still_solving():
                self.bot.log("SUCCESS", "BrowserUse: DM verification already received — stopping retries.")
                return True

            browser = None
            session_id = None
            solved_via_dm = False
            try:
                self.bot.log("SYS", "BrowserUse: Attempt " + str(attempt + 1) + "/" + str(retries))

                session_id, cdp_url = await self._create_browser()
                if not cdp_url:
                    await asyncio.sleep(5)
                    continue

                self.bot.log("SYS", "BrowserUse: Browser created, connecting via CDP...")

                async with async_playwright() as p:
                    browser = await p.chromium.connect_over_cdp(cdp_url, timeout=60000)
                    context = browser.contexts[0]
                    page = context.pages[0] if context.pages else await context.new_page()

                    async def add_auth(route):
                        headers = route.request.headers.copy()
                        headers["authorization"] = discord_token
                        await route.continue_(headers=headers)

                    await page.route("**/discord.com/api/**", add_auth)
                    await page.route("**/owobot.com/api/**", add_auth)

                    self.bot.log("SYS", "BrowserUse: Loading owobot.com...")
                    try:
                        await page.goto("https://owobot.com", wait_until="domcontentloaded", timeout=45000)
                    except Exception as e:
                        self.bot.log("WARN", "BrowserUse: owobot.com load warning: " + str(e))

                    await asyncio.sleep(2)

                    self.bot.log("SYS", "BrowserUse: Authorizing Discord OAuth...")
                    try:
                        oauth_result = await page.evaluate("""async (token) => {
                            try {
                                const res = await fetch("https://discord.com/api/v9/oauth2/authorize?client_id=408785106942164992&response_type=code&redirect_uri=https://owobot.com/api/auth/discord/redirect&scope=identify%20guilds", {
                                    method: "POST",
                                    headers: {
                                        "Authorization": token,
                                        "Content-Type": "application/json"
                                    },
                                    body: JSON.stringify({
                                        authorize: true,
                                        permissions: "0",
                                        integration_type: 0,
                                        location_context: {guild_id: "10000", channel_id: "10000", channel_type: 10000}
                                    })
                                });
                                const data = await res.json();
                                return {status: res.status, data: data};
                            } catch(e) {
                                return {status: 0, error: String(e)};
                            }
                        }""", discord_token)

                        if not oauth_result or oauth_result.get("status") != 200:
                            self.bot.log("WARN", "BrowserUse: OAuth fetch failed: " + str(oauth_result))
                        else:
                            redirect_url = oauth_result.get("data", {}).get("location")
                            if redirect_url:
                                try:
                                    await page.goto(redirect_url, wait_until="domcontentloaded", timeout=30000)
                                except Exception:
                                    pass
                    except Exception as e:
                        self.bot.log("WARN", "BrowserUse: OAuth step warning: " + str(e))

                    await asyncio.sleep(2)

                    self.bot.log("SYS", "BrowserUse: Opening captcha page...")
                    try:
                        await page.goto(self.captcha_url, wait_until="domcontentloaded", timeout=45000)
                    except Exception as e:
                        self.bot.log("WARN", "BrowserUse: Captcha page load warning: " + str(e))

                    self.bot.log("SYS", "BrowserUse: Waiting for captcha to be solved...")

                    token = None
                    for _ in range(55):
                        await asyncio.sleep(2)

                        # --- If OwO sent the "verified" DM, the solve is confirmed ---
                        if not self._still_solving():
                            solved_via_dm = True
                            break

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
                                    } catch(err) {}
                                }
                                return null;
                            }""")
                        except Exception:
                            token = None
                        if token:
                            break

                    try:
                        await browser.close()
                    except Exception:
                        pass

                    # --- If DM confirmed, we're done ---
                    if solved_via_dm:
                        self.bot.log("SUCCESS", "BrowserUse: DM verification confirmed — captcha solved.")
                        return True

                    if token:
                        self.bot.log("SUCCESS", "BrowserUse: hCaptcha solved, submitting to OwO...")
                        if await self._verify_with_owo(token):
                            return True
                        else:
                            self.bot.log("ERROR", "BrowserUse: OwO rejected the token, retrying...")
                    else:
                        self.bot.log("WARN", "BrowserUse: No hCaptcha token detected, retrying...")

            except Exception as e:
                self.bot.log("ERROR", "BrowserUse attempt " + str(attempt + 1) + " failed: " + str(e))
            finally:
                if session_id:
                    await self._stop_browser(session_id)
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
                        self.bot.log("SUCCESS", "BrowserUse: OwO verification succeeded!")
                        return True
                    err = await resp.text()
                    self.bot.log("ERROR", "BrowserUse verify failed: " + str(resp.status) + " - " + err)
                    return False
        except Exception as e:
            self.bot.log("ERROR", "BrowserUse verify exception: " + str(e))
            return False