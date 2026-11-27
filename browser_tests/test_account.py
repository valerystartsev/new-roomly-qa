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
    expect(page.get_by_role('heading', name='Офисы и ресурсы')).to_be_visible()
    expect(page.get_by_role('heading', name='Управление офисами')).to_be_hidden()
    password_form = page.locator('#password')
    password_form.get_by_label('Текущий пароль').fill('initial-password-123')
    password_form.get_by_label('Новый пароль').fill('changed-password-123')
    password_form.get_by_role('button', name='Изменить пароль').click()
    expect(page.get_by_role('heading', name='Вход')).to_be_visible()
    sign_in(page, email, 'changed-password-123')


def test_administrator_can_edit_and_restore_office(page):
    page.goto(os.environ['APP_URL'] + '/account/')
    sign_in(page, os.environ['INITIAL_ADMIN_EMAIL'], os.environ['INITIAL_ADMIN_PASSWORD'])
    office_select = page.get_by_label('Существующий офис')
    expect(office_select.locator('option')).not_to_have_count(1)
    office_id = office_select.locator('option').nth(1).get_attribute('value')
    office_select.select_option(office_id)
    name = page.get_by_label('Название офиса')
    original = name.input_value()
    temporary = f'Office {uuid.uuid4().hex}'
    try:
        name.fill(temporary)
        page.get_by_role('button', name='Сохранить офис').click()
        expect(page.locator('#message')).to_have_text('Готово.')
        expect(page.locator('#office-picker')).to_contain_text(temporary)
    finally:
        office_select.select_option(office_id)
        name.fill(original)
        page.get_by_role('button', name='Сохранить офис').click()
        expect(page.locator('#office-picker')).to_contain_text(original)


def test_administrator_can_edit_room_and_equipment(page):
    page.goto(os.environ['APP_URL'] + '/account/')
    sign_in(page, os.environ['INITIAL_ADMIN_EMAIL'], os.environ['INITIAL_ADMIN_PASSWORD'])
    room_select = page.get_by_label('Существующая комната')
    expect(room_select.locator('option')).not_to_have_count(1)
    room_id = room_select.locator('option').nth(1).get_attribute('value')
    room_select.select_option(room_id)
    room_name = page.get_by_label('Название комнаты')
    original_room = room_name.input_value()
    temporary_room = f'Room {uuid.uuid4().hex}'
    try:
        room_name.fill(temporary_room)
        page.get_by_role('button', name='Сохранить комнату').click()
        expect(page.locator('#room-list')).to_contain_text(temporary_room)
    finally:
        room_select.select_option(room_id)
        room_name.fill(original_room)
        page.get_by_role('button', name='Сохранить комнату').click()
        expect(page.locator('#room-list')).to_contain_text(original_room)

    equipment_select = page.get_by_label('Существующее оборудование')
    equipment_id = equipment_select.locator('option').nth(1).get_attribute('value')
    equipment_select.select_option(equipment_id)
    label = page.get_by_label('Обозначение оборудования')
    original_label = label.input_value()
    temporary_label = f'Unit {uuid.uuid4().hex}'
    try:
        label.fill(temporary_label)
        page.get_by_role('button', name='Сохранить оборудование').click()
        expect(page.locator('#equipment-list')).to_contain_text(temporary_label)
    finally:
        equipment_select.select_option(equipment_id)
        label.fill(original_label)
        page.get_by_role('button', name='Сохранить оборудование').click()
        expect(page.locator('#equipment-list')).to_contain_text(original_label)
