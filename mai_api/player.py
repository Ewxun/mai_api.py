
class BasePlayer:
    '''Base class for player representation.'''
    def __init__(self):
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
        self.cource_rank_url = None
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
        self.cource_rank_url = data.get("cource_rank_url")
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
        

class Friend(BasePlayer):
    '''
    Represents a friend of the player.
    '''
    def __init__(self):
        super().__init__()