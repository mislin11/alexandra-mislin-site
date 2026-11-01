/* Small host-independent compatibility layer for original Squarespace pagination URLs.
   Navigation, articles and the three ordinary page routes work without JavaScript. */
(() => {
  const list = document.querySelector('[data-legacy-pagination]');
  if (!list) return;
  const params = new URLSearchParams(location.search);
  const rawOffset = params.get('offset');
  if (!rawOffset || !/^\d+$/.test(rawOffset)) return;
  const offset = Number(rawOffset);
  const reverse = params.get('reversePaginate') === 'true';
  const rows = Array.from(list.querySelectorAll('[data-published]'));
  const eligible = rows.filter(row => reverse ? Number(row.dataset.published) > offset : Number(row.dataset.published) < offset);
  const visible = reverse ? eligible.slice(-3) : eligible.slice(0, 3);
  rows.forEach(row => { row.hidden = !visible.includes(row); });
  document.querySelectorAll('.pagination [aria-current]').forEach(link => link.removeAttribute('aria-current'));
})();
