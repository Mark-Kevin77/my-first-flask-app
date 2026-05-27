from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = 'todos.json'

def load_todos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 兼容旧格式：如果是字符串列表，转换成带状态的字典列表
            if data and isinstance(data[0], str):
                return [{'text': t, 'done': False} for t in data]
            return data
    return []

def save_todos(todos):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

todos = load_todos()

@app.route('/', methods=['GET', 'POST'])
def index():
    global todos
    if request.method == 'POST':
        task = request.form.get('task')
        if task:
            todos.append({'text': task, 'done': False})
            save_todos(todos)
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>我的待办</title>
        <style>
            body { font-family: Arial; max-width: 500px; margin: 50px auto; }
            ul { list-style: none; padding: 0; }
            li { margin: 10px 0; padding: 8px; background: #f5f5f5; border-radius: 5px; }
            .done { text-decoration: line-through; color: #999; }
            .delete { color: red; float: right; text-decoration: none; margin-left: 15px; }
            .task-text { margin-left: 8px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>待办清单</h1>
        <form method="POST">
            <input type="text" name="task" placeholder="写个任务..." required style="width: 70%; padding: 8px;">
            <button type="submit" style="padding: 8px 16px;">添加</button>
        </form>
        <ul>
            {% for t in todos %}
                <li>
                    <input type="checkbox" 
                           onclick="toggleDone({{ loop.index0 }}, this.checked)"
                           {{ 'checked' if t.done else '' }}>
                    <span class="task-text {{ 'done' if t.done else '' }}">{{ t.text }}</span>
                    <a href="/delete/{{ loop.index0 }}" class="delete">删除</a>
                </li>
            {% endfor %}
        </ul>
        <script>
            function toggleDone(index, isDone) {
                fetch('/toggle/' + index, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({done: isDone})
                }).then(() => location.reload());
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, todos=todos)

@app.route('/delete/<int:task_id>')
def delete(task_id):
    global todos
    if 0 <= task_id < len(todos):
        todos.pop(task_id)
        save_todos(todos)
    return index()

@app.route('/toggle/<int:task_id>', methods=['POST'])
def toggle(task_id):
    global todos
    if 0 <= task_id < len(todos):
        data = request.get_json()
        todos[task_id]['done'] = data.get('done', False)
        save_todos(todos)
    return 'OK'

if __name__ == '__main__':
    app.run(debug=True)