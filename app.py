from flask import Flask, jsonify, request, render_template
import mysql.connector
import os
import time

app = Flask(__name__)

# MySQL Configuration (Matches Docker Stack)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'mysql-master'),
    'user': os.getenv('DB_USER', 'app_user'),
    'password': os.getenv('DB_PASSWORD', 'userpass'),
    'database': os.getenv('DB_NAME', 'app_db'),
    'port': 3306
}

def get_db_connection(max_retries=3, retry_delay=2):
    """Handles MySQL connection with retry logic for failover"""
    for attempt in range(max_retries):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            return conn
        except mysql.connector.Error as err:
            print(f"DB Connection failed (attempt {attempt + 1}): {err}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    raise Exception("Could not connect to MySQL after retries")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data', methods=['GET', 'POST'])
def handle_data():
    if request.method == 'POST':
        # Insert data
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO messages (content) VALUES (%s)", 
                          (request.json.get('content'),))
            conn.commit()
            return jsonify({"status": "success"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if 'conn' in locals():
                conn.close()

    else:
        # Get all data
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM messages")
            results = cursor.fetchall()
            return jsonify(results)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if 'conn' in locals():
                conn.close()

@app.route('/health')
def health_check():
    try:
        conn = get_db_connection(max_retries=1)
        conn.close()
        return "OK", 200
    except:
        return "DB Unavailable", 503

if __name__ == '__main__':
    # Initialize DB table if not exists
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"DB initialization failed: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

    app.run(host='0.0.0.0', port=5000)