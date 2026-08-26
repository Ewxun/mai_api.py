import aiohttp
import os
import re


class Album:
    def __init__(self, data: dict):
        self.id: str = data.get("id")
        self.name: str = data.get("name")
        self.time: str = data.get("time")
        self.difficulty: str = data.get("difficulty")
        self.image_url: str = data.get("image_url")  # URLs are private and require authentication to access, other users cannot access them
        self.location: str = data.get("location")

    async def download_image(self, save_path: str):
        """Download the album image to the specified path.
        Args:
            save_path (str): The path where the image will be saved.
        """
        
        if not os.path.exists(os.path.dirname(save_path)):
            os.makedirs(os.path.dirname(save_path))

        async with aiohttp.ClientSession() as session:
            async with session.get(self.image_url) as response:
                if response.status == 200:
                    with open(save_path, 'wb') as f:
                        f.write(await response.read())
                else:
                    raise Exception(f"Failed to download image. Status code: {response.status}")
        
class SongRecord:
    '''
    Represents a song record fetched from the playlog endpoint. Contains basic information about the song and the player's performance.
    '''
    def __init__(self, client, data: dict):
        '''
        Initializes a SongRecord object with the provided data.
        '''
        self.client = client
        self.id: str = data.get("id")
        self.play_datetime: str = data.get("play_datetime")
        self.trackcount: str = data.get("play_trackcount")
        self.name: str = data.get("song_name")
        self.level: str = data.get("song_level")
        self.chart_type: str = data.get("song_type")
        self.difficulty: str = data.get("diff_name")
        self.score: str = data.get("song_score")
        self.score_rank: str = data.get("song_score_rank")
        self.dx_score: list[int] = data.get("song_dx_score")
        self.is_score_new_record: bool = data.get("is_score_new_record")
        self.is_dx_score_new_record: bool = data.get("is_dx_score_new_record")
        self.dx_star: int = data.get("dx_star")
        self.cover_img: str = data.get("song_cover_img")
        self.vs_rank: str = data.get("vs_rank")
        self.stats: list[str] = data.get("stats")

        self.raw_data = data

        # Additional details that are not present in the initial data but can be fetched with the get_details method
        self.judgement = {
            "tap": [],  # [crit perfect, perfect, great, good, miss]
            "hold": [],
            "slide": [],
            "touch": [],
            "break": []
        }
        self.fast_late = {"fast": 0, "late": 0}
        self.max_combo = None  # [current_combo, max_combo]
        self.max_sync = None   # [current_sync, max_sync]
        self.up_rating = 0
        self.tour_members = []
        self.played_together = []
        

    async def get_details(self) -> 'SongRecord':
        '''
        Fetches additional details about the song record using the provided client.
    
        Returns:
            SongRecord: The updated SongRecord object with additional details.
        '''
        details_path = "record/playlogDetail/?idx=" + self.id
        details_dom = await self.client._fetch_dom(details_path)

        judgement_table_rows = details_dom.xpath('//table[contains(@class, "playlog_notes_detail")]//tr')[1:]  # Get all rows in the judgement table, skip the header row

        for idx, row in enumerate(judgement_table_rows):
            cells = row.xpath('.//td')
            note_judgement = []
            for cell in cells:
                cell_text = cell.xpath('.//text()')[0].strip()
                note_judgement.append(int(cell_text if cell_text.isdigit() else 0))  # In cases like standard charts (touch)/no crit perfect judgement, the cell is empty, so we default to 0

            self.judgement[list(self.judgement.keys())[idx]] = note_judgement

        fast_late_block = details_dom.xpath('//div[contains(@class, "playlog_fl_block")]//div[contains(@class, "w_96") and contains(@class, "f_l")]')

        # First is fast, second is late
        fast = fast_late_block[0].xpath('.//text()')
        late = fast_late_block[1].xpath('.//text()')
        self.fast_late["fast"] = int(fast[0].strip())
        self.fast_late["late"] = int(late[0].strip())

        up_rating = details_dom.xpath('//span[contains(@class, "f_11") and contains(@class, "v_t")]//text()')[0].strip()
        regex = r"(\d+)"
        up_rating_match = re.search(regex, up_rating)
        if up_rating_match:
            self.up_rating = int(up_rating_match.group(1))
        # There's supposedly a "down rating" but I haven't seen it yet
        # There's an asset for it: https://maimaidx-eng.com/maimai-mobile/img/playlog/rating_down.png
        # Possibly for when you update to a newer version of the game

        combo_text = details_dom.xpath('//img[contains(@src, "img/playlog/maxcombo.png")]//following-sibling::div[contains(@class, "f_r") and contains(@class, "f_14")]/text()')[0]
        self.max_combo = [int(s) for s in combo_text.split("/")]

        max_sync_text = details_dom.xpath('//img[contains(@src, "img/playlog/maxsync.png")]//following-sibling::div[contains(@class, "f_r") and contains(@class, "f_14")]/text()')[0]
        if "/" in max_sync_text:
            self.max_sync = [int(s) for s in max_sync_text.split("/")]

        tour_member_urls = details_dom.xpath('//img[contains(@class, "chara_cycle_img")]/@src')
        tour_members = [await self.client.url_convert.get_tour_member(url) for url in tour_member_urls]
        self.tour_members = [member for member in tour_members if member]

        if self.max_sync:  # Only exists if played with others, obviously...
            play_together_block = details_dom.xpath('//div[contains(@class, "see_through_block") and contains(@id, "matching")]/span[contains(@class, "p_3") and contains(@class, "d_ib")]')
            for player in play_together_block:
                if "gray_block" in player.xpath('@class')[0]:
                    continue
                player_name = player.xpath('.//div[contains(@class, "basic_block") and contains(@class, "t_c")]/text()')[0].strip()
                player_diff_url = player.xpath('.//img[contains(@src, "img/diff_")]/@src')[0]
                player_diff = self.client.url_convert.diff(player_diff_url)

                self.played_together.append({
                    "player_name": player_name,
                    "difficulty": player_diff
                })

        return self