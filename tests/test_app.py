def test_index_loads():
    from app import app
    client = app.test_client()
    r = client.get('/')
    assert r.status_code == 200
    assert b'LANDLORDPRO' in r.data

def test_login_landlord_dashboard():
    from app import app
    client = app.test_client()
    r = client.post('/auth/login', data={'email':'landlord@landlordpro.com','password':'password123'}, follow_redirects=True)
    assert r.status_code == 200
    assert b'Landlord Dashboard' in r.data

def test_jwt_api_login_and_me():
    from app import app
    client = app.test_client()
    r = client.post('/api/v1/login', json={'email':'tenant@landlordpro.com','password':'password123'})
    assert r.status_code == 200
    token = r.get_json()['token']
    r = client.get('/api/v1/me', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200
    assert r.get_json()['role'] == 'tenant'
