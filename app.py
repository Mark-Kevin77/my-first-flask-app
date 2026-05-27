from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

# 数据文件路径
DATA_FILE = 'todos.json'

# 加载任务
def load_todos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# 保存任务
def save_todos(todos):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

# 初始化
todos = load_todos()

@app.route('/', methods=['GET', 'POST'])
def index():
    global todos
    if request.method == 'POST':
        new_task = request.form.get('task')
        if new_task:
            todos.append(new_task)
            save_todos(todos)  # 保存到文件
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>我的待办</title>
        <style>
            body { font-family: Arial; max-width: 500px; margin: 50px auto; }
            ul { list-style: none; padding: 0; }
            li { margin: 10px 0; }
            .delete { color: red; margin-left: 15px; text-decoration: none; font-size: 14px; }
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
                    {{ t }}
                    <a href="/delete/{{ loop.index0 }}" class="delete">删除</a>
                </li>
            {% endfor %}
        </ul>
    </body>
    </html>
    '''
    return render_template_string(html, todos=todos)

@app.route('/delete/<int:task_id>')
def delete(task_id):
    global todos
    if 0 <= task_id < len(todos):
        todos.pop(task_id)
        save_todos(todos)  # 删除后保存
    return index()

if __name__ == '__main__':
    app.run(debug=True)