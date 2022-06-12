from time import sleep

import game_assets
import mk_functions
import screen_coords
from champion import Champion
from game_assets import champion_data, full_items
# import comps
from comps import Comps
import ocr
import arena_functions

class Arena:
    def __init__(self, message_queue):
        self.message_queue = message_queue
        self.board_size = 0
        self.bench = [None, None, None, None, None, None, None, None, None]
        self.board = []
        self.board_unknown = []
        self.comps = Comps(message_queue=message_queue)
        self.unknown_slots = self.comps.get_unknown_slots()
        self.champs_to_buy = self.comps.champions_to_buy()
        self.board_names = []
        self.items = []
        self.final_comp = False
        self.level = 0
        self.spam_roll = False

    def fix_board_state(self):
        bench_occupied = arena_functions.bench_occupied_check()
        for index, slot in enumerate(self.bench):
            if slot is None and bench_occupied[index] is True:
                self.bench[index] = "?"
            if isinstance(slot, str) and bench_occupied[index] is False:
                self.bench[index] = None
            if isinstance(slot, Champion) and bench_occupied[index] is False:
                self.bench[index] = None

    def bought_champion(self, name, slot):
        items = []
        for item in self.comps.comp[name]["items"]:
            items.append(item)
        self.bench[slot] = Champion(name, screen_coords.bench_loc[slot], items, slot,
                                    champion_data[name]["Board Size"], self.comps.comp[name]["final_comp"])
        mk_functions.move_mouse(screen_coords.default_loc)
        sleep(0.5)
        self.fix_board_state()

    def have_champion(self):
        for champion in self.bench:
            if isinstance(champion, Champion):
                if champion.name not in self.board_names:
                    return champion
        return None

    def move_known(self, champion):
        self.message_queue.put(("CONSOLE", f"Moving {champion.name} to board"))
        destination = screen_coords.board_loc[self.comps.comp[champion.name]["board_position"]]
        mk_functions.left_click(champion.coords)
        mk_functions.left_click(destination)
        champion.coords = destination
        self.board.append(champion)
        self.board_names.append(champion.name)
        self.bench[champion.index] = None
        champion.index = self.comps.comp[champion.name]["board_position"]
        self.board_size += champion.size

    def move_unknown(self):
        for index, champion in enumerate(self.bench):
            if isinstance(champion, str):
                self.message_queue.put(("CONSOLE", f"Moving {champion} to board"))
                mk_functions.left_click(screen_coords.bench_loc[index])
                mk_functions.left_click(screen_coords.board_loc[self.unknown_slots[len(self.board_unknown)]])
                self.bench[index] = None
                self.board_unknown.append(champion)
                self.board_size += 1
                return

    def sell_bench(self):
        for index, _ in enumerate(self.bench):
            mk_functions.press_e(screen_coords.bench_loc[index])
            self.bench[index] = None

    def unknown_in_bench(self):
        for slot in self.bench:
            if isinstance(slot, str):
                return True
        return False

    def move_champions(self):
        self.level = arena_functions.get_level()
        while self.level > self.board_size:
            champion = self.have_champion()
            if champion is not None:
                self.move_known(champion)
            elif self.unknown_in_bench():
                self.move_unknown()
            else:
                bought_unknown = False
                shop = arena_functions.get_shop()
                for index, champion in enumerate(shop):
                    try:  # Can fail if the shop slot is ""
                        if champion_data[champion]["Gold"] <= arena_functions.get_gold() and champion_data[champion][
                            "Board Size"] == 1 and champion not in self.champs_to_buy and champion not in self.board_unknown:
                            none_slot = arena_functions.empty_slot()
                            mk_functions.left_click(screen_coords.buy_loc[index])
                            sleep(0.2)
                            self.bench[none_slot] = f"{champion}"
                            self.move_unknown()
                            bought_unknown = True
                            break
                    except KeyError:
                        pass
                if not bought_unknown:
                    self.message_queue.put(("CONSOLE", "Need to sell entire bench to keep track of board"))
                    self.sell_bench()
                    return

    def replace_unknown(self):
        champion = self.have_champion()
        if len(self.board_unknown) > 0 and champion is not None:
            mk_functions.press_e(screen_coords.board_loc[self.unknown_slots[len(self.board_unknown) - 1]])
            self.board_unknown.pop()
            self.board_size -= 1
            self.move_known(champion)

    def bench_cleanup(self):
        for index, champion in enumerate(self.bench):
            if champion == "?" or isinstance(champion, str):
                self.message_queue.put(("CONSOLE", "Selling unknown champion"))
                mk_functions.press_e(screen_coords.bench_loc[index])
                self.bench[index] = None
            elif isinstance(champion, Champion):
                if champion.name not in self.champs_to_buy and champion.name in self.board_names:
                    self.message_queue.put(("CONSOLE", "Selling unknown champion"))
                    mk_functions.press_e(screen_coords.bench_loc[index])
                    self.bench[index] = None

    def place_items(self):
        self.items = arena_functions.get_items()
        log_items = list(filter((None).__ne__, self.items))
        self.message_queue.put(("CONSOLE", f"Items: {log_items}"))
        for index, _ in enumerate(self.items):
            if self.items[index] is not None:
                self.add_item_to_champs(index)

    def add_item_to_champs(self, item_index):
        for champ in self.board:
            if champ.does_need_items() and self.items[item_index] is not None:
                self.add_item_to_champ(item_index, champ)

    def add_item_to_champ(self, item_index, champ):
        item = self.items[item_index]
        if item in full_items:
            if item in champ.build:
                mk_functions.left_click(screen_coords.item_pos[item_index][0])
                mk_functions.left_click(champ.coords)
                self.message_queue.put(("CONSOLE", f"Placed {item} on {champ.name}"))
                champ.completed_items.append(item)
                champ.build.remove(item)
                self.items[self.items.index(item)] = None
        else:
            if len(champ.current_building) == 0:
                item_to_move = None
                for build_item in champ.build:
                    build_item_components = list(full_items[build_item])
                    if item in build_item_components:
                        item_to_move = item
                        build_item_components.remove(item)
                        champ.current_building.append((build_item, build_item_components[0]))
                        champ.build.remove(build_item)
                if item_to_move is not None:
                    mk_functions.left_click(screen_coords.item_pos[item_index][0])
                    mk_functions.left_click(champ.coords)
                    self.message_queue.put(("CONSOLE", f"Placed {item} on {champ.name}"))
                    self.items[self.items.index(item)] = None
            else:
                for builditem in champ.current_building:
                    if item == builditem[1]:
                        mk_functions.left_click(screen_coords.item_pos[item_index][0])
                        mk_functions.left_click(champ.coords)
                        champ.completed_items.append(builditem[0])
                        champ.current_building.clear()
                        self.items[self.items.index(item)] = None
                        self.message_queue.put(("CONSOLE", f"Placed {item} on {champ.name}"))
                        self.message_queue.put(("CONSOLE", f"Completed {builditem[0]}"))
                        return

    def fix_unknown(self):
        sleep(0.25)
        mk_functions.press_e(screen_coords.board_loc[self.unknown_slots[0]])
        self.board_unknown.pop(0)
        self.board_size -= 1

    def remove_champion(self, champion):
        for index, slot in enumerate(self.bench):
            if isinstance(slot, Champion):
                if slot.name == champion.name:
                    mk_functions.press_e(slot.coords)
                    self.bench[index] = None

        self.champs_to_buy = list(filter(f"{champion.name}".__ne__,
                                         self.champs_to_buy))  # Remove all instances of champion in champs_to_buy

        mk_functions.press_e(champion.coords)
        self.board_names.remove(champion.name)
        self.board_size -= champion.size
        self.board.remove(champion)

    def final_comp_check(self):
        for slot in self.bench:
            if isinstance(slot, Champion):
                if slot.final_comp is True and slot.name not in self.board_names:
                    for champion in self.board:
                        if champion.final_comp is False and champion.size == slot.size:
                            self.message_queue.put(("CONSOLE", f"Replacing {champion.name} with {slot.name}"))
                            self.remove_champion(champion)
                            self.move_known(slot)
                            break

    def tacticians_check(self):
        mk_functions.move_mouse(screen_coords.item_pos[0][0])
        sleep(2)
        item = ocr.get_text(screenxy=screen_coords.item_pos[0][1], scale=3, psm=13,
                            whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        item = arena_functions.valid_item(item)
        try:
            if "TacticiansCrown" in item:
                self.message_queue.put(("CONSOLE", "Tacticians Crown on bench, adding extra slot to board"))
                self.board_size -= 1
            else:
                self.message_queue.put(("CONSOLE", f"{item} is not TacticiansCrown"))
        except TypeError:
            self.message_queue.put(("CONSOLE", "Tacticians Crown check failed"))

    def buy_wanted_champions(self):
        shop = arena_functions.get_shop()
        self.message_queue.put(("CONSOLE", f"Shop: {shop}"))
        for index, champion in enumerate(shop):
            if champion in self.champs_to_buy:
                if arena_functions.get_gold() - game_assets.champion_data[champion]["Gold"] >= 0:
                    none_slot = arena_functions.empty_slot()
                    if none_slot != -1:
                        mk_functions.left_click(screen_coords.buy_loc[index])
                        self.message_queue.put(("CONSOLE", f"Purchased {champion}"))
                        self.bought_champion(champion, none_slot)
                        self.champs_to_buy.remove(champion)

    def spend_gold(self):  # Rework this function

        #slowroll level 6
        if self.comps.roll_level == 6:
            first_run = True
            min_gold = 13 if self.spam_roll is True else 56
            while first_run or arena_functions.get_gold() >= min_gold:



                # level to 6, slowrolling, leveling to 9
                if not first_run and arena_functions.get_level() < self.comps.roll_level:
                    mk_functions.buy_xp()
                    self.message_queue.put(("CONSOLE", "   Purchasing XP"))

                # slowrolling
                elif not first_run and arena_functions.get_level() == self.comps.roll_level and self.comps.do_slow_roll():
                    mk_functions.reroll()
                    self.message_queue.put(("CONSOLE", "   Rerolling shop"))

                # Leveling to 9
                elif not first_run and arena_functions.get_level() >= self.comps.roll_level:
                    if arena_functions.get_level() != 9:
                        mk_functions.buy_xp()
                        self.message_queue.put(("CONSOLE", "   Purchasing XP"))
                    mk_functions.reroll()
                    self.message_queue.put(("CONSOLE", "   Rerolling shop"))

                self.buy_wanted_champions()

                first_run = False

        #standard
        else :
            first_run = True
            min_gold = 24 if self.spam_roll is True else 56
            while first_run or arena_functions.get_gold() >= min_gold:
                if not first_run:
                    if arena_functions.get_level() != 9:
                        mk_functions.buy_xp()
                        self.message_queue.put(("CONSOLE", "   Purchasing XP"))
                    mk_functions.reroll()
                    self.message_queue.put(("CONSOLE", "   Rerolling shop"))
                shop = arena_functions.get_shop()
                self.message_queue.put(("CONSOLE", f"Shop: {shop}"))
                for index, champion in enumerate(shop):
                    if champion in self.champs_to_buy:
                        if arena_functions.get_gold() - game_assets.champion_data[champion]["Gold"] >= 0:
                            none_slot = arena_functions.empty_slot()
                            if none_slot != -1:
                                mk_functions.left_click(screen_coords.buy_loc[index])
                                self.message_queue.put(("CONSOLE", f"Purchased {champion}"))
                                self.bought_champion(champion, none_slot)
                                self.champs_to_buy.remove(champion)
                first_run = False


    def krug_round(self):
        if arena_functions.get_gold() >= 4:
            mk_functions.buy_xp()

    def pick_augment(self):
        augments = []
        for coords in screen_coords.augment_pos:
            augment = ocr.get_text(screenxy=coords, scale=3, psm=7, whitelist="")
            augments.append(augment)

        for augment in augments:
            for potential in self.comps.priority_augments:
                if potential in augment:
                    self.message_queue.put(("CONSOLE", f"Choosing priority augment {augment}"))
                    mk_functions.left_click(screen_coords.augment_loc[augments.index(augment)])
                    return

        for augment in augments:
            for potential in self.comps.backup_augments:
                if potential in augment:
                    self.message_queue.put(("CONSOLE", f"Choosing backup augment {augment}"))
                    mk_functions.left_click(screen_coords.augment_loc[augments.index(augment)])
                    return

        self.message_queue.put(("CONSOLE",
                                "[!] No priority or backup augment found, undefined behavior may occur for the rest of the round"))
        mk_functions.left_click(screen_coords.augment_loc[0])

    def check_health(self):
        health = arena_functions.get_health()
        if health <= 100 and health >= 0:
            self.message_queue.put(("CONSOLE", f"Health: {health}"))
            if self.spam_roll is False:
                if health < 30:
                    self.message_queue.put(("CONSOLE", f"Health under 30, spam roll activated"))
                    self.spam_roll = True
        else:
            self.message_queue.put(("CONSOLE", "Health check failed"))
            return

    def get_label(self):
        labels = []
        for slot in self.bench:
            if isinstance(slot, Champion):
                labels.append((f"{slot.name}", slot.coords))

        for slot in self.board:
            if isinstance(slot, Champion):
                labels.append((f"{slot.name}", slot.coords))

        for index, slot in enumerate(self.board_unknown):
            labels.append((slot, screen_coords.board_loc[self.unknown_slots[index]]))

        self.message_queue.put(("LABEL", labels))
