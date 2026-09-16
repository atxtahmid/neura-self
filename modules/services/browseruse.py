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
            browser = None
            session_id = None
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

                    self.bot.log("SYS", "BrowserUse: Authorizing Discord OAuth...")
                    await page.goto(self.oauth_url, wait_until="networkidle", timeout=60000)
                    await asyncio.sleep(2)

                    self.bot.log("SYS", "BrowserUse: Opening captcha page...")
                    await page.goto(self.captcha_url, wait_until="networkidle", timeout=60000)

                    self.bot.log("SYS", "BrowserUse: Waiting for captcha to be solved...")
                    token = None
                    for _ in range(55):
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

                    if token:
                        self.bot.log("SUCCESS", "BrowserUse: Captcha solved, submitting to OwO...")
                        if await self._verify_with_owo(token):
                            return True
                        else:
                            self.bot.log("ERROR", "BrowserUse: OwO rejected the token, retrying...")
                    else:
                        self.bot.log("WARN", "BrowserUse: No captcha token detected, retrying...")

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
