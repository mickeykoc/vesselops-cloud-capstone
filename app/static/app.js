'use strict';
let token = '';
let selected = null;
let tickets = [];
const $ = id => document.getElementById(id);
function node(tag, text, cls) { const item = document.createElement(tag); if (text !== undefined) item.textContent = text; if (cls) item.className = cls; return item; }
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
function clearRecords() {
  tickets = []; selected = null;
  for (const id of ['metric-active', 'metric-overdue', 'metric-incidents', 'metric-assets']) $(id).textContent = '—';
  $('ticket-rows').replaceChildren(); $('incident-list').replaceChildren(); $('asset-list').replaceChildren();
}
function lock() { $('ticket-dialog').close(); $('ticket-history').replaceChildren(); $('update-note').value = ''; token = ''; $('token').value = ''; clearRecords(); document.body.classList.remove('connected'); $('connection-state').textContent = 'Locked'; }
async function api(path, method = 'GET', body) {
  if (!token) throw new Error('Connect with your operator token first.');
  const response = await fetch(path, { method, headers: { Authorization: 'Bearer ' + token, ...(body ? { 'Content-Type': 'application/json' } : {}) }, ...(body ? { body: JSON.stringify(body) } : {}) });
  const result = await response.json();
  if (!response.ok) { if (response.status === 401) lock(); throw new Error(result.error || 'Request failed'); }
  return result;
}
function render(data) {
  tickets = data.tickets;
  $('metric-active').textContent = data.summary.active; $('metric-overdue').textContent = data.summary.overdue;
  $('metric-incidents').textContent = data.summary.incidents; $('metric-assets').textContent = data.assets.length;
  const rows = tickets.map(ticket => {
    const row = node('tr'); const issue = node('td'); issue.append(node('b', ticket.title), node('small', (ticket.asset_id || 'No linked asset') + (ticket.overdue ? ' · OVERDUE' : '')));
    const priority = node('td'); priority.append(node('span', ticket.priority, 'badge ' + ticket.priority));
    const status = node('td'); status.append(node('span', ticket.status.replaceAll('_', ' '), 'badge ' + ticket.status));
    const action = node('td'); const button = node('button', 'Review →', 'small-button'); button.type = 'button'; button.addEventListener('click', () => review(ticket)); action.append(button);
    row.append(issue, priority, status, action); return row;
  });
  if (!rows.length) { const row = node('tr'); const cell = node('td', 'No tickets yet. Open your first support case below.', 'empty'); cell.colSpan = 4; row.append(cell); rows.push(row); }
  $('ticket-rows').replaceChildren(...rows);
  $('incident-list').replaceChildren(...data.incidents.map(incident => {
    const card = node('article', undefined, 'incident-card'); card.append(node('span', incident.severity, 'badge ' + incident.severity), node('h3', incident.title), node('p', incident.summary), node('code', incident.event_ids.join(' · ')), node('p', 'Source: ' + incident.source)); return card;
  }));
  if (!data.incidents.length) $('incident-list').append(node('p', 'No incidents. Run the scenario tool to import synthetic evidence.', 'empty'));
  $('asset-list').replaceChildren(...data.assets.map(asset => { const row = node('div', undefined, 'asset-item'); const name = node('div', asset.hostname); name.append(node('small', asset.id + ' / ' + asset.owner)); row.append(name, node('span', 'REGISTERED', 'tag')); return row; }));
  if (!data.assets.length) $('asset-list').append(node('p', 'Register a synthetic asset below.', 'empty'));
}
async function refresh() { render(await api('/api/state')); }
function review(ticket) {
  selected = ticket; $('dialog-title').textContent = ticket.title; $('dialog-error').textContent = ''; $('update-note').value = '';
  const next = { open: 'in_progress', in_progress: 'resolved', resolved: 'open' }[ticket.status];
  const option = node('option', next.replaceAll('_', ' ')); option.value = next; $('next-status').replaceChildren(option);
  $('ticket-history').replaceChildren(...ticket.history.map(entry => { const p = node('p', entry.note); p.append(node('small', entry.status + ' · ' + new Date(entry.at).toLocaleString())); return p; }));
  $('ticket-dialog').showModal();
}
$('connect-form').addEventListener('submit', async event => { event.preventDefault(); token = $('token').value.trim(); $('token').value = ''; try { await refresh(); document.body.classList.add('connected'); $('connection-state').textContent = 'Connected'; message('Operator session active. Records loaded.'); } catch (error) { lock(); message(error.message, true); } });
$('disconnect').addEventListener('click', () => { lock(); message('Session locked. Token and displayed records cleared.'); });
$('refresh').addEventListener('click', async () => { try { await refresh(); message('Records refreshed.'); } catch (error) { message(error.message, true); } });
for (const [formId, endpoint] of [['ticket-form', '/api/tickets'], ['asset-form', '/api/assets']]) {
  $(formId).addEventListener('submit', async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.target)); if (formId === 'ticket-form' && !data.asset_id) delete data.asset_id; try { await api(endpoint, 'POST', data); event.target.reset(); await refresh(); message('Record created.'); } catch (error) { message(error.message, true); } });
}
$('close-dialog').addEventListener('click', () => $('ticket-dialog').close());
$('update-form').addEventListener('submit', async event => { event.preventDefault(); if (!selected) return; try { await api('/api/tickets/' + encodeURIComponent(selected.id), 'PATCH', { status: $('next-status').value, note: $('update-note').value, version: selected.version }); $('ticket-dialog').close(); await refresh(); message('Ticket updated. Investigation history preserved.'); } catch (error) { $('dialog-error').textContent = error.message; } });
