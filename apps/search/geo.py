import math

# Shahar ichida to'g'ri chiziq emas, yo'l bo'ylab yuriladi
ROAD_FACTOR = 1.35
SPEED_KMH = {"walk": 4.8, "car": 22.0}   # Toshkent tirbandligida o'rtacha


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def travel_minutes(distance_km: float, travel: str = "car") -> float:
    """Taxminiy yo'l vaqti (daqiqa). Keyinchalik Maps API bilan almashtiriladi."""
    speed = SPEED_KMH.get(travel, SPEED_KMH["car"])
    return distance_km * ROAD_FACTOR / speed * 60 + (2 if travel == "car" else 0)
