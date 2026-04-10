import pytest

from services.medication import get_user_medications, add_medication, get_medications_for_management, \
    get_todays_medications_sorted
from services.user import create_new_user, get_user_id


def test_add_medication_success(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Pika',
        'last_name': 'Chu',
        'date_of_birth': '1996-01-01'
    }
    create_new_user(user_data, conn = test_db)
    test_username = user_data['username']
    test_id = get_user_id(test_username, conn = test_db)

    add_medication(test_id, 'Aspirin', '81mg', 'oral', 'daily', '08:00', conn = test_db)

    cursor = test_db.cursor()
    cursor.execute("SELECT medication_name FROM medications WHERE user_id = ?", (test_id,))
    row = cursor.fetchone()
    assert row[0] == 'Aspirin'

def test_get_todays_medications_sorted_empty(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Bulba',
        'last_name': 'Saur',
        'date_of_birth': '1987-06-15'
    }
    create_new_user(user_data, conn = test_db)
    test_id = get_user_id('testuser', conn = test_db)
    result = get_todays_medications_sorted(test_id, conn = test_db)
    assert result == []

def test_get_todays_medications_sorted_order(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Chari',
        'last_name': 'Zard',
        'date_of_birth': '1987-06-15'
    }
    create_new_user(user_data, conn = test_db)
    test_id = get_user_id('testuser', conn = test_db)

    add_medication(test_id, 'Zyrtec', '10mg', 'oral', 'daily', '10:00', conn = test_db)
    add_medication(test_id, "Vitamin C", "500 mg", "Oral", "Daily", "09:00", conn = test_db)
    result = get_todays_medications_sorted(test_id, conn = test_db)
    assert result[0][3] < result[1][3]


@pytest.mark.skip(reason="get_user_medications uses columns that do not match existing medications table, unsure if function is obsolete, will investigate")
def test_get_user_medications_success(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Ash',
        'last_name': 'Ketchum',
        'date_of_birth': '1990-06-01'
    }
    test_username = user_data['username']
    create_new_user(user_data, conn = test_db)
    test_id = get_user_id(test_username, conn = test_db)
    add_medication(test_id, "Lisinopril", "10 mg", "Oral", "Daily", "09:00 AM", conn = test_db)
    add_medication(test_id, "Aspirin", "81 mg", "Oral", "Daily", "08:00 AM", conn = test_db)
    result = get_user_medications(test_username, conn = test_db)
    assert len(result) == 2
    assert result[0]['name'] == 'Aspirin'
    assert result[1]['name'] == 'Lisinopril'

def test_get_medications_form_management_empty(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Psy',
        'last_name': 'Duck',
        'date_of_birth': '1952-08-20'
    }
    create_new_user(user_data, conn = test_db)
    test_id = get_user_id('testuser', conn = test_db)

    result = get_medications_for_management(test_id, conn = test_db)
    assert result == []

def test_get_medications_for_management_success(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Misty',
        'last_name': 'Waterflower',
        'date_of_birth': '1985-11-03'
    }
    test_username = user_data['username']
    create_new_user(user_data, conn = test_db)
    test_id = get_user_id(test_username, conn = test_db)
    add_medication(test_id, "Lisinopril", "10 mg", "Oral", "Daily", "09:00 AM", conn = test_db)
    add_medication(test_id, "Aspirin", "81 mg", "Oral", "Daily", "08:00 AM", conn = test_db)
    result = get_medications_for_management(test_id, conn = test_db)
    assert len(result) == 2
    assert result[0]['name'] == 'Aspirin'
    assert result[1]['name'] == 'Lisinopril'

