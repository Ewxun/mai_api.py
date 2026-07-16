
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
    def __init__(self):
        super().__init__()
        self.course_rank_url = None
        self.class_rank_url = None
        self.nameplate_url = None

        self.tour_leader_img = None
        self.stats = {}
        self.play_counts = {"current": 0, "total": 0}
        self.maimiles = 0
        self.tickets = {
            "area_bonus": 0,
            "weekly_bonus": 0,
            "character_level": 0
        }
        self.presents = 0

        self.raw_data = None  # Store the raw data for debugging or further processing

    def _construct_from_dict(self, data: dict):
        self.name = data.get("name")
        self.rating = data.get("rating")
        self.rating_block = data.get("rating_block")
        self.course_rank_url = data.get("course_rank_url")
        self.class_rank_url = data.get("class_rank_url")
        self.icon_url = data.get("icon_url")
        self.nameplate_url = data.get("nameplate_url")

        self._trophy_url = data.get("trophy_url")
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

        self.raw_data = data

        return self

class CircleMember(BasePlayer):
    '''
    Represents a member of a circle.
    '''
    def __init__(self):
        super().__init__()
        

class FriendPartial(BasePlayer):
    '''
    Represents friend data fetched from the friend list, which does not contain all details.
    '''
    def __init__(self):
        super().__init__()
        self.friend_id = None
        self.favorite = False

        self.course_rank_url = None
        self.class_rank_url = None
        self.icon_url = None

    def _construct_from_dict(self, data: dict):
        self.friend_id = data.get("id")
        self.name = data.get("name")
        self.icon_url = data.get("icon")
        self.rating = data.get("rating")
        self.rating_block = data.get("rating_block")
        self.title = data.get("title", {"text": None, "rarity": None})
        self.favorite = data.get("favorite", False)

        return self
    
    async def fetch_details(self, client) -> 'FriendPartial':
        '''
        Fetches the full details of the friend from the details page. Returns a Friend object.
        Args:
            client (Client): The client instance to use for fetching the details.
        Returns:
            Friend: The full details of the friend.
        '''
        return await client.fetch_friend_details(self)
    
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
    

class Friend(FriendPartial):
    '''
    Represents friend fetched from the friend details endpoint. Does not have favorite status, as that is only available from the friend list.
    '''
    def __init__(self):
        super().__init__()
        self.course_rank_url = None
        self.class_rank_url = None
        self.nameplate_url = None
        self.tour_leader_img = None
        self.recent_activity = []
        
    def _construct_from_dict(self, data: dict):
        super()._construct_from_dict(data)
        self.course_rank_url = data.get("course_rank_url")
        self.class_rank_url = data.get("class_rank_url")
        self.nameplate_url = data.get("nameplate_url")
        self.tour_leader_img = data.get("tour_leader_img")
        self.recent_activity = data.get("recent_activity", [])
        return self