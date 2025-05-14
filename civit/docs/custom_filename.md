# Custom Filename Convention

## Overview

This feature allows users to set custom patterns for downloaded filenames using metadata from the civitai model.

## Usage

To use custom filename patterns, pass the `filename_pattern` and `metadata` parameters to the `download_file` function.

### Example

```python
url = "http://example.com/file.zip"
destination = "/tmp"
filename_pattern = "{model_type}-{base_model}-{civit_website_model_name}-{model_id}-{crc32}-{original_filename}"
metadata = {
    "model_type": "LORA",
    "base_model": "Illustrious",
    "civit_website_model_name": "illustrious",
    "model_id": "1373674"
}

filepath = download_file(url, destination, filename_pattern, metadata)
print(filepath)  # Output: /tmp/LORA-Illustrious-illustrious-1373674-5D110398-file.zip
```

## Placeholders

The following placeholders can be used in the filename pattern:

- `{model_type}`: The type of the model.
- `{base_model}`: The base model.
- `{civit_website_model_name}`: The name of the model on the civitai website.
- `{model_id}`: The ID of the model.
- `{crc32}`: The CRC32 checksum of the original filename.
- `{original_filename}`: The original filename.

## Sanitization

The filename is sanitized to ensure it is safe and valid. Invalid characters are replaced with underscores.
