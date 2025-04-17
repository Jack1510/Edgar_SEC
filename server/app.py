from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

conn = psycopg2.connect(
    dbname='stocks_portfolio',
    user='postgres',
    password='Nehasam@15',
    host='localhost',
    port='5432'
)

@app.route('/api/test-db', methods=['GET'])
def test_db():
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT NOW()')
        result = cur.fetchone()
    return jsonify({'connected': True, 'time': result['now']})

@app.route('/api/portfolio', methods=['POST'])
def add_to_portfolio():
    data = request.get_json()
    symbol = data['symbol']
    name = data['name']
    quantity = data['quantity']

    with conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM stocks WHERE symbol = %s', (symbol,))
            stock = cur.fetchone()
            if not stock:
                cur.execute(
                    'INSERT INTO stocks (symbol, name) VALUES (%s, %s) RETURNING *',
                    (symbol, name)
                )
                stock = cur.fetchone()
            stock_id = stock['id']
            cur.execute(
                'INSERT INTO portfolio (stock_id, quantity) VALUES (%s, %s)',
                (stock_id, quantity)
            )
    return 'Stock added to portfolio', 201

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('''
            SELECT s.symbol, s.name, p.quantity
            FROM portfolio p
            JOIN stocks s ON p.stock_id = s.id
        ''')
        portfolio = cur.fetchall()
    return jsonify(portfolio)

if __name__ == '__main__':
    app.run(port=5000)
