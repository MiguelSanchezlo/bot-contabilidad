from flask import Flask, render_template, jsonify, url_for, redirect
from routes import register_blueprints
from dotenv import load_dotenv
from extensions import bcrypt
from config import Config

load_dotenv()

app = Flask(__name__)
bcrypt.init_app(app)  

config = Config()

register_blueprints(app)

@app.route('/')
def home():
    try:
        connection = config.connect()
        if connection:
            return redirect(url_for('facturas.mostrar_facturas'))
        else:
            return render_template('facturas.html', mensaje="No se pudo establecer la conexión a SQL Server", tablas=[])
    except Exception as e:
        return render_template('facturas.html', mensaje=f"Error: {str(e)}", tablas=[])


if __name__ == '__main__':
    app.run(debug=True)
