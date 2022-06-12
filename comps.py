import json

# Comps come from https://tftactics.gg/tierlist/team-comps
# Challengers Academy
# Items are in camel case and a-Z
class Comps():
    def __init__(self, message_queue, compsFile = 'comps/meta-comps.json',):

        self.message_queue = message_queue
        with open(compsFile) as json_file:
            self.team_comps = json.load(json_file)

        #default to first team comp in list
        self.load_team_comp_idx(0)

        # temp for astral mage
        self.roll_level = 6
        self.rolled_gold = 0

        self.stop_rolling = False

    def load_team_comp_idx(self, idx):
        if len(self.team_comps) > idx:
            team_comp = self.team_comps[idx]
            self.name = team_comp["name"]
            self.comp = team_comp["comp"]
            self.priority_augments = team_comp["priority_augments"]
            self.backup_augments = team_comp["backup_augments"]
            self.message_queue.put(("CONSOLE", "Comp Loaded : {}".format(self.name)))
        else:
            self.message_queue.put(("CONSOLE", f"No comps were loaded"))


    def champions_to_buy(self) -> list:
        champs_to_buy = []
        for champion in self.comp:
            if self.comp[champion]["level"] == 1:
                champs_to_buy.append(champion)
            elif self.comp[champion]["level"] == 2:
                for _ in range(3):
                    champs_to_buy.append(champion)
            elif self.comp[champion]["level"] == 3:
                for _ in range(9):
                    champs_to_buy.append(champion)
        return champs_to_buy

    def do_slow_roll(self):

        if self.rolled_gold < 40:
            self.rolled_gold += 2
            return False

        return True

        # for champion in self.comp:
        #     key_unit = self.comp[champion]["key_unit"]
        #     champ_level_wanted = self.comp[champion]["level"]
        #     if key_unit and champ_level_wanted < board[champion]["level"]:
        #         return False
        # return True

    def get_unknown_slots(self):
        container = []
        for champion in self.comp:
            container.append(self.comp[champion]["board_position"])
        return [n for n in range(27) if n not in container]
