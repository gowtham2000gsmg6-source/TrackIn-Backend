import math


def haversine_distance_m(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    """Return the great-circle distance between two WGS84 coordinates in metres."""
    earth_radius_m = 6_371_000
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lng = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lng / 2) ** 2
    )
    return 2 * earth_radius_m * math.asin(math.sqrt(min(1, haversine)))
