from django.db import models


class Medicine(models.Model):
    """Markaziy dori katalogi. Real qoldiq Inventory'da saqlanadi."""

    name = models.CharField("Nomi", max_length=200)
    inn = models.CharField("Xalqaro nomi (MNN)", max_length=200, blank=True)
    form = models.CharField("Shakli", max_length=50, blank=True)          # tabletka, sirop ...
    dosage = models.CharField("Dozasi", max_length=50, blank=True)        # 500 mg
    manufacturer = models.CharField("Ishlab chiqaruvchi", max_length=200, blank=True)
    requires_prescription = models.BooleanField("Retsept talab qilinadi", default=False)
    # Qidiruv uchun boshqa yozilishlar: kirill, ruscha, xato yozilishlar (vergul bilan)
    aliases = models.TextField("Muqobil nomlar", blank=True)
    # Qidiruvni tezlashtirish uchun normallashtirilgan matn
    search_text = models.TextField(editable=False, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} {self.dosage}".strip()

    def save(self, *args, **kwargs):
        from .utils import normalize
        self.search_text = normalize(" ".join([self.name, self.inn, self.aliases]))
        super().save(*args, **kwargs)
