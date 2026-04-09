import pytest

from services.medication import get_user_medications, add_medication, get_medications_for_management
from services.user import create_new_user, get_user_id

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
    print(f"\ntest_id: {test_id}")
    add_medication(test_id, "Lisinopril", "10 mg", "Oral", "Daily", "09:00 AM", conn = test_db)
    add_medication(test_id, "Aspirin", "81 mg", "Oral", "Daily", "08:00 AM", conn = test_db)
    result = get_user_medications(test_username, conn = test_db)
    assert len(result) == 2
    assert result[0]['name'] == 'Aspirin'
    assert result[1]['name'] == 'Lisinopril'

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
    print(f"\ntest_id: {test_id}")
    add_medication(test_id, "Lisinopril", "10 mg", "Oral", "Daily", "09:00 AM", conn = test_db)
    add_medication(test_id, "Aspirin", "81 mg", "Oral", "Daily", "08:00 AM", conn = test_db)
    result = get_medications_for_management(test_id, conn = test_db)
    assert len(result) == 2
    assert result[0]['name'] == 'Aspirin'
    assert result[1]['name'] == 'Lisinopril'

