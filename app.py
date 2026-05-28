from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # 生产环境建议换成固定字符串或环境变量

# 数据库配置
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'todos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # 未登录时自动跳转的页面

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    todos = db.relationship('Todo', backref='owner', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 待办模型（新增 user_id 外键）
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 初始化数据库
with app.app_context():
    db.create_all()

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

# ==================== 核心业务路由（已加权限控制）====================
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        task = request.form.get('task', '').strip()
        if task:
            new_todo = Todo(text=task, done=False, owner=current_user)
            db.session.add(new_todo)
            db.session.commit()
        return redirect(url_for('index'))

    # 只查询当前用户的待办
    todos = Todo.query.filter_by(user_id=current_user.id).order_by(Todo.id.desc()).all()
    return render_template_string(INDEX_HTML, todos=todos)

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
    body { font-family: Arial; max-width: 500px; margin: 50px auto; padding: 0 20px; }
    ul { list-style: none; padding: 0; }
    li { margin: 10px 0; padding: 8px; background: #f5f5f5; border-radius: 5px; display: flex; align-items: center; }
    li span { flex: 1; }
    .done { text-decoration: line-through; color: #999; }
    .delete { color: red; text-decoration: none; margin-left: 15px; white-space: nowrap; }
    input[type="checkbox"] { margin-right: 10px; cursor: pointer; }
    form { display: flex; gap: 8px; margin-bottom: 20px; }
    form input[type="text"], form input[type="password"] { flex: 1; padding: 8px; }
    form button { padding: 8px 16px; cursor: pointer; }
    .flash-error { color: red; margin-bottom: 10px; }
    .flash-success { color: green; margin-bottom: 10px; }
    .nav { margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
    .nav a { text-decoration: none; color: #333; margin-left: 15px; }
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
<form method="POST">
    <input type="text" name="task" placeholder="写个任务..." required>
    <button type="submit">添加</button>
</form>
<ul>
    {{% for t in todos %}}
        <li>
            <input type="checkbox" onchange="toggleDone({{{{ t.id }}}}, this.checked)" {{{{ 'checked' if t.done else '' }}}}>
            <span class="{{{{ 'done' if t.done else '' }}}}">{{{{ t.text }}}}</span>
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
    }}).then(function(response) {{
        if (response.ok) {{ window.location.replace(window.location.href); }}
        else {{ alert('操作失败'); }}
    }});
}}
</script>
</body></html>'''

if __name__ == '__main__':
    app.run(debug=True)

