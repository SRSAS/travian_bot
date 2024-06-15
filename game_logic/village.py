from utils import logger
import database.db_utils as DB


class Village:
    def __init__(self, woodcutters=4, clay_pits=4, iron_mines=4, croplands=6):
        self.population = 0

        self.lumber = 0
        self.clay = 0
        self.iron = 0
        self.crop = 0

        self.resource_buildings = {
            "woodcutters": [0 for _ in range(woodcutters)],
            "clay_pits": [0 for _ in range(clay_pits)],
            "iron_mines": [0 for _ in range(iron_mines)],
            "croplands": [0 for _ in range(croplands)]
        }

        self.buildings = {
            "Academy": 0,
            "Bakery": 0,
            "Barracks": 0,
            "Brewery": 0,
            "Brickyard": 0,
            "City Wall": 0,
            "Clay Pit": 0,
            "Command Center": 0,
            "Cranny": 0,
            "Cropland": 0,
            "Earth Wall": 0,
            "Embassy": 0,
            "Grain Mill": 0,
            "Granary": 0,
            "Great Barracks": 0,
            "Great Granary": 0,
            "Great Stable": 0,
            "Great Warehouse": 0,
            "Hero's Mansion": 0,
            "Horse Drinking Trough": 0,
            "Iron Foundry": 0,
            "Iron Mine": 0,
            "Main Building": 0,
            "Makeshift Wall": 0,
            "Marketplace": 0,
            "Palace": 0,
            "Palisade": 0,
            "Rally Point": 0,
            "Residence": 0,
            "Sawmill": 0,
            "Smithy": 0,
            "Stable": 0,
            "Stone Wall": 0,
            "Stonemason": 0,
            "Tournament Square": 0,
            "Town Hall": 0,
            "Trade Office": 0,
            "Trapper": 0,
            "Treasury": 0,
            "Warehouse": 0,
            "Waterworks": 0,
            "Wonder of the World": 0,
            "Woodcutter": 0,
            "Workshop": 0
        }

        self.troops = {
            "Legionnaire": {"present": 0, "absent": 0},
            "Praetorian": {"present": 0, "absent": 0},
            "Imperian": {"present": 0, "absent": 0},
            "Equites Legati": {"present": 0, "absent": 0},
            "Equites Imperatories": {"present": 0, "absent": 0},
            "Equites Caesaris": {"present": 0, "absent": 0},
            "Battering ram": {"present": 0, "absent": 0},
            "Fire Catapult": {"present": 0, "absent": 0},
            "Senator": {"present": 0, "absent": 0},
            "Settler": {"present": 0, "absent": 0}
        }

        self.gold_bonus_production = {
            "lumber": False,
            "clay": False,
            "iron": False,
            "crop": False
        }

        self.production = {
            "lumber": {"normal": 0, "troop_average": 0},
            "clay": {"normal": 0, "troop_average": 0},
            "iron": {"normal": 0, "troop_average": 0},
            "crop": {"normal": 0, "troop_average": 0},
        }

        self.build_queue = {
            "buildings": [],
            "resources": []
        }

        self.troop_movements = {
            "outgoing": [],
            "incoming": []
        }

        self.trade_routes = {
            "outgoing": [],
            "incoming": []
        }

    def increase_building_level(self, building, levels):
        if building not in self.buildings.keys() and building not in self.resource_buildings.keys():
            logger.error(f"increment_building_level: {building} does not exist")
            return

        if building in self.resource_buildings.keys():
            self.resource_buildings[building] += levels
        elif building in self.buildings.keys():
            self.buildings[building] += levels

    def decrease_building_level(self, building, levels):
        logger.info("decrease_building_level is just sugar for negative increases")
        self.increase_building_level(building, -levels)

    def increase_resource_production(self, resource, production_increase):
        if resource not in self.production.keys():
            logger.error(f"increase_resource_production: {resource} does not exist")
        else:
            self.production[resource] += production_increase

    def decrease_resource_production(self, resource, production_decrease):
        logger.info("decrease_resource_production is just sugar for negative decrease")
        self.increase_resource_production(resource, -production_decrease)

    def increase_troop_number(self, troop, troop_amount):
        if troop not in self.troops.keys():
            logger.error(f"increase_troop_number: {troop} does not exist")
            return
        self.troops[troop] += troop_amount

    def decrease_troop_number(self, troop, troop_amount):
        logger.info("decrease_troop_number is just sugar for negative increases")
        self.increase_troop_number(troop, -troop_amount)

    def apply_production(self, hours):
        new_lumber = self.lumber + hours * self.production["lumber"]["normal"]
        self.lumber = min(new_lumber, self.get_warehouse_capacity())

        new_clay = self.clay + hours * self.production["clay"]["normal"]
        self.clay = min(new_clay, self.get_warehouse_capacity())

        new_iron = self.iron + hours * self.production["iron"]["normal"]
        self.iron = min(new_iron, self.get_warehouse_capacity())

        new_crop = self.crop + hours * self.production["crop"]["normal"]
        self.crop = min(new_crop, self.get_granary_capacity())

    def get_building_current_effect_value(self, building):
        if building not in self.buildings.keys() and building not in self.resource_buildings.keys():
            logger.error(f"get_building_current_effect_value: {building} does not exist")
            return None

        level = self.buildings[building]

        conn = DB.get_connection_to_database()
        cursor = conn.cursor()

        value = DB.get_building_effect_value(cursor, building, level)

        cursor.close()
        conn.close()

        return value

    def get_warehouse_capacity(self):
        capacity = self.get_building_current_effect_value("Warehouse")
        if capacity is None:
            return None
        return int(capacity)

    def get_granary_capacity(self):
        capacity = self.get_building_current_effect_value("Granary")
        if capacity is None:
            return None
        return int(capacity)

    def get_building_upkeep(self, building):
        if building not in self.buildings.keys() and building not in self.resource_buildings.keys():
            logger.error(f"get_building_upkeep: {building} does not exist")
            return None

        conn = DB.get_connection_to_database()
        cursor = conn.cursor()

        level = self.buildings[building]
        level_info_list = DB.get_building_level_info(cursor, building, level, True)
        upkeep = 0
        for level_info in level_info_list:
            upkeep += level_info["upkeep"]

        cursor.close()
        conn.close()

        return upkeep

    def get_building_attribute(self, building, attribute, level=None):
        if building not in self.buildings.keys() and building not in self.resource_buildings.keys():
            logger.error(f"get_building_attribute: {building} does not exist")
            return None

        conn = DB.get_connection_to_database()
        cursor = conn.cursor()

        if level is None:
            level = self.buildings[building]
        level_info = DB.get_building_level_info(cursor, building, level, False)

        cursor.close()
        conn.close()

        return level_info[attribute]
