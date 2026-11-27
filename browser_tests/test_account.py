import os

from playwright.sync_api import expect


def test_administrator_can_sign_in_and_out(page):
    page.goto(os.environ['APP_URL'] + '/account/')
    page.get_by_label('Почта').first.fill(os.environ['INITIAL_ADMIN_EMAIL'])
    page.get_by_label('Пароль', exact=True).first.fill(os.environ['INITIAL_ADMIN_PASSWORD'])
    page.get_by_role('button', name='Войти').click()
    expect(page.get_by_role('heading', name='Учётная запись')).to_be_visible()
    expect(page.get_by_role('heading', name='Создать пользователя')).to_be_visible()
    page.get_by_role('button', name='Выйти').click()
    expect(page.get_by_role('heading', name='Вход')).to_be_visible()
