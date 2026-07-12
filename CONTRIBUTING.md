# Contributing

Use fictional fixtures only. Pull requests must pass tests and the privacy scan. Never contribute personal notes, credentials, company names, internal paths, email addresses, or sanitized copies that retain real metadata.

```bash
pip install -e .
python -m unittest discover -s tests
python scripts/privacy_scan.py .
```

Architecture changes should include benchmark evidence. A retrieval change is not an improvement merely because one example looks better.
