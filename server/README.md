# Shorts Studio cloud server

Google sign-in, plus each user's library synced between computers. The file list is stored in MySQL and the file
contents in S3-compatible storage (Cloudflare R2 by default: 10 GB free, free downloads). The desktop app talks only to this server, never to the database.

## 1. Google OAuth client
Go to Google Cloud Console → APIs & Services:
- **OAuth consent screen**: External, scopes `openid email profile`.
- **Credentials → Create OAuth client ID → Desktop app**.

Copy the client ID and secret. The secret goes only on the server.

## 2. File storage (Cloudflare R2)
In the Cloudflare dashboard, go to **R2 → Create bucket** (for example `shorts-studio-library`; buckets are private).
Then go to **R2 → Manage API tokens → Create token** with *Object Read & Write* on that bucket, and copy:
- the Access Key ID → `S3_KEY`
- the Secret Access Key → `S3_SECRET`
- the endpoint `https://<account id>.r2.cloudflarestorage.com` → `S3_ENDPOINT`

To use DO Spaces or Backblaze B2 instead, put their endpoint, key and region in the same settings.

## 3. Run
```sh
pip install -r server/requirements.txt
cp server/.env.example server/.env   # then fill it in: the server reads it on start
uvicorn server.main:app --host 0.0.0.0 --port 8080
```
The tables (`users`, `sessions`, `files`) are created on the first start. Serve the API over HTTPS (DO App Platform
does this for you). In the database's **Trusted sources**, allow only this server.

## 4. Desktop app
In the data folder's `.env`, set `CLOUD_URL=https://<your server>` and `GOOGLE_CLIENT_ID=...`. Then open
Settings → Account → Sign in with Google.
