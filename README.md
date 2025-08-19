# OpenAI-Compatible Sora API Service

An API service that provides an OpenAI-compatible interface for Sora. It uses cloudscraper to bypass Cloudflare checks and supports multi-key rotation, concurrent processing, and standard OpenAI response formats.

## Features

- **OpenAI-compatible API**: Fully compatible with OpenAI's `/v1/chat/completions` endpoint
- **Cloudflare bypass**: Uses the `cloudscraper` library to pass Cloudflare verification
- **Multi-key rotation**: Supports multiple Sora auth tokens; selects intelligently by weight and rate limits
- **Concurrency**: Handles multiple concurrent requests
- **Streaming responses**: Supports SSE streaming format
- **Image generation**: Supports text-to-image and image-to-image (Remix)
- **Asynchronous processing**: Asynchronously generates images with immediate ack responses to avoid timeouts
- **Status query**: API endpoint to check async task status and results
- **Performance optimizations**: Improved throughput and resource efficiency
- **Health check**: Container healthcheck endpoint

## Requirements

- Python 3.8+
- FastAPI 0.95.0+
- cloudscraper 1.2.71+
- See `requirements.txt` for more

## Quick Start

You can run without setting any environment variables; all config can be set in the admin panel.

- Default admin login key: `sk-123456`
- If `API_AUTH_TOKEN` is not set, API requests use the admin key by default

One-click Docker run:
```bash
docker run -d -p 8890:8890 --name sora-api 1hei1/sora-api:latest
```



### Method 1: Run directly

1. Clone the repo
   ```bash
   git clone https://github.com/1hei1/sora-api.git
   cd sora-api
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Configure API keys (two options)
   - **Option 1**: Create an `api_keys.json` file
     ```json
     [
       {"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60},
       {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}
     ]
     ```
   - **Option 2**: Set environment variables
     ```bash
     # Linux/macOS
     export API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}, {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}]'  
     
     # Windows (PowerShell)
     $env:API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}, {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}]'
     
     # Windows (CMD)
     set API_KEYS=[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}, {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}]  
     ```

4. Configure proxy (optional)
   ```bash
   # Linux/macOS - Basic proxy
   export PROXY_HOST=127.0.0.1
   export PROXY_PORT=7890
   
   # Linux/macOS - Proxy with auth
   export PROXY_HOST=127.0.0.1
   export PROXY_PORT=7890
   export PROXY_USER=username
   export PROXY_PASS=password
   
   # Windows (PowerShell) - Basic proxy
   $env:PROXY_HOST="127.0.0.1"
   $env:PROXY_PORT="7890"
   
   # Windows (PowerShell) - Proxy with auth
   $env:PROXY_HOST="127.0.0.1"
   $env:PROXY_PORT="7890"
   $env:PROXY_USER="username"
   $env:PROXY_PASS="password"
   
   # Windows (CMD) - Basic proxy
   set PROXY_HOST=127.0.0.1
   set PROXY_PORT=7890
   
   # Windows (CMD) - Proxy with auth
   set PROXY_HOST=127.0.0.1
   set PROXY_PORT=7890
   set PROXY_USER=username
   set PROXY_PASS=password
   ```

5. Start the service
   ```bash
   python run.py
   ```

6. Access the service
   - API base URL: http://localhost:8890
   - Admin panel: http://localhost:8890/admin

### Method 2: Docker deployment

1. Build the Docker image
   ```bash
   docker build -t sora-api .
   ```

2. Run the Docker container (options)

   **Basic run**:
   ```bash
   docker run -d -p 8890:8890 --name sora-api sora-api
   ```

   **Use prebuilt image**:
   ```bash
   docker run -d -p 8890:8890 --name sora-api 1hei1/sora-api:latest
   ```

   **Prebuilt image with API keys**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}, {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}]' \
     --name sora-api \
     1hei1/sora-api:v0.1
   ```

   **Prebuilt image with proxy**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}]' \
     -e PROXY_HOST=host.docker.internal \
     -e PROXY_PORT=7890 \
     --name sora-api \
     1hei1/sora-api:v0.1
   ```

   **Custom image with API keys**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}, {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}]' \
     --name sora-api \
     sora-api
   ```

   **Custom image with basic proxy**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}]' \
     -e PROXY_HOST=host.docker.internal \
     -e PROXY_PORT=7890 \
     --name sora-api \
     sora-api
   ```

   **Custom image with auth proxy**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}]' \
     -e PROXY_HOST=host.docker.internal \
     -e PROXY_PORT=7890 \
     -e PROXY_USER=username \
     -e PROXY_PASS=password \
     --name sora-api \
     sora-api
   ```

   **Mount external config file**:
   ```bash
   # Ensure api_keys.json is configured locally first
   docker run -d -p 8890:8890 \
     -v $(pwd)/api_keys.json:/app/api_keys.json \
     -e PROXY_HOST=host.docker.internal \
     -e PROXY_PORT=7890 \
     --name sora-api \
     sora-api
   ```

   **Mount local directory for image storage**:
   ```bash
   docker run -d -p 8890:8890 \
     -v /your/local/path:/app/src/static/images \
     --name sora-api \
     sora-api
   ```

   **Enable verbose logging**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}]' \
     -e VERBOSE_LOGGING=true \
     --name sora-api \
     sora-api
   ```

   **Note**: When using the host proxy inside Docker, use `host.docker.internal` instead of `127.0.0.1` for the proxy host.

3. Check container status
   ```bash
   docker ps
   docker logs sora-api
   ```

4. Stop and remove the container
   ```bash
   docker stop sora-api
   docker rm sora-api
   ```

## Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `API_HOST` | API listen address | `0.0.0.0` | `127.0.0.1` |
| `API_PORT` | API port | `8890` | `9000` |
| `BASE_URL` | Base URL used when localizing images | `http://0.0.0.0:8890` | `https://api.example.com` |
| `PROXY_HOST` | HTTP proxy host | empty (disabled) | `127.0.0.1` |
| `PROXY_PORT` | HTTP proxy port | empty (disabled) | `7890` |
| `PROXY_USER` | HTTP proxy username | empty (no auth) | `username` |
| `PROXY_PASS` | HTTP proxy password | empty (no auth) | `password` |
| `IMAGE_SAVE_DIR` | Image save directory | `src/static/images` | `/data/images` |
| `IMAGE_LOCALIZATION` | Enable local image storage | `False` | `True` |
| `ADMIN_KEY` | Admin API key (password for admin panel) | `sk-123456` | `sk-youradminkey` |
| `API_AUTH_TOKEN` | API auth token (key used by clients) | empty | `your-auth-token` |
| `VERBOSE_LOGGING` | Enable verbose logs | `False` | `True` |

## API Key Configuration

API keys use JSON format. Each key has:

- `key`: Sora auth token (must include `Bearer` prefix)
- `weight`: Polling weight; higher value increases selection probability
- `max_rpm`: Max requests per minute (rate limit)

Example:
```json
[
  {
    "key": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9...",
    "weight": 1,
    "max_rpm": 60
  },
  {
    "key": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9...",
    "weight": 2,
    "max_rpm": 60
  }
]
```

## Usage Examples

### Using curl

```bash
# Text-to-image (non-streaming)
curl -X POST http://localhost:8890/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "sora-1.0",
    "messages": [
      {"role": "user", "content": "Generate a golden retriever running on the grass"}
    ],
    "n": 1,
    "stream": false
  }'

# Text-to-image (streaming)
curl -X POST http://localhost:8890/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "sora-1.0",
    "messages": [
      {"role": "user", "content": "Generate a golden retriever running on the grass"}
    ],
    "n": 1,
    "stream": true
  }'

# Check async task status
curl -X GET http://localhost:8890/v1/generation/chatcmpl-123456789abcdef \
  -H "Authorization: Bearer your-api-key"
```

## Troubleshooting

1. **Connection timeouts or failures**
   - Verify proxy configuration
   - If using proxy auth, confirm username/password
   - Ensure the Sora service is reachable
   - Check local network connectivity

2. **Failed to load API keys**
   - Validate the `api_keys.json` format
   - Check that the `API_KEYS` env var is set correctly
   - Inspect logs for errors

3. **Image generation failed**
   - Ensure Sora token is valid
   - Check error logs
   - Verify account quota/limits

4. **Docker container fails to start**
   - Check for port conflicts
   - Ensure environment variables are correct
   - Review Docker logs for errors
   
5. **Difference between `API_AUTH_TOKEN` and `ADMIN_KEY`**
   - `API_AUTH_TOKEN`: The token your client (e.g., Cheery Studio or NewAPI) uses to call this API
   - `ADMIN_KEY`: The admin panel login password
   - If `API_AUTH_TOKEN` is not set, it defaults to the value of `ADMIN_KEY`
   
6. **Purpose of `BASE_URL`**
   - Used when image localization is enabled. Some clients cannot access Sora, so images are localized; `BASE_URL` defines the URL prefix for localized images.
   
6. **Invalid token**
   - Tokens used for the first time may require setting a username. Use the script below to batch set usernames:
 ```python
import random
import string
import logging
import cloudscraper

# Configure logging
tlogging = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Configuration ---
PROXY = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}
PROFILE_API = "https://sora.chatgpt.com/backend/me"
TOKENS_FILE = "tokens.txt"          # One Bearer token per line
RESULTS_FILE = "update_results.txt" # Save update results
USERNAME_LENGTH = 8                  # Random username length

# --- Utilities ---
def random_username(length: int = USERNAME_LENGTH) -> str:
    """Generate a random lowercase username"""
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def sanitize_headers(headers: dict) -> dict:
    """
    Remove all non-Latin-1 characters to ensure headers can be encoded by the HTTP library.
    """
    new = {}
    for k, v in headers.items():
        if isinstance(v, str):
            new[k] = v.encode('latin-1', 'ignore').decode('latin-1')
        else:
            new[k] = v
    return new


class SoraBatchUpdater:
    def __init__(self, proxy: dict = None):
        self.proxy = proxy or {}

    def update_username_for_token(self, token: str) -> tuple[bool, str]:
        """
        For a single Bearer token, generate a random username and send an update request.
        Returns (success, message).
        """
        scraper = cloudscraper.create_scraper()
        if self.proxy:
            scraper.proxies = self.proxy

        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
        headers = sanitize_headers(headers)

        new_username = random_username()
        payload = {"username": new_username}

        try:
            resp = scraper.post(
                PROFILE_API,
                headers=headers,
                json=payload,
                allow_redirects=False,
                timeout=15
            )
            status = resp.status_code
            if resp.ok:
                msg = f"OK ({new_username})"
                logging.info("Token %s: updated to %s", token[:6], new_username)
                return True, msg
            else:
                text = resp.text.replace('\n', '')
                msg = f"Failed {status}: {text}"  # Brief error message
                logging.warning("Token %s: %s", token[:6], msg)
                return False, msg
        except Exception as e:
            msg = str(e)
            logging.error("Token %s exception: %s", token[:6], msg)
            return False, msg

    def batch_update(self, tokens: list[str]) -> None:
        """
        Batch update usernames for a list of Bearer tokens and write results to RESULTS_FILE.
        """
        results = []
        for token in tokens:
            success, message = self.update_username_for_token(token)
            results.append((token, success, message))

        # Write results
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            for token, success, msg in results:
                status = 'SUCCESS' if success else 'ERROR'
                f.write(f"{token} ---- {status} ---- {msg}\n")
        logging.info("Batch update complete. Results saved to %s", RESULTS_FILE)


def load_tokens(filepath: str) -> list[str]:
    """Load a list of tokens from file (one per line)"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.error("Tokens file not found: %s", filepath)
        return []


if __name__ == '__main__':
    tokens = load_tokens(TOKENS_FILE)
    if not tokens:
        logging.error("No tokens to update. Exiting.")
    else:
        updater = SoraBatchUpdater(proxy=PROXY)
        updater.batch_update(tokens)

```


## Performance Optimizations

The latest version includes:

1. **Refactoring**: Simplified structure for readability and maintainability
2. **Memory optimizations**: Reduced unnecessary memory usage; improved large image handling
3. **Async processing**: Fully async flows for better concurrency
4. **Error handling**: Improved error handling and logging
5. **Key management**: Optimized key rotation algorithm for reliability
6. **Container**: Enhanced Docker config with healthcheck

## Contributing

Issues and PRs are welcome!

## License

MIT
