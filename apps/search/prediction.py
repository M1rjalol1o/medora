"""
Qolish ehtimoli bashorati.

G'oya: dorixonada `n` dona bor. Mijoz `t` daqiqada yetib boradi.
Shu vaqt ichida boshqa xaridorlar nechta sotib oladi? Sotuvlar Poisson
jarayoni deb olinadi: soatiga o'rtacha λ dona (shu soat va hafta kuni uchun).

    P(qoladi) = P(N(t) < n),   N(t) ~ Poisson(λ·t)

λ sotuv tarixidan hisoblanadi; tarix kam bo'lsa umumiy o'rtacha bilan
"silliqlanadi" (smoothing), shunda yangi dorixonada ham ishlaydi.
Keyingi bosqichda bu funksiya ML modeliga almashtiriladi — interfeys o'zgarmaydi.
"""
import math
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone

from apps.pharmacies.models import SaleRecord

# Tarix bo'lmagan holat uchun boshlang'ich taxmin (soatiga dona)
DEFAULT_RATE_PER_HOUR = 0.3
SMOOTHING_DAYS = 3.0


def poisson_prob_less_than(n: int, mu: float) -> float:
    """P(N < n), N ~ Poisson(mu)."""
    if n <= 0:
        return 0.0
    if mu <= 0:
        return 1.0
    term = math.exp(-mu)
    total = term
    for k in range(1, n):
        term *= mu / k
        total += term
    return min(1.0, total)


def hourly_rates(medicine_id: int, pharmacy_ids, at=None) -> dict:
    """Har bir dorixona uchun hozirgi soatdagi sotuv tezligi λ (dona/soat)."""
    at = timezone.localtime(at or timezone.now())
    days = settings.PREDICTION_HISTORY_DAYS
    since = at.date() - timedelta(days=days)
    base = SaleRecord.objects.filter(medicine_id=medicine_id, pharmacy_id__in=pharmacy_ids, date__gte=since)

    # Shu soat (va qo'shni soatlar) bo'yicha sotuvlar
    hours = [(at.hour - 1) % 24, at.hour, (at.hour + 1) % 24]
    in_hour = defaultdict(float)
    for row in base.filter(hour__in=hours).values("pharmacy_id", "hour").annotate(q=Sum("quantity")):
        weight = 2.0 if row["hour"] == at.hour else 1.0
        in_hour[row["pharmacy_id"]] += row["q"] * weight
    # Umumiy kunlik tezlik (silliqlash uchun)
    overall, observed = {}, {}
    for r in base.values("pharmacy_id").annotate(q=Sum("quantity"), d=Count("date", distinct=True)):
        overall[r["pharmacy_id"]] = r["q"]
        observed[r["pharmacy_id"]] = max(1, r["d"])     # tarix qisqa bo'lsa, haqiqiy kunlar soniga bo'lamiz

    rates = {}
    for pid in pharmacy_ids:
        n_days = observed.get(pid, 0)
        if not n_days:
            rates[pid] = DEFAULT_RATE_PER_HOUR
            continue
        hour_rate = in_hour.get(pid, 0.0) / (4.0 * n_days)       # 2+1+1 og'irlik
        overall_rate = overall[pid] / (n_days * 14)              # ~14 ish soati
        # Bayes uslubidagi silliqlash: tarix qancha uzun bo'lsa, soatlik ko'rsatkichga shuncha ishonamiz
        rates[pid] = (hour_rate * n_days + overall_rate * SMOOTHING_DAYS) / (n_days + SMOOTHING_DAYS)
    return rates


def availability_probability(available: int, rate_per_hour: float, minutes: float) -> float:
    return poisson_prob_less_than(available, rate_per_hour * minutes / 60.0)


def hours_until_stockout(available: int, rate_per_hour: float):
    if rate_per_hour <= 0:
        return None
    return available / rate_per_hour
