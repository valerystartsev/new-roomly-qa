let csrfToken = '';
const message = document.querySelector('#message');
async function request(path, method = 'GET', body) {
  const response = await fetch('/api/v1' + path, { method, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }, body: body ? JSON.stringify(body) : undefined });
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
  document.querySelector('#identity').textContent = `${data.user.display_name} · ${data.user.email} · ${data.user.role} · ID ${data.user.id}`;
  if (data.user.role === 'admin') refreshUsers().catch((error) => { message.textContent = error.message; });
}
function showLogin() { csrfToken = ''; document.querySelector('#login-section').hidden = false; document.querySelector('#account-section').hidden = true; }
function formData(form) { return Object.fromEntries(new FormData(form)); }
function handle(id, action) { document.querySelector(id).addEventListener('submit', async (event) => { event.preventDefault(); try { message.textContent = ''; await action(event.currentTarget); event.currentTarget.reset(); if (!message.textContent) message.textContent = 'Готово.'; } catch (error) { message.textContent = error.message; } }); }
handle('#login', async (form) => showAccount(await request('/sessions', 'POST', formData(form))));
handle('#password', async (form) => { await request('/users/me/change-password', 'POST', formData(form)); showLogin(); });
handle('#create-user', async (form) => { const user = await request('/admin/users', 'POST', formData(form)); await refreshUsers(); message.textContent = `Пользователь создан, ID: ${user.id}`; });
handle('#reset-password', async (form) => { const data = formData(form); await request(`/admin/users/${encodeURIComponent(data.user_id)}/reset-password`, 'POST', { password: data.password }); });
document.querySelector('#logout').addEventListener('click', async () => { try { await request('/sessions/current', 'DELETE'); showLogin(); } catch (error) { message.textContent = error.message; } });
request('/sessions/current').then(showAccount).catch(() => {});
