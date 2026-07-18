#!/usr/bin/env python3
"""
GitHub Release Creator for Nexus Driver v3.0.0
Automatically creates a GitHub release with assets using GitHub API
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any


class GitHubReleaseCreator:
    """Create GitHub releases via API"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get('GITHUB_TOKEN')
        if not self.token:
            print("⚠️  GITHUB_TOKEN не найден в environment variables")
            print("Для создания release нужен GitHub Personal Access Token")
            print("\nСоздайте token:")
            print("1. https://github.com/settings/tokens/new")
            print("2. Выберите: repo (full control)")
            print("3. Скопируйте token")
            print("\nИспользование:")
            print("  set GITHUB_TOKEN=your_token_here")
            print("  python create_github_release.py")
            sys.exit(1)
        
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def create_release(
        self,
        owner: str,
        repo: str,
        tag: str,
        name: str,
        body: str,
        draft: bool = False,
        prerelease: bool = False
    ) -> Dict[str, Any]:
        """Create a GitHub release"""
        
        url = f"{self.api_base}/repos/{owner}/{repo}/releases"
        
        data = {
            "tag_name": tag,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease
        }
        
        print(f"\n📦 Создание release {tag}...")
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 201:
            print(f"✅ Release создан успешно!")
            return response.json()
        else:
            print(f"❌ Ошибка создания release: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)
    
    def upload_asset(
        self,
        upload_url: str,
        file_path: Path,
        content_type: str = "application/zip"
    ) -> Dict[str, Any]:
        """Upload asset to release"""
        
        # Remove {?name,label} from upload_url
        upload_url = upload_url.split('{')[0]
        
        file_name = file_path.name
        print(f"📤 Загрузка {file_name}...")
        
        headers = {
            **self.headers,
            "Content-Type": content_type
        }
        
        with open(file_path, 'rb') as f:
            params = {"name": file_name}
            response = requests.post(
                upload_url,
                headers=headers,
                params=params,
                data=f
            )
        
        if response.status_code == 201:
            print(f"✅ {file_name} загружен успешно!")
            return response.json()
        else:
            print(f"❌ Ошибка загрузки {file_name}: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    
    def check_release_exists(self, owner: str, repo: str, tag: str) -> bool:
        """Check if release already exists"""
        
        url = f"{self.api_base}/repos/{owner}/{repo}/releases/tags/{tag}"
        response = requests.get(url, headers=self.headers)
        
        return response.status_code == 200


def main():
    """Main function"""
    
    print("=" * 70)
    print("  NEXUS DRIVER v3.0.0 - GitHub Release Creator")
    print("=" * 70)
    
    # Configuration
    OWNER = "Andrian0123"
    REPO = "Bober-drive"
    TAG = "v3.0.0"
    RELEASE_NAME = "Nexus Driver v3.0.0 — Unified Event-Driven Architecture"
    
    # Paths
    root_dir = Path(__file__).parent
    release_notes_path = root_dir / "RELEASE-NOTES-v3.0.0.md"
    dist_dir = root_dir / "dist"
    zip_file = dist_dir / "nexus-driver-v3.0.0.zip"
    sha256_file = dist_dir / "nexus-driver-v3.0.0.zip.sha256"
    
    # Validate files exist
    if not release_notes_path.exists():
        print(f"❌ Release notes не найдены: {release_notes_path}")
        sys.exit(1)
    
    if not zip_file.exists():
        print(f"❌ ZIP архив не найден: {zip_file}")
        sys.exit(1)
    
    if not sha256_file.exists():
        print(f"❌ SHA256 файл не найден: {sha256_file}")
        sys.exit(1)
    
    # Read release notes
    with open(release_notes_path, 'r', encoding='utf-8') as f:
        release_body = f.read()
    
    # Create API client
    creator = GitHubReleaseCreator()
    
    # Check if release already exists
    print(f"\n🔍 Проверка существования release {TAG}...")
    if creator.check_release_exists(OWNER, REPO, TAG):
        print(f"⚠️  Release {TAG} уже существует!")
        print(f"URL: https://github.com/{OWNER}/{REPO}/releases/tag/{TAG}")
        
        response = input("\nПересоздать release? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Отменено пользователем")
            sys.exit(0)
        
        # Delete existing release
        url = f"{creator.api_base}/repos/{OWNER}/{REPO}/releases/tags/{TAG}"
        delete_response = requests.delete(url, headers=creator.headers)
        if delete_response.status_code == 204:
            print("✅ Существующий release удалён")
        else:
            print(f"⚠️  Не удалось удалить существующий release: {delete_response.status_code}")
    
    # Create release
    release = creator.create_release(
        owner=OWNER,
        repo=REPO,
        tag=TAG,
        name=RELEASE_NAME,
        body=release_body,
        draft=False,
        prerelease=False
    )
    
    upload_url = release['upload_url']
    release_url = release['html_url']
    
    # Upload assets
    print("\n" + "=" * 70)
    print("  ЗАГРУЗКА ASSETS")
    print("=" * 70)
    
    # Upload ZIP
    creator.upload_asset(upload_url, zip_file, "application/zip")
    
    # Upload SHA256
    creator.upload_asset(upload_url, sha256_file, "text/plain")
    
    # Success
    print("\n" + "=" * 70)
    print("  ✅ RELEASE СОЗДАН УСПЕШНО!")
    print("=" * 70)
    print(f"\nRelease URL: {release_url}")
    print(f"Tag: {TAG}")
    print(f"Assets: 2 files uploaded")
    print(f"  - nexus-driver-v3.0.0.zip")
    print(f"  - nexus-driver-v3.0.0.zip.sha256")
    
    print("\n🎉 Nexus Driver v3.0.0 release готов!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
