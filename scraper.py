import requests, time
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO


class PremierLeagueScraper:
    def __init__(self):
        self.all_matches = []
        self.standings_url = "https://fbref.com/en/comps/9/Premier-League-Stats"

    def send_request(self,url,penalty):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        while True:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()  # Raise an error for bad responses
                return response, penalty
            except:
                print(f"Error fetching {url}. Status code: {getattr(response, 'status_code', 'N/A')}. Retrying in {penalty} seconds...")
                penalty *= 2
                if penalty > 60:  # Cap the penalty to avoid excessive waiting
                    penalty = 60
                time.sleep(penalty)

    def get_team_stats(self, years=list(range(2025,2020,-1))):
        for year in years:
            penalty = 2
            response, penalty = self.send_request(self.standings_url,penalty)
            soup = BeautifulSoup(response.text, 'html.parser')
            standings_table = soup.select('table.stats_table')[0]

            links = [link.get('href') for link in standings_table.find_all('a', href=True)]
            links = [link for link in links if '/squads/' in link]
            team_urls = [f"https://fbref.com{link}" for link in links]

            previous_season = soup.select('a.prev')[0].get('href')
            self.standings_url = f"https://fbref.com/{previous_season}"

            for team_url in team_urls:
                team_name = team_url.split('/')[-1].replace('-Stats', '').replace('-', ' ').title()

                response, penalty = self.send_request(team_url, penalty)
                matches = pd.read_html(StringIO(response.text), match='Scores & Fixtures')[0]

                soup = BeautifulSoup(response.text, 'html.parser')
                links = [link.get('href') for link in soup.find_all('a', href=True)]
                links = [link for link in links if link and '/all_comps/shooting/' in link]
                response, penalty = self.send_request(f"https://fbref.com{links[0]}",penalty)
                shooting = pd.read_html(StringIO(response.text), match='Shooting')[0]
                shooting.columns = shooting.columns.droplevel()

                try:
                    team_data = matches.merge(shooting[['Date', 'Sh', 'SoT', 'Dist','FK', 'PK', 'PKatt']], on='Date')
                except ValueError:
                    continue

                team_data = team_data[team_data['Comp'] == 'Premier League']
                team_data['Team'] = team_name
                team_data['Season'] = year
                self.all_matches.append(team_data)
                


        match_df = pd.concat(self.all_matches)
        match_df.columns = [c.lower() for c in match_df.columns]

        match_df.to_csv('matches.csv', index=False)
        
        

        








if __name__ == "__main__":

    url = "https://fbref.com/en/comps/9/Premier-League-Stats"
    scraper = PremierLeagueScraper()
    team_urls = scraper.get_team_stats()
    print("Scraping completed. Data saved to 'matches.csv'.")