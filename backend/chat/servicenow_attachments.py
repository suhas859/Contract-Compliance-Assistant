import os

import requests


def _get_oauth_token(instance_url: str, client_id: str, client_secret: str, user: str, password: str) -> str:
    """
    Exchanges the instance's own admin credentials for a short-lived
    OAuth access token via the Resource Owner Password grant -- used
    because this instance rejects Basic Auth on the REST API outright,
    but the password grant still authenticates with the same admin
    username/password, just wrapped in an OAuth token exchange first.
    """
    response = requests.post(
        f"{instance_url}/oauth_token.do",
        data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": user,
            "password": password,
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"ServiceNow OAuth token request failed (HTTP {response.status_code}): {response.text[:300]!r}"
        )
    return response.json()["access_token"]


def fetch_incident_attachments(sys_id: str) -> list[tuple[str, bytes]]:
    """
    Downloads every file attached to a ServiceNow incident via the
    Attachment REST API, authenticating with a fresh OAuth token per
    call rather than caching one -- this only fires occasionally (one
    incoming webhook at a time), so the extra token request is
    negligible and avoids any expiry/refresh bookkeeping. Returns []
    if the ServiceNow OAuth credentials aren't configured, or the
    incident has no sys_id to look up -- callers treat that the same
    as "no attachments" rather than an error, since the webhook should
    still work for text-only incidents.
    """
    instance_url = os.environ.get("SERVICENOW_INSTANCE_URL", "").rstrip("/")
    user = os.environ.get("SERVICENOW_API_USER")
    password = os.environ.get("SERVICENOW_API_PASSWORD")
    client_id = os.environ.get("SERVICENOW_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("SERVICENOW_OAUTH_CLIENT_SECRET")

    if not (instance_url and user and password and client_id and client_secret and sys_id):
        return []

    token = _get_oauth_token(instance_url, client_id, client_secret, user, password)
    headers = {"Authorization": f"Bearer {token}"}

    list_response = requests.get(
        f"{instance_url}/api/now/attachment",
        params={"sysparm_query": f"table_sys_id={sys_id}^table_name=incident"},
        headers=headers,
        timeout=30,
    )
    if not list_response.ok:
        raise RuntimeError(
            f"ServiceNow attachment list request failed (HTTP {list_response.status_code}): "
            f"{list_response.text[:500]!r}"
        )

    try:
        result = list_response.json().get("result", [])
    except ValueError as exc:
        raise RuntimeError(
            f"ServiceNow attachment list returned non-JSON (HTTP {list_response.status_code}): "
            f"{list_response.text[:300]!r}"
        ) from exc

    files = []
    for attachment in result:
        file_response = requests.get(
            f"{instance_url}/api/now/attachment/{attachment['sys_id']}/file",
            headers=headers,
            timeout=30,
        )
        file_response.raise_for_status()
        files.append((attachment["file_name"], file_response.content))

    return files
