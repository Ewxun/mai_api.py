import aiohttp
import os


class Album:
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.name = data.get("name")
        self.time = data.get("time")
        self.difficulty = data.get("difficulty")
        self.image_url = data.get("image_url")
        self.location = data.get("location")

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
    def __init__(self, data: dict):
        '''
        Initializes a SongRecord object with the provided data.
        '''
        self.id = data.get("id")
        self.datetime = data.get("play_datetime")
        self.trackcount = data.get("play_trackcount")
        self.name = data.get("song_name")
        self.level = data.get("song_level")
        self.chart_type = data.get("song_type")
        self.difficulty = data.get("diff_name")
        self.score = data.get("song_score")
        self.score_rank = data.get("song_score_rank")
        self.dx_score = data.get("song_dx_score")
        self.dx_star = data.get("dx_star")
        self.cover_img = data.get("song_cover_img")
        self.vs_rank = data.get("vs_rank")
        self.stats = data.get("stats")

        self.raw_data = data

    async def get_details(self, client) -> dict:
        '''
        Fetches additional details about the song record using the provided client.
        Args:
            client (Client): The client instance to use for fetching the details.
        Returns:
            dict: A dictionary containing additional details about the song record.
        '''
        details_path = "record/playlogDetail/?idx=" + self.id
        raise NotImplementedError("This method will be implemented to fetch additional song record details soon.")
