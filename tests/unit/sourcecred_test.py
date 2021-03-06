from dotenv import load_dotenv
import os
import pytest
import sys
import time

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from sourcecred import SourceCredManager

load_dotenv()

sc = SourceCredManager(
    github_token=os.getenv("BADGER_SOURCECRED_PAT_TEST"),
    repo="btcookies/SourceCred",
    queue_name="sourcecred-registration-requests",
    table_name="sourcecred-registration",
)


def test_is_action_discord_alias():

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

    assert sc.is_action_discord_alias(test_discord_action) == True
    assert sc.is_action_discord_alias(test_non_discord_action) == False
    assert sc.is_action_discord_alias(test_empty) == False


def test_get_discord_user_identity_id():

    test_discord_id = "653638788026990593"
    test_invalid_discord_id = "12345"

    assert sc.get_discord_user_identity_id(test_discord_id) == "N7pyNa2bp8DIA0RQYNnrmw"
    assert sc.get_discord_user_identity_id(test_invalid_discord_id) == None


def test_get_clean_uuid():

    assert sc._is_uuid_clean("N7pyNa2bp8DIA0RQYNnrmw")
    assert sc._is_uuid_clean("N7pyNa2bp8DIA0RQYNnrcc") == False
    assert sc._is_uuid_clean(sc.get_clean_uuid())


def test_update_ledger(monkeypatch):

    activations = [
        {
            "action": {
                "identityId": "N7pyNa2bp8DIA0RQYNnrmw",
                "type": "TOGGLE_ACTIVATION",
            },
            "ledgerTimestamp": round(time.time() * 1000),
            "uuid": sc.get_clean_uuid(),
            "version": "1",
        },
        {
            "action": {
                "identityId": "N7pyNa2bp8DIA0RQYNnrmw",
                "type": "TOGGLE_ACTIVATION",
            },
            "ledgerTimestamp": round(time.time() * 1000),
            "uuid": sc.get_clean_uuid(),
            "version": "1",
        },
    ]

    sc.update_ledger(activations)
