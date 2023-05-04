class RequestMetadata:
    def __init__(self, link_to_message, reactions, summary, members, users_to_ping):
        self.link_to_message = link_to_message
        self.reactions = reactions
        self.summary = summary
        self.members = members
        self.users_to_ping = users_to_ping

    @staticmethod
    def from_payload(client, payload):
        link_to_message = client.chat_getPermalink(
            channel=payload["channel"]["id"], message_ts=payload["message_ts"])["permalink"]
        
        try:
            reactions_response = client.reactions_get(
                timestamp=payload["message_ts"], full=True, channel=payload["channel"]["id"])
            reactions = reactions_response["message"]["reactions"]
        except KeyError:
            reactions = []

        channel_members = client.conversations_members(channel=payload["channel"]["id"])["members"]

        summary = "*Podsumowanie reakcji na wiadomość " + \
            str(link_to_message) + " *\n"
        
        users_to_ping = []

        return RequestMetadata(link_to_message, reactions, summary, channel_members, users_to_ping)
    
    def to_dict(self):
        return {
            "link_to_message": self.link_to_message,
            "reactions": self.reactions,
            "summary": self.summary,
            "members": self.members,
            "users_to_ping": self.users_to_ping
        }
    
    @staticmethod
    def from_dict(dict):
        return RequestMetadata(
            dict["link_to_message"],
            dict["reactions"],
            dict["summary"],
            dict["members"],
            dict["users_to_ping"]
        )
        