import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from sourcecred import SourceCredManager

ALREADY_ACTIVATED = {
    "discord/sarah#0666": True,
    "discord/DeFi Frog#5912": True,
    "discord/Tritium - VLK#4816": True,
    "discord/Jzjallday#0761": True,
    "discord/TheRealTuna#1036": True,
    "discord/KSR#7481": True,
    "discord/hash_error#7744": True,
    "discord/crip_toe#3121": True,
    "discord/1500$Badger-DIGG1/1#8584": True,
    "discord/tacocat#5740": True,
    "discord/blackbear#4259": True,
    "discord/JJ.C#1987": True,
    "discord/randomwalk#5765": True,
}

if __name__ == "__main__":
    sc = SourceCredManager(
        github_token=os.getenv("BADGER_SOURCECRED_TEST_REPO_TOKEN"),
        repo="btcookies/SourceCred",
    )

    ledger = sc.get_current_ledger(
        "https://raw.githubusercontent.com/Badger-Finance/SourceCred/master/data/ledger.json"
    )

    identities_to_activate = []

    # get all ids for people to activate
    for entry in ledger:
        action = entry.get("action", {})

        if (
            sc.is_action_discord_alias(action)
            and ALREADY_ACTIVATED.get(action.get("alias").get("description")) == None
        ):
            ledger_identity_id = action.get("identityId")
            identities_to_activate.append(ledger_identity_id)

    # create activation items and append to ledger
    for identity_id in identities_to_activate:
        ledger.append(sc.create_activation_action(identity_id))

    # write ledger.json to file
    with open("ledger.json", "w") as f:
        actions = [json.dumps(action) for action in ledger]
        f.write("\n".join(actions))
