
class BasePlayer:
    '''Base class for player representation.'''
    def __init__(self, client):
        self.client = client
        self.name = None
        self.rating = None
        self.rating_block = None
        self.icon_url = None

        self._trophy_url = None         # Internal name for title
        self._trophy_content = None     # Internal name for title text
        self.title = {"text": None, "rarity": None}


class SelfPlayer(BasePlayer):
    '''
    Represents the logged-in player.
    '''
    def __init__(self, client, data: dict):
        super().__init__(client)

        self.name = data.get("name")
        self.rating = data.get("rating")
        self.rating_block = data.get("rating_block")

        self.course_rank_url = data.get("course_rank_url")
        self.class_rank_url = data.get("class_rank_url")
        self.icon_url = data.get("icon_url")
        self.nameplate_url = data.get("nameplate_url")

        self._trophy_url = data.get("trophy_url")  # trophy: Internal name for title
        self._trophy_content = data.get("trophy_content")
        self.title["text"] = self._trophy_content
        self.title["rarity"] = self._trophy_url

        self.tour_leader_img = data.get("tour_leader_img")
        self.stats = data.get("stats", {})
        self.play_counts = data.get("play_counts", {"current": 0, "total": 0})
        self.maimiles = data.get("maimiles", 0)
        self.tickets = data.get("tickets", {
            "area_bonus": 0,
            "weekly_bonus": 0,
            "character_level": 0
        })
        self.presents = data.get("presents", 0)

        self.raw_data = data  # Store the raw data for debugging or further processing
        return self


class CircleMember(BasePlayer):
    '''
    Represents a member of a circle.
    '''
    def __init__(self):
        super().__init__()


class Friend(BasePlayer):
    '''
    Represents friend fetched from the friend details endpoint.
    '''
    def __init__(self, client, data: dict):
        super().__init__(client)
        
        self.friend_id = data.get("id")
        self.name = data.get("name")
        self.favorite = data.get("favorite", False)
        self.icon_url = data.get("icon")
        self.rating = data.get("rating")
        self.rating_block = data.get("rating_block_url")
        self.title = data.get("friend_title", {"text": None, "rarity": None})
        
        self.course_rank_url = data.get("course_rank_url")
        self.class_rank_url = data.get("class_rank_url")
        self.tour_leader_img = data.get("tour_leader_img")
        self.recent_activity = data.get("recent_activity", [])

class FriendPartial(BasePlayer):
    '''
    Represents friend data fetched from the friend list, which does not contain all details.
    '''
    def __init__(self, client, data: dict):
        super().__init__(client)
        self.friend_id = data.get("id")
        self.favorite = data.get("favorite", False)
        self.name = data.get("name")
        self.icon_url = data.get("icon")
        self.rating = data.get("rating")
        self.rating_block = data.get("rating_block")
        self.title = data.get("title", {"text": None, "rarity": None})

        return self

    
    async def fetch_details(self) -> Friend:
        '''
        Fetches the full details of the friend from the details page. Returns a Friend object.
        Returns:
            Friend: The full details of the friend.
        '''
       
        friend_dom = await self.client._fetch_dom(f"friend/friendDetail/?idx={self.friend_id}")
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
                        diff_name = self.client.url_convert.diff(image_src) 
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
            "id": self.friend_id,
            "name": user_name[0].strip() if user_name else "N/A",
            "favorite": self.favorite,
            "icon": friend_icon,
            "rating": rating_int,
            "rating_block_url": rating_block_url[0] if rating_block_url else "N/A",
            "course_rank_url": course_rank_url[0] if course_rank_url else "N/A",
            "class_rank_url": class_rank_url[0] if class_rank_url else "N/A",
            "friend_title": friend_title,
            "tour_leader_img": tour_leader_img if tour_leader_img else "N/A",
            "recent_activity": activity_data
        }

        return Friend(self.client, friend_data)
    
    async def favorite(self, client):
        '''
        Marks this friend as a favorite. Does nothing if the friend is already a favorite.
        Args:
            client (Client): The client instance to use.
        '''
        raise NotImplementedError("Coming soon")

    async def unfavorite(self, client):
        '''
        Removes this friend from favorites. Does nothing if the friend is not a favorite.
        Args:
            client (Client): The client instance to use.
        '''
        raise NotImplementedError("Coming soon")
    
    async def register_rival(self, client):
        '''
        Registers friend as a rival. Raises an error if the rivals list is full (3).
        Args:
            client (Client): The client instance to use.
        '''
        raise NotImplementedError("Coming soon")
    
    async def unregister_rival(self, client):
        '''
        Unregisters friend as a rival.
        Args:
            client (Client): The client instance to use.
        '''
        raise NotImplementedError("Coming soon")