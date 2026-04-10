# Agentic Banking Demo

This project is a sample agentic banking application built with FastAPI and the OCI OpenAI Agents SDK, using:

- OCI Generative AI's OpenAI-compatible endpoint for model inference
- OCI Identity Domain for OIDC authentication
- SQLcl MCP for Oracle Database access
- FastMCP for an authenticated OCI Object Storage MCP server used by statements

The application currently supports:

- Browser-based login through OCI Identity Domain
- A banking chat assistant with account, card, transaction, and transfer workflows
- Oracle schema and seed scripts for sample banking data
- SQLcl MCP integration so the agent can query Oracle as a source of truth
- An authenticated OCI Object Storage MCP server for storing and reading statement documents
- Lazy loading for accounts, cards, and recent activity so the home page can render faster
- Session-backed login with persisted access tokens for authenticated Object Storage calls

Current state:

- The home page initially loads only the customer snapshot
- Accounts, cards, and recent activity are fetched on demand from separate API routes
- The statements page reads monthly statements, tax statements, and communications from OCI Object Storage
- The statements page can generate demo statement files and store them in Object Storage for the logged-in customer
- Statement objects are stored under `statements/<customer_id>/<category>/...`
- If the logged-in OCI user does not map to a customer with accounts in Oracle, the app shows `No matching account found for the logged-in user.`

## Project Files

- `docs/architecture.md`: Mermaid architecture diagram and request-flow summary
- `main.py`: FastAPI application and routes
- `app/agents.py`: agent definitions and runtime agent setup
- `app/auth/`: OCI Identity Domain OIDC integration
- `app/auth/__init__.py`: session handling plus persisted access-token storage for downstream authenticated MCP calls
- `app/config/`: environment variable loading
- `app/data/`: Oracle-backed banking data access and data-layer errors
- `app/data/statements.py`: statement storage and retrieval service backed by the Object Storage MCP server
- `app/mcp/`: MCP server integrations, including SQLcl and OCI Object Storage
- `app/mcp/sql/`: SQLcl MCP integration
- `app/mcp/ocios/`: OCI Object Storage FastMCP server and client wiring
- `app/models/`: domain models
- `app/tools/`: agent tool functions
- `app/user_context.py`: authenticated-user context passed into the chat/tool path
- `db/schema.sql`: Oracle schema creation
- `db/seed.sql`: sample data load script
- `startbank.sh`: convenience script to start the FastAPI banking app with the local virtual environment
- `sanitycheck.py`: quick OCI model connectivity test
- `requirements.txt`: Python dependencies

## Requirements

The Python dependencies are listed in `requirements.txt`:

- `openai`: OpenAI Python SDK used against the OCI OpenAI-compatible endpoint
- `openai-agents`: OpenAI Agents SDK
- `fastmcp`: FastMCP server framework for the OCI Object Storage MCP server
- `fastapi`: backend web framework
- `uvicorn`: local ASGI server
- `python-dotenv`: `.env` loading
- `authlib`: OIDC integration with OCI Identity Domain
- `itsdangerous`: secure session support used by Starlette/FastAPI session middleware
- `oci`: OCI Python SDK used inside the Object Storage MCP server

You also need:

- Python 3.11 or 3.12 recommended
- SQLcl installed locally
- An Oracle Database that your SQLcl saved connection can access
- An OCI Identity Domain application configured for OIDC
- OCI Generative AI access to an OpenAI-compatible model in your region/project
- An OCI Object Storage bucket for statements

## Environment Setup

From the project directory:

```bash
cd /Users/kiranthakkar/Downloads/agentdemo/bankingapplication
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env`.

## Environment Variables

The project reads configuration from `.env`.

### OCI model configuration

- `OCI_BASE_URL`
  The base URL for the OCI OpenAI-compatible endpoint.
  This should be the full endpoint URL for your OCI Generative AI deployment.

- `OCI_GENAI_API_KEY`
  Your OCI Generative AI API key or compatible auth token value used by the OpenAI SDK call path.

- `OCI_GENAI_PROJECT_ID`
  The OCI project identifier sent as the `project` value in SDK requests.

- `OCI_MODEL`
  The model name available in your OCI environment.
  Example values may include `openai.gpt-oss-120b` or another OCI-hosted OpenAI-compatible model that is actually enabled in your region/project.
  If this value is wrong, the app can fail with a 404 model-not-found error.

### Session and authentication

- `SESSION_SECRET`
  Any long random string used to sign the browser session cookie.
  Use a strong secret for real deployments.

- `OIDC_DISCOVERY_URL`
  The OCI Identity Domain OIDC discovery URL.
  This is typically the well-known OpenID configuration endpoint for your identity domain application.

- `OIDC_CLIENT_ID`
  The client ID for your OCI Identity Domain application.

- `OIDC_CLIENT_SECRET`
  The client secret for your OCI Identity Domain application.

- `OIDC_REDIRECT_URI`
  The redirect URI registered in OCI Identity Domain.
  Default:
  `http://localhost:8000/auth/callback`

- `OIDC_SCOPES`
  Space-separated OIDC scopes.
  Default:
  `openid profile email`

- `IDCS_DOMAIN`
  The OCI Identity Domain host used by the authenticated Object Storage MCP server.
  If you leave this empty, the app tries to derive it from `OIDC_DISCOVERY_URL`.

### SQLcl MCP / Oracle Database

- `SQLCL_PATH`
  Path to SQLcl.
  You can set this either to:
  - the SQLcl `bin` directory, for example `/Users/yourname/Downloads/sqlcl/bin`
  - the SQL executable itself, for example `/Users/yourname/Downloads/sqlcl/bin/sql`

- `SQLCL_CONNECTION_NAME`
  The saved SQLcl connection name to use for MCP.
  Example:
  `banking_demo`

- `SQLCL_MCP_ARGS`
  Arguments passed to SQLcl for MCP mode.
  Default:
  `-mcp`

  Note:
  The app now automatically appends `-name <SQLCL_CONNECTION_NAME>` when launching SQLcl MCP, so you do not need to include `-name` manually in this variable.

### OCI Object Storage MCP / Statements

- `OCIOS_MCP_ENABLED`
  Set to `true` to enable the OCI Object Storage MCP integration.

- `OCIOS_MCP_HOST`
  Host for the Object Storage MCP server.
  Default:
  `127.0.0.1`

- `OCIOS_MCP_PORT`
  Port for the Object Storage MCP server.
  Default:
  `9001`

- `OCIOS_MCP_URL`
  Full streamable HTTP MCP endpoint used by the banking app.
  Default:
  `http://127.0.0.1:9001/mcp`

- `STATEMENTS_REGION`
  OCI region used for Object Storage statement files.
  Example:
  `us-ashburn-1`

- `STATEMENTS_BUCKET`
  OCI Object Storage bucket name where statements are stored.
  Example:
  `banking-statements-demo`

Notes:

- The banking app forwards the logged-in user's bearer token to the Object Storage MCP server
- The Object Storage MCP server uses token exchange and does not require `OCI_CONFIG_FILE`
- Statement files are organized by customer and category, for example `statements/CUS-001/monthly/2026-04-relationship-summary.txt`

### Application server

- `APP_RUNTIME_DIR`
  Optional directory for runtime SQLite files such as auth token storage and agent conversation history.
  If not set, the app uses a temp directory outside the project tree so `uvicorn --reload` does not restart on every SQLite write.

- `APP_LOG_LEVEL`
  Python application log level.
  Default:
  `INFO`
  Set this to `DEBUG` when you want detailed request, cache, SQL MCP, and statement-storage tracing.

- `PORT`
  Local FastAPI port.
  Default:
  `8000`

## Example .env

```env
OCI_BASE_URL=https://your-oci-openai-compatible-endpoint
OCI_GENAI_API_KEY=your_oci_genai_api_key
OCI_GENAI_PROJECT_ID=your_project_id
OCI_MODEL=openai.gpt-oss-120b

SESSION_SECRET=replace_with_a_long_random_secret

OIDC_DISCOVERY_URL=https://your-identity-domain/.well-known/openid-configuration
OIDC_CLIENT_ID=your_oidc_client_id
OIDC_CLIENT_SECRET=your_oidc_client_secret
OIDC_REDIRECT_URI=http://localhost:8000/auth/callback
OIDC_SCOPES=openid profile email
IDCS_DOMAIN=your-identity-domain-host

SQLCL_PATH=/Users/yourname/Downloads/sqlcl/bin
SQLCL_CONNECTION_NAME=banking_demo
SQLCL_MCP_ARGS=-mcp

OCIOS_MCP_ENABLED=true
OCIOS_MCP_HOST=127.0.0.1
OCIOS_MCP_PORT=9001
OCIOS_MCP_URL=http://127.0.0.1:9001/mcp
STATEMENTS_REGION=us-ashburn-1
STATEMENTS_BUCKET=banking-statements-demo
APP_RUNTIME_DIR=/tmp/agentic-banking-demo
APP_LOG_LEVEL=INFO

PORT=8000
```

## SQLcl Setup

Before using MCP, make sure SQLcl can connect without prompting for a password.

Example connection save flow:

```sql
conn -save banking_demo -savepwd -replace user/password@//host:1521/service_name
```

Then test it:

```bash
/Users/yourname/Downloads/sqlcl/bin/sql -name banking_demo
```

Inside SQLcl:

```sql
select sysdate from dual;
```

If SQLcl prompts for a password, the saved connection is incomplete and should be recreated with `-savepwd`.

## Bootstrap Oracle Schema And Sample Data

After your SQLcl saved connection works, bootstrap the database:

```bash
/Users/yourname/Downloads/sqlcl/bin/sql -name banking_demo
```

Then run:

```sql
@/Users/kiranthakkar/Downloads/agentdemo/bankingapplication/db/schema.sql
@/Users/kiranthakkar/Downloads/agentdemo/bankingapplication/db/seed.sql
```

Validate the data:

```sql
select * from bank_customers;
select account_id, account_name, balance from bank_accounts;
select transaction_id, account_id, description, amount from bank_transactions;
```

Notes:

- `schema.sql` creates the banking tables and indexes
- `seed.sql` clears existing rows, inserts one sample customer, three sample accounts, two cards, and sample transactions
- The seeded customer starts with placeholder identity data, so for real login testing you should update `bank_customers.identity_subject` and/or `bank_customers.email` to match the OCI user who signs in
- If the tables already exist, rerunning `schema.sql` will fail on `CREATE TABLE`

Example update after you know the logged-in OCI user:

```sql
update bank_customers
set identity_subject = 'your_oci_user_sub',
    email = 'your_oci_user_email'
where customer_id = 'CUS-001';

commit;
```

## Optional OCI Connectivity Sanity Check

Before starting the app, you can validate the OCI model configuration:

```bash
python sanitycheck.py
```

Expected success output includes:

```text
Response: banking sanity check ok
```

If this fails, fix the OCI model settings in `.env` before troubleshooting the app.

## Start The Object Storage MCP Server

The statements flow depends on the authenticated OCI Object Storage MCP server.
Start it in a separate terminal after activating the virtual environment:

```bash
cd /Users/kiranthakkar/Downloads/agentdemo/bankingapplication
source .venv/bin/activate
python -m app.mcp.ocios.server
```

The banking application connects to this server at `OCIOS_MCP_URL` and forwards the logged-in user's bearer token when reading or writing statements.
The server exposes a streamable HTTP MCP endpoint and a simple health endpoint at `/health`.

## Start The Application

The quickest way to start the banking application is:

```bash
cd /Users/kiranthakkar/Downloads/agentdemo/bankingapplication
./startbank.sh
```

`startbank.sh`:

- starts `main:app` with `uvicorn --reload`
- uses `.venv/bin/uvicorn`
- respects `HOST` and `PORT` if they are already set in your shell

If you prefer to start it manually, activate the virtual environment first and run Uvicorn directly:

```bash
cd /Users/kiranthakkar/Downloads/agentdemo/bankingapplication
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

## Quick Smoke Test

After both the Object Storage MCP server and the FastAPI app are running:

1. Open `http://localhost:8000`
2. Sign in through OCI Identity Domain
3. Confirm the dashboard loads customer snapshot data
4. Open the Statements page
5. Click `Generate demo statements`
6. Verify monthly statements, tax statements, and communications appear
7. Click `Preview` on a statement to confirm the content is read back from OCI Object Storage

You can also ask the chat assistant to help with statements after the MCP servers are available, because the agent runtime now receives both SQL MCP tools and Object Storage MCP tools.

If you want to respect the `PORT` value in `.env`, start Uvicorn with that same port number.

## How Authentication Works

- Visiting `/` redirects unauthenticated users to `/login`
- `/auth/login` starts the OCI Identity Domain OIDC flow
- `/auth/callback` receives the login response, stores the signed session, and persists the access token for authenticated Object Storage MCP calls
- `/auth/logout` clears the session
- Access tokens and chat session history are stored server-side in the runtime directory; the browser session stores only the token key, not the bearer token itself

Because authentication is handled by OCI Identity Domain, there is no local username/password form for the banking app itself.

## Detailed Testing

### Browser test

1. Start the app.
2. Open `http://localhost:8000`.
3. Sign in through OCI Identity Domain.
4. Confirm the customer snapshot loads on the home page.
5. Click `Load accounts`, `Load cards`, or `Load recent activity` to fetch those sections on demand.
6. Open `Statements`, click `Generate demo statements`, then verify the monthly, tax, and communications tabs populate for the logged-in customer.
7. Click `Preview` for a statement and confirm the content loads from OCI Object Storage.
8. Open the chat panel and try prompts such as:
   - `Show me all my account balances.`
   - `What are my recent checking transactions?`
   - `What cards do I have?`
   - `Transfer $200 from CHK-001 to SAV-001 for my vacation fund.`

### API test

After login, the browser session can call:

- `GET /api/bootstrap`
  Returns app metadata, logged-in user info, and the customer snapshot used for the initial home page load

- `GET /api/accounts`
  Returns accounts for the logged-in customer

- `GET /api/cards`
  Returns cards for the logged-in customer

- `GET /api/activity`
  Returns recent activity for the logged-in customer

- `POST /api/chat`
  Sends a chat message to the banking agent

- `POST /api/statements/generate-demo`
  Creates demo monthly, tax, and communications statement files for the logged-in customer in OCI Object Storage

- `GET /api/statements/{category}`
  Lists statement objects for `monthly`, `tax`, or `communications`

- `GET /api/statements/{category}/content?object_name=...`
  Reads the selected statement back from OCI Object Storage

Example request body:

```json
{
  "conversation_id": "test-conversation-1",
  "message": "Show me all my account balances."
}
```

### What to expect right now

- Auth should be handled by OCI Identity Domain
- The app should start even if SQLcl MCP is not active, as long as OCI and OIDC are configured
- With SQLcl MCP enabled, the agent is set up to use Oracle as the source of truth for banking queries
- The initial home page fetch is intentionally lightweight and returns only the customer snapshot
- Accounts, cards, and recent activity load only when requested
- The statements page loads the customer snapshot first, then loads statements for the selected tab
- If the OCI user is not mapped to a customer with accounts in Oracle, the UI and chat respond with `No matching account found for the logged-in user.`

## Troubleshooting

### 404 model not found

Cause:
`OCI_MODEL` is not available in your OCI environment.

Fix:
Use a model name that actually exists in your OCI project/region.

### Internal server error from model call

Cause:
Incorrect OCI endpoint, auth values, or model configuration.

Fix:
Run `python sanitycheck.py` and correct `.env`.

### SQLcl prompts for password

Cause:
Saved connection does not include the password.

Fix:
Recreate the SQLcl connection using `-savepwd`.

### OIDC state mismatch / CSRF warning

Cause:
A stale browser login state may still exist.

Fix:
Retry login in a fresh browser session or incognito window. The app also clears stale OCI state before a new login attempt.

### Statements were generated but do not appear

Cause:
The logged-in user may be mapped to a different Oracle customer than expected, or the statement objects may have been written under a different customer prefix.

Fix:
Confirm the signed-in user resolves to the expected `bank_customers.customer_id`, then verify the objects exist under:
`statements/<customer_id>/monthly/`
`statements/<customer_id>/tax/`
`statements/<customer_id>/communications/`

### The app is slow in development with `--reload`

Cause:
SQLite runtime files such as auth token storage or conversation history are being written inside the reload-watched project directory.

Fix:
Use the default temp-based runtime directory or set `APP_RUNTIME_DIR` to a directory outside the project tree, then restart Uvicorn.

### No matching account found for the logged-in user

Cause:
The logged-in OCI user does not match a row in `bank_customers`, or the matched customer has no rows in `bank_accounts`.

Fix:
Update Oracle data so the signed-in user's `sub` or `email` matches `bank_customers.identity_subject` or `bank_customers.email`, and make sure that customer has at least one account row.
