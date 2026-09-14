import { summarize, formatMoney, isKnownCode, normalizeCode } from '/pricing.js';
import { validateOrder } from '/validate.js';

export const CATALOG = [
  { id: 'p1', name: 'Aeropress Go', price: 39.95, blurb: 'Travel press with a cup that doubles as a lid.' },
  { id: 'p2', name: 'Burr Grinder', price: 129.0, blurb: '40 mm conical burrs, 36 grind settings.' },
  { id: 'p3', name: 'Gooseneck Kettle', price: 64.5, blurb: 'Variable temperature, one degree at a time.' },
  { id: 'p4', name: 'Filter Papers', price: 8.25, blurb: 'Pack of 100, oxygen bleached.' },
];

const BANNER_MESSAGES = [
  'Free shipping on orders over $50',
  'Roasted to order, shipped same day',
  'Use code WELCOME10 for 10% off',
];

const BANNER_INTERVAL_MS = 400;

// The reviews endpoint is a static file, so the fixture adds the latency a real
// API would have. The spread is what makes "load, then look" a race.
const REVIEW_LATENCY_MIN_MS = 80;
const REVIEW_LATENCY_SPREAD_MS = 260;

/** Cart state: product id -> quantity. */
const cart = new Map();
let promoCode = '';

const $ = (testid) => document.querySelector(`[data-testid="${testid}"]`);

function cartLines() {
  return [...cart.entries()].map(([id, qty]) => {
    const product = CATALOG.find((item) => item.id === id);
    return { id, name: product.name, price: product.price, qty };
  });
}

function unitCount() {
  return cartLines().reduce((sum, line) => sum + line.qty, 0);
}

function clampQuantity(raw) {
  const parsed = Math.floor(Number(raw));
  if (!Number.isFinite(parsed)) return 1;
  return Math.max(1, parsed);
}

function renderCatalog() {
  const grid = $('product-grid');
  grid.innerHTML = '';
  for (const product of CATALOG) {
    const li = document.createElement('li');
    li.className = 'product';
    li.dataset.testid = `product-${product.id}`;
    li.innerHTML = `
      <h3>${product.name}</h3>
      <span class="price" data-testid="price-${product.id}">${formatMoney(product.price)}</span>
      <p>${product.blurb}</p>
      <button type="button" data-testid="add-${product.id}">Add to cart</button>
    `;
    li.querySelector('button').addEventListener('click', () => {
      cart.set(product.id, (cart.get(product.id) ?? 0) + 1);
      render();
    });
    grid.append(li);
  }
}

function renderCart() {
  const list = $('cart-items');
  const lines = cartLines();
  list.innerHTML = '';

  $('cart-empty').hidden = lines.length > 0;

  for (const line of lines) {
    const li = document.createElement('li');
    li.dataset.testid = `cart-row-${line.id}`;
    li.innerHTML = `
      <span class="line-name">${line.name}</span>
      <input type="number" data-testid="qty-${line.id}" value="${line.qty}" min="1" />
      <span class="line-total" data-testid="line-total-${line.id}">${formatMoney(line.price * line.qty)}</span>
      <button type="button" class="secondary" data-testid="remove-${line.id}" aria-label="Remove ${line.name}">x</button>
    `;
    li.querySelector('input').addEventListener('change', (event) => {
      const qty = clampQuantity(event.target.value);
      cart.set(line.id, qty);
      render();
    });
    li.querySelector('button').addEventListener('click', () => {
      cart.delete(line.id);
      render();
    });
    list.append(li);
  }
}

function renderSummary() {
  const totals = summarize(cartLines(), promoCode);
  $('subtotal').textContent = formatMoney(totals.subtotal);
  $('handling').textContent = formatMoney(totals.handling);
  $('tax').textContent = formatMoney(totals.tax);
  $('discount').textContent = `-${formatMoney(totals.discount)}`;
  $('total').textContent = formatMoney(totals.total);
}

function renderBadge() {
  const units = unitCount();
  $('cart-badge').textContent = `${units} item${units === 1 ? '' : 's'}`;
}

function render() {
  renderCart();
  renderSummary();
  renderBadge();
}

function wirePromo() {
  $('apply-discount').addEventListener('click', () => {
    const entered = $('discount-code').value;
    const status = $('discount-status');
    if (isKnownCode(entered)) {
      promoCode = normalizeCode(entered);
      status.textContent = `Code ${promoCode} applied`;
      status.dataset.state = 'ok';
    } else {
      promoCode = '';
      status.textContent = 'Unknown promo code';
      status.dataset.state = 'error';
    }
    render();
  });
}

function orderId() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let id = '';
  for (let i = 0; i < 6; i += 1) {
    id += alphabet[Math.floor(Math.random() * alphabet.length)];
  }
  return id;
}

function wireCheckout() {
  $('checkout-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const errors = validateOrder({
      name: $('name').value,
      email: $('email').value,
      zip: $('zip').value,
      itemCount: unitCount(),
    });

    const errorBox = $('form-error');
    const confirmation = $('order-confirmation');
    errorBox.innerHTML = '';

    if (errors.length > 0) {
      for (const message of errors) {
        const li = document.createElement('li');
        li.textContent = message;
        errorBox.append(li);
      }
      errorBox.hidden = false;
      confirmation.hidden = true;
      return;
    }

    errorBox.hidden = true;
    const placedOn = new Date().toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    confirmation.textContent = `Order #${orderId()} placed on ${placedOn}`;
    confirmation.hidden = false;

    cart.clear();
    promoCode = '';
    $('discount-code').value = '';
    $('discount-status').textContent = '';
    render();
  });
}

function startBanner() {
  const banner = $('banner');
  // Start on a random message so repeat visitors do not always see the same one.
  let index = Math.floor(Math.random() * BANNER_MESSAGES.length);
  banner.textContent = BANNER_MESSAGES[index];
  setInterval(() => {
    index = (index + 1) % BANNER_MESSAGES.length;
    banner.textContent = BANNER_MESSAGES[index];
  }, BANNER_INTERVAL_MS);
}

function stars(rating) {
  return '*'.repeat(rating);
}

function approvedOnly(reviews) {
  return reviews.filter((review) => review.approved);
}

function averageRating(reviews) {
  if (reviews.length === 0) return 0;
  return reviews.reduce((sum, review) => sum + review.rating, 0) / reviews.length;
}

function wireReviews() {
  $('load-reviews').addEventListener('click', async () => {
    const spinner = $('reviews-spinner');
    const list = $('reviews-list');
    const average = $('average-rating');

    spinner.hidden = false;
    average.hidden = true;
    list.innerHTML = '';

    const response = await fetch('/reviews.json');
    const payload = await response.json();

    await new Promise((resolve) => {
      const delay = REVIEW_LATENCY_MIN_MS + Math.random() * REVIEW_LATENCY_SPREAD_MS;
      setTimeout(resolve, delay);
    });

    const visible = approvedOnly(payload.reviews);
    for (const review of visible) {
      const li = document.createElement('li');
      li.dataset.testid = 'review-item';
      li.innerHTML = `
        <span class="review-author">${review.author}</span>
        <span class="review-stars">${stars(review.rating)}</span>
        <p>${review.body}</p>
      `;
      list.append(li);
    }

    average.textContent = `Average rating: ${averageRating(visible).toFixed(1)} out of 5`;
    average.hidden = false;
    spinner.hidden = true;
  });
}

function renderRecommendations() {
  const list = $('recommendations');
  const shuffled = [...CATALOG];
  for (let i = shuffled.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  list.innerHTML = '';
  for (const product of shuffled.slice(0, 3)) {
    const li = document.createElement('li');
    li.dataset.testid = 'rec-item';
    li.textContent = product.name;
    list.append(li);
  }
}

function wireCartSync() {
  const status = $('cart-sync-status');

  $('save-cart').addEventListener('click', async () => {
    status.textContent = 'Saving...';
    await fetch('/api/saved-cart', {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ lines: cartLines().map(({ id, qty }) => ({ id, qty })) }),
    });
    status.textContent = 'Cart saved';
  });

  $('restore-cart').addEventListener('click', async () => {
    status.textContent = 'Restoring...';
    const response = await fetch('/api/saved-cart');
    const payload = await response.json();
    cart.clear();
    for (const line of payload.lines ?? []) {
      cart.set(line.id, line.qty);
    }
    render();
    status.textContent = 'Cart restored';
  });
}

renderCatalog();
render();
wirePromo();
wireCheckout();
wireReviews();
wireCartSync();
renderRecommendations();
startBanner();
