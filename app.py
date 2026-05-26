from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'hello！实习我来啦！'

if __name__ == '__main__':
    app.run(debug=True)