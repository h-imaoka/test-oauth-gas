import os
import json
import secrets
import requests
import time
from urllib.parse import urlencode
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
import snowflake.connector
# PKCE関連のインポートを削除
from jose import jwt, JWTError

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

# Cognito設定
COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID')
COGNITO_CLIENT_SECRET = os.getenv('COGNITO_CLIENT_SECRET')
COGNITO_DOMAIN = os.getenv('COGNITO_DOMAIN')
AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
SNOWFLAKE_ACCOUNT_IDENTIFIER = os.getenv('SNOWFLAKE_ACCOUNT_IDENTIFIER')
SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE')

# CognitoエンドポイントURL
COGNITO_BASE_URL = f"https://{COGNITO_DOMAIN}.auth.{AWS_REGION}.amazoncognito.com"
TOKEN_ENDPOINT = f"{COGNITO_BASE_URL}/oauth2/token"
AUTHORIZATION_ENDPOINT = f"{COGNITO_BASE_URL}/oauth2/authorize"
JWKS_URL = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{os.getenv('USER_POOL_ID', 'PLACEHOLDER')}/.well-known/jwks.json"

TOKEN_FILE = 'tokens.json'

def save_token(token_data):
    """トークンをローカルファイルに保存（期限情報付き）"""
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
    
    expires_in = token_data.get('expires_in', 3600)
    obtained_at = token_data.get('obtained_at', 0)
    current_time = int(time.time())
    
    return (current_time - obtained_at) >= (expires_in - buffer_seconds)

def refresh_access_token(refresh_token):
    """リフレッシュトークンを使ってアクセストークンを更新"""
    token_data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': COGNITO_CLIENT_ID,
        'client_secret': COGNITO_CLIENT_SECRET
    }
    
    try:
        response = requests.post(TOKEN_ENDPOINT, data=token_data)
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
    
    if is_token_expired(token_data):
        refresh_token = token_data.get('refresh_token')
        if refresh_token:
            new_token_data = refresh_access_token(refresh_token)
            if new_token_data:
                return new_token_data
            else:
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                return None
        else:
            return None
    
    return token_data

def decode_jwt_claims(token):
    """JWTトークンからクレームを抽出（検証なし - デバッグ用）"""
    try:
        # JWTヘッダーとペイロードをデコード（署名検証なし）
        unverified_claims = jwt.get_unverified_claims(token)
        
        # Lambda Triggerでscp/scopeクレームが処理済み
        
        print(f"DEBUG: Full JWT claims: {unverified_claims}")  # デバッグ用
        return unverified_claims
    except JWTError as e:
        print(f"JWT decode error: {e}")
        return None

@app.route('/')
def index():
    token_data = get_valid_token()
    if token_data:
        return render_template('dashboard.html', authenticated=True)
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Cognito OAuth認証を開始（PKCE対応）"""
    if request.method == 'GET':
        return render_template('login.html')
    
    # ロール指定を取得
    role = request.form.get('role', '').strip()
    
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # スコープを動的に設定
    scopes = ['openid', 'profile', 'email']
    if role:
        scopes.append(f'session/role:{role.lower()}')
    else:
        scopes.append('session/role-any')
    
    auth_params = {
        'response_type': 'code',
        'client_id': COGNITO_CLIENT_ID,
        'redirect_uri': 'http://localhost:5000/callback',
        'scope': ' '.join(scopes),
        'state': state
    }
    
    auth_url = f"{AUTHORIZATION_ENDPOINT}?" + urlencode(auth_params)
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
    
    # Client Secret使用のためcode_verifierは不要
    
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': COGNITO_CLIENT_ID,
        'client_secret': COGNITO_CLIENT_SECRET,
        'redirect_uri': 'http://localhost:5000/callback'
    }
    
    try:
        response = requests.post(TOKEN_ENDPOINT, data=token_data)
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
    
    # JWTトークンの情報を表示用に取得
    access_token = token_data.get('access_token')
    id_token = token_data.get('id_token')
    
    access_claims = decode_jwt_claims(access_token) if access_token else None
    id_claims = decode_jwt_claims(id_token) if id_token else None
    
    return render_template('dashboard.html', 
                         authenticated=True, 
                         access_claims=access_claims,
                         id_claims=id_claims)

@app.route('/execute_sql', methods=['POST'])
def execute_sql():
    """SQL実行"""
    token_data = get_valid_token()
    if not token_data:
        flash('認証が必要です。再ログインしてください。', 'error')
        return redirect(url_for('index'))
    
    sql_query = request.form.get('sql_query', '').strip()
    warehouse = request.form.get('warehouse', '').strip()
    
    if not sql_query:
        flash('SQLクエリを入力してください', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Access TokenをSnowflake認証に使用（OAuth標準）
        id_token = token_data.get('id_token')
        access_token = token_data.get('access_token')
        
        # デバッグ: トークンの内容を確認
        print(f"DEBUG: Using Access token: {access_token[:50]}...")
        print(f"DEBUG: Snowflake account: {SNOWFLAKE_ACCOUNT_IDENTIFIER}")
        
        # Snowflake接続（External OAuth使用）
        conn_params = {
            'account': SNOWFLAKE_ACCOUNT_IDENTIFIER,
            'token': access_token,  # Access Tokenを使用（OAuth標準）
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
        
        # JWT Claims情報も取得
        access_claims = decode_jwt_claims(access_token)
        id_claims = decode_jwt_claims(token_data.get('id_token'))
        
        return render_template('dashboard.html', 
                             authenticated=True,
                             sql_query=sql_query,
                             warehouse=warehouse,
                             results=results, 
                             columns=columns,
                             access_claims=access_claims,
                             id_claims=id_claims)
    
    except Exception as e:
        flash(f'SQL実行エラー: {str(e)}', 'error')
        access_claims = decode_jwt_claims(token_data.get('access_token'))
        id_claims = decode_jwt_claims(token_data.get('id_token'))
        return render_template('dashboard.html', 
                             authenticated=True, 
                             sql_query=sql_query,
                             warehouse=warehouse,
                             access_claims=access_claims,
                             id_claims=id_claims)

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