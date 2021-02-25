#!/usr/bin/python3
"""
A robot that downloads stats for MNL creates an image to send to slack.
Intended to hurt diques feelings
F#&$ You, Kevan
Wow this stopped working... nvm, it's working again
"""
import argparse
import csv
import datetime
import io

import logging
import math
from collections import OrderedDict
import os

try:
    import matplotlib.pyplot as plt
except ImportError as e:
    print(e)
    plt = None

import requests
from slack import WebClient

VELOCITY = 13
SHOOTOUT = 0.6
OVERTIME = 0.8

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
SLACK_CLIENT = WebClient(SLACK_CLIENT_ID)
IMGUR_CLIENT_ID = os.environ.get('IMGUR_CLIENT_ID')
CSV_ID = "1txfiFqoekWQFO1yJDyV1sgTzereo_cNBm-V6OIJ0Nww"


class Team:
    """
    Model to hold ELO histories of each team
    """
    def __init__(self, name, color, emoji):
        self.name = name
        self.history = [1500]
        self.color = color
        self.emoji = emoji

    @property
    def elo(self):
        return self.history[-1]

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def win(self, change):
        self.history.append(self.elo + change)

    def lose(self, change):
        self.history.append(self.elo - change)

    def bye_week(self):
        self.history.append(self.elo)

    @property
    def latest_change(self):
        if len(self.history) < 2:
            return 0.0
        return self.elo - self.history[-2]

    def last_game_explanation(self):
        if self.latest_change > 0:
            return f"{self.name} rating goes up to {self.elo:.1f} ({self.latest_change:.1f})"
        elif self.latest_change < 0:
            return f"{self.name} rating goes down to {self.elo:.1f} ({self.latest_change:.1f})"
        else:
            return f"{self.name} rating is at {self.elo:.1f}"


def get_score(score):
    """
    Get the score in the from the csv string
    """
    return int(score.split()[0])


def get_shootout(row):
    """
    Whether or not the game was decided in a shootout
    """
    return ('SO' in row['Home Score']) or ('SO' in row['Away Score'])


def get_overtime(row):
    """
    Whether or not the game was decided in overtime
    """
    return ('OT' in row['Home Score']) or ('OT' in row['Away Score'])


def get_outcome(home_team_score, away_team_score, overtime, shootout):
    """
    Gets the actual value of the game
    """
    if not shootout and home_team_score > away_team_score:
        return 1
    elif overtime and home_team_score > away_team_score:
        return OVERTIME
    elif overtime and away_team_score > home_team_score:
        return 1 - OVERTIME
    elif shootout and home_team_score > away_team_score:
        return SHOOTOUT
    elif shootout and away_team_score > home_team_score:
        return 1 - SHOOTOUT
    else:
        return 0


def get_expected(home_team, away_team):
    """
    get the expected value of a game
    """
    return 1.0 / (1.0 + 10.0 ** (-(home_team.elo - away_team.elo)/400))


def get_margin(home_team, away_team, home_team_score, away_team_score):
    """
    Get the multiplier for the margin of victory
    """
    goal_differential = home_team_score - away_team_score
    return max(1, math.log(
        abs(goal_differential - .85 * ((home_team.elo - away_team.elo)/100)) + math.e - 1)
    )


def process_game(row, teams):
    home_team = teams[row['Home Team']]
    away_team = teams[row['Away Team']]
    home_team_score = get_score(row['Home Score'])
    away_team_score = get_score(row['Away Score'])
    overtime = get_overtime(row)
    shootout = get_shootout(row)
    margin = get_margin(home_team, away_team, home_team_score, away_team_score)
    outcome = get_outcome(home_team_score, away_team_score, overtime, shootout)
    expected = get_expected(home_team, away_team)
    change = abs(VELOCITY * margin * (outcome - expected))

    if home_team_score > away_team_score:
        winner = home_team
        loser = away_team
    elif away_team_score > home_team_score:
        winner = away_team
        loser = home_team
    else:
        raise Exception('THERE ARE NO TIES')

    winner.win(change)
    loser.lose(change)

    return home_team, away_team


def print_elos(teams, on_date, message):
    print(get_print_message(teams, on_date, message))


def plot_elos(teams):
    """
    Returns an in memory PNG of the picture of our teams ratings
    """
    assert plt is not None, "Matplotlib was not able to be imported"
    legend = []
    sorted_teams = OrderedDict(sorted(teams.items(), key=lambda t: -t[1].elo))
    colors = [team.color for team in sorted_teams.values()]

    plt.gca().set_prop_cycle('color', colors)

    plt.title(f"MNL Elo, Velocity:{VELOCITY} OT:{OVERTIME} SO:{SHOOTOUT}")
    for team in sorted_teams.values():
        plt.plot(range(len(team.history)), team.history)
        legend.append(f"{team.name}: {team.elo:.1f}")
    plt.xticks(range(len(team.history)))
    plt.legend(legend, loc='upper left')
    buf = io.BytesIO()
    plt.savefig(buf)
    buf.seek(0)
    return buf


def get_print_message(teams, on, message):
    winner_icons = []
    message += f"MNL Elo ratings for {on:%m/%d/%Y}\n"
    for team in teams.values():
        if team.latest_change > 0:
            winner_icons.append(team.emoji)

    message += "  ".join(winner_icons)
    message += "\n"
    sorted_teams = OrderedDict(sorted(teams.items(), key=lambda t: -t[1].elo))
    for team in sorted_teams.values():
        message += team.last_game_explanation()+"\n"

    return message


def post_elos_to_slack(teams, link, on, channel="tests", message=""):
    SLACK_CLIENT.chat_postMessage(
        channel=channel,
        text=get_print_message(teams, on, message),
        attachments=[
            {
                "image_url": link,
                "title": "Current Elo ratings"
            }
        ],
        as_user=True)


def upload_picture_to_imgur(image):
    response = requests.post(
        "https://api.imgur.com/3/image",
        files={"image": image},
        headers={
            "Authorization": f"Client-ID {IMGUR_CLIENT_ID}"
        },
        timeout=5
    )
    if response.status_code == 200:
        return response.json()['data']['link']
    else:
        raise Exception(f"Couldn't upload picture response \n{response.content.decode()}")


def get_raw_results_reader():
    response = requests.get(
        f"https://docs.google.com/spreadsheets/d/{CSV_ID}/export?format=csv&gid=834633730",
        timeout=2
    )
    buf = io.StringIO()
    buf.write(response.content.decode())
    buf.seek(0)
    return csv.DictReader(buf)


def process_results(teams, results):
    """
    Populate the teams dictionary with the ELOS after the results of each game.
    returns the date of the latest game played
    """
    games = 0
    weekly_teams_played = []
    last_game_date = None
    for row in results:
        try:
            if not row.get('Home Team'):  # bye week
                continue
            weekly_teams_played.extend(process_game(row, teams))
            games += 1
        except IndexError:
            break
        except KeyError:
            continue

        if games % 3 == 0:  # finished the week
            last_game_date = row['Date']
            odd_team_out = list(set(teams.values()) - set(weekly_teams_played))[0]
            odd_team_out.bye_week()
            weekly_teams_played = []

    return datetime.datetime.strptime(last_game_date, "%m/%d/%Y")


def main(post, channel, message):
    teams = {team.name: team for team in [
        Team("Americans", "#FF0000", ":america:"),
        Team("Tigers", "#F1C232", ":tigers:"),
        Team("Maroons", "#660000", ":maroons:"),
        Team("North Stars", "#6AA84F", ":north_stars:"),
        Team("Golden Seals", "#000000", ":seals:"),
        Team("Whalers", "#0000FF", ":whalers:"),
        Team("Nordiques", "#999999", ":nordiques:")
    ]}
    reader = get_raw_results_reader()
    last = process_results(teams, reader)

    if post:
        image = plot_elos(teams)
        link = upload_picture_to_imgur(image)
        post_elos_to_slack(teams, link, last, channel, message)
    else:
        print_elos(teams, last, message)


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(
        description=("Download latest MNL results and calculate ratings and post to slack"))
    PARSER.add_argument('--post', action='store_true')
    PARSER.add_argument('--channel', default="tests")
    PARSER.add_argument('--message', default="")

    ARGS = PARSER.parse_args()

    main(ARGS.post, ARGS.channel, ARGS.message)
