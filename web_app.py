"""
flask frontend for mnl_bot, ya know instead of working
"""

from flask import Flask
from mnl_elo_bot.elo_bot import (
    get_raw_results_reader,
    process_results,
    upload_picture_to_imgur,
    plot_elos,
    post_elos_to_slack
)
app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello world!"


@app.route("/run")
def run_bot():
    last = process_results(get_raw_results_reader())
    link = upload_picture_to_imgur(plot_elos())
    post_elos_to_slack(link, last, "tests", "")
    return "hello i ran"


if __name__ == '__main__':
    app.run()
