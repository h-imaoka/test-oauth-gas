import os
import json
import secrets
import requests
import time
from urllib.parse import urlencode
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
import snowflake.connector
from authlib.common.security import generate_token
from authlib.oauth2.rfc7636 import create_s256_code_challenge

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

SNOWFLAKE_CLIENT_ID = os.getenv('SNOWFLAKE_CLIENT_ID')
SNOWFLAKE_CLIENT_SECRET = os.getenv('SNOWFLAKE_CLIENT_SECRET')
SNOWFLAKE_ACCOUNT_IDENTIFIER = os.getenv('SNOWFLAKE_ACCOUNT_IDENTIFIER')
SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE')

TOKEN_FILE = 'tokens.json'

def save_token(token_data):
    """トークンをローカルファイルに保存（期限情報付き）"""
    # 現在時刻を追加（トークン取得時刻として記録）
    token_data['obtained_at'] = int(time.time())
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f, indent=2)

def load_token():
    """ローカルファイルからトークンを読み込み"""
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def is_token_expired(token_data, buffer_seconds=300):
    """トークンが期限切れかチェック（デフォルト5分前にTrue）"""
    if not token_data or 'expires_in' not in token_data or 'obtained_at' not in token_data:
        return True
    
    expires_in = token_data.get('expires_in', 3600)  # デフォルト1時間
    obtained_at = token_data.get('obtained_at', 0)
    current_time = int(time.time())
    
    # 期限切れの5分前（buffer_seconds）にTrueを返す
    return (current_time - obtained_at) >= (expires_in - buffer_seconds)

def refresh_access_token(refresh_token):
    """リフレッシュトークンを使ってアクセストークンを更新"""
    token_data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': SNOWFLAKE_CLIENT_ID,
        'client_secret': SNOWFLAKE_CLIENT_SECRET
    }
    
    token_url = f"https://{SNOWFLAKE_ACCOUNT_IDENTIFIER}.snowflakecomputing.com/oauth/token-request"
    
    try:
        response = requests.post(token_url, data=token_data)
        if response.status_code == 200:
            new_token_data = response.json()
            save_token(new_token_data)
            return new_token_data
        else:
            print(f"Token refresh failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Token refresh error: {str(e)}")
        return None

def get_valid_token():
    """有効なトークンを取得（必要に応じて自動更新）"""
    token_data = load_token()
    if not token_data:
        return None
    
    # トークンが期限切れ間近かチェック
    if is_token_expired(token_data):
        refresh_token = token_data.get('refresh_token')
        if refresh_token:
            # トークンを更新
            new_token_data = refresh_access_token(refresh_token)
            if new_token_data:
                return new_token_data
            else:
                # リフレッシュに失敗した場合、古いトークンファイルを削除
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                return None
        else:
            return None
    
    return token_data

@app.route('/')
def index():
    token_data = get_valid_token()
    if token_data:
        return render_template('dashboard.html', authenticated=True)
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Snowflake OAuth認証を開始（PKCE対応）"""
    # GETリクエストの場合はログインフォームを表示
    if request.method == 'GET':
        return render_template('login.html')
    
    # POSTリクエストの場合はOAuth認証を開始
    role = request.form.get('role', '').strip()
    
    state = secrets.token_urlsafe(32)
    code_verifier = generate_token(128)
    code_challenge = create_s256_code_challenge(code_verifier)
    
    session['oauth_state'] = state
    session['code_verifier'] = code_verifier
    
    auth_params = {
        'response_type': 'code',
        'client_id': SNOWFLAKE_CLIENT_ID,
        'redirect_uri': 'http://127.0.0.1:5000/callback',
        'scope': f'refresh_token{f" session:role:{role}" if role else ""}',
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
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
    
    code_verifier = session.get('code_verifier')
    if not code_verifier:
        flash('セッションが無効です', 'error')
        return redirect(url_for('index'))
    
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': SNOWFLAKE_CLIENT_ID,
        'client_secret': SNOWFLAKE_CLIENT_SECRET,
        'redirect_uri': 'http://127.0.0.1:5000/callback',
        'code_verifier': code_verifier
    }
    
    token_url = f"https://{SNOWFLAKE_ACCOUNT_IDENTIFIER}.snowflakecomputing.com/oauth/token-request"
    
    try:
        response = requests.post(token_url, data=token_data)
        if response.status_code == 200:
            token_info = response.json()
            save_token(token_info)
            flash('ログイン成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(f'トークン取得に失敗しました: {response.text}', 'error')
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """ダッシュボード画面"""
    token_data = get_valid_token()
    if not token_data:
        return redirect(url_for('index'))
    
    return render_template('dashboard.html', authenticated=True)

@app.route('/execute_sql', methods=['POST'])
def execute_sql():
    """SQL実行"""
    token_data = get_valid_token()
    if not token_data:
        flash('認証が必要です。再ログインしてください。', 'error')
        return redirect(url_for('index'))
    
    sql_query = request.form.get('sql_query', '').strip()
    warehouse = request.form.get('warehouse', '').strip()
    role = request.form.get('role', '').strip()
    
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
        
        # Roleの設定（指定された場合のみ）
        if role:
            conn_params['role'] = role
        
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
                             role=role,
                             results=results, 
                             columns=columns)
    
    except Exception as e:
        flash(f'SQL実行エラー: {str(e)}', 'error')
        return render_template('dashboard.html', 
                             authenticated=True, 
                             sql_query=sql_query,
                             warehouse=warehouse,
                             role=role)

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