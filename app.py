from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'todos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return api_response(message="unauthorized", code=401)
    return redirect(url_for('login'))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    todos = db.relationship('Todo', backref='owner', lazy=True, cascade="all, delete-orphan")
    categories = db.relationship('Category', backref='owner', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    todos = db.relationship('Todo', backref='category', lazy=True, cascade="all, delete-orphan")


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


import sqlite3

def init_db():
    """安全初始化数据库，避免多Worker并发建表冲突"""
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            # 如果表已存在则忽略，仅记录警告
            if "already exists" in str(e):
                print("⚠️ 数据库表已存在，跳过创建")
            else:
                raise

# 仅在非Gunicorn环境下自动建表（开发模式）
# Gunicorn环境下通过preload或外部脚本初始化
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
else:
    # Gunicorn环境：使用before_first_request等效机制
    # Flask 2.3+ 移除了 before_first_request，改用一次性初始化
    import threading
    _db_initialized = False
    _init_lock = threading.Lock()

    @app.before_request
    def ensure_db_initialized():
        global _db_initialized
        if not _db_initialized:
            with _init_lock:
                if not _db_initialized:
                    init_db()
                    _db_initialized = True



# ==================== 认证路由 ====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('用户名和密码不能为空', 'error')
        elif User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('login'))
    return render_template_string(REGISTER_HTML)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('用户名或密码错误', 'error')
    return render_template_string(LOGIN_HTML)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ==================== 分类路由 ====================
@app.route('/category/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name', '').strip()
    if name:
        cat = Category(name=name, owner=current_user)
        db.session.add(cat)
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/category/delete/<int:cat_id>')
@login_required
def delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.user_id != current_user.id:
        flash('无权操作', 'error')
    else:
        db.session.delete(cat)
        db.session.commit()
    return redirect(url_for('index'))


# ==================== 核心业务路由 ====================
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        task = request.form.get('task', '').strip()
        cat_id = request.form.get('category_id', type=int)
        if task:
            new_todo = Todo(text=task, done=False, owner=current_user, category_id=cat_id)
            db.session.add(new_todo)
            db.session.commit()
        return redirect(url_for('index'))

    filter_cat = request.args.get('cat', type=int)
    query = Todo.query.filter_by(user_id=current_user.id)
    if filter_cat:
        query = query.filter_by(category_id=filter_cat)
    todos = query.order_by(Todo.id.desc()).all()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.id).all()
    return render_template_string(INDEX_HTML, todos=todos, categories=categories, filter_cat=filter_cat)


@app.route('/delete/<int:todo_id>')
@login_required
def delete(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        flash('无权操作他人的待办', 'error')
        return redirect(url_for('index'))
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/toggle/<int:todo_id>', methods=['POST'])
@login_required
def toggle(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        return {'error': '无权操作'}, 403
    data = request.get_json(silent=True)
    if data is None:
        return {'error': 'Invalid JSON'}, 400
    todo.done = bool(data.get('done', False))
    db.session.commit()
    return {'status': 'ok'}


# ==================== HTML 模板 ====================
BASE_STYLE = '''
<style>
    body { font-family: Arial; max-width: 600px; margin: 50px auto; padding: 0 20px; }
    ul { list-style: none; padding: 0; }
    li { margin: 10px 0; padding: 8px; background: #f5f5f5; border-radius: 5px; display: flex; align-items: center; }
    li span { flex: 1; }
    .done { text-decoration: line-through; color: #999; }
    .delete { color: red; text-decoration: none; margin-left: 15px; white-space: nowrap; }
    input[type="checkbox"] { margin-right: 10px; cursor: pointer; }
    form { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
    form input[type="text"], form input[type="password"] { flex: 1; padding: 8px; min-width: 120px; }
    form select { padding: 8px; }
    form button { padding: 8px 16px; cursor: pointer; }
    .flash-error { color: red; margin-bottom: 10px; }
    .flash-success { color: green; margin-bottom: 10px; }
    .nav { margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
    .nav a { text-decoration: none; color: #333; margin-left: 15px; }
    .cat-filter { margin-bottom: 15px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    .cat-filter a { padding: 4px 12px; border-radius: 15px; text-decoration: none; font-size: 14px; background: #eee; color: #333; }
    .cat-filter a.active { background: #333; color: #fff; }
    .cat-tag { font-size: 12px; color: #666; background: #e0e0e0; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
    .add-cat-form { display: flex; gap: 8px; margin-bottom: 15px; }
    .add-cat-form input { flex: 1; padding: 6px; }
    .add-cat-form button { padding: 6px 12px; cursor: pointer; font-size: 14px; }
</style>
'''

FLASH_MESSAGES = '''
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    {% for category, message in messages %}
      <div class="flash-{{ category }}">{{ message }}</div>
    {% endfor %}
  {% endif %}
{% endwith %}
'''

LOGIN_HTML = f'''<!DOCTYPE html><html><head><title>登录</title>{BASE_STYLE}</head><body>
<h1>登录</h1>
{FLASH_MESSAGES}
<form method="POST">
    <input type="text" name="username" placeholder="用户名" required>
    <input type="password" name="password" placeholder="密码" required>
    <button type="submit">登录</button>
</form>
<p>没有账号？<a href="{{{{ url_for('register') }}}}">去注册</a></p>
</body></html>'''

REGISTER_HTML = f'''<!DOCTYPE html><html><head><title>注册</title>{BASE_STYLE}</head><body>
<h1>注册</h1>
{FLASH_MESSAGES}
<form method="POST">
    <input type="text" name="username" placeholder="用户名" required>
    <input type="password" name="password" placeholder="密码" required>
    <button type="submit">注册</button>
</form>
<p>已有账号？<a href="{{{{ url_for('login') }}}}">去登录</a></p>
</body></html>'''

INDEX_HTML = f'''<!DOCTYPE html><html><head><title>我的待办</title>{BASE_STYLE}</head><body>
<div class="nav">
    <strong>👤 {{{{ current_user.username }}}}</strong>
    <div><a href="{{{{ url_for('logout') }}}}">退出登录</a></div>
</div>
<h1>待办清单</h1>
{FLASH_MESSAGES}

<div class="add-cat-form">
    <form method="POST" action="{{{{ url_for('add_category') }}}}" style="margin-bottom:0;flex:1;">
        <input type="text" name="name" placeholder="新建分类..." required>
        <button type="submit">+ 分类</button>
    </form>
</div>

<div class="cat-filter">
    <a href="{{{{ url_for('index') }}}}" class="{{{{ 'active' if not filter_cat else '' }}}}">全部</a>
    {{% for c in categories %}}
        <a href="{{{{ url_for('index', cat=c.id) }}}}" class="{{{{ 'active' if filter_cat == c.id else '' }}}}">
            {{{{ c.name }}}}
        </a>
        <a href="/category/delete/{{{{ c.id }}}}" onclick="return confirm('删除分类会同时删除该分类下所有待办，确定吗？')" style="background:none;color:red;padding:0 4px;font-size:12px;">✕</a>
    {{% endfor %}}
</div>

<form method="POST">
    <input type="text" name="task" placeholder="写个任务..." required>
    <select name="category_id">
        <option value="">无分类</option>
        {{% for c in categories %}}
            <option value="{{{{ c.id }}}}">{{{{ c.name }}}}</option>
        {{% endfor %}}
    </select>
    <button type="submit">添加</button>
</form>

<ul>
    {{% for t in todos %}}
        <li>
            <input type="checkbox" onchange="toggleDone({{{{ t.id }}}}, this.checked)" {{{{ 'checked' if t.done else '' }}}}>
            <span class="{{{{ 'done' if t.done else '' }}}}">
                {{{{ t.text }}}}
                {{% if t.category %}}<span class="cat-tag">{{{{ t.category.name }}}}</span>{{% endif %}}
            </span>
            <a href="/delete/{{{{ t.id }}}}" class="delete" onclick="return confirm('确定删除吗？')">删除</a>
        </li>
    {{% endfor %}}
</ul>
{{% if not todos %}}<p style="color:#999; text-align:center;">暂无待办事项 🎉</p>{{% endif %}}

<script>
function toggleDone(id, isDone) {{
    fetch('/toggle/' + id, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ done: isDone }})
    }}).then(function(r) {{
        if (r.ok) window.location.replace(window.location.href);
        else alert('操作失败');
    }});
}}
</script>
</body></html>'''

# ==================== P4: RESTful API ====================
from flask import jsonify

# 统一 JSON 响应封装
def api_response(data=None, message="ok", code=200):
    return jsonify({"code": code, "message": message, "data": data}), code

# ---------- Todo API ----------
@app.route('/api/v1/todos', methods=['GET'])
@login_required
def api_get_todos():
    cat_id = request.args.get('cat', type=int)
    query = Todo.query.filter_by(user_id=current_user.id)
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    todos = query.order_by(Todo.id.desc()).all()
    result = [{
        "id": t.id,
        "text": t.text,
        "done": t.done,
        "category_id": t.category_id,
        "category_name": t.category.name if t.category else None
    } for t in todos]
    return api_response(data=result)

@app.route('/api/v1/todos', methods=['POST'])
@login_required
def api_create_todo():
    data = request.get_json(silent=True)
    if not data or not data.get('text', '').strip():
        return api_response(message="text is required", code=400)
    todo = Todo(
        text=data['text'].strip(),
        done=bool(data.get('done', False)),
        category_id=data.get('category_id'),
        owner=current_user
    )
    db.session.add(todo)
    db.session.commit()
    return api_response(data={"id": todo.id}, message="created", code=201)

@app.route('/api/v1/todos/<int:todo_id>', methods=['PATCH'])
@login_required
def api_update_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        return api_response(message="forbidden", code=403)
    data = request.get_json(silent=True)
    if not data:
        return api_response(message="invalid json", code=400)
    if 'done' in data:
        todo.done = bool(data['done'])
    if 'text' in data:
        todo.text = data['text'].strip()
    if 'category_id' in data:
        todo.category_id = data['category_id']
    db.session.commit()
    return api_response(message="updated")

@app.route('/api/v1/todos/<int:todo_id>', methods=['DELETE'])
@login_required
def api_delete_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != current_user.id:
        return api_response(message="forbidden", code=403)
    db.session.delete(todo)
    db.session.commit()
    return '', 204

# ---------- Category API ----------
@app.route('/api/v1/categories', methods=['GET'])
@login_required
def api_get_categories():
    cats = Category.query.filter_by(user_id=current_user.id).order_by(Category.id).all()
    result = [{"id": c.id, "name": c.name} for c in cats]
    return api_response(data=result)

@app.route('/api/v1/categories', methods=['POST'])
@login_required
def api_create_category():
    data = request.get_json(silent=True)
    if not data or not data.get('name', '').strip():
        return api_response(message="name is required", code=400)
    cat = Category(name=data['name'].strip(), owner=current_user)
    db.session.add(cat)
    db.session.commit()
    return api_response(data={"id": cat.id}, message="created", code=201)

if __name__ == '__main__':
    app.run(debug=True)

