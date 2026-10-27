"""
Natijalarni saralash.

normal  — o'rtacha kutiladigan vaqt bo'yicha:  t_A + (1 − p_A) · t(A→B)
urgent  — kafolatli vaqt bo'yicha: p ≥ chegara bo'lsa t_A, aks holda eng yomon holat
          (A ga borib, topolmay, eng yaqin kafolatli B ga o'tish).
"""
from django.conf import settings

from .geo import haversine_km, travel_minutes


def rank_offers(offers: list, mode: str, travel: str) -> list:
    guaranteed = settings.GUARANTEED_PROBABILITY
    safe = [o for o in offers if o["probability"] >= guaranteed]

    for o in offers:
        # A topilmasa — eng yaqin kafolatli zaxira dorixona
        backup = None
        best = None
        for s in safe:
            if s["pharmacy"]["id"] == o["pharmacy"]["id"]:
                continue
            d = haversine_km(o["pharmacy"]["lat"], o["pharmacy"]["lng"], s["pharmacy"]["lat"], s["pharmacy"]["lng"])
            m = travel_minutes(d, travel)
            if best is None or m < best:
                best, backup = m, s
        fallback = best if best is not None else 60.0   # zaxira yo'q — katta jarima
        o["worst_case_minutes"] = round(o["eta_minutes"] + (0 if o["probability"] >= guaranteed else fallback), 1)
        o["expected_minutes"] = round(o["eta_minutes"] + (1 - o["probability"]) * fallback, 1)
        o["backup_pharmacy"] = backup["pharmacy"]["name"] if backup and o["probability"] < guaranteed else None
        o["guaranteed"] = o["probability"] >= guaranteed

    key = "worst_case_minutes" if mode == "urgent" else "expected_minutes"
    ranked = sorted(offers, key=lambda o: (o["available"] == 0, o[key], -o["probability"]))
    for i, o in enumerate(ranked):
        o["rank"] = i + 1
    if ranked and ranked[0]["available"] > 0:
        ranked[0]["recommended"] = True
    return ranked
