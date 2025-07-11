# Testing Scripts

This directory contains helper scripts for running load tests against a Press instance.

## http_load_test.py

`http_load_test.py` uses the `requests` library so it can be executed outside a Frappe bench. It sends concurrent HTTP requests to create sites and can optionally archive them once done.

### Prerequisites

- Python 3.10+
- Install dependencies:
  ```bash
  pip install requests click
  ```

### Usage

Run the script with your Press base URL and API token:

```bash
python http_load_test.py \
    --base-url https://press.example.com \
    --token YOUR_API_TOKEN \
    --count 10 \
    --concurrency 5 \
    --cleanup
```

Key options:

- `--saas` – use the SaaS site creation API.
- `--site-template` – JSON payload template for the site.
- `--cleanup` – archive created sites after the test.

See `python http_load_test.py --help` for all options.
