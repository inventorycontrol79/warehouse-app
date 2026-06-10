import streamlit as st
import pandas as pd
import gspread
import json

# --- HARD-CODED CREDENTIALS (BYPASSING SECRETS MANAGER) ---
# Paste your JSON object here exactly as you have it
CREDS_DICT = {
    "type": "service_account",
    "project_id": "sabin-erp-engine",
    "private_key_id": "0990e08a6dbe187eb04ecafdf7700e18cbcc0603",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDmaG3IMtE1Fg1T\n2D3q9rli6KWNsMFulrIofEYhUzkY6e9JEsVaiSTgH/1luEsbGjwc+HLFRrWyXUHh\nR2LO0REo8DGz2Nm0oaoREJc7VxXqmEcZKhagb3cdnd13SHGCWOksumyFrUHdCEAt\n+aBmnGvBatpxWFO9G6bllcumo8p7MI9O024q1m1nGPTzf1Bo10O6nQHhjYYYno1c\nWStVSdO7zPNCHl915jgjrwajLrb6mwEbBb+ioN7rA39D3dG3RhvLXse0J6K31MQy\n+OwbDkn431pqr5/UJBfBEbrESdAtVzdf8ZmjHasK0j66H76SVJlfbr74aIfC8hVV\nTEZbz7hDAgMBAAECggEACJQKwlFiCJ/xjxWV+JGHBW+z+jqCeSOTLn6x/bujfJH5\nHrdcMaq5fL60KH1cDn5DjrCRVVb0nNdsBH8r5pdSFDwdHZ0NPfRm6Iu9lbAAWOOi\nggVXIlIEFU4zWKWR1FCLHecy8ycoNJqCCTQqDKf2OxVHXMD1HS1SYWnaUzH17/Ak\nzmj2f2Ok9NGR7Qc/cuwzg4LKTJ8e1l/O6vXCbUdnHBLoDYlUfIyextT5QfHmiAEI\nqfDFZDAqeokmEdN8sdfj7dQn0wQljaqXyBGul0H/1aXQKw4GFfe2ebcdK63iG0vo\nDQTI3A2nPy//b2J3oG9M2amz3J8Z3b8f6ENmTQyDQQKBgQD5h6VE1lIO/GqEyqdN\nKtACBcmaxkon4PkndhNHtN0JpEjjryoj2MiopsK/fYBe2ZwzSBHSvIpxpObacNvs\n4F4VQkQjPCmrCmcYXOez4vAof37/wnnoYSoStRlFHvyTex4jGu8f4IhVxCoqYGPr\nbt7C6hiHaStmrRog155q0pc4rQKBgQDsYdqNLNfY6ZO1+ODGlO/rSLpzwiTJ6pGJ\ns2vvDwbEsOeChIpDY+yHklo4/eaHxY1sJeW6BI9uq0q+iCR2U3zSvEuSFw0EE9Ak\nbCgFwowuGfAcdFw07pdZq7LpLqI+QEfWD5+n1gtVm4J0Gb5yTzgC17EgO9U1j3HN\nGyD/lK0irwKBgFhpxJhIbBjdPQzCFVdVRRCCZnWNrrbEkuN1hc1Re0QwTpdF+GNt\nK2P+emCJIlP5PMw6y/3kShWMPTPG61XaBdv4d9YYOhddfzv1py9oyHlA+4m5qaI5\n00N/oW2JVisXY41CvNmJoCTrdZlAQAcqaImdkoVgMT2XNfvPClWFOomdAoGAHrOW\n7z8jyciMptXsW958StLnZKGSpacRwBDNs/7/ogxYBVuxmY8g6XrYvQ49IuVFuQYz\nEDYHaxhUXOrR0YyGadiK+C6GQkFQh2qEyDq8ekBkL03tq/JRNhRW6HJmIC+5JNRi\nqCnkzvmjt/CgC7i+TaA2ITmkN5Cp9znOz2NAGYECgYA4QLya7qec93zWToggleOD7U\nAditmgFkZxAcma83dvTVEOUox3KSKZZ+HetDfH2qf+SQaBLSA/ew/61c1VMRRgF/\nDlQfhPGUst2mLtP7Moth+PHncZAbxTNPn/Ab+9p9YJA4BXg72dnZHSVD6Z1gV9C1\nR3bbV3G5a0QPUPF2mVdtFA==\n-----END PRIVATE KEY-----",
    "client_email": "sabin-bot@sabin-erp-engine.iam.gserviceaccount.com",
    "client_id": "102532041684182521279",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/sabin-bot%40sabin-erp-engine.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

@st.cache_resource
def get_gc():
    # Explicitly use the dict with no parsing step
    return gspread.service_account_from_dict(CREDS_DICT)

def load_data():
    gc = get_gc()
    # Ensure this is the correct URL for your now-converted Google Sheet
    sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1nfD90CqHeb0TFSbivR9_rvoBlECJ37FgA5j-2G2Eyzc/edit?gid=0#gid=0")
    return pd.DataFrame(sh.get_worksheet(0).get_all_records())