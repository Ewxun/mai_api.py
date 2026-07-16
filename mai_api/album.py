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
        
