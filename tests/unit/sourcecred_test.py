import os
import pytest
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from sourcecred import SourceCred

sc = SourceCred()


def test_is_discord_alias_action():

    test_discord_action = {
        "alias": {
            "address": "N\u0000sourcecred\u0000discord\u0000MEMBER\u0000user\u0000653638788026990593\u0000",
            "description": "discord/cookies#4969",
        },
        "identityId": "7aGWmcJLo8Ak6EGiPYLdRw",
        "type": "ADD_ALIAS",
    }
    test_non_discord_action = {
        "identity": {
            "address": "N\u0000sourcecred\u0000core\u0000IDENTITY\u0000FwDf9X8JzrvoCzMHYwYYLw\u0000",
            "aliases": [],
            "id": "FwDf9X8JzrvoCzMHYwYYLw",
            "name": "Tritium---VLK",
            "subtype": "USER",
        },
        "type": "CREATE_IDENTITY",
    }
    test_empty = {}

    assert sc.is_discord_alias_action(test_discord_action) == True
    assert sc.is_discord_alias_action(test_non_discord_action) == False
    assert sc.is_discord_alias_action(test_empty) == False


def test_get_user_identity_id():

    test_discord_id = "653638788026990593"
    test_invalid_discord_id = "12345"

    assert sc.get_user_identity_id(test_discord_id) == "7aGWmcJLo8Ak6EGiPYLdRw"
    assert sc.get_user_identity_id(test_invalid_discord_id) == None
