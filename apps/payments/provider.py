"""
To'lov provayderi abstraksiyasi.

Ilova karta raqamini O'ZI SAQLAMAYDI. Karta provayderga (Payme/Click/Uzum Bank) yuboriladi,
provayder SMS kod jo'natadi, tasdiqlangach token qaytaradi. Keyingi to'lovlar token bilan.

SandboxProvider — sinov uchun: haqiqiy pul yechilmaydi, SMS kod javobda qaytariladi.
Haqiqiy ulanish: PaymeProvider(BaseProvider) yozib, settings.PAYMENT_PROVIDER = "payme".
"""
import hashlib
import secrets


def luhn_ok(number: str) -> bool:
    digits = [int(d) for d in number][::-1]
    total = 0
    for i, d in enumerate(digits):
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def card_brand(number: str) -> str:
    if number.startswith("8600") or number.startswith("5614"):
        return "Uzcard"
    if number.startswith("9860"):
        return "Humo"
    if number.startswith("4"):
        return "Visa"
    if number.startswith("5") or number.startswith("2"):
        return "Mastercard"
    return "Karta"


def mask(number: str) -> str:
    return f"{number[:4]} •••• •••• {number[-4:]}"


def hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class BaseProvider:
    name = "base"
    returns_code = False      # sinovda SMS kodni javobda ko'rsatish

    def start_binding(self, number: str, expiry: str) -> dict:
        """Kartani bog'lashni boshlaydi: {token, phone_hint, otp}"""
        raise NotImplementedError

    def charge(self, token: str, amount: int, description: str) -> dict:
        """{ok: bool, ref: str, error: str|None}"""
        raise NotImplementedError

    def refund(self, ref: str, amount: int) -> bool:
        raise NotImplementedError


class SandboxProvider(BaseProvider):
    name = "sandbox"
    returns_code = True

    def start_binding(self, number, expiry):
        return {
            "token": "sbx_" + secrets.token_hex(16) + "#" + number[-4:],
            "phone_hint": "+998 ** *** ** " + number[-2:],
            "otp": f"{secrets.randbelow(1_000_000):06d}",
        }

    def charge(self, token, amount, description):
        # Sinov qoidasi: oxiri 0002 bo'lgan karta — "mablag' yetarli emas"
        if token.endswith("#0002"):
            return {"ok": False, "ref": "", "error": "insufficient"}
        return {"ok": True, "ref": "sbx_pay_" + secrets.token_hex(8), "error": None}

    def refund(self, ref, amount):
        return True


def get_provider() -> BaseProvider:
    from django.conf import settings
    return {"sandbox": SandboxProvider}.get(settings.PAYMENT_PROVIDER, SandboxProvider)()
