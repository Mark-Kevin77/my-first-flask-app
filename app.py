from flask import Flask, request, render_template_string, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# 数据库配置：使用项目根目录下的 todos.db
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'todos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 定义 Todo 数据模型
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {'id': self.id, 'text': self.text, 'done': self.done}

# 初始化数据库表（仅在首次运行时创建）
with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def index():
    # PRG模式：添加后重定向，防止刷新重复提交
    if request.method == 'POST':
        task = request.form.get('task', '').strip()
        if task:
            new_todo = Todo(text=task, done=False)
            db.session.add(new_todo)
            db.session.commit()
        return redirect(url_for('index'))

    # GET 请求：从数据库查询所有待办
    todos = Todo.query.order_by(Todo.id.desc()).all()

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>我的待办</title>
        <style>
            body { font-family: Arial; max-width: 500px; margin: 50px auto; }
            ul { list-style: none; padding: 0; }
            li { margin: 10px 0; padding: 8px; background: #f5f5f5; border-radius: 5px; display: flex; align-items: center; }
            li span { flex: 1; }
            .done { text-decoration: line-through; color: #999; }
            .delete { color: red; text-decoration: none; margin-left: 15px; white-space: nowrap; }
            input[type="checkbox"] { margin-right: 10px; cursor: pointer; }
            form { display: flex; gap: 8px; margin-bottom: 20px; }
            form input[type="text"] { flex: 1; padding: 8px; }
            form button { padding: 8px 16px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>待办清单</h1>
        <form method="POST">
            <input type="text" name="task" placeholder="写个任务..." required>
            <button type="submit">添加</button>
        </form>
        <ul>
            {% for t in todos %}
                <li>
                    <input type="checkbox"
                           onchange="toggleDone({{ t.id }}, this.checked)"
                           {{ 'checked' if t.done else '' }}>
                    <span class="{{ 'done' if t.done else '' }}">{{ t.text }}</span>
                    <a href="/delete/{{ t.id }}" class="delete"
                       onclick="return confirm('确定删除吗？')">删除</a>
                </li>
            {% endfor %}
        </ul>
        {% if not todos %}
            <p style="color:#999; text-align:center;">暂无待办事项 🎉</p>
        {% endif %}
        <script>
            function toggleDone(id, isDone) {
                fetch('/toggle/' + id, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ done: isDone })
                }).then(function(response) {
                    if (response.ok) {
                        // 保持 location.replace 避免刷新重放POST
                        window.location.replace(window.location.href);
                    } else {
                        alert('操作失败，请重试');
                    }
                });
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, todos=todos)

@app.route('/delete/<int:todo_id>')
def delete(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/toggle/<int:todo_id>', methods=['POST'])
def toggle(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'error': 'Invalid JSON'}), 400
    todo.done = bool(data.get('done', False))
    db.session.commit()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True)
