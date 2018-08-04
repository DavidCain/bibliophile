# Importing grequests will monkeypatch SSL
# Recursion errors occur if this import does not come before module imports
import grequests  # NoQA
