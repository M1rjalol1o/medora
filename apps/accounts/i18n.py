"""Backend xabarlari 3 tilda. Frontend Accept-Language sarlavhasini yuboradi."""
MESSAGES = {
    "not_found": ("Topilmadi.", "Не найдено.", "Not found."),
    "rx_required": ("Retseptli dori uchun retsept biriktiring.", "Для рецептурного препарата прикрепите рецепт.", "Attach a prescription for prescription medicines."),
    "closed": ("Dorixona hozir yopiq.", "Аптека сейчас закрыта.", "The pharmacy is closed now."),
    "only_left": ("Afsuski, faqat {n} dona qoldi.", "К сожалению, осталось только {n} шт.", "Sorry, only {n} left."),
    "cannot_cancel": ("Buni bekor qilib bo'lmaydi.", "Это нельзя отменить.", "This cannot be cancelled."),
    "wrong_code": ("Kod noto'g'ri.", "Неверный код.", "Wrong code."),
    "bad_status": ("Holat bunga ruxsat bermaydi.", "Статус не позволяет это действие.", "Status does not allow this."),
    "unknown_action": ("Noma'lum amal.", "Неизвестное действие.", "Unknown action."),
    "bad_value": ("Qiymat noto'g'ri: {f}", "Неверное значение: {f}", "Invalid value: {f}"),
    "empty_cart": ("Savat bo'sh.", "Корзина пуста.", "Cart is empty."),
    "card_invalid": ("Karta raqami noto'g'ri.", "Неверный номер карты.", "Invalid card number."),
    "card_expired": ("Karta muddati o'tgan yoki noto'g'ri.", "Срок карты истёк или неверен.", "Card expired or invalid."),
    "card_required": ("Karta tanlang.", "Выберите карту.", "Choose a card."),
    "otp_wrong": ("SMS kod noto'g'ri.", "Неверный SMS-код.", "Wrong SMS code."),
    "otp_expired": ("SMS kod muddati o'tdi. Qaytadan urinib ko'ring.", "Срок SMS-кода истёк. Попробуйте снова.", "SMS code expired. Try again."),
    "insufficient": ("Kartada mablag' yetarli emas.", "Недостаточно средств на карте.", "Insufficient funds."),
    "already_paid": ("Buyurtma allaqachon to'langan.", "Заказ уже оплачен.", "Order already paid."),
    "delivery_taken": ("Bu yetkazishni boshqa haydovchi oldi.", "Эту доставку уже взял другой водитель.", "Another driver already took this delivery."),
    "not_ready": ("Dorixona buyurtmani hali tayyorlamadi.", "Аптека ещё не подготовила заказ.", "The pharmacy has not prepared the order yet."),
    "has_active": ("Sizda tugallanmagan yetkazish bor.", "У вас есть незавершённая доставка.", "You have an unfinished delivery."),
    "offline": ("Avval 'Onlayn' rejimini yoqing.", "Сначала включите режим «Онлайн».", "Go online first."),
    "image_required": ("Rasm yoki matn yuboring.", "Отправьте фото или текст.", "Send a photo or text."),
}
LANGS = ("uz", "ru", "en")


def lang_of(request) -> str:
    header = (request.headers.get("Accept-Language") or "uz")[:2].lower()
    return header if header in LANGS else "uz"


def msg(request, key: str, **kw) -> str:
    texts = MESSAGES.get(key, (key, key, key))
    return texts[LANGS.index(lang_of(request))].format(**kw)
