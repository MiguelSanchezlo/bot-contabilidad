from .facturas import facturas_completo_bp

def register_blueprints(app):
    app.register_blueprint(facturas_completo_bp)
