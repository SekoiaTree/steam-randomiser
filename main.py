#!/usr/bin/env python3
import argparse
import random
import re
import requests


def steam_api_call_json(template, url_tokens):
    """Make a steam api call and return the json result, or throw a ValueError exception."""
    url = ("http://api.steampowered.com/" + template).format(**url_tokens)
    r = requests.get(url)
    if r.status_code != 200:
        raise ValueError("Status code of request is not 200.")
    return r.json()


def get_id_from_vanity(key, vanity):
    """Get a user_id from a provided vanity url name, or throw a ValueError exception."""
    template = "ISteamUser/ResolveVanityURL/v0001/?key={key}&vanityurl={vanity}"
    json = steam_api_call_json(template, {"key": key, "vanity": vanity})
    if json["response"]["success"] != 1:
        raise ValueError("Failed to get Steam ID from vanity name.")
    return json["response"]["steamid"]


def get_owned_games(key, steam_id):
    """Get the list of owned games for a user."""
    template = "IPlayerService/GetOwnedGames/v0001/?key={key}&steamid={id}&include_appinfo=1"
    return steam_api_call_json(template, {"key": key, "id": steam_id})["response"]["games"]


def parse_id_input(id_input, api_key):
    """Accept multiple forms of user id input and return the 17 character form."""
    if re.match(r'^[0-9]{17}$', id_input):  # if input matches correct form
        return id_input
    elif re.search(r'profiles/([0-9]{17})$', id_input):  # if using url with steamid64
        return re.search(r'profiles/([0-9]{17})$', id_input).group(1)
    elif re.search(r'id/(.*)$', id_input):  # if using url with vanity id
        vanity = re.search(r'id/(.*)$', id_input).group(1)
        return get_id_from_vanity(api_key, vanity)
    else:  # assume it is a vanity ID
        return get_id_from_vanity(api_key, id_input)


def pick_random_game(key, user_id, all_games=False, time_played=0):
    """Pick a random game from a user's library."""
    # convert user_id input into steam id 64 format
    steam_id = parse_id_input(user_id, key)

    # get games list, get list of unplayed games, pick one randomly and print
    owned_games = get_owned_games(key, steam_id)
    if all_games:
        selectable_games = owned_games
    else:
        selectable_games = [game for game in owned_games if game["playtime_forever"] <= time_played]

    return random.choice(selectable_games)


def get_achievement_stats_for_game(game_id):
    template = "ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/?gameid={game_id}"
    json = steam_api_call_json(template, {"game_id": game_id})
    return json["achievementpercentages"]["achievements"]


def get_schema_for_game(key, app_id):
    template = "ISteamUserStats/GetSchemaForGame/v2/?key={key}&appid={app_id}"
    json = steam_api_call_json(template, {"key": key, "app_id": app_id})
    return json


def get_random_achievement(key, appid, cutoff=80):
    achievements = get_achievement_stats_for_game(appid)
    if len(achievements) == 0:
        print("No achievements for this game")
        return None

    schema = get_schema_for_game(key, appid)
    schema_achievements = schema["game"]["availableGameStats"]["achievements"]
    modifier = 100.0 / achievements[0]["percent"]
    candidates = [achievement for achievement in achievements if achievement["percent"] * modifier >= cutoff]
    for item in schema_achievements:
        for stat in achievements:
            if item["name"] == stat["name"]:
                item["percent"] = stat["percent"]
                break

    sorted_by_unlocked = reversed(sorted(schema_achievements, key=lambda tup: tup["percent"]))
    for achievement in sorted_by_unlocked:
        print("%s: %.1f%%" % (achievement["displayName"].encode("ascii", errors='replace').decode("ascii"), achievement["percent"]))

    random_cheevo_name = random.choice(candidates)["name"]
    found_display_name = ""
    for item in schema_achievements:
        if item["name"] == random_cheevo_name:
            found_display_name = item["displayName"]
    return found_display_name


def main():
    # command line arg handling
    parser = argparse.ArgumentParser(description='Pick a random game from a user\'s Steam library.')
    parser.add_argument('user_id', help='the ID of the Steam account')
    parser.add_argument('-a', '--all_games', help='pick from all games, not just unplayed ones', action='store_true')
    parser.add_argument(
        '-t', '--time_played', type=int, default=0,
        help='the time in minutes a game needs to have been played to count as played'
    )
    parser.add_argument('-c', '--achievement', help='pick a random achievement as an objective', action='store_true')
    args = parser.parse_args()

    # read key in from file
    with open("steam-api-key.txt", "r") as f:
        key = f.read().strip()

    # get a random game from the user's library
    game = pick_random_game(key, args.user_id, all_games=args.all_games, time_played=args.time_played)
    print("App ID: %s" % game["appid"])
    print(game["name"])
    if args.achievement:
        print("Challenge achievement: %s" % get_random_achievement(key, game["appid"]))


if __name__ == "__main__":
    main()
