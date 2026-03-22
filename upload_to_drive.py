"""
pome_neta_list.csv を Google Drive のルートフォルダにアップロードするスクリプト。
既存の同名ファイルがあれば上書き更新する。
"""

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# アップロード対象ファイル
SCRIPT_DIR = Path(__file__).parent
CSV_FILE = SCRIPT_DIR / "pome_neta_list.csv"

# OAuth スコープ（Drive ファイルへの読み書き）
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# 認証情報ファイルのパス
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"


def get_credentials() -> Credentials:
    """保存済みトークンを読み込む。なければ認証フローを実行して保存する。"""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"credentials.json が見つかりません: {CREDENTIALS_FILE}\n"
                    "Google Cloud Console からダウンロードして同じフォルダに置いてください。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"トークンを保存しました: {TOKEN_FILE}")

    return creds


def find_existing_file(service, filename: str) -> str | None:
    """Drive のルートフォルダに同名ファイルがあれば file_id を返す。"""
    query = (
        f"name = '{filename}' "
        f"and 'root' in parents "
        f"and trashed = false"
    )
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def upload_csv() -> None:
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"アップロード対象が見つかりません: {CSV_FILE}")

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    filename = CSV_FILE.name
    media = MediaFileUpload(str(CSV_FILE), mimetype="text/csv", resumable=False)

    existing_id = find_existing_file(service, filename)

    if existing_id:
        # 既存ファイルを上書き更新
        service.files().update(
            fileId=existing_id,
            media_body=media,
        ).execute()
        print(f"更新完了: {filename} (id={existing_id})")
    else:
        # 新規アップロード
        metadata = {"name": filename, "parents": ["root"]}
        result = service.files().create(
            body=metadata,
            media_body=media,
            fields="id",
        ).execute()
        print(f"アップロード完了: {filename} (id={result['id']})")


if __name__ == "__main__":
    upload_csv()
