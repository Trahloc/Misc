# Civit Downloader

A tool for downloading models from Civitai with custom filename patterns.

## Installation

```bash
# Install in development mode
pip install -e .
```

## Usage

```bash
# Download a model with custom naming
civit https://civitai.com/api/download/models/1609305?type=Model&format=SafeTensor

# Download with standard output (warnings and errors)
civit https://civitai.com/api/download/models/1609305

# Download with verbose logging
civit -v https://civitai.com/api/download/models/1609305

# Download with debug logging
civit -vv https://civitai.com/api/download/models/1609305
# or
civit --debug https://civitai.com/api/download/models/1609305

# Download with authentication (for premium or restricted models)
civit -k YOUR_CIVITAI_API_KEY https://civitai.com/api/download/models/1609305
# or set the CIVITAPI environment variable
export CIVITAPI=YOUR_CIVITAI_API_KEY
civit https://civitai.com/api/download/models/1609305

# Download silently (errors only)
civit -q https://civitai.com/api/download/models/1609305

# Specify output directory
civit -o /path/to/output https://civitai.com/api/download/models/1609305

# Download multiple files
civit URL1 URL2 URL3 -o /path/to/output
```

## Getting a Civitai API Key

1. Create an account on [Civitai](https://civitai.com/)
2. Go to your profile settings
3. Navigate to the API Keys section
4. Create a new API key with appropriate permissions
5. Use this key with the `-k` option or set the `CIVITAPI` environment variable

## Filename Pattern

By default, downloaded files use the following pattern:
