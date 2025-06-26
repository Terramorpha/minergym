import rdflib
from minergym.ontology import Ontology
import minergym.data.building as building


def test_zones():

    zones_expected = [
        "Breezeway",
        "attic",
        "crawlspace",
        "living_unit1_BackRow_BottomFloor",
        "living_unit1_BackRow_MiddleFloor",
        "living_unit1_BackRow_TopFloor",
        "living_unit1_FrontRow_BottomFloor",
        "living_unit1_FrontRow_MiddleFloor",
        "living_unit1_FrontRow_TopFloor",
        "living_unit2_BackRow_BottomFloor",
        "living_unit2_BackRow_MiddleFloor",
        "living_unit2_BackRow_TopFloor",
        "living_unit2_FrontRow_BottomFloor",
        "living_unit2_FrontRow_MiddleFloor",
        "living_unit2_FrontRow_TopFloor",
        "living_unit3_BackRow_BottomFloor",
        "living_unit3_BackRow_MiddleFloor",
        "living_unit3_BackRow_TopFloor",
        "living_unit3_FrontRow_BottomFloor",
        "living_unit3_FrontRow_MiddleFloor",
        "living_unit3_FrontRow_TopFloor",
    ]

    ont = Ontology.from_json(building.crawlspace)

    zones_real = [node.toPython() for node in ont.zones()]

    assert set(zones_expected) == set(zones_real)
