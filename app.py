from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = 'todos.json'

def load_todos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
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
            todos.append(task)
            save_todos(todos)
    
    html = '''
    <h1>待办清单</h1>
    <form method="POST">
        <input type="text" name="task" placeholder="写个任务...">
        <button type="submit">添加</button>
    </form>
    <ul>
        {% for t in todos %}
            <li>
                {{ t }}
                <a href="/delete/{{ loop.index0 }}" style="color:red; margin-left:15px;">删除</a>
            </li>
        {% endfor %}
    </ul>
    '''
    return render_template_string(html, todos=todos)

@app.route('/delete/<int:task_id>')
def delete(task_id):
    global todos
    if 0 <= task_id < len(todos):
        todos.pop(task_id)
        save_todos(todos)
    return index()

if __name__ == '__main__':
    app.run(debug=True)