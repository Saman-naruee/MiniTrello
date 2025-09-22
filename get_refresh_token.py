from google_auth_oauthlib.flow import InstalledAppFlow
from custom_tools.logger import custom_logger as printclr
from decouple import config


# Define the necessary scope for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def get_client_config():
    """
    Get Google OAuth client configuration from environment variables.
    """
    return {
        "web": {
            "client_id": config('GOOGLE_OAUTH_CLIENT_ID'),
            "project_id": config('GOOGLE_PROJECT_ID'),
            "auth_uri": config('GOOGLE_AUTH_URI'),
            "token_uri": config('GOOGLE_TOKEN_URI'),
            "auth_provider_x509_cert_url": config('GOOGLE_AUTH_PROVIDER_X509_CERT_URL'),
            "client_secret": config('GOOGLE_OAUTH_CLIENT_SECRET'),
            "redirect_uris": eval(config('GOOGLE_REDIRECT_URIS'))
        }
    }


def main():
    """
    Runs the OAuth 2.0 flow to obtain and print a refresh token.
    """
    # Create a flow object from environment variables
    client_config = get_client_config()
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

    # Run the flow, which will open a browser window for you to log in
    # and authorize the application.
    credentials = flow.run_local_server(port=0)

    # Print the refresh token to the console
    print("\n--- Your Refresh Token ---")
    print("Copy this value into your .env file as GOOGLE_REFRESH_TOKEN")
    printclr(credentials.refresh_token)
    with open("refresh_token.txt", "w") as f:
        f.write(credentials.refresh_token)
    printclr("Refresh token also saved to refresh_token.txt")
    print("--------------------------\n")

if __name__ == '__main__':
    main()
