from dotenv import load_dotenv
import os
from pathlib import Path
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


'''
    Pobranie tokenów jako zmiennych środowiskowych z pliku .env znajdującego się w tym samym folderze
'''
env_path = Path('.') / '.env'
load_dotenv(env_path)

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_TOKEN"))

timestamp = None
channel_id = None
# Link do wiadomości
link_to_message = None

# id wywołania
trigger_id = None

# pobieranie reakcji z tej wiadomości
reactions_response = None

reactions = None

# pobranie listy użytkowników kanału
members = None

respond_ = None


summary = "*Podsumowanie reakcji na wiadomość " + \
    str(link_to_message) + " *\n"

users_to_ping = []

MODAL_ID = "COUNT_REACTIONS_MODAL"
'''
    Message shortcut (czyli opcja przy kliknięciu ... przy wiadomości na kanale gdzie jest bot)
    Wywoływany przez callback "len"
    client - klient Slacka do API
    ack - funkcja którą trzeba wywołać żeby Slack wiedział że dostaliśmy wezwanie
    respond - funkcja za pomocą której można odpowiadać w miejscu wywołania bota (dodatkowo można skorzystać z 
        typu ephemeral żeby wiadomość była wyświetlana tylko jednej osobie)
    payload - wszystkie informacje na temat wiadomości i wywołania 
'''


def show_reactions(reactions_chosen, members):
    summary = ""
    reaction_counter = 0
    for reaction_type in reactions:
        if reaction_type['name'] in reactions_chosen:
            reaction_counter += 1
            # print(reaction_type)
            # dla każdej reakcji wypisujemy ją, ilość oraz osoby
            summary += str(reaction_counter) + ". Reakcja: :" + str(reaction_type['name']) \
                + ": \n\t- Ilość odpowiedzi: " + str(reaction_type['count']) +\
                "\n\t- Kto głosował:\n"
            for user in reaction_type["users"]:
                #act_usr = client.users_info(user=user)
                #summary += "\t\t<@" + str(act_usr["user"]["name"]) + ">\n"
                summary += "\t\t<@" + str(user) + ">\n"
                if user in members:
                    members.remove(user)
    return summary


def show_not_reacted(members, users_to_ping, client):
    # w members są też boty które trzeba odliczyć żeby wiedzieć czy wszyscy odpowiedzieli
    boty = 0
    summary = ""
    if len(members) > 0:
        # sprawdzamy kto nie odpowiedział
        summary += "Niewdzięcznicy którzy nie odpowiedzieli to:\n"
        for user in members:
            # TODO uwydajnić to
            act_usr = client.users_info(user=user)
            if "bot_id" in act_usr["user"]["profile"]:
                boty += 1
                continue
            #summary += "\t- " + str(act_usr["user"]["name"]) + "\n"
            summary += "\t\t<@" + str(user) + ">\n"
            users_to_ping.append(user)

    if len(members) == boty:
        summary += "Ja pierdziu ale Ty masz posłuch, każdy odpowiedział!!! :party_blob:"

    return summary


@app.shortcut("len")
def shortcut_count(client, ack, respond, payload):
    # odpowiadamy że otrzymaliśmy
    ack()
    # print(payload)
    global respond_, timestamp, channel_id, link_to_message, trigger_id, reactions_response, reactions, members, summary, users_to_ping

    respond_ = respond
    # W celu charakteryzacji wiadomości
    timestamp = payload["message_ts"]
    # ID kanału
    channel_id = payload["channel"]["id"]
    # Link do wiadomości
    link_to_message = client.chat_getPermalink(
        channel=channel_id, message_ts=timestamp)["permalink"]

    # id wywołania
    trigger_id = payload["trigger_id"]

    # pobieranie reakcji z tej wiadomości
    reactions_response = client.reactions_get(
        timestamp=timestamp, full=True, channel=channel_id)

    reactions = reactions_response["message"]["reactions"]

    # pobranie listy użytkowników kanału
    members = client.conversations_members(channel=channel_id)["members"]

    open_modal(client, trigger_id, reactions)

    summary = "*Podsumowanie reakcji na wiadomość " + \
        str(link_to_message) + " *\n"

    users_to_ping = []

    # wysyłamy wiadomość widoczna tylko dla tej osoby

    # ping_users(client, users_to_ping, link_to_message)


@app.view(MODAL_ID)
def handle_submission(client, ack, body, view):
    ack()
    print(body)
    global summary, respond_
    chosen_reactions = []
    for reaction in view["state"]["values"]["SELECT_REACTIONS"]["REACTIONS_LIST"]["selected_options"]:
        chosen_reactions.append(reaction["value"])

    str_react = str(show_reactions(chosen_reactions, members))
    str_not_react = str(show_not_reacted(members, users_to_ping, client))

    for option in view["state"]["values"]["SELECT_OPTIONS"]["checkboxes-action"]["selected_options"]:
        if str(option["value"]) == "PING":
            ping_users(client, users_to_ping, link_to_message)

        if str(option["value"]) == "SHOW_VOTES":
            summary += str_react
        if str(option["value"]) == "SHOW_NOT_REACTED":
            summary += str_not_react

    respond_(response_type="ephemeral", text=summary)
    print("Pomyslnie wykonano zliczanie reakcji")


def ping_users(client, users, message_link):
    ping_channel_name = "#ping"
    # oznaczamy kogoś za pomocą <@usr_id>
    if len(users) > 0:
        ping_message = "*Pan Policjant porządku pilnuje, wursowiczów na slacku wciąż pinguje*\nDelikwenci którzy nie odpowiedzieli na wiadomość: " + \
            str(message_link) + " to:\n"
        for user in users:
            ping_message += "\t<@" + user + ">\n"

    client.chat_postMessage(channel=ping_channel_name, text=ping_message)


def open_modal(client, trigger_id, reactions):
    reactions_menu = ""
    count = 0
    for reaction_type in reactions:
        if(count > 0):
            reactions_menu += ''',
            '''
        reactions_menu += '''{
                                "text": {
                                    "type": "plain_text",
                                    "text": ":''' + reaction_type["name"] + ''': ''' + reaction_type["name"] + '''",
                                    "emoji": true
                                },
                                "value": "''' + reaction_type["name"] + '''"
                            }'''
        count += 1

    view = '''
        {
            "type": "modal",
            "callback_id": "''' + MODAL_ID + '''",
            "submit": {
                "type": "plain_text",
                "text": "Do podawczego",
                "emoji": true
            },
            "close": {
                "type": "plain_text",
                "text": "Taktyczny odwrót",
                "emoji": true
            },
            "title": {
                "type": "plain_text",
                "text": "Policz reakcje :wave:",
                "emoji": true
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "Witaj disco robaczku :wave: \nPomogę Ci żebyś miał_ więcej czasu na flanki :baby_bottle:",
                        "emoji": true
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "block_id": "SELECT_OPTIONS",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Jakie sosiwo wariacie?*"
                    },
                    "accessory": {
                        "type": "checkboxes",
                        "options": [
                            {
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "Wyświetl głosy"
                                },
                                "description": {
                                    "type": "mrkdwn",
                                    "text": "Lista osób które zagłosowały"
                                },
                                "value": "SHOW_VOTES"
                            },
                            {
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "Wyświetl gamoni"
                                },
                                "description": {
                                    "type": "mrkdwn",
                                    "text": "Lista patafianów którzy nie zareagowali (w żaden sposób)"
                                },
                                "value": "SHOW_NOT_REACTED"
                            },
                            {
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "Przypomnij matołkom"
                                },
                                "description": {
                                    "type": "mrkdwn",
                                    "text": "Wyślij prywatną wiadomość głuptasom co zapomnieli"
                                },
                                "value": "SEND_DM_NOT_REACTED"
                            },
                            {
                                "text": {
                                    "type": "mrkdwn",
                                    "text": ":female-police-officer::rotating_light: *PING* :rotating_light::male-police-officer:"
                                },
                                "description": {
                                    "type": "mrkdwn",
                                    "text": "Miarka się przebrała"
                                },
                                "value": "PING"
                            }
                        ],
                        "action_id": "checkboxes-action"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "input",
                    "label": {
                        "type": "plain_text",
                        "text": "Jakie reakcje chcesz zliczyć (dotyczy opcji wyświetl głosy)?",
                        "emoji": true
                    },
                    "block_id": "SELECT_REACTIONS",
                    "element": {
                        "action_id": "REACTIONS_LIST",
                        "type": "multi_static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Wszystkie reakcje",
                            "emoji": true
                        },
                        "options": [''' + \
        reactions_menu + \
        ''']
                    }
                }
            ]
        }
    '''

    client.views_open(trigger_id=trigger_id, view=view)


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
