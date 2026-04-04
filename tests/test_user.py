from services.user import create_new_user, verify_user


def test_create_new_user_success(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Spike',
        'last_name': 'Spiegel',
        'date_of_birth': '1975-01-01'
    }
    result = create_new_user(user_data, conn = test_db)
    assert result == True

def test_create_new_user_duplicate(test_db):
    user_data_first = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Faye',
        'last_name': 'Valentine',
        'date_of_birth': '1976-02-02'
    }

    user_data_second = {
        'username': 'testuser',
        'password': 'TestPass321',
        'first_name': 'Jet',
        'last_name': 'Black',
        'date_of_birth': '1969-03-03'
    }
    create_new_user(user_data_first, conn = test_db)
    result = create_new_user(user_data_second, conn = test_db)
    assert result == False

def test_verify_user_success(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Kagome',
        'last_name': 'Higurashi',
        'date_of_birth': '1990-07-16'
    }
    create_new_user(user_data, conn=test_db)
    result = verify_user(user_data['username'], user_data['password'], conn = test_db)
    assert result == True

def test_verify_user_wrong_password(test_db):
    user_data = {
        'username': 'testuser',
        'password': 'TestPass123',
        'first_name': 'Kagome',
        'last_name': 'Higurashi',
        'date_of_birth': '1990-07-16'
    }
    create_new_user(user_data, conn=test_db)
    result = verify_user(user_data['username'], "WrongPass345", conn=test_db)
    assert result == False
