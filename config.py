import os
import pyodbc
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.driver = os.getenv('SQLSERVER_DRIVER', 'ODBC Driver 17 for SQL Server')
        self.server = os.getenv('SQLSERVER_HOST')
        self.database = os.getenv('SQLSERVER_DB')
        self.username = os.getenv('SQLSERVER_USER')
        self.password = os.getenv('SQLSERVER_PASSWORD')
        self.trust_cert = os.getenv('SQLSERVER_TRUSTED', 'yes')

    def get_connection_string(self):
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"TrustServerCertificate={self.trust_cert};"
        )

    def connect(self):
        try:
            conn_str = self.get_connection_string()
            connection = pyodbc.connect(conn_str)
            return connection
        except pyodbc.Error as e:
            print(f"[ERROR] Conexión fallida: {e}")
            return None


def execute_query(query):
    """
    Ejecuta una consulta y devuelve una lista de filas
    """
    config = Config()
    conn = config.connect()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print(f"[ERROR] Fallo en ejecución de consulta: {e}")
        return []

def execute_query_df(query):
    resultados, columnas = execute_query_with_columns(query)
    return pd.DataFrame(resultados, columns=columnas)

def execute_query_with_columns(query):
    config = Config()
    conn = config.connect()
    if not conn:
        return [], []

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        results = [tuple(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return results, columns
    except Exception as e:
        print(f"[ERROR] Fallo en ejecución de consulta: {e}")
        return [], []
