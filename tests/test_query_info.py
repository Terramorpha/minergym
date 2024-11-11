import rdflib
import tests.test_data as test_data
import clean_energyplus.query_info as query_info


def test_zones():

    epjson = test_data.building.joinpath("crawlspace.epJSON")

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

    rdf = query_info.json_to_rdf(epjson)

    zones_real = query_info.rdf_zones(rdf)

    assert set(zones_expected) == set(zones_real)
