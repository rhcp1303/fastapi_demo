# hubspot.py
import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
from fastapi import Request

from backend.redis_client import add_key_value_redis, get_value_redis, delete_key_redis

CLIENT_ID = '6c007d68-a6a1-4b2e-a71a-1a2c2988d24b'
CLIENT_SECRET = 'b4e1f93d-c23e-454c-9157-b410b942d1fb'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fintegrations%2Fhubspot%2Foauth2callback'
scope = 'automation%20oauth'


async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }

    encoded_state = json.dumps(state_data)

    auth_url = f'{authorization_url}&state={encoded_state}&scope={scope}'
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', json.dumps(state_data), expire=600)
    return auth_url


async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description'))
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(encoded_state)

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': REDIRECT_URI,
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )

    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)

    close_window_script = """
       <html>
           <script>
               window.close();
           </script>
       </html>
       """
    return HTMLResponse(content=close_window_script)


async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

async def create_integration_item_metadata_object(response_json):
    # TODO
    pass


async def get_items_hubspot(credentials):
    # TODO
    pass
