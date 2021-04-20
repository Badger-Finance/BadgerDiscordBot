import json
import logging
import shortuuid
import re
import requests
import time


class SourceCred:
    """
    Contains all functions required to manage Badger's sourcecred
    ecosystem
    """

    def __init__(
        self,
        ledger_url="https://raw.githubusercontent.com/Badger-Finance/SourceCred/gh-pages/data/ledger.json",
    ):
        self.ledger = requests.get(ledger_url)
        self.logger = logging.getLogger("badger-bot")

    def create_activation_actions(self, discord_ids: list) -> list:
        """
        Creates sourcecred TOGGLE_ACTIVATION action for a discord user.

        params
        - discord_id: string id representing discord identity

        returns
        - dict representing TOGGLE_ACTIVATION action.

        ex: {
            "action":
                {
                    "identityId":"N7pyNa2bp8DIA0RQYNnrmw",
                    "type":"TOGGLE_ACTIVATION"
                },
                "ledgerTimestamp":1617931054549,
                "uuid":"ZueUX45XoDqhwbkCKaql8A",
                "version":"1"
            }
        """
        activation_actions = []
        for discord_id in discord_ids:

            identity_id = self.get_user_identity_id(discord_id)

            if identity_id:
                activation_actions.append(self.create_activation_action(identity_id))
            # else:
            # TODO: send user message asking them to wait to register until tomorrow, haven't been in server long enough

        # TODO: implement function to append activation actions to end of ledger and make pr with new file

    def get_user_identity_id(self, user_discord_id: str) -> str:
        """
        Gets the sourcecred identityId for the provided discord user and returns None if not found
        """

        # return if invalid id
        if len(user_discord_id) != 18:
            return None

        identity_ids = []

        for entry in self.ledger.iter_lines():
            action = json.loads(entry).get("action", {})

            if self.is_discord_alias_action(action):
                address = action.get("alias").get("address").split("\0")
                alias_discord_id = address[5]

                if alias_discord_id == user_discord_id:
                    ledger_identity_id = action.get("identityId")
                    self.logger.info(
                        f"discord id: {user_discord_id}\t"
                        + f"identityId: {ledger_identity_id}"
                    )
                    return ledger_identity_id

        return None

    def is_discord_alias_action(self, action: dict) -> bool:
        """[summary]

        Args:
            action (dict): [description]

        Returns:
            bool: [description]
        """
        alias = action.get("alias")
        address = alias.get("address").split("\0") if alias else []
        return address[2] == "discord" if len(address) >= 6 else False

    def create_activation_action(self, identity_id: str) -> dict:
        """

        ex: {
            "action":
                {
                    "identityId":"N7pyNa2bp8DIA0RQYNnrmw",
                    "type":"TOGGLE_ACTIVATION"
                },
                "ledgerTimestamp":1617931054549,
                "uuid":"ZueUX45XoDqhwbkCKaql8A",
                "version":"1"
            }
        """
        activation_action = {
            "action": {"identityId": identity_id, "type": "TOGGLE_ACTIVATION"},
            "ledgerTimestamp": time.time(),
            "uuid": shortuuid.uuid(),
            "version": "1",
        }

        return activation_action
