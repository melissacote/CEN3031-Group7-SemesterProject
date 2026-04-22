from services.administration_log import log_medication_taken, undo_medication_taken
from services.medication import add_medication, update_medication
from services.user import create_new_user, get_user_id
from services.reports import get_medication_history


def test_log_medication_taken_success(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Edward',
        'last_name': 'Elric',
        'date_of_birth': '1990-01-01'
    }
    create_new_user(user_data, conn = test_db)
    test_username = user_data['username']
    test_id = get_user_id(test_username, conn = test_db)

    add_medication(test_id, 'Vitamin C', '500 mg', 'oral', 'daily', '08:00', conn = test_db)
    log_medication_taken(test_id, 1, conn = test_db)

    cursor = test_db.cursor()
    cursor.execute("SELECT status FROM administration_log WHERE user_id = ? AND medication_id = ?", (test_id, 1))
    row = cursor.fetchone()
    assert row[0] == 1

def test_undo_medication_taken_success(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Alphonse',
        'last_name': 'Elric',
        'date_of_birth': '1994-01-01'
    }
    create_new_user(user_data, conn=test_db)
    test_username = user_data['username']
    test_id = get_user_id(test_username, conn=test_db)

    add_medication(test_id, 'Vitamin C', '500 mg', 'oral', 'daily', '08:00', conn=test_db)
    log_medication_taken(test_id, 1, conn=test_db)
    undo_medication_taken(test_id, 1, conn=test_db)

    cursor = test_db.cursor()
    cursor.execute("SELECT status FROM administration_log WHERE user_id = ? AND medication_id = ?", (test_id, 1))
    row = cursor.fetchone()
    assert row is None

def test_undo_medication_taken_no_log_entry(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Roy',
        'last_name': 'Mustang',
        'date_of_birth': '1987-10-10'
    }
    create_new_user(user_data, conn=test_db)
    test_username = user_data['username']
    test_id = get_user_id(test_username, conn=test_db)

    add_medication(test_id, 'Vitamin C', '500 mg', 'oral', 'daily', '08:00', conn=test_db)
    result = undo_medication_taken(test_id, 1, conn=test_db)
    assert result == False

def test_log_entry_not_overwritten_when_medication_changes(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Trisha',
        'last_name': 'Elric',
        'date_of_birth': '1990-01-01'
    }
    create_new_user(user_data, conn = test_db)
    test_username = user_data['username']
    test_id = get_user_id(test_username, conn = test_db)

    add_medication(test_id, 'Vitamin C', '500 mg', 'oral', 'daily', '08:00', conn = test_db)
    log_medication_taken(test_id, 1, conn = test_db)

    update_medication(1, 'Vitamin C', '1000 mg', 'oral', 'daily', '08:00', special_instructions='', conn = test_db)

    logs, start_date, end_date = get_medication_history(test_id, conn = test_db)
    assert logs[0]['dosage'] == '500 mg'

