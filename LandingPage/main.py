from flask import Flask, render_template, url_for

def create_app():
    app = Flask(__name__, template_folder='Templates')

    @app.route('/')
    def index():
        return render_template('index.html')

    return app