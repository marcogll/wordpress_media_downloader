import os
import sys
import json
import time
import requests
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv


def load_env_config():
    """Load configuration from .env file if it exists."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        return True
    return False


def prompt_input(prompt_text, default=None, required=True):
    """Prompt user for input with optional default value."""
    if default:
        full_prompt = f"{prompt_text} [{default}]: "
    else:
        full_prompt = f"{prompt_text}: "

    value = input(full_prompt).strip()

    if not value and default:
        return default
    if not value and required:
        print("  This field is required.")
        return prompt_input(prompt_text, default, required)
    return value


def get_config():
    """Get configuration from env or interactive prompts."""
    has_env = load_env_config()

    if has_env and os.getenv("WP_SITE_URL"):
        print("Configuration loaded from .env file.\n")
        site_url = os.getenv("WP_SITE_URL", "").rstrip("/")
        username = os.getenv("WP_USERNAME", "")
        app_password = os.getenv("WP_APP_PASSWORD", "")
        download_dir = os.getenv("DOWNLOAD_DIR", "./downloads")
        save_metadata = os.getenv("SAVE_METADATA", "true").lower() == "true"
        preserve_structure = os.getenv("PRESERVE_STRUCTURE", "true").lower() == "true"
    else:
        print("=" * 60)
        print("  WordPress Media Downloader")
        print("=" * 60)
        print()

        site_url = prompt_input("Site URL (e.g. https://yoursite.com)", required=True)
        site_url = site_url.rstrip("/")

        print()
        print("Authentication (Application Password recommended):")
        print("  Create one at: WP Admin > Users > Profile > Application Passwords")
        print()

        username = prompt_input("Username", required=True)
        app_password = prompt_input("Application Password", required=True)

        print()
        download_dir = prompt_input("Download directory", default="./downloads")
        save_metadata = prompt_input("Save metadata JSON? (true/false)", default="true")
        preserve_structure = prompt_input("Preserve year/month folder structure? (true/false)", default="true")

        save_metadata = save_metadata.lower() == "true"
        preserve_structure = preserve_structure.lower() == "true"

        print()
        save_env = input("Save these settings to .env file? (y/n) [n]: ").strip().lower()
        if save_env == "y":
            save_env_file(site_url, username, app_password, download_dir, save_metadata, preserve_structure)

    return {
        "site_url": site_url,
        "username": username,
        "app_password": app_password,
        "download_dir": Path(download_dir),
        "save_metadata": save_metadata,
        "preserve_structure": preserve_structure,
    }


def save_env_file(site_url, username, app_password, download_dir, save_metadata, preserve_structure):
    """Save configuration to .env file."""
    env_content = f"""# WordPress Media Downloader Configuration
# Copy this file to .env and fill in your details

WP_SITE_URL={site_url}
WP_USERNAME={username}
WP_APP_PASSWORD={app_password}
DOWNLOAD_DIR={download_dir}
SAVE_METADATA={str(save_metadata).lower()}
PRESERVE_STRUCTURE={str(preserve_structure).lower()}
"""
    env_path = Path(__file__).parent / ".env"
    env_path.write_text(env_content)
    print(f"  Settings saved to {env_path}")


def verify_connection(config):
    """Verify connection to WordPress site."""
    url = f"{config['site_url']}/wp-json/wp/v2/media?per_page=1"

    try:
        response = requests.get(
            url,
            auth=(config["username"], config["app_password"]),
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        print(f"\nError: Cannot connect to {config['site_url']}")
        print("  Check that the URL is correct and the site is accessible.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\nError: Connection timed out.")
        sys.exit(1)

    if response.status_code == 401:
        print("\nError: Authentication failed (401 Unauthorized).")
        print("  Check your username and application password.")
        print("  Make sure Application Passwords are enabled for your user.")
        sys.exit(1)
    elif response.status_code == 403:
        print("\nError: Access forbidden (403).")
        print("  Your user may not have permission to access the media library.")
        sys.exit(1)
    elif response.status_code != 200:
        print(f"\nError: Unexpected response (HTTP {response.status_code})")
        print(f"  Response: {response.text[:200]}")
        sys.exit(1)

    # Check X-WP-Total header
    total = int(response.headers.get("X-WP-Total", 0))
    print(f"  Connected successfully! Found {total} media items.")
    return total


def get_file_path(media_item, download_dir, preserve_structure):
    """Determine the local file path for a media item."""
    source_url = media_item.get("source_url", "")
    if not source_url:
        # Fallback to guid
        source_url = media_item.get("guid", {}).get("rendered", "")

    if not source_url:
        return None, None

    parsed = urlparse(source_url)
    filename = Path(parsed.path).name

    if not filename:
        return None, None

    if preserve_structure:
        # Try to extract year/month from the URL
        path_parts = Path(parsed.path).parts
        year_month = None
        for i, part in enumerate(path_parts):
            if part == "uploads" and i + 2 < len(path_parts):
                year_month = f"{path_parts[i+1]}/{path_parts[i+2]}"
                break

        if year_month:
            local_path = download_dir / year_month / filename
        else:
            local_path = download_dir / filename
    else:
        local_path = download_dir / filename

    return local_path, filename


def download_media(config, total_count):
    """Download all media items from WordPress."""
    download_dir = config["download_dir"]
    download_dir.mkdir(parents=True, exist_ok=True)

    per_page = 100
    total_pages = (total_count + per_page - 1) // per_page

    downloaded = 0
    skipped = 0
    errors = 0
    error_list = []

    for page in range(1, total_pages + 1):
        url = f"{config['site_url']}/wp-json/wp/v2/media"
        params = {"per_page": per_page, "page": page, "orderby": "id", "order": "asc"}

        try:
            response = requests.get(
                url,
                params=params,
                auth=(config["username"], config["app_password"]),
                timeout=60,
            )
        except requests.exceptions.RequestException as e:
            print(f"\n  Error fetching page {page}: {e}")
            errors += 1
            continue

        if response.status_code != 200:
            print(f"\n  Error fetching page {page}: HTTP {response.status_code}")
            errors += 1
            continue

        media_items = response.json()

        if not media_items:
            break

        for item in media_items:
            local_path, filename = get_file_path(item, download_dir, config["preserve_structure"])

            if not local_path or not filename:
                skipped += 1
                continue

            if local_path.exists():
                skipped += 1
                continue

            # Get the actual media file URL
            media_url = item.get("source_url", "")
            if not media_url:
                media_url = item.get("guid", {}).get("rendered", "")

            if not media_url:
                skipped += 1
                continue

            # Create directory if needed
            local_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                file_response = requests.get(media_url, timeout=120, stream=True)
                file_response.raise_for_status()

                with open(local_path, "wb") as f:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        f.write(chunk)

                downloaded += 1

                # Save metadata if enabled
                if config["save_metadata"]:
                    meta_path = local_path.with_suffix(local_path.suffix + ".json")
                    metadata = {
                        "id": item.get("id"),
                        "title": item.get("title", {}).get("rendered", ""),
                        "description": item.get("description", {}).get("rendered", ""),
                        "caption": item.get("caption", {}).get("rendered", ""),
                        "alt_text": item.get("alt_text", ""),
                        "mime_type": item.get("mime_type", ""),
                        "media_type": item.get("media_type", ""),
                        "source_url": item.get("source_url", ""),
                        "date": item.get("date", ""),
                        "modified": item.get("modified", ""),
                        "author": item.get("author"),
                        "media_details": item.get("media_details", {}),
                    }
                    with open(meta_path, "w") as f:
                        json.dump(metadata, f, indent=2)

                # Progress output
                current = downloaded + skipped + errors
                progress = (current / total_count) * 100
                print(f"\r  [{current}/{total_count}] ({progress:.1f}%) Downloaded: {downloaded} | Skipped: {skipped} | Errors: {errors}", end="", flush=True)

            except requests.exceptions.RequestException as e:
                errors += 1
                error_list.append({"file": filename, "error": str(e)})
            except OSError as e:
                errors += 1
                error_list.append({"file": filename, "error": str(e)})

    print()  # New line after progress
    return downloaded, skipped, errors, error_list


def main():
    """Main entry point."""
    config = get_config()

    print(f"\nSite: {config['site_url']}")
    print(f"Download to: {config['download_dir'].resolve()}")
    print(f"Save metadata: {'Yes' if config['save_metadata'] else 'No'}")
    print(f"Preserve structure: {'Yes' if config['preserve_structure'] else 'No'}")
    print()

    print("Verifying connection...")
    total_count = verify_connection(config)

    if total_count == 0:
        print("\nNo media items found in the library.")
        return

    print(f"\nStarting download of {total_count} media items...")
    print("-" * 60)

    start_time = time.time()
    downloaded, skipped, errors, error_list = download_media(config, total_count)
    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print("  Download Complete!")
    print("=" * 60)
    print(f"  Downloaded:  {downloaded}")
    print(f"  Skipped:     {skipped} (already exists)")
    print(f"  Errors:      {errors}")
    print(f"  Time:        {elapsed:.1f}s")
    print(f"  Location:    {config['download_dir'].resolve()}")
    print()

    if error_list:
        print("  Errors:")
        for err in error_list[:10]:
            print(f"    - {err['file']}: {err['error']}")
        if len(error_list) > 10:
            print(f"    ... and {len(error_list) - 10} more")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user.")
        sys.exit(0)
