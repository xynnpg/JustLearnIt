from flask import Flask, request, jsonify
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_db():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/database', methods=['GET'])
def get_database():
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')
        with open(db_path, 'rb') as f:
            return f.read(), 200, {'Content-Type': 'application/octet-stream'}
    except Exception as e:
        logger.error(f"Error getting database: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/database/execute', methods=['POST'])
def execute_query():
    try:
        data = request.get_json()
        statement = data.get('statement')
        parameters = data.get('parameters', [])

        if not statement:
            return jsonify({"error": "No statement provided"}), 400

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(statement, parameters)
        conn.commit()

        # Get the results
        if cursor.description:
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return jsonify({
                "description": cursor.description,
                "rowcount": cursor.rowcount,
                "rows": rows
            })
        else:
            return jsonify({
                "description": None,
                "rowcount": cursor.rowcount,
                "rows": []
            })
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/database/executemany', methods=['POST'])
def execute_many():
    try:
        data = request.get_json()
        statement = data.get('statement')
        parameters = data.get('parameters', [])

        if not statement:
            return jsonify({"error": "No statement provided"}), 400

        conn = get_db()
        cursor = conn.cursor()
        cursor.executemany(statement, parameters)
        conn.commit()

        # Get the results
        if cursor.description:
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return jsonify({
                "description": cursor.description,
                "rowcount": cursor.rowcount,
                "rows": rows
            })
        else:
            return jsonify({
                "description": None,
                "rowcount": cursor.rowcount,
                "rows": []
            })
    except Exception as e:
        logger.error(f"Error executing batch query: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(port=5000) 