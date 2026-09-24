from app.agent import find_nearby_places, geocode_address


def test_geocode_address():
    res = geocode_address("1600 Amphitheatre Parkway, Mountain View, CA")
    assert res.get("status") == "success"
    assert "location" in res
    assert "latitude" in res["location"]
    assert "longitude" in res["location"]


def test_find_nearby_places():
    places = find_nearby_places(latitude=37.4224864, longitude=-122.0855962, place_type="store", radius=1000.0)
    assert isinstance(places, list)
    assert len(places) > 0
    first_place = places[0]
    assert "name" in first_place
    assert "address" in first_place
    assert "location" in first_place
