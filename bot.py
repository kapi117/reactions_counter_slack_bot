"""
    Autor: Kacper Iwicki
    Mail: kacper.iwi@gmail.com
"""

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import re
import json

# my modules
from utils.requests import RequestMetadata

with open("./assets/strings/user_strings.json", "r") as f:
    STRINGS_USER = json.load(f)

with open("./assets/strings/utils_strings.json", "r") as f:
    STRINGS_UTILS = json.load(f)

app = App(token=STRINGS_USER["general"]["bot_token"])

requests = {}

RESPOND_NAME = "respond"
LINK_TO_MESSAGE_NAME = "link_to_message"
REACTIONS_NAME = "reactions"
SUMMARY_NAME = "summary"
MEMBERS_NAME = "members"
USERS_TO_PING_NAME = "users_to_ping"


### SHORTCUT REQUEST ###
@app.shortcut("analyse_reaction")
def shortcut_count(ack, respond, payload):
    # koniecznie odpowiadamy że otrzymaliśmy
    ack()

    req_meta = RequestMetadata.from_payload(app.client, payload)

    trigger_id = payload["trigger_id"]
    open_main(trigger_id, req_meta)


def open_main(trigger_id, req_meta):
    reactions_menu = create_reactions_menu(req_meta.reactions)

    replacements = {
        "{{reactions_menu}}": f"[{reactions_menu}]",
        "{{inactive_users}}": json.dumps(STRINGS_UTILS["inactive_users"]),
    }

    view = load_modal(STRINGS_UTILS["modals"]["main"]["file"], replacements, req_meta)

    app.client.views_open(trigger_id=trigger_id, view=view)
    print("Otwarto okienko")


def create_reactions_menu(reactions):
    reactions_menu = ""
    count = 0
    for reaction_type in reactions:
        if count > 0:
            reactions_menu += """,
            """
        reactions_menu += get_reaction_entry(reaction_type["name"])
        count += 1

    return reactions_menu


def get_reaction_entry(reaction_name):
    entry = (
        """ {
            "text": {
                "type": "plain_text",
                "text": ":"""
        + reaction_name
        + """: """
        + reaction_name
        + '''",
                "emoji": true
            },
            "value": "'''
        + reaction_name
        + """"
        }"""
    )
    return entry


def load_modal(modal_json_filename, repl_in, req_meta):
    result_modal = ""

    with open(modal_json_filename, "r") as modal_file:
        modal_text = modal_file.read()

        result_modal = replace_tags_in_text(modal_text, repl_in)

    result_modal = load_private_metadata_to_modal_text(result_modal, req_meta)

    return result_modal


def replace_tags_in_text(text, repl_dict):
    replacements = dict((re.escape(k), v) for k, v in repl_dict.items())
    pattern = re.compile("|".join(replacements.keys()))
    result_text = pattern.sub(lambda m: replacements[re.escape(m.group(0))], text)
    return result_text


def load_private_metadata_to_modal_text(modal_text, req_meta: RequestMetadata):
    modal_json = json.loads(modal_text)
    modal_json["private_metadata"] = req_meta.to_string()
    modal_text = json.dumps(modal_json)
    return modal_text


### MAIN SUBMISSION ###
@app.view(STRINGS_UTILS["modals"]["main"]["id"])
def handle_submission(ack, body, view, respond):
    try:
        metadata = get_private_metadata_from_view(view)
        req_meta = RequestMetadata.from_string(metadata)

    except KeyError as e:
        errors = {}
        errors["metadata_not_found"] = str(e)
        ack(response_action="errors", errors=errors)
        return None

    inactive_users = get_inactive_users_from_main(view)
    load_inactive_users_to_utils(inactive_users)

    ack()

    chosen_reactions = get_reactions_chosen_in_main(view)

    req_meta.users_to_ping = get_users_not_reacted_to_any_reactions(
        req_meta, chosen_reactions
    )

    chosen_actions = get_actions_chosen_from_view(view)

    if "SHOW_VOTES" in chosen_actions:
        reacted_summary = summary_reactions(chosen_reactions, req_meta)
        req_meta.summary += reacted_summary

    if "SHOW_NOT_REACTED" in chosen_actions:
        not_reacted_summary = summary_not_reacted(req_meta)
        req_meta.summary += not_reacted_summary

    if "PING" in chosen_actions:
        trigger_id = body["trigger_id"]
        open_ping_modal(trigger_id, req_meta)

        req_meta.summary += """\nOtworzyłem okienko ping\n"""

    if "SEND_DM_NOT_REACTED" in chosen_actions:
        trigger_id = body["trigger_id"]
        open_dm_modal(trigger_id, req_meta)

        req_meta.summary += """Otworzyłem okienko wysyłania wiadomości :yum:\n"""

    app.client.chat_postEphemeral(
        channel=req_meta.channel, text=req_meta.summary, user=req_meta.user
    )

    print("Pomyslnie wykonano zliczanie reakcji")


def get_private_metadata_from_view(view):
    if not "private_metadata" in view:
        raise KeyError("Key 'private_metadata' not found!")

    return view["private_metadata"]


def get_inactive_users_from_main(view):
    inactive_users = []
    for user in view["state"]["values"]["SELECT_INACTIVE"]["INACTIVE_USERS_LIST"][
        "selected_conversations"
    ]:
        inactive_users.append(user)
    return inactive_users


def load_inactive_users_to_utils(inactive_users):
    STRINGS_UTILS["inactive_users"] = inactive_users
    with open("./assets/strings/utils_strings.json", "w") as f:
        json.dump(STRINGS_UTILS, f)


def get_reactions_chosen_in_main(view):
    chosen_reactions = []
    for reaction in view["state"]["values"]["SELECT_REACTIONS"]["REACTIONS_LIST"][
        "selected_options"
    ]:
        chosen_reactions.append(reaction["value"])

    return chosen_reactions


def summary_reactions(reactions_chosen, req_meta: RequestMetadata):
    reaction_counter = 0
    summary = ""
    reactions = [
        reaction_type
        for reaction_type in req_meta.reactions
        if reaction_type["name"] in reactions_chosen
    ]

    for reaction in reactions:
        reaction_counter += 1
        summary += get_reaction_single_summary(reaction_counter, reaction)

    return summary


def summary_not_reacted(req_meta: RequestMetadata):
    summary = ""

    if len(req_meta.users_to_ping) > 0:
        summary += "Niewdzięcznicy którzy nie odpowiedzieli to:\n"
        summary += get_users_text_with_links(req_meta.users_to_ping)

    else:
        summary += "Ja pierdziu ale Ty masz posłuch, każdy odpowiedział!!! :party_blob:"

    return summary


def get_reaction_single_summary(no_reaction, reaction):
    line = (
        str(no_reaction)
        + ". Reakcja: :"
        + str(reaction["name"])
        + ": \n\t- Ilość odpowiedzi: "
        + str(reaction["count"])
        + "\n\t- Kto głosował:\n"
    )

    line += get_users_text_with_links(reaction["users"])

    return line


def get_users_text_with_links(users):
    summary = ""
    for user in users:
        summary += "\t\t<@" + str(user) + ">\n"
    return summary


def get_users_not_reacted_to_any_reactions(req_meta: RequestMetadata, reactions):
    req_meta.users_to_ping = req_meta.members

    remove_inactive_users_from_ping(req_meta)

    reactions = [
        reaction_type
        for reaction_type in req_meta.reactions
        if reaction_type["name"] in reactions
    ]

    for reaction in reactions:
        remove_from_ping(reaction, req_meta)

    req_meta.users_to_ping = [
        user for user in req_meta.users_to_ping if not user in STRINGS_USER["bots_id"]
    ]

    return req_meta.users_to_ping


def remove_inactive_users_from_ping(req_meta: RequestMetadata):
    for user in STRINGS_UTILS["inactive_users"]:
        if user in req_meta.users_to_ping:
            req_meta.users_to_ping.remove(user)


def remove_from_ping(reaction, req_meta):
    for user in reaction["users"]:
        if user in req_meta.users_to_ping:
            req_meta.users_to_ping.remove(user)


def get_actions_chosen_from_view(view):
    chosen_options = []
    for option in view["state"]["values"]["SELECT_OPTIONS"]["checkboxes-action"][
        "selected_options"
    ]:
        chosen_options.append(option["value"])

    return chosen_options


def open_ping_modal(trigger_id, req_meta: RequestMetadata):
    initial_users = get_users_for_initial_choice(req_meta.users_to_ping)

    replacements = {
        "{{link_to_message}}": f"{req_meta.link_to_message}",
        "{{initial_users}}": f"{initial_users}",
    }

    view = load_modal(STRINGS_UTILS["modals"]["ping"]["file"], replacements, req_meta)

    app.client.views_open(trigger_id=trigger_id, view=view)
    print("Otwarto okienko ping")


def open_dm_modal(trigger_id, req_meta: RequestMetadata):
    initial_users = get_users_for_initial_choice(req_meta.users_to_ping)

    replacements = {
        "{{link_to_message}}": f"{req_meta.link_to_message}",
        "{{initial_users}}": f"{initial_users}",
    }

    view = load_modal(STRINGS_UTILS["modals"]["dm"]["file"], replacements, req_meta)

    app.client.views_open(trigger_id=trigger_id, view=view)
    print("Otwarto okienko dm")


def get_users_for_initial_choice(users):
    initial_users = ""
    count = 0
    for user in users:
        if count > 0:
            initial_users += """,
            """
        initial_users += '"' + str(user) + '"'
        count += 1

    return initial_users


@app.view(STRINGS_UTILS["modals"]["ping"]["id"])
def handle_ping_submission(ack, body, view):
    ack()
    req_meta = RequestMetadata.from_string(view["private_metadata"])
    users_to_ping = get_users_to_ping_from_view(view)

    ping_users(users_to_ping, req_meta)
    print("Zamknięto okienko pingu")


def get_users_to_ping_from_view(view):
    users_to_ping = []
    for user in view["state"]["values"]["SELECT_TO_PING"]["USERS_LIST"][
        "selected_conversations"
    ]:
        users_to_ping.append(user)
    return users_to_ping


def ping_users(users, req_meta: RequestMetadata):
    if len(users) > 0:
        ping_message = (
            "Ping na życzenie <@"
            + str(req_meta.user)
            + ">)\nDelikwenci którzy nie odpowiedzieli na wiadomość: "
            + str(req_meta.link_to_message)
            + " to:\n"
        )

        ping_message += get_users_text_with_links(users)

    app.client.chat_postMessage(
        channel=STRINGS_USER["ping_channel_name"], text=ping_message
    )


@app.view(STRINGS_UTILS["modals"]["dm"]["id"])
def handle_dm_submission(client, ack, body, view):
    ack()
    req_meta = RequestMetadata.from_string(view["private_metadata"])
    users_to_dm = get_users_to_dm_from_view(view)

    send_dm_to_users(client, users_to_dm, req_meta)
    print("Zamknięto okienko DM")


def get_users_to_dm_from_view(view):
    users_to_dm = []
    for user in view["state"]["values"]["SELECT_TO_DM"]["USERS_LIST"][
        "selected_conversations"
    ]:
        users_to_dm.append(user)

    return users_to_dm


def send_dm_to_users(client, users_to_ping, req_meta: RequestMetadata):
    text = (
        """
        Siemanko kochany WRSS'owiczu! :wave: Dostałem zadanie od <@"""
        + req_meta.user
        + """> przypomnieć Ci żeby odpowiedzieć na wiadomość, która znajduje się tutaj: 
        """
        + req_meta.link_to_message
        + """
Wiem, że pewnie masz niesłychanie dużo pracy, ale myślę, że pójdzie Ci to szybko :wink:
A z tego co wiem, lepiej nie lądować na kanale *#ping* :woozy_face:"""
    )
    for user in users_to_ping:
        client.chat_postMessage(channel=user, text=text)


if __name__ == "__main__":
    SocketModeHandler(app, STRINGS_USER["general"]["app_token"]).start()
