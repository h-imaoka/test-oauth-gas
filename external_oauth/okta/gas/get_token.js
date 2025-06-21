/**
 * 1) スクリプトプロパティに以下を登録しておく
 *    OKTA_DOMAIN, OKTA_CLIENT_ID, OKTA_CLIENT_SECRET
 * 2) 「デプロイ」→「新しいデプロイ」→「ウェブアプリ」
 *    - 実行するユーザー：自分
 *    - アクセスできるユーザー：自分のみ（組織内）
 *    - リダイレクトURIとして出てくる exec URL を Okta の Login redirect URIs に登録
 */

// OAuth2 サービス定義
function getOAuthService() {
  const p = PropertiesService.getScriptProperties();
  return OAuth2.createService('OktaToken')
    .setAuthorizationBaseUrl(`https://${p.getProperty('OKTA_DOMAIN')}/oauth2/default/v1/authorize`)
    .setTokenUrl(`https://${p.getProperty('OKTA_DOMAIN')}/oauth2/default/v1/token`)
    .setClientId(p.getProperty('OKTA_CLIENT_ID'))
    .setClientSecret(p.getProperty('OKTA_CLIENT_SECRET'))
    .setCallbackFunction('authCallback')
    .setPropertyStore(PropertiesService.getUserProperties())
    .setScope('openid profile email offline_access session:role-any');
}

// Web アプリのエントリポイント
function doGet(e) {
  const service = getOAuthService();
  // トークン未取得 or 失効時は認可画面へのリンクを出力
  if (!service.hasAccess()) {
    const authUrl = service.getAuthorizationUrl();
    return HtmlService.createHtmlOutput(
      `<p><a href="${authUrl}" target="_blank">▶ Okta で認可してトークン取得</a></p>`
    );
  }
  // 取得済みトークンの確認画面
  // トークン情報を一式取得
   const tokenObj     = service.getToken();
   const accessToken  = tokenObj.access_token;
   const refreshToken = tokenObj.refresh_token || '—未発行—';
   // expires_in は「この瞬間から何秒後に切れるか」
   const expiresInSec = tokenObj.expires_in || 0;
   const expiresAt    = expiresInSec
     ? new Date(Date.now() + expiresInSec * 1000)
     : '取得できませんでした';

  return HtmlService.createHtmlOutput(`
    <h3>✅ トークン取得済み</h3>
    <p><strong>Access Token:</strong><br><code>${accessToken}</code></p>
    <p><strong>Refresh Token:</strong><br><code>${refreshToken}</code></p>
    <p><strong>Expires At:</strong> ${
      expiresAt instanceof Date 
        ? expiresAt.toLocaleString() 
        : expiresAt
    }</p>
  `);
}

// Okta からのコールバック受け口
function authCallback(request) {
  const service = getOAuthService();
  const authorized = service.handleCallback(request);
  return HtmlService.createHtmlOutput(
    authorized
      ? '<p>認証成功！このウィンドウを閉じて、もう一度最初の URL にアクセスしてください。</p>'
      : '<p>認証失敗…設定を見直してください。</p>'
  );
}

function clearOAuthTokens() {
  const service = getOAuthService();
  service.reset();  // 既存の access/refresh token をすべて消去
  Logger.log('OAuth tokens have been cleared.');
}

function debugValidateToken() {
  const service = getOAuthService();
  if (!service.hasAccess()) {
    Logger.log('⚠️ まだアクセストークンを取得していません');
    return;
  }
  // 1) トークン文字列を取得
  const token = service.getAccessToken();
  //Logger.log('Access Token:' + token);

  // 2) JWT を “.`“ で分割してデコード
  const parts = token.split('.');
  if (parts.length !== 3) {
    Logger.log('⚠️ JWT 形式ではありません:', parts.length);
    return;
  }
  const decode = (s) => JSON.parse(
    Utilities.newBlob(Utilities.base64DecodeWebSafe(s)).getDataAsString()
  );
  const header  = decode(parts[0]);
  const payload = decode(parts[1]);

  // 3) ログに出力
  Logger.log('=== JWT Header ===\n' + JSON.stringify(header, null, 2));
  Logger.log('=== JWT Payload ===\n' + JSON.stringify(payload, null, 2));

  // 4) 主要クレームをピックアップ
  Logger.log('iss:' + payload.iss);
  Logger.log('aud:' , Array.isArray(payload.aud) ? payload.aud.join(',') : payload.aud);
  Logger.log('exp:' + new Date(payload.exp * 1000).toLocaleString());
  Logger.log('sub:' + payload.sub);
}