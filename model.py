import pandas as pd
from sklearn.svm import SVC
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score, precision_score
import random




# Custom dictionary class to handle missing keys gracefully
class MissingDict(dict):
    __missing__ = lambda self, key: key  # Return the key itself if it's not found in the dictionary


# Mapping of team names to their standardized versions
map_values = {
    "Brighton and Hove Albion": "Brighton",
    'Brighton And Hove Albion': "Brighton",
    'Manchester Utd': "Manchester United",
    "Newcastle United": "Newcastle",
    'Newcastle Utd': "Newcastle",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves",
    'Sheffield Utd': "Sheffield United",
    'West Bromwich Albion': "West Brom",
    "Nott'ham Forest": "Nottingham Forest",
    'Aston Villa': "Aston Villa"
}

# Create a mapping dictionary to standardize team names using the MissingDict class
mapping = MissingDict(**map_values)

# Load match data from CSV file into a DataFrame
matches = pd.read_csv('datasets/final_matches.csv')

# Map team and opponent names using the defined mapping
matches['team'] = matches['team'].map(mapping)
matches['opponent'] = matches['opponent'].map(mapping)

# Convert date column to datetime format and sort by date
matches['date'] = pd.to_datetime(matches['date'])
matches = matches.sort_values('date').reset_index(drop=True)

# Encode categorical variables for venue and teams
matches['venue_code'] = matches['venue'].astype('category').cat.codes  # Venue encoding
matches['team_code'] = matches['team'].astype('category').cat.codes  # Team encoding

# Extract hour from time string (removing minutes) and convert to integer
matches['hour'] = matches['time'].str.replace(':.+', "", regex=True).astype(int)

# Get day of the week as a numerical value (0=Monday, 6=Sunday)
matches['day_code'] = matches['date'].dt.dayofweek

# Create target variable based on match result ('W' for win, else -1 for loss)
matches['target'] = matches['result'].apply(lambda x: 1 if x == 'W' else -1)




def rolling_average(group, cols, new_cols):
    # Sort the group by date to ensure the rolling calculations are in chronological order
    group = group.sort_values('date')
    
    # Calculate rolling averages for specified columns
    rolling_stats = group[cols].rolling(3, closed='left').mean()
    group[new_cols] = rolling_stats

    # Define points mapping based on match results
    result_to_points = {'W': 3, 'D': 1, 'L': 0}
    
    # Map results to points and calculate a rolling sum of points for form
    points = group['result'].map(result_to_points)
    group['form_rolling'] = points.rolling(3, closed='left').sum()

    # Drop rows with NaN values in the newly created columns and form_rolling column
    group = group.dropna(subset=new_cols + ['form_rolling'])
    
    return group

# List of statistic columns for which to calculate rolling averages
cols = ['gf', 'ga', 'xga', 'xg', 'poss', 'sh', 'sot', 'dist', 'fk', 'pk', 'pkatt']
new_cols = [f'{col}_rolling' for col in cols]  # Create new column names for rolling stats

# Group matches by team and apply the rolling_average function to each team’s data
grouped_matches = matches.groupby('team')
matches_rolling = grouped_matches.apply(lambda x: rolling_average(x, cols, new_cols))

# Remove the multi-level index created by grouping 
matches_rolling = matches_rolling.droplevel('team')

# Reset index to have a clean integer index after applying the function
matches_rolling.index = range(matches_rolling.shape[0])

# Sort the resulting DataFrame by date to maintain chronological order
matches_rolling.sort_values('date', inplace=True)



# Create a match_id by sorting team/opponent and combining with date
def get_match_id(row):
    # Sort teams to ensure consistency in match ID (home vs. away)
    teams = sorted([row['team'], row['opponent']])
    
    # Ensure the date is formatted as a string in YYYY-MM-DD format
    date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
    
    # Create and return the match ID in the format: "YYYY-MM-DD_team1_team2"
    return f"{date_str}_{teams[0]}_{teams[1]}"

# Apply the get_match_id function to each row of matches_rolling DataFrame
matches_rolling['match_id'] = matches_rolling.apply(get_match_id, axis=1)

# Count occurrences of each match_id
match_id_counts = matches_rolling['match_id'].value_counts()

# Filter out rows where the match_id appears only once (keeping those that appear more than once)
matches_rolling = matches_rolling[matches_rolling['match_id'].map(match_id_counts) > 1].reset_index(drop=True)



df = matches_rolling.iloc[:, [0,9] + list(range(26, matches_rolling.shape[1]))]

# Merge the DataFrame with itself on match_id
merged_df = pd.merge(
    df,
    df,
    on='match_id',
    suffixes=('_home', '_away')
)

# Filter out self-merging by ensuring home and away teams are different
merged_df = merged_df[merged_df['team_home'] != merged_df['team_away']].reset_index(drop=True)



# Initialize the Support Vector Classifier with RBF kernel
rf = SVC(kernel='rbf', C=1, random_state=1)

# List of predictor features to use for training the model
predictors = ['venue_code_home', 'team_code_home', 'team_code_away', 'day_code_home','gf_rolling_home', 'gf_rolling_away',
              'ga_rolling_home', 'ga_rolling_away', 'xga_rolling_home', 'xga_rolling_away', 'xg_rolling_home', 'xg_rolling_away',
              'sh_rolling_home', 'sh_rolling_away', 'sot_rolling_home', 'sot_rolling_away', 'dist_rolling_home', 'dist_rolling_away',
              'fk_rolling_home', 'fk_rolling_away', 'pk_rolling_home', 'pk_rolling_away', 'pkatt_rolling_home', 'pkatt_rolling_away',
              'form_rolling_home', 'form_rolling_away']

# Define the season for which we want to test the model
season = 2023

# Split the dataset into training and testing sets based on season
train = merged_df[merged_df['season_home'] != season]  # Training data (not in test season)
test = merged_df[merged_df['season_home'] == season]   # Testing data (specific test season)

# Perform cross-validation on the training set and calculate accuracy scores
scores = cross_val_score(rf, train[predictors], train['target_home'], cv=5, scoring='accuracy')
print(f"Cross-validation accuracy: {scores.mean():.2f}")

# Fit the model on the training data
rf.fit(train[predictors], train['target_home'])

# Make predictions on the test set
preds = rf.predict(test[predictors])

# Calculate accuracy and precision of predictions on the test set
acc = accuracy_score(test['target_home'], preds)
precision = precision_score(test['target_home'], preds)

# Print out Test Accuracy and Precision results
print(f"Test Accuracy: {acc:.2f}, Test Precision: {precision:.2f}")




# Create a DataFrame to store results of the test predictions
results_df = pd.DataFrame({
    'date': test['date_home'],
    'Team': test['team_home'],
    'Opponent': test['team_away'],
    'Actual': test['target_home'],
    'Predicted': preds,
}).sort_values('date').reset_index(drop=True)

# Get the unique list of teams from the results DataFrame
team_list = results_df['Team'].unique().tolist()
team_points = []  # Initialize a list to hold points for each team

# Calculate points for each team based on match outcomes
for team in team_list:
    point = 0  # Initialize points for the current team
    
    # Filter data for home games and away games for the current team
    team_home_data = results_df[results_df['Team'] == team]
    team_away_data = results_df[results_df['Opponent'] == team]

    # Iterate through each home game played by the current team
    for index, row in team_home_data.iterrows():
        # Find the corresponding away game on the same date
        similar_game = team_away_data[team_away_data['date'] == row['date']].iloc[0]
        
        pred1 = row['Predicted']
        pred2 = similar_game['Predicted']
        
        # Points calculation based on predictions matching or not
        if pred1 == pred2:  # Predictions match between home and away games
            if random.random() < 0.5:  # Randomly decide to award points with a probability of 50%
                if random.random() < 1/3:  # One-third chance to award 3 points, otherwise award 1 point
                    point += 3
                else:
                    point += 1

        elif row['Predicted'] == 1:  # If home team's prediction is a win (1)
            point += 3
            
    # Append calculated points for the current team to the list
    team_points.append({'Team': team, 'Points': point})

# Sort teams by their total points in descending order
team_points = sorted(team_points, key=lambda x: x['Points'], reverse=True)

# Create a DataFrame to represent the ranking table of teams based on total points 
team_ranking = pd.DataFrame(team_points)

# Displaying final ranking table of teams with their respective points
print(team_ranking)

