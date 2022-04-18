'''
    Autor: Kacper Iwicki
    Mail: kacper.iwi@gmail.com
'''

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
app = App(token=os.environ.get("SLACK_TOKEN_WRSS"))

requests = {}

RESPOND_NAME = "respond"
LINK_TO_MESSAGE_NAME = "link_to_message"
REACTIONS_NAME = "reactions"
SUMMARY_NAME = "summary"
MEMBERS_NAME = "members"
USERS_TO_PING_NAME = "users_to_ping"


MODAL_ID = "COUNT_REACTIONS_MODAL"
PING_MODAL_ID = "PING_USERS_MODAL"

'''
    Message shortcut (czyli opcja przy kliknięciu ... przy wiadomości na kanale gdzie jest bot)
    Wywoływany przez callback "len"
    client - klient Slacka do API
    ack - funkcja którą trzeba wywołać żeby Slack wiedział że dostaliśmy wezwanie
    respond - funkcja za pomocą której można odpowiadać w miejscu wywołania bota (dodatkowo można skorzystać z 
        typu ephemeral żeby wiadomość była wyświetlana tylko jednej osobie)
    payload - wszystkie informacje na temat wiadomości i wywołania 
'''


def show_reactions(reactions_chosen, members, reactions):
    summary = ""
    reaction_counter = 0
    for reaction_type in reactions:
        if reaction_type['name'] in reactions_chosen:
            reaction_counter += 1
            # dla każdej reakcji wypisujemy ją, ilość oraz osoby
            summary += str(reaction_counter) + ". Reakcja: :" + str(reaction_type['name']) \
                + ": \n\t- Ilość odpowiedzi: " + str(reaction_type['count']) +\
                "\n\t- Kto głosował:\n"
            for user in reaction_type["users"]:
                summary += "\t\t<@" + str(user) + ">\n"
                if user in members:
                    members.remove(user)
    return summary


def show_not_reacted(members, users_to_ping, client):
    # w members są też boty które trzeba odliczyć żeby wiedzieć czy wszyscy odpowiedzieli
    boty = 0
    bots_id = ["U03BV419LD9"]
    summary = ""
    if len(members) > 0:
        # sprawdzamy kto nie odpowiedział
        summary += "Niewdzięcznicy którzy nie odpowiedzieli to:\n"
        for user in members:
            if user in bots_id:
                boty += 1
                continue
            summary += "\t\t<@" + str(user) + ">\n"
            users_to_ping.append(user)

    if len(members) == boty:
        summary += "Ja pierdziu ale Ty masz posłuch, każdy odpowiedział!!! :party_blob:"

    return summary


@app.shortcut("analyse_reaction")
def shortcut_count(client, ack, respond, payload):
    # odpowiadamy że otrzymaliśmy
    ack()
    # print(payload)
    global requests

    token = payload["token"]

    requests[token] = {}
    requests[token][RESPOND_NAME] = respond
    # W celu charakteryzacji wiadomości
    timestamp = payload["message_ts"]
    # ID kanału
    channel_id = payload["channel"]["id"]
    # Link do wiadomości
    requests[token][LINK_TO_MESSAGE_NAME] = client.chat_getPermalink(
        channel=channel_id, message_ts=timestamp)["permalink"]

    # id wywołania
    trigger_id = payload["trigger_id"]
    # print(payload)

    # pobieranie reakcji z tej wiadomości
    reactions_response = client.reactions_get(
        timestamp=timestamp, full=True, channel=channel_id)

    requests[token][REACTIONS_NAME] = reactions_response["message"]["reactions"]

    # pobranie listy użytkowników kanału
    requests[token][MEMBERS_NAME] = client.conversations_members(channel=channel_id)[
        "members"]

    open_modal(client, trigger_id, requests[token][REACTIONS_NAME])

    requests[token][SUMMARY_NAME] = "*Podsumowanie reakcji na wiadomość " + \
        str(requests[token][LINK_TO_MESSAGE_NAME]) + " *\n"

    requests[token][USERS_TO_PING_NAME] = []

    # wysyłamy wiadomość widoczna tylko dla tej osoby

    # ping_users(client, users_to_ping, link_to_message)


@app.view_closed(MODAL_ID)
def handle_close(ack, body):
    token = body["token"]
    requests.pop(token)
    ack()
    print("Zamknięto okienko")


@app.view(PING_MODAL_ID)
def handle_ping_submission(client, ack, body, view):
    ack()
    link_to_message = view["private_metadata"]
    users_to_ping = []
    for user in view["state"]["values"]["SELECT_TO_PING"]["USERS_LIST"]["selected_conversations"]:
        users_to_ping.append(user)

    ping_users(client, users_to_ping, link_to_message)
    print("Zamknięto okienko pingu")


@app.view(MODAL_ID)
def handle_submission(client, ack, body, view):
    token = body["token"]
    trigger_id = body["trigger_id"]
    global requests
    if token not in requests:
        errors = {}
        errors["token_not_found"] = "Something went wrong: token not found"
        ack(response_action="errors", errors=errors)
        return None

    ack()
    # print(body)
    chosen_reactions = []
    for reaction in view["state"]["values"]["SELECT_REACTIONS"]["REACTIONS_LIST"]["selected_options"]:
        chosen_reactions.append(reaction["value"])

    str_react = str(show_reactions(
        chosen_reactions, requests[token][MEMBERS_NAME], requests[token][REACTIONS_NAME]))
    str_not_react = str(show_not_reacted(
        requests[token][MEMBERS_NAME], requests[token][USERS_TO_PING_NAME], client))

    for option in view["state"]["values"]["SELECT_OPTIONS"]["checkboxes-action"]["selected_options"]:
        if str(option["value"]) == "PING":
            '''ping_users(client, requests[token][USERS_TO_PING_NAME],
                       requests[token][LINK_TO_MESSAGE_NAME])'''
            open_ping_modal(client=client, trigger_id=trigger_id,
                            users_to_ping=requests[token][USERS_TO_PING_NAME], link_to_message=requests[token][LINK_TO_MESSAGE_NAME])

            requests[token][SUMMARY_NAME] += '''
                Otworzyłem okienko ping
            '''

        if str(option["value"]) == "SHOW_VOTES":
            requests[token][SUMMARY_NAME] += str_react
        if str(option["value"]) == "SHOW_NOT_REACTED":
            requests[token][SUMMARY_NAME] += str_not_react
        if str(option["value"]) == "SEND_DM_NOT_REACTED":
            send_dm_to_users(
                client, requests[token][USERS_TO_PING_NAME], requests[token][LINK_TO_MESSAGE_NAME])
            requests[token][SUMMARY_NAME] += '''
                Wysłałem prywatne wiadomości do tych wszystkich, co nie odpowiedzieli :yum:
            '''

    requests[token][RESPOND_NAME](
        response_type="ephemeral", text=requests[token][SUMMARY_NAME])
    print("Pomyslnie wykonano zliczanie reakcji")
    requests.pop(token)


def send_dm_to_users(client, users_to_ping, link_to_message):
    text = '''
        Siemanko kochany WRSS'owiczu! :wave: Dostałem zadanie przypomnieć Ci żeby odpowiedzieć na wiadomość, która znajduje się tutaj: 
        ''' + link_to_message + '''
    Wiem, że pewnie masz niesłychanie dużo pracy, ale myślę, że pójdzie Ci to szybko :wink:
    A z tego co wiem, lepiej nie lądować na kanale *#ping* :woozy_face:'''
    for user in users_to_ping:
        client.chat_postMessage(
            channel=user, text=text)


def ping_users(client, users, message_link):
    # TODO wyświetlaj okienko z osobami które będą spingowane i z możliwością ich odznaczenia
    ping_channel_name = "#ping"
    # oznaczamy kogoś za pomocą <@usr_id>
    if len(users) > 0:
        ping_message = "*Pan Policjant porządku pilnuje, wursowiczów na slacku wciąż pinguje*\nDelikwenci którzy nie odpowiedzieli na wiadomość: " + \
            str(message_link) + " to:\n"
        for user in users:
            ping_message += "\t<@" + user + ">\n"

    client.chat_postMessage(channel=ping_channel_name, text=ping_message)


def open_ping_modal(client, trigger_id, users_to_ping, link_to_message):
    initial_users = ""
    count = 0
    for user in users_to_ping:
        if count > 0:
            initial_users += ''',
            '''
        initial_users += '"' + str(user) + '"'
        count += 1

    view = '''{
    "private_metadata": "''' + link_to_message + '''",
	"title": {
		"type": "plain_text",
		"text": "PING - O nie! :scream:",
		"emoji": true
	},
	"submit": {
		"type": "plain_text",
		"text": "Jazda z nimi",
		"emoji": true
	},
	"type": "modal",
	"callback_id": "''' + PING_MODAL_ID + '''",
	"close": {
		"type": "plain_text",
		"text": "Jednak nie pinguje",
		"emoji": true
	},
	"blocks": [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "Ktoś śmiał nie odpowiedzieć na tą wiadomość! Ostatnia szansa aby uratować tego osobnika bez RiGCZu przed *PINGIEM*!"
			}
		},
		{
            "block_id": "SELECT_TO_PING",
			"type": "input",
			"element": {
				"type": "multi_conversations_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Nie każdy bohater nosi pelerynę",
					"emoji": true
				},
                "filter": {
                    "include": [
                        "im"
                    ],
                    "exclude_bot_users": true
                },
				"initial_conversations": [''' \
                                        + initial_users + \
        '''],
				"action_id": "USERS_LIST"
			},
			"label": {
				"type": "plain_text",
				"text": "Odznacz osobniki które zabierasz ze sobą na barkę i będą ocaleni",
				"emoji": true
			}
		}
	]
}
    '''
    client.views_open(trigger_id=trigger_id, view=view)
    print("Otwarto okienko ping")


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
            "notify_on_close": true,
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
        '''],
                        "initial_options": [''' + \
        reactions_menu + \
        ''']
                    }
                }
            ]
        }
    '''

    client.views_open(trigger_id=trigger_id, view=view)
    print("Otwarto okienko")


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN_WRSS"]).start()
