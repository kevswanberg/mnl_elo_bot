#!/usr/bin/python3
"""
A robot that downloads stats for MNL creates an image to send to slack.
Intended to hurt diques feelings
F#&$ You, Kevan
Wow this stopped working
"""
import argparse
import csv
import datetime
import io
import logging
import math
import png
import numpy

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
LOGGER.setLevel(logging.DEBUG)

SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
SLACK_CLIENT = SlackClient(SLACK_CLIENT_ID)
IMGUR_CLIENT_ID = os.environ.get('IMGUR_CLIENT_ID')
CSV_ID = "1MWKxBdUF8HegOtyjkznthRbGB42F2xrUD_Iryzv7ShQ"


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

    def win(self, change):
        self.history.append(self.elo + change)

    def lose(self, change):
        self.history.append(self.elo - change)

    @property
    def latest_change(self):
        if len(self.history) < 2:
            return 0.0
        return self.elo - self.history[-2]

    def last_game_explanation(self):
        if self.latest_change > 0:
            return "{} rating goes up to {:.1f} ({:.1f})".format(
                self.name,
                self.elo,
                self.latest_change
            )
        elif self.latest_change < 0:
            return "{} rating goes down to {:.1f} ({:.1f})".format(
                self.name,
                self.elo,
                self.latest_change
            )
        else:
            "{} rating is at {}".format(self.name, self.elo)


NORTH_STARS = Team("North Stars", "#000000", ":north-stars:")
GOLDEN_SEALS = Team("Golden Seals", "#ffd966", ":seals:")
NORDIQUES = Team("Nordiques", "#a4c2f4", ":nordiques:")
WHALERS = Team("Whalers", "#6aa84f", ":whalers:")
MIGHTY_DUCKS = Team("Mighty Ducks", "#b4a7d6", ":mighty_ducks:")
AMERICANS = Team("Americans", "#dd7e6b", ":america:")

TEAMS = {team.name: team for team in [
    NORTH_STARS,
    GOLDEN_SEALS,
    NORDIQUES,
    WHALERS,
    MIGHTY_DUCKS,
    AMERICANS
]}


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
    else:
        raise Exception('THERE ARE NO TIES')


def print_elos(on_date):
    print(get_print_message(on_date))


def plot_elos():
    """
    Returns an in memory PNG of the picture of our teams ratings
    """
    assert plt is not None, "Matplotlib was not able to be imported"
    legend = []
    sorted_teams = OrderedDict(sorted(TEAMS.items(), key=lambda t: -t[1].elo))
    colors = [team.color for team in sorted_teams.values()]

    plt.gca().set_prop_cycle('color', colors)

    plt.title("MNL Elo, Velocity:{} OT:{} SO:{}".format(VELOCITY, OVERTIME, SHOOTOUT))
    for team in sorted_teams.values():
        plt.plot(range(len(team.history)), team.history)
        legend.append("{}: {}".format(team.name, int(team.elo)))
    plt.xticks(range(len(team.history)))
    plt.legend(legend, loc='upper left')
    buf = io.BytesIO()
    plt.savefig(buf)
    buf.seek(0)
    return buf


def get_print_message(on):
    winner_icons = []
    message = ARGS.message + "\n" if ARGS.message else ""
    message += "MNL Elo ratings for {:%m/%d/%Y}\n".format(on)
    for team in TEAMS.values():
        if team.latest_change > 0:
            winner_icons.append(team.emoji)

    message += "  ".join(winner_icons)
    message += "\n"
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
            "Authorization": "Client-ID {}".format(IMGUR_CLIENT_ID)
        }
    )
    if response.status_code == 200:
        return response.json()['data']['link']
    else:
        raise Exception("Couldn't upload picture response \n{}".format(response.content.decode()))


def get_raw_results_reader():
    response = requests.get(
        "https://docs.google.com/spreadsheets/d/{}/export?format=csv&gid=834633730".format(
            CSV_ID
        )
    )
    buf = io.StringIO()
    buf.write(response.content.decode())
    buf.seek(0)
    return csv.DictReader(buf)


def process_results(results):
    for row in results:
        try:
            if not row.get('Home Team'):  # bye week
                continue
            process_game(row)
        except IndexError:
            break
    last = datetime.datetime.strptime(row['Date'], "%m/%d/%Y") - datetime.timedelta(days=7)
    image = plot_elos()
    if ARGS.post:
        link = upload_picture_to_imgur(image)
        post_elos_to_slack(link, last, ARGS.channel)
    if ARGS.save:
        with open('out.png', 'wb') as out:
            reader = png.Reader(image)
            w, h, pixels, metadata = reader.read_flat()
            p = set()
            for y, row in enumerate(numpy.array_split(pixels, 480)[-1:]):
                for x, col in enumerate(numpy.array_split(pixels, len(pixels)/4)):
                    p.add(tuple(col))
            print(len(p))

    else:
        print_elos(last)


PARSER = argparse.ArgumentParser(
    description=("Download latest MNL results and calculate ratings and post to slack"))
PARSER.add_argument('--post', action='store_true')
PARSER.add_argument('--channel', default="tests")
PARSER.add_argument('--message', default=None)
PARSER.add_argument('--save', action='store_true', default=False)

ARGS = PARSER.parse_args()


if __name__ == '__main__':
    process_results(get_raw_results_reader())
