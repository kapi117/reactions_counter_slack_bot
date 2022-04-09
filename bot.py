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

'''
    Message shortcut (czyli opcja przy kliknięciu ... przy wiadomości na kanale gdzie jest bot)
    Wywoływany przez callback "len"
    client - klient Slacka do API
    ack - funkcja którą trzeba wywołać żeby Slack wiedział że dostaliśmy wezwanie
    respond - funkcja za pomocą której można odpowiadać w miejscu wywołania bota (dodatkowo można skorzystać z 
        typu ephemeral żeby wiadomość była wyświetlana tylko jednej osobie)
    payload - wszystkie informacje na temat wiadomości i wywołania 
'''


@app.shortcut("len")
def shortcut_count(client, ack, respond, payload):
    # odpowiadamy że otrzymaliśmy
    ack()

    # W celu charakteryzacji wiadomości
    timestamp = payload["message_ts"]
    # ID kanału
    channel_id = payload["channel"]["id"]

    # pobieranie reakcji z tej wiadomości
    reactions_response = client.reactions_get(
        timestamp=timestamp, full=True, channel=channel_id)

    reactions = reactions_response["message"]["reactions"]

    # pobranie listy użytkowników kanału
    members = client.conversations_members(channel=channel_id)["members"]

    summary = "*Podsumowanie reakcji na wiadomość*\n"
    reaction_counter = 0
    for reaction_type in reactions:
        reaction_counter += 1
        # dla każdej reakcji wypisujemy ją, ilość oraz osoby
        summary += str(reaction_counter) + ". Reakcja: :" + str(reaction_type['name']) \
            + ": \n\t- Ilość odpowiedzi: " + str(reaction_type['count']) +\
            "\n\t- Kto głosował:\n"
        for user in reaction_type["users"]:
            act_usr = client.users_info(user=user)
            summary += "\t\t" + str(act_usr["user"]["name"]) + "\n"
            if user in members:
                members.remove(user)
    # w members są też boty które trzeba odliczyć żeby wiedzieć czy wszyscy odpowiedzieli
    boty = 0
    if len(members) > 0:
        # sprawdzamy kto nie odpowiedział
        summary += "Natomiast niewdzięcznicy którzy nie odpowiedzieli to:\n"
        for user in members:
            act_usr = client.users_info(user=user)
            if "bot_id" in act_usr["user"]["profile"]:
                boty += 1
                continue
            summary += str(act_usr["user"]["name"]) + "\n"
    if len(members) == boty:
        summary += "Ja pierdziu ale Ty masz posłuch, każdy odpowiedział!!! :party_blob:"

    # wysyłamy wiadomość widoczna tylko dla tej osoby
    respond(response_type="ephemeral", text=summary)
    print("Pomyslnie wykonano zliczanie reakcji")


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
