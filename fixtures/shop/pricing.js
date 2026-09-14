// Money math for the storefront.
//
// Store policy, in one place so it can be read without running the app:
//   * every amount is rounded to cents with half-up rounding
//   * handling is a flat fee, waived when the cart is empty
//   * tax is charged on the goods only, never on handling
//   * a promo code discounts the GROSS amount, i.e. after tax

export const TAX_RATE = 0.0825;
export const HANDLING_FEE = 2.5;

export const DISCOUNT_CODES = {
  WELCOME10: 0.1,
  SAVE20: 0.2,
};

/** Round to cents. */
export function round2(value) {
  return Math.round(value * 100) / 100;
}

/** Sum of price * quantity over all cart lines. */
export function subtotal(lines) {
  return round2(lines.reduce((sum, line) => sum + line.price * line.qty, 0));
}

/** Flat handling fee, waived for an empty cart. */
export function handling(lines) {
  return lines.length === 0 ? 0 : HANDLING_FEE;
}

/** Sales tax on the goods. */
export function tax(goods) {
  return round2(goods * TAX_RATE);
}

/** Discount for a code, as an amount off the gross. */
export function discountAmount(gross, code) {
  const rate = DISCOUNT_CODES[normalizeCode(code)] ?? 0;
  return round2(gross * rate);
}

export function normalizeCode(code) {
  return String(code ?? '').trim().toUpperCase();
}

export function isKnownCode(code) {
  return Object.prototype.hasOwnProperty.call(DISCOUNT_CODES, normalizeCode(code));
}

/** Full order summary for a set of cart lines and an optional promo code. */
export function summarize(lines, code) {
  const goods = subtotal(lines);
  const fee = handling(lines);
  const taxDue = tax(goods);
  const gross = round2(goods + fee + taxDue);
  const discount = discountAmount(gross, code);
  return {
    subtotal: goods,
    handling: fee,
    tax: taxDue,
    discount,
    total: round2(gross - discount),
  };
}

/** Format an amount the way the storefront shows it. */
export function formatMoney(value) {
  const sign = value < 0 ? '-' : '';
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}
