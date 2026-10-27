// Savat: bir nechta dorixonadan dorilar, lekin to'lov bitta.
import { store } from "./api.js";

const KEY = "apteka.cart";
const listeners = new Set();

export const cart = {
  get items() { return store.get(KEY) || []; },
  save(items) { store.set(KEY, items); listeners.forEach((f) => f(items)); },
  add(offer, medicine, qty = 1) {
    const items = this.items;
    const ex = items.find((i) => i.inventory_id === offer.inventory_id);
    if (ex) ex.quantity = Math.min(ex.quantity + qty, offer.available);
    else items.push({
      inventory_id: offer.inventory_id, quantity: qty, max: offer.available, price: offer.price,
      name: medicine.name, dosage: medicine.dosage, rx: !!medicine.requires_prescription,
      pharmacy_id: offer.pharmacy.id, pharmacy: offer.pharmacy.name,
    });
    this.save(items);
  },
  setQty(id, qty) {
    let items = this.items;
    const it = items.find((i) => i.inventory_id === id);
    if (!it) return;
    if (qty <= 0) items = items.filter((i) => i.inventory_id !== id);
    else it.quantity = Math.min(qty, it.max || 99);
    this.save(items);
  },
  clear() { this.save([]); },
  get count() { return this.items.reduce((s, i) => s + i.quantity, 0); },
  get hasRx() { return this.items.some((i) => i.rx); },
  onChange(f) { listeners.add(f); return () => listeners.delete(f); },
};
