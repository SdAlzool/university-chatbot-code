import os
import base64
import requests
from config import GITHUB_TOKEN, GITHUB_REPO

def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

def list_repository_folders():
    """Return the top-level course folders in the configured GitHub repository."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
    response = requests.get(url, headers=github_headers(), timeout=20)
    if response.status_code != 200:
        return None
    entries = response.json()
    if not isinstance(entries, list):
        return []
    return sorted(entry["name"] for entry in entries if entry.get("type") == "dir")

def slugify_course_name(name):
    cleaned = name.strip().replace("/", "-").replace("\\", "-")
    return "-".join(cleaned.split())

def slugify_file_stem(file_name):
    base, _ = os.path.splitext(file_name)
    cleaned = base.strip().replace("/", "-").replace("\\", "-")
    cleaned = "-".join(cleaned.split())
    return cleaned or "file"

def list_course_files_with_sha(course_folder):
    if not course_folder or not course_folder.strip():
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{course_folder.strip()}"
    response = requests.get(url, headers=github_headers())
    if response.status_code != 200:
        return None
    entries = response.json()
    if not isinstance(entries, list):
        return []
    files = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == "file":
            files.append({"name": entry["name"], "sha": entry["sha"], "path": entry["path"]})
        elif entry.get("type") == "dir":
            sub_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{entry['path']}"
            sub_response = requests.get(sub_url, headers=github_headers())
            if sub_response.status_code != 200:
                continue
            sub_entries = sub_response.json()
            if not isinstance(sub_entries, list):
                continue
            for sub in sub_entries:
                if isinstance(sub, dict) and sub.get("type") == "file":
                    files.append({"name": sub["name"], "sha": sub["sha"], "path": sub["path"]})
    return files

def get_file_download_url_by_path(file_path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    response = requests.get(url, headers=github_headers())
    if response.status_code != 200:
        return None
    return response.json().get("download_url")

def get_file_sha_by_path(file_path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    response = requests.get(url, headers=github_headers())
    if response.status_code != 200:
        return None
    data = response.json()
    return data.get("sha") if isinstance(data, dict) else None

def download_file_bytes(file_path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    response = requests.get(
        url,
        headers={**github_headers(), "Accept": "application/vnd.github.raw"},
        timeout=60,
    )
    if response.status_code != 200:
        return None
    return response.content

def github_upload_file(course_folder, file_name, content_bytes, commit_message):
    subfolder = slugify_file_stem(file_name)
    file_path = f"{course_folder}/{subfolder}/{file_name}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    b64_content = base64.b64encode(content_bytes).decode()
    payload = {"message": commit_message, "content": b64_content}
    existing_sha = get_file_sha_by_path(file_path)
    if existing_sha:
        payload["sha"] = existing_sha
    response = requests.put(url, headers=github_headers(), json=payload)
    return response.status_code in (200, 201)

def github_delete_file(file_path, sha, commit_message):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    payload = {"message": commit_message, "sha": sha}
    response = requests.delete(url, headers=github_headers(), json=payload)
    return response.status_code == 200
