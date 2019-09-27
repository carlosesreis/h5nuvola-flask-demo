from flask import Flask, render_template

app = Flask(__name__)

@app.route('/home')
def home():
    return render_template("template-A.html")

app.run(port=5000)