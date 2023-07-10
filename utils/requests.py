import json


class RequestMetadata:
    def __init__(
        self, link_to_message, reactions, summary, members, users_to_ping, channel, user
    ):
        self.link_to_message = link_to_message
        self.reactions = reactions
        self.summary = summary
        self.members = members
        self.users_to_ping = users_to_ping
        self.channel = channel
        self.user = user

    @staticmethod
    def from_payload(client, payload):
        channel = payload["channel"]["id"]
        user = payload["user"]["id"]

        link_to_message = client.chat_getPermalink(
            channel=channel, message_ts=payload["message_ts"]
        )["permalink"]

        try:
            reactions_response = client.reactions_get(
                timestamp=payload["message_ts"],
                full=True,
                channel=channel,
            )
            reactions = reactions_response["message"]["reactions"]
        except KeyError:
            reactions = []

        channel_members = client.conversations_members(channel=channel)["members"]

        summary = "*Podsumowanie reakcji na wiadomość " + str(link_to_message) + " *\n"

        users_to_ping = {}

        return RequestMetadata(
            link_to_message,
            reactions,
            summary,
            channel_members,
            users_to_ping,
            channel,
            user,
        )

    def to_dict(self):
        return {
            "link_to_message": self.link_to_message,
            "reactions": self.reactions,
            "summary": self.summary,
            "members": self.members,
            "users_to_ping": self.users_to_ping,
            "channel": self.channel,
            "user": self.user,
        }

    @staticmethod
    def from_dict(dict):
        return RequestMetadata(
            dict["link_to_message"],
            dict["reactions"],
            dict["summary"],
            dict["members"],
            dict["users_to_ping"],
            dict["channel"],
            dict["user"],
        )

    def to_string(self):
        self_json = json.dumps(self.to_dict())

        return self_json

    @staticmethod
    def from_string(str_self):
        return RequestMetadata.from_dict(json.loads(str_self))
