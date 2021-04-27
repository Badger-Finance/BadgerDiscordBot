import base64
from github import Github
import json
import logging
import os
import re
import requests
import time


class SourceCredManager:
    """
    Contains all functions required to manage Badger's sourcecred ecosystem
    """

    def __init__(
        self, github_token: str, repo: str,
    ):
        self.github_token = github_token
        self.repo = repo
        self.ledger = self.get_current_ledger(
            f"https://raw.githubusercontent.com/{repo}/master/data/ledger.json"
        )
        self.logger = logging.getLogger("badger-bot")

    def get_current_ledger(self, ledger_url: str) -> list:
        """
        Downloads SourceCred ledger and stores it as a list of dicts

        Args:
            ledger_url (str): url for SourceCred ledger

        Returns:
            list: list of dicts representing each action (or line) of the SourceCred ledger
        """
        response = requests.get(ledger_url)
        ledger = []

        for entry in response.iter_lines():
            ledger.append(json.loads(entry))
        return ledger

    def activate_discord_users(self, discord_ids: list) -> list:
        """
        Activates a list of discord users by updating ledger.json.

        params
        - discord_ids: list of string ids representing discord identity

        returns
        - list of dicts representing TOGGLE_ACTIVATION actions.

        example TOGGGLE_ACTIVATION action:
        {
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

            identity_id = self.get_discord_user_identity_id(discord_id)

            if identity_id:
                activation_actions.append(self.create_activation_action(identity_id))
            # else:
            # TODO: send user message asking them to wait to register until tomorrow, haven't been in server long enough

        self.update_ledger(activation_actions)

        self.mark_users_active(discord_ids)

    def get_discord_user_identity_id(self, user_discord_id: str) -> str:
        """
        Gets the sourcecred identityId for the provided discord user and returns None if not found
        """

        # return if invalid id
        if len(user_discord_id) != 18:
            return None

        for entry in self.ledger:
            action = entry.get("action", {})

            if self.is_action_discord_alias(action):
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

    def is_action_discord_alias(self, action: dict) -> bool:
        """
        Checks if action is sourcred discord alias object

        Args:
            action (dict): sourcecred action object

        Returns:
            bool: True if action is discord alias, otherwise False
        """
        alias = action.get("alias")
        address = alias.get("address").split("\0") if alias else []
        return address[2] == "discord" if len(address) >= 6 else False

    def create_activation_action(self, identity_id: str) -> dict:
        """

        ex:
        {
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
            "ledgerTimestamp": round(time.time() * 1000),
            "uuid": self.get_clean_uuid(),
            "version": "1",
        }

        return activation_action

    def get_clean_uuid(self) -> str:

        uuid = self._get_random_uuid()
        while not self._is_uuid_clean(uuid):
            uuid = self._get_random_uuid()

        return uuid[:-2]

    def _get_random_uuid(self) -> str:
        base64_bytes = base64.b64encode(os.urandom(16))
        return base64_bytes.decode("ascii")

    def _is_uuid_clean(self, uuid: str) -> bool:
        _RE_UNCLEAN = "[+/\\-_]|[csfhuit]{2}"
        return False if re.search(_RE_UNCLEAN, uuid, flags=re.IGNORECASE) else True

    def update_ledger(self, activation_actions: list) -> None:
        self.ledger.extend(activation_actions)
        actions = [json.dumps(action) for action in self.ledger]

        g = Github(self.github_token)
        repo = g.get_repo(self.repo)

        branch = json.loads(
            requests.get(
                f"https://api.github.com/repos/{self.repo}/git/ref/heads/master"
            ).content
        )
        commit_sha = branch.get("object").get("sha")

        commit = json.loads(
            requests.get(
                f"https://api.github.com/repos/{self.repo}/git/commits/{commit_sha}"
            ).content
        )
        tree_sha = commit.get("sha")
        self.logger.info(f"tree_sha {tree_sha} commit {commit}")

        ledger_sha = self.get_ledger_sha(tree_sha)

        self.logger.info(f"Updating ledger.json with following actions")
        self.logger.info(actions)

        response = repo.update_file(
            "data/ledger.json",
            "update ledger to activate users",
            "\n".join(actions),
            ledger_sha,
            branch="master",
        )

        self.logger.info(f"Update response: {response}")

    def get_ledger_sha(self, tree_sha: str) -> str:
        """[summary]

        Args:
            tree_sha (str): sha of tree returned by github data api

        Raises:
            ValueError: if we can't find ledger.json, throws error

        Returns:
            str: [description]
        """
        tree = json.loads(
            requests.get(
                f"https://api.github.com/repos/{self.repo}/git/trees/{tree_sha}"
            ).content
        )
        for subtree in tree.get("tree"):
            if subtree.get("path") == "ledger.json":
                return subtree.get("sha")
            elif subtree.get("path") == "data":
                return self.get_ledger_sha(subtree.get("sha"))

        raise ValueError(
            f"Tree with sha {tree_sha} did not contain the ledger.json file"
        )

    def mark_users_active(self, discord_ids: list):
        """
        TODO: implement function to write discord id to db and mark as active

        Args:
            discord_ids (list): [description]
        """
        pass
