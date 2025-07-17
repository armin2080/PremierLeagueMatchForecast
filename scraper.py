import requests
from bs4 import BeautifulSoup

class PremierLeagueScraper:
    def __init__(self):
        pass

    def get_team_urls(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for bad responses
            soup = BeautifulSoup(response.text, 'html.parser')
            standings_table = soup.select('table.stats_table')[0]
            links = standings_table.find_all('a', href=True)
            links = [link['href'] for link in links if 'href' in link.attrs]
            links = [link for link in links if '/squads/' in link]
            team_urls = [f"https://fbref.com{link}" for link in links]

            return team_urls
        except:
            print(f"An error occurred.")
            return None
        








if __name__ == "__main__":

    url = "https://fbref.com/en/comps/9/Premier-League-Stats"
    scraper = PremierLeagueScraper()
    team_urls = scraper.get_team_urls(url)
    print(team_urls)