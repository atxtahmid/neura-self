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



import sys
import asyncio
import time
import re
import os
import threading
import unicodedata
import requests
import random
import json
import discord
from discord.ext import commands
from plyer import notification
import core.state as state

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cfg = bot.config.get('security', {})
        self.enabled = cfg.get('enabled', True)
        self.notifications_enabled = cfg.get('notifications', {}).get('enabled', True)
        self.notification_title = cfg.get('notifications', {}).get('desktop', {}).get('title', "Neura Security Alert")
        self.webhook_url = cfg.get('webhook_url')
        self.monitor_id = str(bot.config.get('core', {}).get('monitor_bot_id', '408785106942164992'))
        self.beep_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "beeps", "security_beep.mp3")
        self.ban_keywords = [
            "youhavebeenbanned",
            "bannedforbotting",
            "bannedformacros"
        ]
        self.captcha_keywords = [
            "areyouarealhuman",
            "verifythatyouarehuman",
            "pleasecompletethiswithin",
            "pleaseusethelinkbelow",
            "completeyourcaptcha",
            "pleasedmmewiththefollowing",
            "pleasedmmewithonly",
            "ifyouhavetroublesolvingthecaptcha",
            "pleasecomplete",
            "tocheckthatyouareahuman",
            "tocheck",
            "human"
        ]
        self.warning_pattern = re.compile(r'\(\s*(\d+)\s*/\s*(\d+)\s*\)')
        self.image_captcha_keywords = [
            "pleasedmme",
            "dmme",
            "beepboop",
            "checkthatyouareahuman",
            "solvingthecaptcha",
            "letterword"
        ]

    async def register_actions(self):
        cfg = self.bot.config.get('security', {})
        self.enabled = cfg.get('enabled', True)
        self.notifications_enabled = cfg.get('notifications', {}).get('enabled', True)
        self.notification_title = cfg.get('notifications', {}).get('desktop', {}).get('title', "Neura Security Alert")
        self.webhook_url = cfg.get('webhook_url')
        self.monitor_id = str(self.bot.config.get('core', {}).get('monitor_bot_id', '408785106942164992'))
        self.bot.log("SYS", "Security Module settings refreshed (Live Sync).")

    def _normalize(self, text):
        if not text:
            return ""
        text = unicodedata.normalize("NFKD", text)
        return re.sub(r'[^a-zA-Z0-9]', '', text.lower())

    def _show_desktop_notification(self, message):
        if not self.notifications_enabled:
            return
        sec_cfg = self.bot.config.get('security', {})
        notif_cfg = sec_cfg.get('notifications', {})
        if self.bot.is_mobile:
            mobile = notif_cfg.get('mobile', {})
            if mobile.get('enabled', True):
                try:
                    os.system(f'termux-notification --title "{self.notification_title}" --content "{message}"')
                    vib = mobile.get('vibrate', {})
                    if vib.get('enabled', True):
                        duration = int(vib.get('time', 0.5) * 1000)
                        os.system(f'termux-vibrate -d {duration}')
                    toast = mobile.get('toast', {})
                    if toast.get('enabled', True):
                        bg = toast.get('bg_color', 'black')
                        fg = toast.get('text_color', 'white')
                        pos = toast.get('position', 'middle')
                        os.system(f'termux-toast -b {bg} -c {fg} -g {pos} "{message}"')
                    tts = mobile.get('tts', {})
                    if tts.get('enabled', False):
                        os.system(f'termux-tts-speak "{message}"')
                except:
                    pass
            return
        desktop = notif_cfg.get('desktop', {})
        if desktop.get('enabled', True):
            try:
                notification.notify(title=self.notification_title, message=message, timeout=10)
            except:
                pass

    def _send_webhook(self, title, message):
        cfg = self.bot.config.get('security', {})
        wh_cfg = cfg.get('webhook', {})
        if not wh_cfg.get('enabled', True): return
        url = wh_cfg.get('url')
        if not url: return
        payload = {
            "content": "@everyone @here",
            "embeds": [{
                "title": title,
                "description": message,
                "color": 0xFF3B3B,
                "author": {
                    "name": f"NeuraSelf Security - {self.bot.username}",
                    "icon_url": "https://media.discordapp.net/attachments/1357951011456684252/1524069544401047773/neuralogo.png?ex=6a4e67df&is=6a4d165f&hm=21deba052462f712808661dc8aac4204eecb781cfcaa1[...]
                },
                "footer": {"text": f"NeuraSelf • Account: {self.bot.username}"},
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
            }]
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except:
            pass

    async def play_beep(self):
        def _play():
            if not os.path.exists(self.beep_file):
                return
            if self.bot.is_mobile:
                try:
                    os.system(f'termux-media-player play "{self.beep_file}"')
                except:
                    pass
                return
            try:
                from playsound3 import playsound
                playsound(self.beep_file, block=False)
            except:
                pass
        threading.Thread(target=_play, daemon=True).start()

    def _contains_keyword(self, text, keywords):
        cleaned = self._normalize(text)
        return any(k in cleaned for k in keywords)

    def _get_captcha_url(self, message):
        if not message.components:
            return None
        for comp in message.components:
            if not getattr(comp, "children", None): continue
            for child in comp.children:
                url = str(getattr(child, "url", "") or "")
                if "owobot.com/captcha" in url:
                    return url
        return None

    def _has_solver_key(self, sol_cfg):
        return bool(
            sol_cfg.get("browserless_api_key") or
            os.getenv("BROWSERLESS_TOKEN") or
            sol_cfg.get("yescaptcha_api_key") or
            sol_cfg.get("nopecha_api_key") or
            sol_cfg.get("anticaptcha_api_key") or
            sol_cfg.get("captchaly_api_key")
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.enabled: return
        if (message.guild is None or isinstance(message.channel, discord.DMChannel)) and message.author.id == int(self.monitor_id):
            if (discord.utils.utcnow() - message.created_at).total_seconds() > 30: return
            if "i have verified that you are human" in message.content.lower():
                self.bot.web_solver.mark_verification_done(str(self.bot.user.id))
                self.bot._solving_captcha = False
                try:
                    from dashboard.app import clear_captcha_challenge
                    clear_captcha_challenge(str(self.bot.user.id))
                except Exception as e:
                    self.bot.log("ERROR", f"Failed to clear captcha challenge: {e}")
                self.bot.paused = False
                self.bot.throttle_until = 0.0
                self.bot.last_sent_time = 0
                self.bot.warmup_until = 0
                grinding_cog = self.bot.get_cog('Grinding')
                if grinding_cog:
                    grinding_cog.cooldowns['hunt'] = 0
                    grinding_cog.cooldowns['battle'] = 0
                    grinding_cog.cooldowns['owo'] = 0
                self.bot.log("SUCCESS", "Verified detected in DM. Captcha solved successfully. Resuming...")
                self.bot.log("INFO", "All cooldowns reset. Bot will resume in 2 seconds...")
                await asyncio.sleep(2)
                return

            if "letterword" in message.content.lower() and message.attachments:
                self.bot.log("SECURITY", "Detection AI: Letterword captcha identified in DMs.")
                count_match = re.search(r'(\d+)\s*letterword', message.content.lower())
                letter_count = int(count_match.group(1)) if count_match else 5
                image_url = message.attachments[0].url
                self.bot.log("SYS", f"Attempting to solve DM Captcha ({letter_count} letters)...")
                answer = await self.bot.captcha_solver.solve_image(image_url, letter_count)
                if answer:
                    self.bot.log("SUCCESS", f"AI Solver Answer: {answer}. Sending to OwO...")
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    async with message.channel.typing():
                        await asyncio.sleep(len(answer) * 0.1)
                        await message.channel.send(answer)
                else:
                    self.bot.log("ERROR", "AI Solver failed to generate an answer. Pausing bot.")
                    self.bot.paused = True
                    self.bot.throttle_until = float('inf')
                    self._show_desktop_notification("AI Solver failed! Solve manually.")
                    self.bot.web_solver.enqueue_manual_solve(str(self.bot.user.id), "https://owobot.com/captcha")
                return

            captcha_url = self._get_captcha_url(message)
            if not captcha_url:
                url_match = re.search(r'https?://owobot\.com/captcha/\S+', message.content)
                if url_match: captcha_url = url_match.group(0)

            if captcha_url:
                self.bot.paused = True
                self.bot.throttle_until = float('inf')
                self.bot.log("ALARM", "LINK CAPTCHA DETECTED IN DM!")
                await self.play_beep()
                self._show_desktop_notification("DM Captcha detected!")

                sec_cfg = self.bot.config.get("security", {})
                sol_cfg = sec_cfg.get("captcha_solver", {})

                try:
                    from dashboard.app import register_captcha_challenge
                    register_captcha_challenge(
                        str(self.bot.user.id),
                        {
                            "account_name": self.bot.username,
                            "captcha_url": captcha_url or "https://owobot.com/captcha"
                        }
                    )
                    self.bot.log("SYS", f"Captcha registered for dashboard display (account_id={self.bot.user.id})")
                except Exception as e:
                    self.bot.log("ERROR", f"Failed to register captcha for dashboard: {e}")

                if getattr(self.bot, '_solving_captcha', False):
                    self.bot.log("SECURITY", "[GUARD] Captcha already being solved – skipping duplicate DM captcha task.")
                    return
                self.bot._solving_captcha = True

                autosolved = False
                has_key = self._has_solver_key(sol_cfg)
                if sol_cfg.get("enabled", True) and has_key:
                    service_name = self.bot.web_solver.active_service_name.capitalize()
                    self.bot.log("SYS", f"Attempting {service_name} auto-solve for DM...")
                    autosolved = await self.bot.web_solver.auto_verify()
                    if autosolved:
                        self.bot._solving_captcha = False
                        self.bot.log("SUCCESS", f"{service_name} solved successfully (DM)!")
                        self._show_desktop_notification(f"{service_name} solved successfully!")
                    else:
                        self.bot.log("ERROR", f"{service_name} auto-solve failed (DM)!")
                        self._show_desktop_notification(f"{service_name} failed! Solve manually.")

                if not autosolved:
                    self._send_webhook("DM CAPTCHA", f"Solve link in DM: {captcha_url}")
                    if not getattr(self.bot, 'is_mobile', False):
                        auto_open = sec_cfg.get("open_captcha_url_on_pc", False)
                    else:
                        auto_open = sec_cfg.get("open_captcha_url_on_mobile", False)
                    if auto_open:
                        self.bot.log("SYS", "Queuing manual solve for DM captcha...")
                        self.bot.web_solver.enqueue_manual_solve(str(self.bot.user.id), captcha_url)
                        self._show_desktop_notification(f"Manual solve queued for {self.bot.username}")
                return

        if str(message.author.id) != self.monitor_id: return

        if self.bot.owo_user is None:
            self.bot.owo_user = message.author

        content = message.content or ""
        embed_text = ""
        if message.embeds:
            parts = []
            for e in message.embeds:
                if e.title: parts.append(e.title)
                if e.description: parts.append(e.description)
                if e.footer and e.footer.text: parts.append(e.footer.text)
            embed_text = " ".join(parts)
        text_to_check = f"{content} {embed_text}"
        is_for_me = self.bot.is_message_for_me(message)
        if not is_for_me: return


        is_security_event = (
            self._contains_keyword(text_to_check, self.ban_keywords) or
            self.warning_pattern.search(text_to_check) is not None or
            (len(message.attachments) > 0 and self._contains_keyword(text_to_check, self.image_captcha_keywords)) or
            self._contains_keyword(text_to_check, self.captcha_keywords) or
            self._get_captcha_url(message) is not None or
            re.search(r'https?://owobot\.com/captcha/\S+', text_to_check) is not None
        )

        try:
            allowed_channels = [int(ch) for ch in self.bot.channels]
        except:
            allowed_channels = [self.bot.channel_id]

        if not is_security_event and message.channel.id not in allowed_channels:
            return

        if self._contains_keyword(text_to_check, self.ban_keywords):
            self.bot.paused = True
            self.bot.log("ALARM", "BAN DETECTED!")
            await self.play_beep()
            self._show_desktop_notification("Ban detected!")
            self._send_webhook("BAN DETECTED", f"Message:\n{content}")
            return

        warning_match = self.warning_pattern.search(text_to_check)
        if warning_match:
            current_warning = int(warning_match.group(1))
            max_warnings = int(warning_match.group(2))
            normalized = self._normalize(text_to_check)
            captcha_url = self._get_captcha_url(message)
            if not captcha_url:
                url_match = re.search(r'https?://owobot\.com/captcha/\S+', text_to_check)
                if url_match:
                    captcha_url = url_match.group(0)

            if captcha_url or any(kw in normalized for kw in ["pleasecomplete", "captcha", "verify", "human"]):
                self.bot.paused = True
                self.bot.throttle_until = float('inf')
                self.bot.stats['last_captcha_msg'] = text_to_check[:200]
                self.bot.log("ALARM", f"CAPTCHA WARNING DETECTED ({current_warning}/{max_warnings})!")
                await self.play_beep()
                self._show_desktop_notification(f"Captcha warning {current_warning}/{max_warnings} detected!")
                self._send_webhook("CAPTCHA WARNING", f"Warning {current_warning}/{max_warnings}\nMessage:\n{content}")

                if captcha_url:
                    sec_cfg = self.bot.config.get("security", {})
                    sol_cfg = sec_cfg.get("captcha_solver", {})

                    try:
                        from dashboard.app import register_captcha_challenge
                        register_captcha_challenge(
                            str(self.bot.user.id),
                            {
                                "account_name": self.bot.username,
                                "captcha_url": captcha_url or "https://owobot.com/captcha"
                            }
                        )
                        self.bot.log("SYS", f"Captcha registered for dashboard display (account_id={self.bot.user.id})")
                    except Exception as e:
                        self.bot.log("ERROR", f"Failed to register captcha for dashboard: {e}")

                    if getattr(self.bot, '_solving_captcha', False):
                        self.bot.log("SECURITY", "[GUARD] Captcha already being solved – skipping duplicate warning captcha task.")
                        return
                    self.bot._solving_captcha = True

                    autosolved = False
                    has_key = self._has_solver_key(sol_cfg)
                    if sol_cfg.get("enabled", True) and has_key:
                        service_name = self.bot.web_solver.active_service_name.capitalize()
                        self.bot.log("SYS", f"Attempting {service_name} auto-solve...")
                        autosolved = await self.bot.web_solver.auto_verify()
                        if autosolved:
                            self.bot._solving_captcha = False
                            self.bot.log("SUCCESS", f"{service_name} solved successfully!")
                            self._show_desktop_notification(f"{service_name} solved successfully!")
                        else:
                            self.bot.log("ERROR", f"{service_name} auto-solve failed!")
                            self._show_desktop_notification(f"{service_name} failed! Solve manually.")

                    if not autosolved:
                        solve_link = captcha_url or "https://owobot.com/captcha"
                        self._send_webhook("CAPTCHA WARNING", f"Solve: {solve_link}")
                        if not getattr(self.bot, 'is_mobile', False):
                            auto_open = sec_cfg.get("open_captcha_url_on_pc", False)
                        else:
                            auto_open = sec_cfg.get("open_captcha_url_on_mobile", False)
                        if auto_open:
                            self.bot.log("SYS", "Queuing manual solve for captcha...")
                            self.bot.web_solver.enqueue_manual_solve(str(self.bot.user.id), captcha_url)
                            self._show_desktop_notification(f"Manual solve queued for {self.bot.username}")
                return

        has_image = len(message.attachments) > 0
        image_captcha_hit = self._contains_keyword(text_to_check, self.image_captcha_keywords)
        if has_image and image_captcha_hit:
            self.bot.paused = True
            self.bot.throttle_until = float('inf')
            self.bot.stats['last_captcha_msg'] = text_to_check[:200]
            self.bot.log("ALARM", "IMAGE CAPTCHA DETECTED! Warning triggered.")
            await self.play_beep()
            self._show_desktop_notification("Image captcha detected! Check DMs.")
            img_urls = "\n".join([att.url for att in message.attachments])
            self._send_webhook("IMAGE CAPTCHA DETECTED", f"Message:\n{content}\n\nImages:\n{img_urls}")

            count_match = re.search(r'(\d+)\s*letterword', text_to_check)
            letter_count = int(count_match.group(1)) if count_match else 5
            image_url = message.attachments[0].url
            self.bot.log("SYS", f"Attempting to solve image captcha ({letter_count} letters)...")
            answer = await self.bot.captcha_solver.solve_image(image_url, letter_count)
            if answer:
                self.bot.log("SUCCESS", f"AI Solver Answer: {answer}. Sending to OwO...")

                await self.bot.send_message(answer, skip_typing=True, priority=True)
                self._show_desktop_notification(f"Image captcha solved: {answer}")
            else:
                self.bot.log("ERROR", "AI Solver failed to generate an answer for image captcha.")
                self._show_desktop_notification("AI Solver failed! Solve manually.")
                self.bot.web_solver.enqueue_manual_solve(str(self.bot.user.id), "https://owobot.com/captcha")
            return

        captcha_keywords_hit = self._contains_keyword(text_to_check, self.captcha_keywords)
        captcha_url = self._get_captcha_url(message)
        if not captcha_url:
            url_match = re.search(r'https?://owobot\.com/captcha/\S+', text_to_check)
            if url_match:
                captcha_url = url_match.group(0)

        if captcha_url or captcha_keywords_hit:
            self.bot.paused = True
            self.bot.throttle_until = float('inf')
            self.bot.stats['last_captcha_msg'] = text_to_check[:200]
            self.bot.log("ALARM", "CAPTCHA DETECTED!")
            await self.play_beep()
            self._show_desktop_notification("Captcha detected!")

            sec_cfg = self.bot.config.get("security", {})
            sol_cfg = sec_cfg.get("captcha_solver", {})

            try:
                from dashboard.app import register_captcha_challenge
                register_captcha_challenge(
                    str(self.bot.user.id),
                    {
                        "account_name": self.bot.username,
                        "captcha_url": captcha_url or "https://owobot.com/captcha"
                    }
                )
                self.bot.log("SYS", f"Captcha registered for dashboard display (account_id={self.bot.user.id})")
            except Exception as e:
                self.bot.log("ERROR", f"Failed to register captcha for dashboard: {e}")

            if getattr(self.bot, '_solving_captcha', False):
                self.bot.log("SECURITY", "[GUARD] Captcha already being solved – skipping duplicate channel captcha task.")
                return
            self.bot._solving_captcha = True

            autosolved = False
            has_key = self._has_solver_key(sol_cfg)
            if sol_cfg.get("enabled", True) and has_key:
                service_name = self.bot.web_solver.active_service_name.capitalize()
                self.bot.log("SYS", f"Attempting {service_name} auto-solve...")
                autosolved = await self.bot.web_solver.auto_verify()
                if autosolved:
                    self.bot._solving_captcha = False
                    self.bot.log("SUCCESS", f"{service_name} solved successfully!")
                    self._show_desktop_notification(f"{service_name} solved successfully!")
                else:
                    self.bot.log("ERROR", f"{service_name} auto-solve failed!")
                    self._show_desktop_notification(f"{service_name} failed! Solve manually.")

            if not autosolved:
                solve_link = captcha_url or "https://owobot.com/captcha"
                self._send_webhook("CAPTCHA DETECTED", f"Solve: {solve_link}")
                if not getattr(self.bot, 'is_mobile', False):
                    auto_open = sec_cfg.get("open_captcha_url_on_pc", False)
                else:
                    auto_open = sec_cfg.get("open_captcha_url_on_mobile", False)
                if auto_open:
                    self.bot.log("SYS", "Queuing manual solve for captcha...")
                    self.bot.web_solver.enqueue_manual_solve(str(self.bot.user.id), captcha_url)
                    self._show_desktop_notification(f"Manual solve queued for {self.bot.username}")
            return

async def setup(bot):
    await bot.add_cog(Security(bot))
