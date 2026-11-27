let csrfToken = '';
const message = document.querySelector('#message');
async function request(path, method = 'GET', body) {
  const response = await fetch('/api/v1' + path, { method, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }, body: body ? JSON.stringify(body) : undefined });
  if (response.status === 409) throw new Error('Операция невозможна: ресурс уже существует, неактивен или занят бронированием.');
  if (response.status === 422) throw new Error('Проверьте корректность заполненных полей.');
  if (!response.ok) throw new Error('Не удалось выполнить запрос. Проверьте данные и права доступа.');
  return response.json();
}
async function refreshUsers() {
  const list = document.querySelector('#user-list');
  list.replaceChildren();
  for (const user of await request('/admin/users')) {
    const item = document.createElement('li');
    item.textContent = `${user.id}: ${user.display_name} · ${user.email} · ${user.role}`;
    list.append(item);
  }
}
function showAccount(data) {
  csrfToken = data.csrf_token;
  document.querySelector('#login-section').hidden = true;
  document.querySelector('#account-section').hidden = false;
  document.querySelector('#admin-section').hidden = data.user.role !== 'admin';
  document.querySelector('#resources-admin').hidden = data.user.role !== 'admin';
  refreshResources().catch((error) => { message.textContent = error.message; });
  document.querySelector('#identity').textContent = `${data.user.display_name} · ${data.user.email} · ${data.user.role} · ID ${data.user.id}`;
  if (data.user.role === 'admin') refreshUsers().catch((error) => { message.textContent = error.message; });
}
function showLogin() { csrfToken = ''; document.querySelector('#login-section').hidden = false; document.querySelector('#account-section').hidden = true; }
function formData(form) { return Object.fromEntries(new FormData(form)); }
function handle(id, action) { document.querySelector(id).addEventListener('submit', async (event) => { event.preventDefault(); const form = event.currentTarget; try { message.textContent = ''; await action(form); form.reset(); if (!message.textContent) message.textContent = 'Готово.'; } catch (error) { message.textContent = error.message; } }); }
handle('#login', async (form) => showAccount(await request('/sessions', 'POST', formData(form))));
handle('#password', async (form) => { await request('/users/me/change-password', 'POST', formData(form)); showLogin(); });
handle('#create-user', async (form) => { const user = await request('/admin/users', 'POST', formData(form)); await refreshUsers(); message.textContent = `Пользователь создан, ID: ${user.id}`; });
handle('#reset-password', async (form) => { const data = formData(form); await request(`/admin/users/${encodeURIComponent(data.user_id)}/reset-password`, 'POST', { password: data.password }); });
document.querySelector('#logout').addEventListener('click', async () => { try { await request('/sessions/current', 'DELETE'); showLogin(); } catch (error) { message.textContent = error.message; } });
request('/sessions/current').then(showAccount).catch(() => {});

let offices = [];
let rooms = [];
let equipment = [];
const officePicker = document.querySelector('#office-picker');
const officeForm = document.querySelector('#office-form');
const roomForm = document.querySelector('#room-form');
const equipmentForm = document.querySelector('#equipment-form');

function populate(select, items, label, emptyText, selected = '') {
  select.replaceChildren(new Option(emptyText, ''));
  for (const item of items) select.add(new Option(label(item), String(item.id)));
  select.value = selected;
}
function resetResourceForm(form) {
  form.reset();
  form.elements.id.value = '';
  form.elements.active.checked = true;
  if (form.elements.type) form.elements.type.disabled = false;
}
function showItems(selector, items, label) {
  const list = document.querySelector(selector);
  list.replaceChildren();
  for (const item of items) {
    const li = document.createElement('li');
    li.textContent = label(item);
    list.append(li);
  }
}
async function refreshResources(selectedOffice = officePicker.value) {
  offices = await request('/offices');
  const selected = offices.some((item) => String(item.id) === selectedOffice) ? selectedOffice : String(offices[0]?.id || '');
  populate(officePicker, offices, (item) => `${item.name} · ${item.timezone}${item.active ? '' : ' · неактивен'}`, 'Выберите офис', selected);
  populate(officeForm.elements.id, offices, (item) => item.name, 'Новый офис');
  rooms = selected ? await request(`/offices/${selected}/rooms`) : [];
  equipment = selected ? await request(`/offices/${selected}/equipment`) : [];
  showItems('#room-list', rooms, (item) => `${item.name} · ${item.category} · ${item.capacity} чел.${item.active ? '' : ' · неактивна'}`);
  showItems('#equipment-list', equipment, (item) => `${item.label} · ${item.type === 'projector' ? 'проектор' : 'громкая связь'}${item.active ? '' : ' · неактивно'}`);
  populate(roomForm.elements.id, rooms, (item) => item.name, 'Новая комната');
  populate(equipmentForm.elements.id, equipment, (item) => item.label, 'Новое оборудование');
  resetResourceForm(officeForm);
  resetResourceForm(roomForm);
  resetResourceForm(equipmentForm);
}
function fillResourceForm(form, items) {
  const item = items.find((entry) => String(entry.id) === form.elements.id.value);
  if (!item) { resetResourceForm(form); return; }
  for (const [key, value] of Object.entries(item)) {
    const input = form.elements.namedItem(key);
    if (!input || key === 'id') continue;
    if (input.type === 'checkbox') input.checked = value;
    else input.value = value;
  }
  if (form.elements.type) form.elements.type.disabled = true;
}
officePicker.addEventListener('change', () => refreshResources(officePicker.value).catch((error) => { message.textContent = error.message; }));
officeForm.elements.id.addEventListener('change', () => fillResourceForm(officeForm, offices));
roomForm.elements.id.addEventListener('change', () => fillResourceForm(roomForm, rooms));
equipmentForm.elements.id.addEventListener('change', () => fillResourceForm(equipmentForm, equipment));
handle('#office-form', async (form) => {
  const id = form.elements.id.value;
  const body = { name: form.elements.name.value, timezone: form.elements.timezone.value };
  if (id) body.active = form.elements.active.checked;
  const result = await request(id ? `/admin/offices/${id}` : '/admin/offices', id ? 'PATCH' : 'POST', body);
  await refreshResources(String(result.id));
});
handle('#room-form', async (form) => {
  const id = form.elements.id.value;
  const body = { name: form.elements.name.value, category: form.elements.category.value, capacity: Number(form.elements.capacity.value) };
  if (id) body.active = form.elements.active.checked;
  else body.office_id = Number(officePicker.value);
  await request(id ? `/admin/rooms/${id}` : '/admin/rooms', id ? 'PATCH' : 'POST', body);
  await refreshResources();
});
handle('#equipment-form', async (form) => {
  const id = form.elements.id.value;
  const body = { label: form.elements.label.value };
  if (id) body.active = form.elements.active.checked;
  else { body.office_id = Number(officePicker.value); body.type = form.elements.type.value; }
  await request(id ? `/admin/equipment/${id}` : '/admin/equipment', id ? 'PATCH' : 'POST', body);
  await refreshResources();
});
