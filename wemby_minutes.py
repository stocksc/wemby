import streamlit as st
import pandas as pd
import numpy as np
import sportsdataverse.nba as nba
from datetime import datetime, timedelta

st.title("👽 Wemby Minutes 👽")

# Get 2026 box scores
season_games_df = nba.load_nba_team_boxscore(seasons=2026, return_as_pandas=True)

# Get spurs games
spurs_games = season_games_df.loc[season_games_df['team_name']=="Spurs"]

# Get recent spurs games
n_days_recent = 7
recent_days = []
for n in range(n_days_recent):
    recent_days += [str(datetime.now() - timedelta(n+1))[0:10]]
spurs_games = spurs_games.loc[spurs_games['game_date'].isin(recent_days)]

game_ids = list(spurs_games['game_id'])
len(game_ids)

# Play by play for recent spurs games
all_games = {}
for game_id in game_ids:
    
    # Basic game info
    game = spurs_games.loc[spurs_games['game_id'] == game_id]
    if game['team_home_away'].values[0] == "home":
        game_title = f"Spurs vs {game['opponent_team_name'].values[0]}"
    else:
        game_title = f"Spurs at {game['opponent_team_name'].values[0]}"
    game_title = game_title + f" ({game['game_date'].values[0]})"
    st.subheader(game_title)

    # API pull
    all_games[game_id] = nba.espn_nba_pbp(game_id=game_id)
    pbp = pd.DataFrame(all_games[game_id]['plays'])

    # Box score spoilers
    box = pd.DataFrame(columns=all_games[game_id]['boxscore']['players'][0]['statistics'][0]['names'])
    for team in [0, 1]:
        for player in all_games[game_id]['boxscore']['players'][team]['statistics'][0]['athletes']:
            if player['athlete']['id'] == "5104157":
                box.loc[0] = player['stats']
    box[['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PF']] = box[['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PF']].astype(int)

    # Game rating
    chili_peps = ""
    if box['PTS'].values[0] >= 25:
        chili_peps += "🔥"
    if box['PTS'].values[0] >= 30:
        chili_peps += "🔥"
    if box['PTS'].values[0] >= 35:
        chili_peps += "🔥"
    if box['PTS'].values[0] >= 40:
        chili_peps += "🔥"
    if (box[['PTS', 'REB', 'AST', 'STL', 'BLK']] >= 10).sum().sum() >= 3:
        chili_peps += "🔥🔥"
    if box['BLK'].values[0] >= 5:
        chili_peps += "🔥"

    with st.expander("Stats "+chili_peps):
        st.dataframe(box, hide_index=True)

    # Get Wemby sub patterns
    subs = pbp.loc[pbp['type.text']=='Substitution']
    wemby_subs = subs.loc[(subs['participants.0.athlete.id']=="5104157") | (subs['participants.1.athlete.id']=="5104157")].copy()
    wemby_subs = wemby_subs[['qtr', 'time', 'wallclock', 'end.game_seconds_remaining', 'text']]

    # If there are no Wemby subs, assume he didn't play
    if wemby_subs.shape[0] == 0:
        st.text("Wemby did not play.")
        continue
    
    # Define subs in vs out
    wemby_subs['subbed_out'] = wemby_subs['text'].str.endswith("enters the game for Victor Wembanyama")

    # Add entries for start/end of game (assumes he started)
    wemby_subs = pd.concat([wemby_subs, pd.DataFrame(data={
        'qtr':['1', '4'],
        'time':['12:00', '0:00'],
        'wallclock':[pbp.head(1)['wallclock'].values[0], pbp.tail(1)['wallclock'].values[0]],
        'end.game_seconds_remaining':[12*60*4, 0],
        'subbed_out':[False, True]
    })])
    wemby_subs.sort_values(['end.game_seconds_remaining'], ascending=False, inplace=True)

    # Friendlier formatted timestamp
    wemby_subs['timestamp'] = "Q" + wemby_subs['qtr'].astype(str) + "-" + wemby_subs['time'].astype(str)

    # Make sub patterns log
    play_log = pd.DataFrame(columns = ['Play', 'Sit'])
    play_count = 0
    sit_count = 0
    for i in range(len(wemby_subs)):
        
        if wemby_subs.iloc[i]['subbed_out'] == False:
            
            # Count playtime from sub in to sub out
            play_log.loc[play_count, "Play"] = f"Played from [{wemby_subs.iloc[i]['timestamp']}] to [{wemby_subs.iloc[i+1]['timestamp']}]   "
            play_count += 1

            # Only print sit time if he will sub in later
            if False in list(wemby_subs['subbed_out'][i+1:]):
                fmt = "%Y-%m-%dT%H:%M:%SZ"
                sit_time = datetime.strptime(wemby_subs.iloc[i+1]['wallclock'], fmt) - datetime.strptime(wemby_subs.iloc[i]['wallclock'], fmt) 
                sit_seconds = sit_time.total_seconds()
                display_seconds = str(int(sit_seconds % 60))
                if len(display_seconds) == 1:
                    display_seconds = "0"+display_seconds
                sit_string = f"Sat for [{int(sit_seconds // 60)}:{display_seconds}] of real time ({int((sit_seconds/15)//1)} skips)   " 
                play_log.loc[sit_count, "Sit"] = sit_string
                sit_count += 1
            elif wemby_subs.iloc[i+1]['end.game_seconds_remaining'] != 0:
                play_log.loc[sit_count, "Sit"] = "Sat for the rest of the game"
                sit_count += 1

    with st.expander("See sit/play log"):
        st.dataframe(play_log, hide_index=True, column_config={"0":"Stretches"})