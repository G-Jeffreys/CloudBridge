from authlib.integrations.httpx_client import OAuth2Client

class GoogleDriveAuth:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.client = OAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope="https://www.googleapis.com/auth/drive",
            authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            token_endpoint="https://oauth2.googleapis.com/token",
        )

    def get_authorization_url(self):
        authorization_url, state = self.client.create_authorization_url()
        return authorization_url, state

    def fetch_token(self, authorization_response, state):
        self.client.fetch_token(authorization_response=authorization_response, state=state)
        return self.client.token 