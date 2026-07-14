import asyncio
import aiohttp
import random
import logging
from lxml import etree

from typing import Literal

from .constants import API_BASE, USER_AGENTS
from .player import SelfPlayer
from . import utils

logger = logging.getLogger(__name__)

class MaiAPIClient:
    def __init__(self, sega_id: str, password: str, region: Literal["jp", "intl"] = "intl", session: aiohttp.ClientSession = None, retry_attempts: int = 3):
        '''Initialize the MaiAPIClient with Sega ID, password, and region.
        Args:
            sega_id (str): Sega ID for login.
            password (str): Password for login.
            region (str, optional): Region code ("jp" or "intl"). Default: "intl".
            retry_attempts (int, optional): Number of retry attempts for login. Default: 3.
            session (aiohttp.ClientSession, optional): Optional aiohttp session. Default: None.
        '''
        self.base_url = API_BASE.get(region)
        self.region = region
        self.session = aiohttp.ClientSession() if session is None else session
        self.login_info = {"sega_id": sega_id, "password": password}
        self.retry_attempts = retry_attempts


    def _random_user_agent(self):
        return random.choice(USER_AGENTS)
        
    async def login(self, aime=0):
        """Login to maimai and return cookies for further requests

        Args:
            aime (int, optional): Index of the AIME card to use. Default: 0. (JP only?)
        Returns:
            dict: cookies dictionary, used for other async functions
        """
        user_agent = self._random_user_agent()

        connector = aiohttp.TCPConnector(ssl=False, limit=10, ttl_dns_cache=300)

        if self.region == "intl":
            async with aiohttp.ClientSession(connector=connector) as session:
                try:
                    async with session.get(
                        "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/"
                    ) as resp:
                        if resp.status == 503:
                            logger.warning("[Maimai] Server maintenance (503): region=INTL")
                            return "MAINTENANCE"
                        resp.raise_for_status()
                except Exception as e:
                    logger.error(f"[Maimai] Failed to access INTL login page: error={e}")
                    raise

                # login
                async with session.post(
                    "https://lng-tgk-aime-gw.am-all.net/common_auth/login/sid",
                    data={
                        "sid": self.login_info["sega_id"],
                        "password": self.login_info["password"],
                        "retention": "1",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    allow_redirects=False
                ) as login_resp:
                    redirect_url = login_resp.headers.get("Location")

                # Check if redirect URL is present
                if not redirect_url:
                    logger.error(f"[Maimai] Login failed: no redirect URL, region=INTL, sega_id={self.login_info['sega_id']}")
                    return None

                # Follow the redirect to get the final cookies
                async with session.get(
                    redirect_url,
                    headers={
                        "Referer": "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/",
                        "User-Agent": user_agent,
                        "Host": "maimaidx-eng.com"
                    },
                    allow_redirects=True
                ) as final_resp:
                    pass

                return session.cookie_jar.filter_cookies("https://maimaidx-eng.com")

        else:  # jp
            async with aiohttp.ClientSession(connector=connector) as session:
                token = None
                last_status = None
                last_html_len = 0
                last_snippet = ""
                for attempt in range(self.retry_attempts):
                    try:
                        async with session.get("https://maimaidx.jp/maimai-mobile/login/") as response:
                            last_status = response.status
                            if response.status == 503:
                                logger.warning("[Maimai] Server maintenance (503): region=JP")
                                return "MAINTENANCE"
                            response.raise_for_status()
                            html = await response.text()

                        last_html_len = len(html or "")
                        dom = await asyncio.to_thread(etree.HTML, html)
                        token_list = dom.xpath('//input[@name="token"]/@value')
                        if token_list:
                            token = token_list[0]
                            if attempt > 0:
                                logger.info(f"[Maimai] JP login token obtained ({attempt + 1}/{self.retry_attempts})")
                            break
                        last_snippet = (html or "")[:200].replace("\n", " ")
                        logger.warning(
                            f"[Maimai] JP login token missing (Attempt {attempt + 1}/{self.retry_attempts}): "
                            f"status={last_status}, html_len={last_html_len}, snippet={last_snippet!r}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"[Maimai] JP login failed (Attempt {attempt + 1}/{self.retry_attempts}): {e}"
                        )

                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(random.uniform(2, 5))  # Random delay before retrying

                if not token:
                    raise Exception(
                        f"Unable to fetch login token after {self.retry_attempts} attempts"
                        f"(last_status={last_status}, last_html_len={last_html_len})"
                    )

                # login
                async with session.post(
                    "https://maimaidx.jp/maimai-mobile/submit/",
                    data={
                        "segaId": self.login_info["sega_id"],
                        "password": self.login_info["password"],
                        "save_cookie": "on",
                        "token": token
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    allow_redirects=True
                ) as login_response:
                    pass

                # Pick desired aime card
                async with session.get(f"https://maimaidx.jp/maimai-mobile/aimeList/submit/?idx={aime}") as _aime_response:
                    pass

                return session.cookie_jar.filter_cookies("https://maimaidx.jp")

    async def _fetch_dom(self, path: str) -> etree._Element:
        """Get webpage DOM"""

        user_agent = self._random_user_agent()

        if self.region == "intl":
            headers = {
                "Referer": "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/",
                "User-Agent": user_agent,
                "Host": "maimaidx-eng.com"
            }
        else:
            headers = {
                "Referer": "https://maimaidx.jp/maimai-mobile/login/",
                "User-Agent": user_agent,
                "Host": "maimaidx.jp"
            }

        try:
            async with self.session.get(f"{self.base_url}{path if path.endswith('/') else path + '/'}", headers=headers, ssl=False) as resp:
                if resp.status == 503:
                    logger.warning(f"[Maimai] Server maintenance (503): region={self.region}, path={path}")
                    return "MAINTENANCE"
                resp.raise_for_status()
                html = await resp.text()

                if ("Please agree to the following terms of service before log in." in html or
                    "再度ログインしてください" in html):
                    return None

                return await asyncio.to_thread(etree.HTML, html)
            
        except Exception as e:
            logger.error(f"[Maimai] Fetch failed: region={self.region}, path={path}, error={e}")
            return None
        

    async def get_profile(self) -> SelfPlayer:
        """Fetch player profile data"""
        paths = [
            "playerData/",
            "collection/",
            "collection/nameplate/",
            "collection/trophy/",
            "collection/character/",
            "collection/partner/"
        ]

        tasks = [self._fetch_dom(path) for path in paths]
        doms = await asyncio.gather(*tasks)

        # Check if maimai net is in maintenance mode
        for dom in doms:
            if dom == "MAINTENANCE":
                return {"error": "MAINTENANCE"}
            if dom is None:
                return {}

        player_dom, collection_dom, nameplate_dom, trophy_dom, tour_dom, partner_dom = doms

        # Player profile
        user_name = player_dom.xpath('//div[contains(@class, "name_block")]/text()')
        rating_block_url = player_dom.xpath('//img[contains(@class, "h_30") and contains(@class, "f_r")]/@src')
        rating = player_dom.xpath('//div[@class="rating_block"]/text()')
        cource_rank_url = player_dom.xpath('//img[contains(@class, "h_35") and contains(@class, "f_l")]/@src')
        class_rank_url = player_dom.xpath('//img[contains(@class, "w_160") and contains(@class, "p_15") and contains(@class, "m_r_10")]/@src')

        # Player icon
        icon_url = collection_dom.xpath('//img[contains(@class, "w_80") and contains(@class, "m_r_10") and contains(@class, "f_l")]/@src')

        # Nameplate
        nameplate_url = nameplate_dom.xpath('//img[contains(@class, "w_396") and contains(@class, "m_r_10")]/@src')

        # Player title
        trophy_type_block = trophy_dom.xpath('//div[contains(@class, "block_info") and contains(@class, "f_11") and contains(@class, "orange")]/text()')
        trophy_type = trophy_type_block[0].strip().lower() if trophy_type_block else "rainbow"
        trophy_type = "rainbow" if trophy_type == "ランダム" else trophy_type
        trophy_blocks = trophy_dom.xpath('//div[contains(@class, "trophy_inner_block") and contains(@class, "f_13")]')
        if trophy_blocks:
            trophy_block = trophy_blocks[0]
            trophy_texts = trophy_block.xpath('.//text()')
            trophy_content = trophy_texts[1] if len(trophy_texts) > 1 else "ERROR"
        else:
            trophy_content = "ERROR"

        # Convert rating to int
        rating_str = rating[0].strip() if rating else "0"
        try:
            rating_int = int(rating_str)
        except ValueError:
            rating_int = 0
        
        # Tour Leader Image
        # Tour leader is always the first, no filtering needed
        tour_leader_img = tour_dom.xpath(f"//img[contains(@class, 'chara_cycle_img')]/@src")[0]

        # Partner Image
        partner_url = partner_dom.xpath('//div[contains(@class,"collection_setting_block")]//img[contains(@class, "w_80")]/@src')[0]
        partner_info = utils.get_partner_details(partner_url.rsplit("/", 1)[1])

        # Play Stats (FCs, APs, etc.)
        stat_dict = {}
        stat_keys = ["sssp", "sss", "ssp", "ss", "sp", "s", "clear", "dxstar_5", "dxstar_4", "dxstar_3", "dxstar_2", "dxstar_1", "app", "ap", "fcp", "fc", "fdxp", "fdx", "fsp", "fs", "sync"]
        for statkey in stat_keys:
            stat_value = player_dom.xpath(f"//img[contains(@src, 'music_icon_{statkey}.png')]/parent::div/following-sibling::div[contains(@class,'musiccount_counter_block')]/text()")[0].split("/")[0]
            stat_dict[statkey] = stat_value.replace(",", "")

        # Play counts
        pc_raw = player_dom.xpath("//div[contains(@class, 'm_5') and contains(@class, 'f_12')]/text() | //div[contains(@class, 'm_5') and contains(@class, 'f_12')]/br/following-sibling::text()")
        pc_dict = {
            "current": pc_raw[0].rsplit("：", 1)[1].replace(",", ""),
            "total": pc_raw[1].rsplit("：", 1)[1].replace(",", "")
        }

        # Maimiles
        maimiles = player_dom.xpath("//div[contains(@class, 'mile_block') and contains(@class, 'p_t_7')]/text()")[0].replace(",", "")

        # Tickets 
        # Hex codes are the ticket image file name
        ticket_1_5_block = player_dom.xpath("//img[contains(@src, 'b6437a39d9c5491e')]/following-sibling::div[contains(@class,'ticket_txt')]/text()")
        ticket_1_5 = 0 if len(ticket_1_5_block) == 0 else ticket_1_5_block[0].strip().rsplit(" ", 1)[1]
        ticket_2_block = player_dom.xpath("//img[contains(@src, '6048526950e7f4a8')]/following-sibling::div[contains(@class,'ticket_txt')]/text()")
        ticket_2 = 0 if len(ticket_2_block) == 0 else ticket_2_block[0].strip().rsplit(" ", 1)[1]
        ticket_character_block = player_dom.xpath("//img[contains(@src, '7b113dc41580bd5b')]/following-sibling::div[contains(@class,'ticket_txt')]/text()")
        ticket_character = 0 if len(ticket_character_block) == 0 else ticket_character_block[0].strip().rsplit(" ", 1)[1]

        # Presents
        presents_block = player_dom.xpath("//div[contains(@class, 'intimateup_txt')]/text()")
        presents = presents_block[0].rsplit(" ", 1)[1] if len(presents_block) > 0 else "0"

        user_info = {
            "name": user_name[0] if user_name else "NAME_ERROR",
            "rating_block": rating_block_url[0] if rating_block_url else "N/A",
            "rating": rating_int,
            "cource_rank_url": cource_rank_url[0] if cource_rank_url else "N/A",
            "class_rank_url": class_rank_url[0] if class_rank_url else "N/A",
            "icon_url": icon_url[0] if icon_url else "N/A",
            "nameplate_url": nameplate_url[0] if nameplate_url else "N/A",
            "trophy_url": f"https://maimaidx.jp/maimai-mobile/img/trophy_{trophy_type}.png",
            "trophy_content": trophy_content if trophy_content else "N/A",
            "tour_leader_img": tour_leader_img,
            "stats": stat_dict,
            "play_counts": pc_dict,
            "maimiles": maimiles,
            "tickets": {
                "area_bonus": ticket_1_5,
                "weekly_bonus": ticket_2,
                "character_level": ticket_character
            },
            "presents": presents
        }

        return SelfPlayer()._construct_from_dict(user_info)