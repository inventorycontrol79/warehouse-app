import streamlit as st
import pandas as pd
import gspread

# 1. Clean the Private Key by removing potential formatting issues
RAW_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDmaG3IMtE1Fg1T
2D3q9rli6KWNsMFulrIofEYhUzkY6e9JEsVaiSTgH/1luEsbGjwc+HLFRrWyXUHh
R2LO0REo8DGz2Nm0oaoREJc7VxXqmEcZKhagb3cdnd13SHGCWOksumyFrUHdCEAt
+aBmnGvBatpxWFO9G6bllcumo8p7MI9O024q1m1nGPTzf1Bo10O6nQHhjYYYno1c
WStVSdO7zPNCHl915jgjrwajLrb6mwEbBb+ioN7rA39D3dG3RhvLXse0J6K31MQy
+OwbDkn431pqr5/UJBfBEbrESdAtVzdf8ZmjHasK0j66H76SVJlfbr74aIfC8hVV
TEZbz7hDAgMBAAECggEACJQKwlFiCJ/xjxWV+JGHBW+z+jqCeSOTLn6x/bujfJH5
HrdcMaq5fL60KH1cDn5DjrCRVVb0nNdsBH8r5pdSFDwdHZ0NPfRm6Iu9lbAAWOOi
ggVXIlIEFU4zWKWR1FCLHecy8ycoNJqCCTQqDKf2OxVHXMD1HS1SYWnaUzH17/Ak
zmj2f2Ok9NGR7Qc/cuwzg4LKTJ8e1l/O6vXCbUdnHBLoDYlUfIyextT5QfHmiAEI
qfDFZDAqeokmEdN8sdfj7dQn0wQljaqXyBGul0H/1aXQKw4GFfe2ebcdK63iG0vo
DQTI3A2nPy//b2J3oG9M2amz3J8Z3b8f6ENmTQyDQQKBgQD5h6VE1lIO/GqEyqdN
KtACBcmaxkon4PkndhNHtN0JpEjjryoj2MiopsK/fYBe2ZwzSBHSvIpxpObacNvs
4F4VQkQjPCmrCmcYXOez4vAof37/wnnoYSoStRlFHvyTex4jGu8f4IhVxCoqYGPr
bt7C6hiHaStmrRog155q0pc4rQKBgQDsYdqNLNfY6ZO1+ODGlO/rSLpzwiTJ6pGJ
s2vvDwbEsOeChIpDY+yHklo4/eaHxY1sJeW6BI9uq0q+iCR2U3zSvEuSFw0EE9Ak
nbCgFwowuGfAcdFw07pdZq7LpLqI+QEfWD5+n1gtVm4J0Gb5yTzgC17EgO9U1j3HN
GyD/lK0irwKBgFhpxJhIbBjdPQzCFVdVRRCCZnWNrrbEkuN1hc1Re0QwTpdF+GNt
K2P+emCJIlP5PMw6y/3kShWMPTPG61XaBdv4d9YYOhddfzv1py9oyHlA+4m5qaI5
00N/oW2JVisXY41CvNmJoCTrdZlAQAcqaImdkoVgMT2XNfvPClWFOomdAoGAHrOW
7z8jyciMptXsW958StLnZKGSpacRwBDNs/7/ogxYBVuxmY8g6XrYvQ49IuVFuQYz
EDYHaxhUXOrR0YyGadiK+C6GQkFQh2qEyDq8ekBkL03tq/JRNhRW6HJmIC+5JNRi
qCnkzvmjt/CgC7i+TaA2ITmkN5Cp9znOz2NAGYECgYA4QLya7qec93zWToggleOD7U
AditmgFkZxAcma83dvTVEOUox3KSKZZ+HetDfH2qf+SQaBLSA/ew/61c1VMRRgF/
DlQfhPGUst2mLtP7Moth+PHncZAbxTNPn/Ab+9p9YJA4BXg72dnZHSVD6Z1gV9C1
R3bbV3G5a0QPUPF2mVdtFA==
-----END PRIVATE KEY-----"""

# 2. Setup the credentials dictionary
creds = {
    "type": "service_account",
    "project_id": "sabin-erp-engine",
    "private_key_id": "0990e08a6dbe187eb04ecafdf7700e18cbcc0603",
    "private_key": RAW_KEY,
    "client_email": "sabin-bot@sabin-erp-engine.iam.gserviceaccount.com",
    "client_id": "102532041684182521279",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/sabin-bot%40sabin-erp-engine.iam.gserviceaccount.com"
}

st.title("SABIN ERP")

try:
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1nfD90CqHeb0TFSbivR9_rvoBlECJ37FgA5j-2G2Eyzc/edit")
    df = pd.DataFrame(sh.get_worksheet(0).get_all_records())
    st.dataframe(df)
except Exception as e:
    st.error(f"If you see this, tell me the exact text: {e}")