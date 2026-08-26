
def spendings_calc():
    # Implement soon?
    return

def get_partner_details(filename):
    # TODO: Reorganise based on version
    # TODO: Allow multiple different portraits?
    partner_map = {
        "bd58d9c2274ce8fd.png": {
            "name": "リズ",
            "en_name": "Ris",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/7sref/icon/01.png"
        },
        "d898a52edae0366f.png": {
            "name": "でらっくま",
            "en_name": "Deraakuma",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/start/icon/01.png"
        },
        "03efbc6d3ed52964.png": {
            "name": "らいむっくま＆れもんっくま",
            "en_name": "Lime & Lemon Kuma",
            "potrait_url": "https://discordwidgets.com/uploads/82a4f571837331a52f22c65ea95cf135c74f0d6b98bd3ed03cea0523f5e36f22.png"
        },
        "fdd6e58cf81b1e2e.png": {
            "name": "乙姫",
            "en_name": "Otohime",
            "potrait_url": "https://maimai.sega.jp/maimai_finale/chara/assets/pc/sd_otohime.png"
        },
        "2c0bf461478499e7.png": {
            "name": "黒姫",
            "en_name": "Kurohime",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/metropolis/icon/05.png"
        },
        "5e986e798844059e.png": {
            "name": "ラズ (ふぇすてぃばる)",
            "en_name": "Ras (Festival)",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/hapifes/icon/01.png"
        },
        "ef567595e1e81020.png": {
            "name": "シフォン (ふぇすてぃばる)",
            "en_name": "Chiffon (Festival)",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/hapifes/icon/02.png"
        },
        "3dc276a1b659e33e.png": {
            "name": "ソルト (ふぇすてぃばる)",
            "en_name": "Salt (Festival)",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/hapifes/icon/03.png"
        },
        "7ff83da1b44efeb3.png": {
            "name": "ラズ",
            "en_name": "Ras",
            "potrait_url": "https://maimai.sega.jp/maimai_finale/chara/assets/pc/sd_ras.png"
        },
        "a508919b350bf720.png": {
            "name": "シフォン",
            "en_name": "Chiffon",
            "potrait_url": "https://maimai.sega.jp/maimai_finale/chara/assets/pc/sd_chiffon.png"
        },
        "a340d37188cce20e.png": {
            "name": "ソルト",
            "en_name": "Salt",
            "potrait_url": "https://maimai.sega.jp/maimai_finale/chara/assets/pc/sd_salt.png"
        },
        "8ae99321df691564.png": {
            "name": "しゃま",
            "en_name": "Shama",
            "potrait_url": "https://maimai.sega.jp/maimai_finale/chara/assets/pc/sd_syama.png"
        },
        "1318eef8e5fc5a0a.png": {
            "name": "みるく",
            "en_name": "Milk",
            "potrait_url": "https://maimai.sega.jp/maimai_finale/chara/assets/pc/sd_milk.png"
        },
        "240b94b8dc3174b9.png": {
            "name": "乙姫（すぷらっしゅ）",
            "en_name": "Otohime (Splash)",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/shuwa-shuwa2/icon/01.png"
        },
        "25da565b1ceb62f2.png": {
            "name": "しゃま（ゆにばーす）",
            "en_name": "Shama (Universe)",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/universe/icon/01.png"
        },
        "b1b87682f19db7f8.png": {
            "name": "みるく（ゆにばーす）",
            "en_name": "Milk (Universe)",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/universe/icon/02.png"
        },
        "5ac032ec087a91e7.png": {
            "name": "ちびみるく",
            "en_name": "Chibi Milk",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/universe2/icon/01.png"
        },
        "689d29adbdb7d8fe.png": {
            "name": "百合咲ミカ",
            "en_name": "Yurisaki Mika",
            "potrait_url": "https://maimai.sega.jp/storage/area/region/heaven3/icon/01.png"
        },
    }
    return partner_map.get(filename)

class URL_Convert:
    '''
    Util functions to convert maimai resource urls to human friendly terms
    '''
    def __init__(self, client):
        self.client = client

    def diff(self, url: str):
        if "img/diff_" in url:
            diff_name = url.split('/')[-1].split('.')[0].split('_')[-1]
            return diff_name
        
    def music_icon(self, url: str):
        if "img/music_" in url:
            music_icon = url.split('/')[-1].split('.')[0].split('_')[-1]
            return music_icon
        
    def playlog(self, url: str):
        if "img/playlog" in url:
            playlog_name = url.split('/')[-1].split('.')[0].split('_')[-1]
            return playlog_name if playlog_name != 'dummy' else None

    async def get_tour_member(self, url: str):
        if "img/tour_member" in url:
            tour_member_dom = await self.client._fetch_dom("collection/character/")
            event_member_dom = await self.client._fetch_dom("collection/eventCharacter/")

            tour_member = {
                "name": None,
                "chiho": None,
                "level": None,
                "stars": None,
                "is_from_event": False,
                "is_obtained": False,
                "image_url": url
            }

            tour_doms = [tour_member_dom, event_member_dom]
            for idx, dom in enumerate(tour_doms):
                if idx == 1:
                    tour_member["is_from_event"] = True

                for member_block in dom.xpath('//div[contains(@class, "see_through_block") and contains(@class, "f_0")]'):
                    tour_member_url = member_block.xpath('.//img[contains(@class, "chara_cycle_img")]/@src')[0]
                    if tour_member_url == url:
                        member_name = member_block.xpath('.//div[contains(@class, "p_t_10") and contains(@class, "break")]/text()')[0].strip()
                        member_chiho_name = member_block.xpath('preceding-sibling::div[contains(@class, "t_c") and contains(@class, "f_b")]/text()')[0].strip()
                        is_obtained = not bool(member_block.xpath('.//div[contains(@class, "gray_img")]'))
                    if is_obtained:
                        star_count = int(member_block.xpath('.//span[contains(@class, "collection_chara_awakening_block_txt")]/text()')[0].strip())
                        level = int(member_block.xpath('.//div[contains(@class, "collection_chara_lv_block")]/text()')[0].strip().replace("Lv", ""))
                        tour_member["stars"] = star_count
                        tour_member["level"] = level

                    tour_member["name"] = member_name
                    tour_member["chiho"] = member_chiho_name
                    tour_member["is_obtained"] = is_obtained

                    return tour_member