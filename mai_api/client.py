import asyncio
import aiohttp
import random
import logging
from lxml import etree

from typing import Literal, Union

from .constants import API_BASE, USER_AGENTS
from .player import Friend, SelfPlayer, FriendPartial
from . import utils
from .songs import Album, SongRecord

logger = logging.getLogger(__name__)
url_convert = utils.URL_Convert()

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
        course_rank_url = player_dom.xpath('//img[contains(@class, "h_35") and contains(@class, "f_l")]/@src')
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
            "course_rank_url": course_rank_url[0] if course_rank_url else "N/A",
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
    
    async def get_friends(self):
        """Fetch friend list data"""
        friends_list = []
        friend_dom = await self._fetch_dom("friend/")
        friend_block_list = friend_dom.xpath('//div[contains(@class, "see_through_block") and contains(@class, "p_10")]')

        # Loop through each friend block
        for friend_block in friend_block_list:
            friend_id = friend_block.xpath('.//input[contains(@name, "idx")]/@value')[0]
            friend_name = friend_block.xpath('.//div[contains(@class, "name_block")]/text()')[0].strip()
            friend_icon = friend_block.xpath('.//img[contains(@class, "w_112") and contains(@src, "img/Icon")]/@src')[0]
            
            trophy_type_block = friend_block.xpath('.//div[contains(@class, "trophy_block") and contains(@class, "f_0")]/@class')
            
            trophy_type = trophy_type_block[0].split(" ")[1] if trophy_type_block else "rainbow"
            trophy_type = "rainbow" if trophy_type == "ランダム" else trophy_type.split("_")[1] if "_" in trophy_type else trophy_type

            trophy_blocks = friend_block.xpath('.//div[contains(@class, "trophy_inner_block") and contains(@class, "f_13")]')
            if trophy_blocks:
                trophy_block = trophy_blocks[0]
                trophy_texts = trophy_block.xpath('.//text()')
                trophy_content = trophy_texts[1] if len(trophy_texts) > 1 else "ERROR"
            else:
                trophy_content = "ERROR"

            friend_title = {"text": trophy_content, "rarity": trophy_type}

            friend_rating = friend_block.xpath('.//div[contains(@class, "rating_block")]/text()')[0].strip()
            friend_rating_frame = friend_block.xpath('.//img[contains(@src, "rating_base")]/@src')[0]

            friend_course_rank = friend_block.xpath('.//img[contains(@src, "course_rank")]/@src')[0]
            friend_class_rank = friend_block.xpath('.//img[contains(@src, "class_rank")]/@src')[0]
            friend_stars = friend_block.xpath('.//div[contains(@class, "p_l_10") and contains(@class, "f_14")]/text()')[0].strip().replace('×', '')

            friend_favorite_icon = friend_block.xpath('.//img[contains(@class, "friend_favorite_icon")]/@src')
            friend_favorite = len(friend_favorite_icon) > 0

            friend_info = {
                'id': friend_id,
                'name': friend_name,
                'icon': friend_icon,
                'rating': friend_rating,
                'rating_frame': friend_rating_frame,
                'course_rank_url': friend_course_rank,
                'class_rank_url': friend_class_rank,
                'stars': friend_stars,
                'favorite': friend_favorite,
                'title': friend_title
            }

            friends_list.append(FriendPartial()._construct_from_dict(friend_info))
        return friends_list
    
    async def fetch_friend_details(self, friend: Union[FriendPartial, str]) -> Union[FriendPartial, None]:
        """Fetch detailed information for a specific friend
        Args:
            friend (Union[FriendPartial, str]): FriendPartial object or friend ID string.
        """
        friend_id = friend.id if isinstance(friend, FriendPartial) else friend
        friend_dom = await self._fetch_dom(f"friend/friendDetail/?idx={friend_id}")
        if friend_dom is None:
            return None

        user_name = friend_dom.xpath('//div[contains(@class, "name_block")]/text()')
        rating_block_url = friend_dom.xpath('//img[contains(@class, "h_30") and contains(@class, "f_r")]/@src')
        rating = friend_dom.xpath('//div[@class="rating_block"]/text()')
        course_rank_url = friend_dom.xpath('//img[contains(@class, "h_35") and contains(@class, "f_l")]/@src')
        class_rank_url = friend_dom.xpath('//img[contains(@class, "w_160") and contains(@class, "p_15") and contains(@class, "m_r_10")]/@src')
        friend_icon = friend_dom.xpath('.//img[contains(@class, "w_112") and contains(@src, "img/Icon")]/@src')[0]
        
        trophy_type_block = friend_dom.xpath('.//div[contains(@class, "trophy_block") and contains(@class, "f_0")]/@class')
                    
        trophy_type = trophy_type_block[0].split(" ")[1] if trophy_type_block else "rainbow"
        trophy_type = "rainbow" if trophy_type == "ランダム" else trophy_type.split("_")[1] if "_" in trophy_type else trophy_type

        trophy_blocks = friend_dom.xpath('.//div[contains(@class, "trophy_inner_block") and contains(@class, "f_13")]')
        if trophy_blocks:
            trophy_block = trophy_blocks[0]
            trophy_texts = trophy_block.xpath('.//text()')
            trophy_content = trophy_texts[1] if len(trophy_texts) > 1 else "ERROR"
        else:
            trophy_content = "ERROR"

        friend_title = {"text": trophy_content, "rarity": trophy_type}

        # Convert rating to int
        rating_str = rating[0].strip() if rating else "0"
        try:
            rating_int = int(rating_str)
        except ValueError:
            rating_int = 0

        # Tour Leader Image
        tour_leader_img = friend_dom.xpath(f".//img[contains(@src, 'img/Chara/')]/@src")[0]

        # Recent Activity
        activity_blocks = friend_dom.xpath('.//div[contains(@class, "town_block") and contains(@class, "f_0")]')

        # loop through each activity block
        activity_data = []
        for activity_section in activity_blocks:
            log_entry = activity_section.xpath('.//div[contains(@class, "t_l")]')
            for log in log_entry:
                activity_time = log.xpath('.//div[contains(@class, "f_11")]/text()')
                log_text_block = log.xpath('.//div[contains(@class, "f_13")]')[0]

                # Replace the image with the actual text
                image_block = log_text_block.xpath('.//img/@src')
                if len(image_block) > 0:
                    image_src = image_block[0]
                    if "img/diff_" in image_src:
                        # Extract difficulty name from the image source
                        # Get the last part after 'diff_'
                        diff_name = url_convert.diff(image_src) 
                        raw_log = "".join(log.xpath('.//div[contains(@class, "f_13")]/text()')).strip()
                        log_text = raw_log + f" (Difficulty: {diff_name})"
                else:
                    log_text = "".join(log.xpath('.//div[contains(@class, "f_13")]/text()')).strip()
                
                # Remove extra whitespace from log_text
                log_text = " ".join(log_text.split())

                activity_data.append({
                    "time": activity_time[0].strip() if activity_time else "N/A",
                    "text": log_text
                })

        friend_data = {
            "id": friend_id,
            "name": user_name[0].strip() if user_name else "N/A",
            "icon": friend_icon,
            "rating": rating_int,
            "rating_block_url": rating_block_url[0] if rating_block_url else "N/A",
            "course_rank_url": course_rank_url[0] if course_rank_url else "N/A",
            "class_rank_url": class_rank_url[0] if class_rank_url else "N/A",
            "friend_title": friend_title,
            "tour_leader_img": tour_leader_img if tour_leader_img else "N/A",
            "recent_activity": activity_data
        }
        

        return Friend()._construct_from_dict(friend_data)
    
    async def get_album(self) -> list[Album]:
        """Fetch album data
        Returns:
            list[Album]: List of Album objects.
        """
        album_dom = await self._fetch_dom("playerData/photo/")
        if album_dom is None:
            return None

        album_blocks = album_dom.xpath('//div[contains(@class, "m_10") and contains(@class, "f_0")]')

        album_data = []
        for album_block in album_blocks:
            time = album_block.xpath('.//div[contains(@class, "block_info")]/text()')
            diff_url = album_block.xpath('.//img[contains(@class, "h_16") and contains(@class, "f_l")]/@src')
            diff = url_convert.diff(diff_url[0]) if diff_url else "N/A"
            song_name = album_block.xpath('.//div[contains(@class, "black_block") and contains(@class, "break")]/text()')[0].strip()
            image_url = album_block.xpath('.//img[contains(@class, "w_430")]/@src')[0] 
            location = album_block.xpath('.//div[contains(@class, "see_through_block") and contains(@class, "break")]/text()')[0].strip()

            album_id = image_url.split('/')[-1]

            album = Album({
                "id": album_id,
                "name": song_name,
                "time": time[0].strip() if time else "N/A",
                "difficulty": diff,
                "image_url": image_url,
                "location": location
            })
            album_data.append(album)

        return album_data

    async def get_recent_plays(self) -> list[SongRecord]:
        record_dom = self._fetch_dom("record/")
        record_blocks = record_dom.xpath('.//div[contains(@class, "p_10") and contains(@class, "v_b")]')

        song_records = []
        for record_block in record_blocks:
            playlog_top = record_block.xpath('.//div[contains(@class, "playlog_top_container")]')[0]
            diff_img = playlog_top.xpath('.//img[contains(@class, "playlog_diff")]/@src')[0]
            diff_name = url_convert.diff(diff_img)

            play_trackcount = playlog_top.xpath('.//div[contains(@class, "sub_title") and contains(@class, "t_c")]/span[1]/text()')[0].strip()
            play_datetime = playlog_top.xpath('.//div[contains(@class, "sub_title") and contains(@class, "t_c")]/span[2]/text()')[0].strip()

            song_name = record_block.xpath('.//div[contains(@class, "w_80") and contains(@class, "f_r")]/text()')[0].strip()
            song_level = record_block.xpath('.//div[contains(@class, "playlog_level_icon")]/text()')[0].strip()
            song_type_img = record_block.xpath('.//img[contains(@class, "playlog_music_kind_icon")]/@src')[0]
            song_type = url_convert.music_icon(song_type_img)
            song_cover_img = record_block.xpath('.//img[contains(@class, "music_img")]/@src')[0]

            song_score = "".join(record_block.xpath('.//div[contains(@class, "playlog_achievement_txt")]//text()')).strip()
            song_score_rank_img = record_block.xpath('.//img[contains(@class, "playlog_scorerank")]/@src')[0]
            song_score_rank = url_convert.playlog(song_score_rank_img)
            song_dx_score = record_block.xpath('.//div[contains(@class, "p_r_5") and contains(@class, "f_r")]//text()')[0].strip()

            dx_star_url = record_block.xpath('.//img[contains(@class, "playlog_deluxscore_star")]/@src')
            dx_star = url_convert.playlog(dx_star_url[0]) if dx_star_url else 0

            stat_block = record_block.xpath('.//div[contains(@class, "playlog_result_innerblock")]')[0]
            stat_imgs = stat_block.xpath('.//img[contains(@class, "h_35") and contains(@class, "m_5")]/@src')

            stats = []
            for stat_img in stat_imgs:
                stat_name = url_convert.playlog(stat_img)
                if stat_name:
                    stats.append(stat_name)
            vs_rank_img = stat_block.xpath('.//img[contains(@class, "playlog_matching_icon")]/@src')
            vs_rank = url_convert.playlog(vs_rank_img[0]) if vs_rank_img else None

            record_id = record_block.xpath('.//form[contains(@class, "m_t_5") and contains(@class, "t_r")]/input[1]/@value')[0]

            record_data = {
                "id": record_id,
                "play_datetime": play_datetime,
                "play_trackcount": play_trackcount,
                "song_name": song_name,
                "song_level": song_level,
                "song_type": song_type,
                "diff_name": diff_name,
                "song_score": song_score,
                "song_score_rank": song_score_rank,
                "song_dx_score": song_dx_score,
                "dx_star": dx_star,
                "song_cover_img": song_cover_img,
                "vs_rank": vs_rank,
                "stats": stats
            }
            song_records.append(SongRecord(record_data))

        return song_records