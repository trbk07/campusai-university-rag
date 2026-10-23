import {$, $$, state, events, hydrate, showDialog, closeDialog, notify} from './shared.js';
import {initDocuments, refreshDocuments} from '../features/documents.js';
import {initChat} from '../features/chat.js';

hydrate();
let drawer = null, returnFocus = null;
const small = () => matchMedia('(max-width:1279px)').matches;
export function closeDrawer() {
  if (!drawer) return;
  document.body.classList.remove('menu-open','sources-open');
  $('#drawer-backdrop').hidden = true;
  $('#menu-toggle').setAttribute('aria-expanded','false'); $('#source-toggle').setAttribute('aria-expanded','false');
  drawer.removeAttribute('role'); drawer.removeAttribute('aria-modal');
  $$('.workspace,.sidebar,.source-panel,.topbar').forEach(el => { el.inert = false; });
  drawer = null;
  if (returnFocus?.isConnected && returnFocus.getClientRects().length) returnFocus.focus();
}
function openDrawer(kind) {
  closeDrawer(); returnFocus = document.activeElement;
  drawer = $(kind === 'menu' ? '#sidebar' : '#sources');
  document.body.classList.add(kind === 'menu' ? 'menu-open' : 'sources-open');
  document.body.classList.remove('sources-hidden');
  $('#drawer-backdrop').hidden = false;
  $(kind === 'menu' ? '#menu-toggle' : '#source-toggle').setAttribute('aria-expanded','true');
  drawer.setAttribute('role','dialog'); drawer.setAttribute('aria-modal','true');
  $$('.workspace,.sidebar,.source-panel,.topbar').forEach(el => { if (el !== drawer) el.inert = true; });
  $('button,a[href],input', drawer)?.focus();
}
events.addEventListener('open-sources', () => { if (small()) openDrawer('sources'); else document.body.classList.remove('sources-hidden'); });
$('#menu-toggle').addEventListener('click', () => openDrawer('menu'));
$('#menu-close').addEventListener('click', closeDrawer);
$('#source-toggle').addEventListener('click', () => { if (small()) openDrawer('sources'); else document.body.classList.toggle('sources-hidden'); });
$('#source-close').addEventListener('click', () => { if (small()) closeDrawer(); else document.body.classList.add('sources-hidden'); });
$('#drawer-backdrop').addEventListener('click', closeDrawer);
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && drawer) { event.preventDefault(); closeDrawer(); }
  if (event.key === 'Tab' && drawer) {
    const focusable = $$('button:not(:disabled),a[href],input:not(:disabled),[tabindex="0"]', drawer).filter(el => el.getClientRects().length);
    const first = focusable[0], last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }
  if (event.key === '/' && !drawer && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName) && !document.querySelector('dialog[open]')) { event.preventDefault(); if ($('#global-search').getClientRects().length) $('#global-search').focus(); }
});
document.addEventListener('click', event => {
  const close = event.target.closest('.dialog-close'); if (close) closeDialog(close.closest('dialog'));
  if (event.target.closest('.upload-trigger')) { if (drawer) closeDrawer(); showDialog('upload-dialog'); }
});
$$('dialog').forEach(dialog => { dialog.addEventListener('close', () => { if (dialog.id === 'preview-dialog') $('#preview-body').replaceChildren(); }); });
function navigate() {
  const requested = location.hash.slice(1) || 'assistant';
  state.tab = ['assistant','documents','collections','guide'].includes(requested) ? requested : 'assistant';
  $$('.view').forEach(view => { view.hidden = view.id !== `view-${state.tab}`; });
  $$('.nav-item').forEach(link => { const active = link.hash === `#${state.tab}`; link.classList.toggle('active',active); if (active) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current'); });
  document.body.classList.toggle('other-view', state.tab !== 'assistant');
  document.title = `CampusAI · ${$('.nav-item.active').textContent.trim()}`;
  closeDrawer(); notify('navigation');
}
window.addEventListener('hashchange', () => { navigate(); $('#main').focus(); });
window.addEventListener('resize', closeDrawer);
$('#global-search-form').addEventListener('submit', event => { event.preventDefault(); state.search = $('#global-search').value; state.category = 'all'; location.hash = 'documents'; notify('search'); });
initDocuments(); initChat(); navigate(); refreshDocuments();
