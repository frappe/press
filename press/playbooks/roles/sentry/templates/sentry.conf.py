OIDC_CLIENT_ID = "{{ sentry_oauth_client_id }}"
OIDC_CLIENT_SECRET = "{{ sentry_oauth_client_secret }}"

OIDC_ISSUER = "Frappe"
OIDC_SCOPE = "openid email"

OIDC_AUTHORIZATION_ENDPOINT = (
	"{{ sentry_oauth_server_url }}/api/method/frappe.integrations.oauth2.authorize"
)
OIDC_TOKEN_ENDPOINT = (
	"{{ sentry_oauth_server_url }}/api/method/frappe.integrations.oauth2.get_token"
)
OIDC_USERINFO_ENDPOINT = (
	"{{ sentry_oauth_server_url }}/api/method/frappe.integrations.oauth2.openid_profile"
)
