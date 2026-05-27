from flask import Flask, request, render_template_string

app = Flask(__name__)

todos = []

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        new_task = request.form.get('task')
        if new_task:
            todos.append(new_task)
    
    # 生成带删除按钮的页面
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

# 删除任务的路由
@app.route('/delete/<int:task_id>')
def delete(task_id):
    if 0 <= task_id < len(todos):
        todos.pop(task_id)
    return index()

if __name__ == '__main__':
    app.run(debug=True)