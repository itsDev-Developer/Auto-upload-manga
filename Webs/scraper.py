import requests
from cloudscraper import create_scraper
from asyncio import to_thread


class Scraper:
  def __init__(self):
    self.scraper = create_scraper()
    
  async def get(self, url, rjson=None, cs=None, *args, **kwargs):
      if cs:
        response = await to_thread(self.scraper.get, url, *args, **kwargs)
      
      else:
        response = await to_thread(requests.get, url, *args, **kwargs)
        response.raise_for_status()
      
      if response.status_code == 200:
        return response.json() if rjson else response.text
      else:
        return None
  
  async def post(self, url, rjson=None, cs=None, *args, **kwargs):
    if cs:
      response = await to_thread(self.scraper.post, url, *args, **kwargs)

    else:
      response = await to_thread(requests.post, url, *args, **kwargs)
      response.raise_for_status()

    if response.status_code == 200:
      return response.json() if rjson else response.text
    else:
      return None
    
    
    
    
  
