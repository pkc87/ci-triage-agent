// Checkout form validation. Pure functions so the rules are readable on their own.

export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
export const ZIP_PATTERN = /^\d{5}$/;

/**
 * Validate an order. Returns a list of human-readable errors; empty means valid.
 */
export function validateOrder({ name = '', email = '', zip = '', itemCount = 0 } = {}) {
  const errors = [];

  if (!name.trim()) {
    errors.push('Name is required');
  }

  if (!EMAIL_PATTERN.test(email.trim())) {
    errors.push('Enter a valid email address');
  }

  if (!ZIP_PATTERN.test(zip.trim())) {
    errors.push('ZIP code must be 5 digits');
  }

  if (itemCount <= 0) {
    errors.push('Your cart is empty');
  }

  return errors;
}
