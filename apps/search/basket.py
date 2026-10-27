"""
Bir nechta dori (retsept) uchun eng yaxshi dorixona(lar) kombinatsiyasi.

Shifokor odatda 2-3 ta dori yozadi. Biz quyidagi variantlarni hisoblaymiz:
  * Tavsiya        — tanlangan rejim (oddiy / shoshilinch) bo'yicha eng yaxshi to'liq variant
  * Hammasi bir joyda — barcha dorilar BITTA dorixonada va yetib borguncha tugamaydi
  * Eng tez        — umumiy yo'l vaqti eng kam (bir nechta dorixona bo'lishi mumkin)
  * Eng yaqin      — eng yaqin dorixona (hammasi bo'lmasligi mumkin — nima yetishmasligi ko'rsatiladi)

Har bir dorixonaga yetib borish vaqti marshrut bo'yicha hisoblanadi (A -> B -> C), shuning
uchun ikkinchi dorixonadagi dori uchun qolish ehtimoli kechroq vaqt bilan hisoblanadi.
Variantning umumiy ehtimoli = hamma dorilar qolish ehtimollari ko'paytmasi.
"""
from itertools import combinations, permutations

from django.conf import settings

from apps.pharmacies.models import Inventory

from .geo import haversine_km, travel_minutes
from .prediction import hourly_rates, poisson_prob_less_than

STOP_MINUTES = 3            # har bir dorixonada navbat/xarid
MISS_PENALTY = 25           # dori topilmasa qo'shimcha qidirish vaqti (daqiqa)
MAX_CANDIDATES = 12
MAX_STOPS = 3


def _prob(available, qty, rate, minutes):
    # Kerakli `qty` dona qolishi uchun: shu vaqtda sotiladigan soni <= available - qty
    return poisson_prob_less_than(available - qty + 1, rate * minutes / 60.0) if available >= qty else 0.0


def plan_basket(wanted, lat, lng, mode="normal", travel="car"):
    """wanted: [(Medicine, qty)]"""
    guaranteed = settings.GUARANTEED_PROBABILITY
    med_ids = [m.id for m, _ in wanted]
    qty_of = {m.id: q for m, q in wanted}
    med_of = {m.id: m for m, _ in wanted}

    invs = [i for i in Inventory.objects.select_related("pharmacy", "medicine")
            .filter(medicine_id__in=med_ids, pharmacy__is_active=True)
            if i.pharmacy.is_open_now()]
    stock = {}                       # (pharmacy_id, med_id) -> Inventory
    pharmacies = {}
    for inv in invs:
        if inv.available_quantity >= qty_of[inv.medicine_id]:
            stock[(inv.pharmacy_id, inv.medicine_id)] = inv
            pharmacies[inv.pharmacy_id] = inv.pharmacy
    rates = {mid: hourly_rates(mid, list(pharmacies)) for mid in med_ids}

    eta_home = {pid: travel_minutes(haversine_km(lat, lng, p.lat, p.lng), travel) for pid, p in pharmacies.items()}
    has = {pid: {mid for (p, mid) in stock if p == pid} for pid in pharmacies}
    not_anywhere = [mid for mid in med_ids if not any(mid in s for s in has.values())]
    findable = set(med_ids) - set(not_anywhere)

    cands = sorted(pharmacies, key=lambda pid: (-len(has[pid]), eta_home[pid]))
    nearest_first = sorted(pharmacies, key=lambda pid: eta_home[pid])
    pool = list(dict.fromkeys(nearest_first[:MAX_CANDIDATES] + cands[:6]))

    def evaluate(route):
        """route: dorixonalar tartibi. Har bir dori — eng ishonchli to'xtash joyiga biriktiriladi."""
        arrival, t, prev = {}, 0.0, None
        for pid in route:
            p = pharmacies[pid]
            t += eta_home[pid] if prev is None else travel_minutes(
                haversine_km(prev.lat, prev.lng, p.lat, p.lng), travel)
            arrival[pid] = t
            t += STOP_MINUTES
            prev = p
        assign, joint = {}, 1.0
        for mid in findable:
            best = None
            for pid in route:
                inv = stock.get((pid, mid))
                if not inv:
                    continue
                pr = _prob(inv.available_quantity, qty_of[mid], rates[mid].get(pid, 0), arrival[pid])
                if best is None or pr > best[1] + 1e-9:
                    best = (pid, pr, inv)
            if best is None:
                return None
            assign[mid] = best
            joint *= best[1]
        used = [pid for pid in route if any(a[0] == pid for a in assign.values())]
        if used != list(route):
            return None                                   # keraksiz to'xtash joyi bor
        total = arrival[route[-1]]
        return {"route": list(route), "arrival": arrival, "assign": assign, "probability": joint,
                "total_minutes": total,
                "expected": total + (1 - joint) * MISS_PENALTY,
                "worst": total + (0 if joint >= guaranteed else MISS_PENALTY)}

    plans = []
    for k in range(1, min(MAX_STOPS, len(findable)) + 1):
        for combo in combinations(pool, k):
            if set().union(*(has[p] for p in combo)) < findable:
                continue
            best = None
            for route in permutations(combo):
                r = evaluate(route)
                if r and (best is None or r["total_minutes"] < best["total_minutes"]):
                    best = r
            if best:
                plans.append(best)
        if len(plans) > 400:
            break

    key = "worst" if mode == "urgent" else "expected"

    def fmt(plan, kind):
        stops = []
        for pid in plan["route"]:
            p = pharmacies[pid]
            items = []
            for mid, (apid, pr, inv) in plan["assign"].items():
                if apid != pid:
                    continue
                m = med_of[mid]
                items.append({"medicine_id": mid, "name": m.name, "dosage": m.dosage,
                              "requires_prescription": m.requires_prescription, "quantity": qty_of[mid],
                              "inventory_id": inv.id, "available": inv.available_quantity,
                              "price": inv.final_price, "probability": round(pr, 3)})
            stops.append({"pharmacy": {"id": p.id, "name": p.name, "address": p.address, "phone": p.phone,
                                       "lat": p.lat, "lng": p.lng, "is_24h": p.is_24h},
                          "arrival_minutes": round(plan["arrival"][pid], 1), "items": items})
        total_price = sum(i["price"] * i["quantity"] for s in stops for i in s["items"])
        return {"kind": kind, "stops": stops, "pharmacies": len(stops),
                "total_minutes": round(plan["total_minutes"], 1), "probability": round(plan["probability"], 3),
                "guaranteed": plan["probability"] >= guaranteed, "total_price": total_price,
                "missing": [med_of[m].name for m in not_anywhere]}

    options, seen = [], set()

    def add(plan, kind):
        sig = tuple(sorted(plan["route"]))
        if sig in seen:
            for o in options:                 # bir xil variant — belgisini qo'shamiz
                if tuple(sorted(s["pharmacy"]["id"] for s in o["stops"])) == sig:
                    o.setdefault("also", []).append(kind)
            return
        seen.add(sig)
        options.append(fmt(plan, kind))

    if plans:
        add(min(plans, key=lambda p: (p[key], -p["probability"])), "recommended")
        singles = [p for p in plans if len(p["route"]) == 1]
        if singles:
            add(min(singles, key=lambda p: (p[key], -p["probability"])), "all_in_one")
        add(min(plans, key=lambda p: p["total_minutes"]), "fastest")
        safest = [p for p in plans if p["probability"] >= guaranteed]
        if safest:
            add(min(safest, key=lambda p: p["total_minutes"]), "safest")

    # Eng yaqin dorixona — to'liq bo'lmasa ham ko'rsatamiz (nima yetishmasligi bilan)
    nearest = None
    if nearest_first:
        pid = nearest_first[0]
        p = pharmacies[pid]
        got, miss = [], []
        for mid in med_ids:
            inv = stock.get((pid, mid))
            if inv:
                got.append({"medicine_id": mid, "name": med_of[mid].name, "dosage": med_of[mid].dosage,
                            "quantity": qty_of[mid], "inventory_id": inv.id, "price": inv.final_price,
                            "available": inv.available_quantity,
                            "probability": round(_prob(inv.available_quantity, qty_of[mid],
                                                       rates[mid].get(pid, 0), eta_home[pid]), 3)})
            else:
                miss.append(med_of[mid].name)
        nearest = {"pharmacy": {"id": p.id, "name": p.name, "address": p.address, "lat": p.lat, "lng": p.lng},
                   "eta_minutes": round(eta_home[pid], 1), "has": got, "missing": miss,
                   "covers_all": not miss}

    return {"mode": mode, "travel": travel, "options": options, "nearest": nearest,
            "not_found": [med_of[m].name for m in not_anywhere],
            "medicines": [{"id": m.id, "name": m.name, "dosage": m.dosage, "quantity": q} for m, q in wanted]}
