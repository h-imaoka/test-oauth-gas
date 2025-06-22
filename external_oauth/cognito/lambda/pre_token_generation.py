import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Pre Token Generation Lambda Trigger v2.0
    Access TokenとID Token両方にSnowflake用のscpクレームを追加
    """
    
    logger.info(f"Received event: {json.dumps(event, indent=2)}")
    
    try:
        # カスタムクレーム
        custom_claims = {
            'scp': 'session:role-any'
        }
        
        # Access Token専用クレーム（audienceを追加）
        access_token_claims = {
            'scp': 'session:role-any',
            'aud': os.environ.get('COGNITO_CLIENT_ID', 'cognito-client-id')  # 環境変数からaud取得、なければデフォルト
        }
        logger.info(f"Adding scp claim: {custom_claims['scp']}")
        
        # 既存のresponseがない場合は初期化
        if 'response' not in event or event['response'] is None:
            event['response'] = {}
        
        # v2.0対応: ID TokenとAccess Token両方にクレーム追加
        event['response']['claimsAndScopeOverrideDetails'] = {
            'idTokenGeneration': {
                'claimsToAddOrOverride': custom_claims,
                'claimsToSuppress': []
            },
            'accessTokenGeneration': {
                'claimsToAddOrOverride': access_token_claims,  # audienceクレーム付き
                'claimsToSuppress': [],
                'scopesToAdd': [],
                'scopesToSuppress': []
            }
        }
        
        logger.info(f"Final response: {json.dumps(event['response'], indent=2)}")
        
    except Exception as e:
        logger.error(f"Error processing token: {str(e)}")
        if 'response' not in event:
            event['response'] = {}
        
    return event
