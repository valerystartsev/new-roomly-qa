import os
import uuid

from playwright.sync_api import expect


def sign_in(page, email, password):
    form = page.locator('#login')
    form.get_by_label('Почта').fill(email)
    form.get_by_label('Пароль', exact=True).fill(password)
    form.get_by_role('button', name='Войти').click()
    expect(page.get_by_role('heading', name='Учётная запись')).to_be_visible()


def test_administrator_can_sign_in_and_out(page):
    page.goto(os.environ['APP_URL'] + '/account/')
    sign_in(page, os.environ['INITIAL_ADMIN_EMAIL'], os.environ['INITIAL_ADMIN_PASSWORD'])
    expect(page.get_by_role('heading', name='Создать пользователя')).to_be_visible()
    page.get_by_role('button', name='Выйти').click()
    expect(page.get_by_role('heading', name='Вход')).to_be_visible()


def test_admin_creates_user_and_user_changes_password(page):
    email = f'{uuid.uuid4().hex}@example.test'
    page.goto(os.environ['APP_URL'] + '/account/')
    sign_in(page, os.environ['INITIAL_ADMIN_EMAIL'], os.environ['INITIAL_ADMIN_PASSWORD'])
    form = page.locator('#create-user')
    form.get_by_label('Имя').fill('Browser User')
    form.get_by_label('Почта').fill(email)
    form.get_by_label('Пароль').fill('initial-password-123')
    form.get_by_role('button', name='Создать').click()
    expect(page.locator('#user-list')).to_contain_text(email)
    page.get_by_role('button', name='Выйти').click()
    sign_in(page, email, 'initial-password-123')
    expect(page.get_by_role('heading', name='Создать пользователя')).to_be_hidden()
    password_form = page.locator('#password')
    password_form.get_by_label('Текущий пароль').fill('initial-password-123')
    password_form.get_by_label('Новый пароль').fill('changed-password-123')
    password_form.get_by_role('button', name='Изменить пароль').click()
    expect(page.get_by_role('heading', name='Вход')).to_be_visible()
    sign_in(page, email, 'changed-password-123')
