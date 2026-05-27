from flask import Flask, request, render_template_string, redirect, url_for, jsonify
import json
import os

app = Flask(__name__)

DATA_FILE = 'todos.json'


def load_todos():
    """每次从文件读取，避免全局状态问题"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容旧格式（纯字符串列表）
                if data and isinstance(data[0], str):
                    return [{'text': t, 'done': False} for t in data]
                return data
        except (json.JSONDecodeError, IndexError):
            return []
    return []


def save_todos(todos):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        task = request.form.get('task', '').strip()
        if task:
            todos = load_todos()
            todos.append({'text': task, 'done': False})
            save_todos(todos)
        return redirect(url_for('index'))

    # GET 请求正常渲染
    todos = load_todos()

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
                           onchange="toggleDone({{ loop.index0 }}, this.checked)"
                           {{ 'checked' if t.done else '' }}>
                    <span class="{{ 'done' if t.done else '' }}">{{ t.text }}</span>
                    <a href="/delete/{{ loop.index0 }}" class="delete"
                       onclick="return confirm('确定删除吗？')">删除</a>
                </li>
            {% endfor %}
        </ul>
        {% if not todos %}
            <p style="color:#999; text-align:center;">暂无待办事项 🎉</p>
        {% endif %}
        <script>
            function toggleDone(index, isDone) {
                fetch('/toggle/' + index, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ done: isDone })
                }).then(function(response) {
                    if (response.ok) {
                        window.location.replace(window.location.href);
                    } else {
                        alert('操作失败，请重试');
                        location.reload();
                    }
                }).catch(function() {
                    alert('网络错误');
                    location.reload();
                });
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, todos=todos)


@app.route('/delete/<int:task_id>')
def delete(task_id):
    todos = load_todos()
    if 0 <= task_id < len(todos):
        todos.pop(task_id)
        save_todos(todos)
    return redirect(url_for('index'))


@app.route('/toggle/<int:task_id>', methods=['POST'])
def toggle(task_id):
    todos = load_todos()
    if 0 <= task_id < len(todos):
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({'error': 'Invalid JSON'}), 400
        todos[task_id]['done'] = bool(data.get('done', False))
        save_todos(todos)
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Task not found'}), 404


if __name__ == '__main__':
    app.run(debug=True)
