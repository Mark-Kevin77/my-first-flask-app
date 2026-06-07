import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db, User, Todo


@pytest.fixture(scope='module')
def client():
    """模块级初始化，只建库一次"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as test_client:
        with app.app_context():
            db.create_all()
        yield test_client
        with app.app_context():
            db.drop_all()


@pytest.fixture(scope='function', autouse=True)
def clean_data(client):
    """每个测试前重置数据，避免状态污染"""
    with app.app_context():
        # 清空所有表数据但保留表结构
        db.session.query(Todo).delete()
        db.session.query(User).delete()
        db.session.commit()

        # 插入标准测试数据
        user = User(username='testuser')
        user.set_password('testpass')
        db.session.add(user)
        db.session.flush()  # 获取 user.id

        for i in range(5):
            db.session.add(Todo(text=f'test task {i}', user_id=user.id, is_deleted=False))
        db.session.add(Todo(text='deleted task', user_id=user.id, is_deleted=True))
        db.session.commit()

    yield

    # 测试后清理限流器状态
    from app import todo_limiter
    with todo_limiter._lock:
        todo_limiter._requests.clear()


@pytest.fixture(scope='function')
def auth_header(client):
    resp = client.post('/login', data={'username': 'testuser', 'password': 'testpass'})
    return {'Cookie': resp.headers.get('Set-Cookie')}


class TestPagination:
    def test_default_page(self, client, auth_header):
        resp = client.get('/api/v1/todos', headers=auth_header)
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data['data']['items']) == 5
        assert data['data']['pagination']['total'] == 5

    def test_per_page_limit(self, client, auth_header):
        resp = client.get('/api/v1/todos?per_page=2', headers=auth_header)
        data = resp.get_json()
        assert len(data['data']['items']) == 2
        assert data['data']['pagination']['pages'] == 3

    def test_out_of_range_page(self, client, auth_header):
        resp = client.get('/api/v1/todos?page=999', headers=auth_header)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['data']['items'] == []
        assert data['data']['pagination']['total'] == 5


class TestSoftDeleteRestore:
    def test_deleted_not_in_list(self, client, auth_header):
        resp = client.get('/api/v1/todos', headers=auth_header)
        texts = [item['text'] for item in resp.get_json()['data']['items']]
        assert 'deleted task' not in texts

    def test_restore_success(self, client, auth_header):
        with app.app_context():
            from sqlalchemy import select
            stmt = select(Todo).where(Todo.text == 'deleted task')
            todo = db.session.execute(stmt).scalar_one()
            todo_id = todo.id

        resp = client.post(f'/api/v1/todos/{todo_id}/restore', headers=auth_header)
        assert resp.get_json()['code'] == 200

        list_resp = client.get('/api/v1/todos', headers=auth_header)
        texts = [item['text'] for item in list_resp.get_json()['data']['items']]
        assert 'deleted task' in texts


class TestRateLimit:
    def test_rate_limit_triggers(self, client, auth_header):
        from app import todo_limiter

        original_max = todo_limiter.max_requests
        todo_limiter.max_requests = 3

        try:
            statuses = []
            for _ in range(5):
                resp = client.get('/api/v1/todos', headers=auth_header)
                statuses.append(resp.status_code)
            assert statuses[:3] == [200, 200, 200]
            assert 429 in statuses[3:]
        finally:
            todo_limiter.max_requests = original_max
