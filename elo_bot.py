#!/usr/bin/python3
"""
A robot that downloads stats for MNL creates an image to send to slack.
Intended to hurt diques feelings
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
except ImportError:
    plt = None

import requests
from slackclient import SlackClient

VELOCITY = 13
SHOOTOUT = 0.6
OVERTIME = 0.8

LOGGER = logging.getLogger(__name__)

SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
SLACK_CLIENT = SlackClient(SLACK_CLIENT_ID)
IMGUR_CLIENT_ID = os.environ.get('IMGUR_CLIENT_ID')


class Team:
    """
    Model to hold ELO histories of each team
    """
    def __init__(self, name, color):
        self.name = name
        self.elo = 1500
        self.history = []
        self.color = color

    def __str__(self):
        return self.name

    def win(self, change):
        self.history.append(self.elo)
        self.elo += change

    def lose(self, change):
        self.history.append(self.elo)
        self.elo -= change

    def full_history(self):
        return self.history + [self.elo]

    def num_games(self):
        return len(self.full_history())

    def last_game_up_or_down(self):
        if self.latest_change() < 0:
            return "goes down to"
        else:
            return "goes up to"

    def latest_change(self):
        return self.elo - self.history[-1]

    def last_game_explanation(self):
        return "{} rating {} {:.1f} ({:.1f})".format(
            self.name,
            self.last_game_up_or_down(),
            self.elo,
            self.latest_change())


NORTH_STARS = Team("North Stars", "green")
GOLDEN_SEALS = Team("Golden Seals", "cyan")
WHALERS = Team("Whalers", "blue")
NORDIQUES = Team("Nordiques", "red")

TEAMS = {team.name: team for team in [NORTH_STARS, GOLDEN_SEALS, WHALERS, NORDIQUES]}

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
        abs(goal_differential -.85 * ((home_team.elo - away_team.elo)/100)) + math.e -1))


def set_elos(winner, loser, change, winner_score, loser_score, overtime, shootout):
    LOGGER.info(("{winner_name} {winner_score} {loser_name} {loser_score}{overtime}{shootout}. "
                 "{winner_name} elo {winner_elo:.1f} + {change:.1f} "
                 "{loser_name} elo {loser_elo:.1f} - {change:.1f}").format(
                     winner_name=winner.name,
                     winner_elo=winner.elo,
                     loser_name=loser.name,
                     loser_elo=loser.elo,
                     winner_score=winner_score,
                     loser_score=loser_score,
                     change=change,
                     overtime=" (OT)" if overtime else "",
                     shootout=" (SO)" if shootout else ""))
    winner.win(change)
    loser.lose(change)


def process_game(row):
    home_team = TEAMS[row['Home Team']]
    away_team = TEAMS[row['Away Team']]
    home_team_score = get_score(row['Home Score'])
    away_team_score = get_score(row['Away Score'])
    overtime = get_overtime(row)
    shootout = get_shootout(row)
    margin = get_margin(home_team, away_team, home_team_score, away_team_score)
    outcome = get_outcome(home_team_score, away_team_score, overtime, shootout)
    expected = get_expected(home_team, away_team)
    change = VELOCITY * margin * (outcome - expected)

    if home_team_score > away_team_score:
        set_elos(home_team, away_team, change,
                 home_team_score, away_team_score,
                 overtime, shootout)
    elif away_team_score > home_team_score:
        set_elos(away_team, home_team, -change,
                 away_team_score, home_team_score,
                 overtime, shootout)


def print_elos(on_date):
    print(get_print_message(on_date))


def plot_elos():
    """
    Returns an in memory PNG of the picture of our teams ratings
    """
    assert plt != None, "Matplotlib was not able to be imported"
    legend = []
    sorted_teams = OrderedDict(sorted(TEAMS.items(), key=lambda t: -t[1].elo))
    colors = [team.color for team in sorted_teams.values()]

    plt.gca().set_color_cycle(colors)
    plt.title("MNL Elo, Velocity:{} OT:{} SO:{}".format(VELOCITY, OVERTIME, SHOOTOUT))
    for team in sorted_teams.values():
        plt.plot(range(team.num_games()), team.full_history())
        legend.append("{}: {}".format(team.name, int(team.elo)))
    plt.legend(legend, loc='upper left')
    buf = io.BytesIO()
    plt.savefig(buf)
    buf.seek(0)
    return buf


def get_print_message(on):
    message = "MNL Elo ratings for {:%m/%d/%Y}\n".format(on)
    sorted_teams = OrderedDict(sorted(TEAMS.items(), key=lambda t: -t[1].elo))
    for team in sorted_teams.values():
        message += team.last_game_explanation()+"\n"
    return message


def post_elos_to_slack(link, on, channel="tests"):
    SLACK_CLIENT.api_call(
        'chat.postMessage',
        channel=channel,
        text=get_print_message(on),
        attachments=[
            {
                "image_url":link,
                "title":"Current Elo ratings"
            }
        ],
        as_user=True)

def upload_picture_to_imgur(image):
    response = requests.post(
        "https://api.imgur.com/3/image",
        files={"image":image},
        headers={
            "Authorization": "Client-ID {}".format(IMGUR_CLIENT_ID)
        }
    )
    return response.json()['data']['link']

def get_raw_results_reader():
    response = requests.get(
        ("https://docs.google.com/spreadsheets"
         "/u/1/d/1JcjwMdsjzPI-WesV6l4O0eThWGVU"
         "AvN7-Z7lTrUG_iY/export?format=csv&"
         "id=1JcjwMdsjzPI-WesV6l4O0eThWGVUAvN7-Z7lTrUG_iY&gid=0"))
    buf = io.StringIO()
    buf.write(response.content.decode())
    buf.seek(0)
    return csv.DictReader(buf)

def process_results(results):
    for row in results:
        try:
            process_game(row)
        except IndexError:
            break

    last = datetime.datetime.strptime(row['Date'], "%m/%d/%Y") - datetime.timedelta(days=7)
    if ARGS.post:
        image = plot_elos()
        link = upload_picture_to_imgur(image)
        post_elos_to_slack(link, last, ARGS.channel)
    else:
        print_elos(last)

PARSER = argparse.ArgumentParser(
    description=("Download latest MNL results and calculate ratings and post to slack"))
PARSER.add_argument('--post', action='store_true')
PARSER.add_argument('--channel', default="tests")
ARGS = PARSER.parse_args()



if __name__ == '__main__':

    process_results(get_raw_results_reader())
