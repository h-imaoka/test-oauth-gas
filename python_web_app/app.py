import os
import json
import secrets
import requests
from urllib.parse import urlencode
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

SNOWFLAKE_CLIENT_ID = os.getenv('SNOWFLAKE_CLIENT_ID')
SNOWFLAKE_CLIENT_SECRET = os.getenv('SNOWFLAKE_CLIENT_SECRET')
SNOWFLAKE_ACCOUNT_IDENTIFIER = os.getenv('SNOWFLAKE_ACCOUNT_IDENTIFIER')
SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE')
SNOWFLAKE_DATABASE = os.getenv('SNOWFLAKE_DATABASE')
SNOWFLAKE_SCHEMA = os.getenv('SNOWFLAKE_SCHEMA')

TOKEN_FILE = 'tokens.json'

def save_token(token_data):
    """トークンをローカルファイルに保存"""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f, indent=2)

def load_token():
    """ローカルファイルからトークンを読み込み"""
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

@app.route('/')
def index():
    token_data = load_token()
    if token_data:
        return render_template('dashboard.html', authenticated=True)
    return render_template('login.html')

@app.route('/login')
def login():
    """Snowflake OAuth認証を開始"""
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    auth_params = {
        'response_type': 'code',
        'client_id': SNOWFLAKE_CLIENT_ID,
        'redirect_uri': 'http://127.0.0.1:5000/callback',
        'scope': 'refresh_token',
        'state': state
    }
    
    auth_url = f"https://{SNOWFLAKE_ACCOUNT_IDENTIFIER}.snowflakecomputing.com/oauth/authorize?" + urlencode(auth_params)
    return redirect(auth_url)

@app.route('/callback')
def callback():
    """OAuth認証のコールバック処理"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        flash('認証に失敗しました', 'error')
        return redirect(url_for('index'))
    
    if state != session.get('oauth_state'):
        flash('不正なリクエストです', 'error')
        return redirect(url_for('index'))
    
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': SNOWFLAKE_CLIENT_ID,
        'client_secret': SNOWFLAKE_CLIENT_SECRET,
        'redirect_uri': 'http://127.0.0.1:5000/callback'
    }
    
    token_url = f"https://{SNOWFLAKE_ACCOUNT_IDENTIFIER}.snowflakecomputing.com/oauth/token-request"
    
    try:
        response = requests.post(token_url, data=token_data)
        if response.status_code == 200:
            token_info = response.json()
            save_token(token_info)
            flash('认证成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(f'トークン取得に失敗しました: {response.text}', 'error')
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """ダッシュボード画面"""
    token_data = load_token()
    if not token_data:
        return redirect(url_for('index'))
    
    return render_template('dashboard.html', authenticated=True)

@app.route('/execute_sql', methods=['POST'])
def execute_sql():
    """SQL実行"""
    token_data = load_token()
    if not token_data:
        return redirect(url_for('index'))
    
    sql_query = request.form.get('sql_query', '').strip()
    warehouse = request.form.get('warehouse', '').strip()
    
    if not sql_query:
        flash('SQLクエリを入力してください', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        access_token = token_data.get('access_token')
        
        conn_params = {
            'account': SNOWFLAKE_ACCOUNT_IDENTIFIER,
            'token': access_token,
            'authenticator': 'oauth'
        }
        
        conn = snowflake.connector.connect(**conn_params)
        cursor = conn.cursor()
        
        # Warehouseの設定（指定された場合のみ）
        if warehouse:
            cursor.execute(f"USE WAREHOUSE {warehouse}")
        
        # メインクエリを実行
        cursor.execute(sql_query)
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        cursor.close()
        conn.close()
        
        return render_template('dashboard.html', 
                             authenticated=True, 
                             sql_query=sql_query,
                             warehouse=warehouse,
                             results=results, 
                             columns=columns)
    
    except Exception as e:
        flash(f'SQL実行エラー: {str(e)}', 'error')
        return render_template('dashboard.html', 
                             authenticated=True, 
                             sql_query=sql_query,
                             warehouse=warehouse)

@app.route('/logout')
def logout():
    """ログアウト"""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    session.clear()
    flash('ログアウトしました', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)