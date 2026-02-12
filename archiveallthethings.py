#!/usr/bin/env python3
"""
Archive All The Things - The Thingiverse Thing Downloader

Downloads Things from Thingiverse including all files, images, and metadata.
Can download a single thing by ID or all published things by a user.

Usage:
    python archiveallthethings.py --thing 11190
    python archiveallthethings.py --user tbuser --output ./archive
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

API_BASE = "https://api.thingiverse.com"
DEFAULT_THROTTLE_SECONDS = 5.0
ENV_TOKEN_NAME = "THINGIVERSE_TOKEN"


def get_auth_token(token_arg=None):
    """
    Get authentication token from (in order of precedence):
    1. Command-line argument
    2. Environment variable THINGIVERSE_TOKEN
    """
    # 1. Command-line argument
    if token_arg:
        return token_arg

    # 2. Environment variable
    env_token = os.environ.get(ENV_TOKEN_NAME)
    if env_token:
        return env_token.strip()

    raise ValueError(
        f"No auth token found. Provide one via:\n"
        f"  1. --token argument\n"
        f"  2. {ENV_TOKEN_NAME} environment variable"
    )


def sanitize_filename(name, for_directory=False, for_image=False):
    """Convert a name to a safe directory/file name."""
    if for_directory or for_image:
        # Strip punctuation and special characters
        name = re.sub(r'[<>:"/\\|?*,;!@#$%^&()+=\[\]{}\'`~]', '', name)
        # Replace spaces with underscores and lowercase
        name = name.replace(' ', '_').lower()
    else:
        # Remove or replace invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing spaces and dots
    name = name.strip(' .')
    # Limit length
    if len(name) > 200:
        name = name[:200]
    return name


def api_get(endpoint, token, params=None):
    """Make a GET request to the Thingiverse API."""
    url = f"{API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def download_file(url, dest_path, token=None):
    """Download a file from a URL to the destination path."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return dest_path


def get_thing(thing_id, token):
    """Get Thing details from the API."""
    return api_get(f"/things/{thing_id}", token)


def get_thing_files(thing_id, token):
    """Get all files for a Thing."""
    return api_get(f"/things/{thing_id}/files", token)


def get_thing_images(thing_id, token):
    """Get all images for a Thing."""
    return api_get(f"/things/{thing_id}/images", token)


def get_thing_derivatives(thing_id, token):
    """Get remixes/derivatives of a Thing."""
    return api_get(f"/things/{thing_id}/derivatives", token)


def get_thing_makes(thing_id, token):
    """Get makes (prints) of a Thing."""
    return api_get(f"/things/{thing_id}/copies", token)


def get_thing_comments(thing_id, token):
    """Get comments for a Thing."""
    return api_get(f"/things/{thing_id}/comments", token)


def get_user_things(username, token):
    """Get all published things by a user."""
    things = []
    page = 1
    per_page = 30

    while True:
        params = {"page": page, "per_page": per_page}
        result = api_get(f"/users/{username}/things", token, params)

        if not result:
            break

        things.extend(result)

        if len(result) < per_page:
            break

        page += 1
        time.sleep(DEFAULT_THROTTLE_SECONDS)  # Throttle pagination requests

    return things


def create_readme(thing, files, images, derivatives, makes_count, comments_count, output_dir):
    """Create a README.md file with Thing metadata."""
    readme_path = output_dir / "README.md"

    with open(readme_path, "w", encoding="utf-8") as f:
        # Title
        f.write(f"# {thing.get('name', 'Unknown Thing')}\n\n")

        # Main image (if available)
        if images:
            first_image = images[0]
            image_name = first_image.get('_safe_name', '')
            if image_name:
                f.write(f"![{thing.get('name', 'Thing')}](images/{image_name})\n\n")

        # Metadata section
        f.write("## Metadata\n\n")
        f.write(f"- **Thing ID:** {thing.get('id')}\n")
        f.write(f"- **URL:** {thing.get('public_url', 'N/A')}\n")

        creator = thing.get('creator', {})
        if creator:
            creator_name = creator.get('name', creator.get('first_name', 'Unknown'))
            creator_url = creator.get('public_url', '')
            f.write(f"- **Creator:** [{creator_name}]({creator_url})\n")

        f.write(f"- **Added:** {thing.get('added', 'N/A')}\n")
        f.write(f"- **Modified:** {thing.get('modified', 'N/A')}\n")
        f.write(f"- **License:** {thing.get('license', 'N/A')}\n")
        f.write(f"- **Like Count:** {thing.get('like_count', 0)}\n")
        f.write(f"- **Download Count:** {thing.get('download_count', 0)}\n")
        f.write(f"- **View Count:** {thing.get('view_count', 0)}\n")
        f.write(f"- **Collect Count:** {thing.get('collect_count', 0)}\n")
        f.write(f"- **Comment Count:** {comments_count}\n")
        f.write(f"- **Makes Count:** {makes_count}\n")
        f.write(f"- **Remix Count:** {len(derivatives)}\n")

        # Tags
        tags = thing.get('tags', [])
        if tags:
            tag_names = [tag.get('name', '') for tag in tags if tag.get('name')]
            if tag_names:
                f.write(f"- **Tags:** {', '.join(tag_names)}\n")

        f.write("\n")

        # Description
        f.write("## Description\n\n")
        description = thing.get('description', 'No description available.')
        # Convert HTML to markdown-ish format
        description = re.sub(r'<br\s*/?>', '\n', description)
        description = re.sub(r'</?p>', '\n', description)
        description = re.sub(r'<[^>]+>', '', description)  # Remove remaining HTML tags
        f.write(f"{description}\n\n")

        # Instructions (if available)
        instructions = thing.get('instructions', '')
        if instructions:
            f.write("## Instructions\n\n")
            instructions = re.sub(r'<br\s*/?>', '\n', instructions)
            instructions = re.sub(r'</?p>', '\n', instructions)
            instructions = re.sub(r'<[^>]+>', '', instructions)
            f.write(f"{instructions}\n\n")

        # Ancestors section
        ancestors = thing.get('ancestors', [])
        if ancestors:
            f.write("## Ancestors\n\n")
            f.write("This thing is a remix of:\n\n")
            for ancestor in ancestors:
                name = ancestor.get('name', 'Unknown')
                url = ancestor.get('public_url', '')
                creator = ancestor.get('creator', {})
                creator_name = creator.get('name', creator.get('first_name', 'Unknown')) if creator else 'Unknown'
                f.write(f"- [{name}]({url}) by {creator_name}\n")
            f.write("\n")

        # Remixes section
        if derivatives:
            f.write("## Remixes\n\n")
            f.write("Things remixed from this:\n\n")
            for derivative in derivatives:
                name = derivative.get('name', 'Unknown')
                url = derivative.get('public_url', '')
                creator = derivative.get('creator', {})
                creator_name = creator.get('name', creator.get('first_name', 'Unknown')) if creator else 'Unknown'
                f.write(f"- [{name}]({url}) by {creator_name}\n")
            f.write("\n")

        # Files section
        f.write("## Files\n\n")
        if files:
            for file_info in files:
                file_name = file_info.get('name', 'unknown')
                file_size = file_info.get('size', 0)
                # Convert to human readable size
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024*1024):.2f} MB"
                elif file_size > 1024:
                    size_str = f"{file_size / 1024:.2f} KB"
                else:
                    size_str = f"{file_size} bytes"
                f.write(f"- [{file_name}](files/{file_name}) ({size_str})\n")
        else:
            f.write("No files available.\n")
        f.write("\n")

        # Images section
        f.write("## Images\n\n")
        if images:
            for img in images:
                safe_name = img.get('_safe_name', '')
                if safe_name:
                    img_name = img.get('name', 'image')
                    f.write(f"![{img_name}](images/{safe_name})\n\n")
        else:
            f.write("No images available.\n")

    return readme_path


def create_comments_file(thing, comments, output_dir):
    """Create a COMMENTS.md file with all comments."""
    comments_path = output_dir / "COMMENTS.md"

    with open(comments_path, "w", encoding="utf-8") as f:
        f.write(f"# Comments for {thing.get('name', 'Unknown Thing')}\n\n")
        f.write(f"**Thing URL:** {thing.get('public_url', 'N/A')}\n\n")
        f.write(f"**Total Comments:** {len(comments)}\n\n")
        f.write("---\n\n")

        if comments:
            for comment in comments:
                user = comment.get('user', {})
                user_name = user.get('name', user.get('first_name', 'Unknown'))
                user_url = user.get('public_url', '')
                added = comment.get('added', 'Unknown date')
                body = comment.get('body', '')

                # Clean up HTML in comment body
                body = re.sub(r'<br\s*/?>', '\n', body)
                body = re.sub(r'</?p>', '\n', body)
                body = re.sub(r'<[^>]+>', '', body)

                f.write(f"### [{user_name}]({user_url})\n")
                f.write(f"*{added}*\n\n")
                f.write(f"{body}\n\n")
                f.write("---\n\n")
        else:
            f.write("No comments yet.\n")

    return comments_path


def create_license_file(thing, output_dir):
    """Create a LICENSE.md file with license information."""
    license_path = output_dir / "LICENSE.md"

    license_name = thing.get('license', 'Unknown')
    thing_name = thing.get('name', 'Unknown Thing')
    thing_url = thing.get('public_url', '')
    creator = thing.get('creator', {})
    creator_name = creator.get('name', creator.get('first_name', 'Unknown')) if creator else 'Unknown'
    creator_url = creator.get('public_url', '') if creator else ''

    # Map common Thingiverse licenses to URLs
    license_urls = {
        'Creative Commons - Attribution': 'https://creativecommons.org/licenses/by/4.0/',
        'Creative Commons - Attribution - Share Alike': 'https://creativecommons.org/licenses/by-sa/4.0/',
        'Creative Commons - Attribution - No Derivatives': 'https://creativecommons.org/licenses/by-nd/4.0/',
        'Creative Commons - Attribution - Non-Commercial': 'https://creativecommons.org/licenses/by-nc/4.0/',
        'Creative Commons - Attribution - Non-Commercial - Share Alike': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
        'Creative Commons - Attribution - Non-Commercial - No Derivatives': 'https://creativecommons.org/licenses/by-nc-nd/4.0/',
        'Creative Commons - Public Domain Dedication': 'https://creativecommons.org/publicdomain/zero/1.0/',
        'GNU - GPL': 'https://www.gnu.org/licenses/gpl-3.0.en.html',
        'GNU - LGPL': 'https://www.gnu.org/licenses/lgpl-3.0.en.html',
        'BSD License': 'https://opensource.org/licenses/BSD-3-Clause',
    }

    license_url = license_urls.get(license_name, '')

    with open(license_path, "w", encoding="utf-8") as f:
        f.write("# License\n\n")
        f.write(f"## {thing_name}\n\n")
        f.write(f"**Thing URL:** [{thing_url}]({thing_url})\n\n")
        f.write(f"**Creator:** [{creator_name}]({creator_url})\n\n")
        f.write(f"**License:** {license_name}\n\n")

        if license_url:
            f.write(f"**License URL:** [{license_url}]({license_url})\n\n")

        f.write("---\n\n")

        # Add license summary based on type
        if 'Creative Commons' in license_name:
            f.write("## License Summary\n\n")
            f.write("This work is licensed under a Creative Commons license.\n\n")

            if 'Attribution' in license_name:
                f.write("- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made.\n")
            if 'Non-Commercial' in license_name or 'NonCommercial' in license_name:
                f.write("- **Non-Commercial** — You may not use the material for commercial purposes.\n")
            if 'Share Alike' in license_name or 'ShareAlike' in license_name:
                f.write("- **Share Alike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license.\n")
            if 'No Derivatives' in license_name or 'NoDerivatives' in license_name:
                f.write("- **No Derivatives** — If you remix, transform, or build upon the material, you may not distribute the modified material.\n")
            if 'Public Domain' in license_name:
                f.write("- **Public Domain** — The creator has waived all copyright and related rights. You can copy, modify, distribute and perform the work, even for commercial purposes, all without asking permission.\n")

            f.write(f"\nFor full license terms, see: {license_url}\n")
        elif 'GPL' in license_name:
            f.write("## License Summary\n\n")
            f.write("This work is licensed under the GNU General Public License.\n\n")
            f.write("You are free to use, modify, and distribute this work, but any derivative works must also be released under the GPL.\n")
            f.write(f"\nFor full license terms, see: {license_url}\n")
        elif 'BSD' in license_name:
            f.write("## License Summary\n\n")
            f.write("This work is licensed under the BSD License.\n\n")
            f.write("You are free to use, modify, and distribute this work with minimal restrictions.\n")
            f.write(f"\nFor full license terms, see: {license_url}\n")

    return license_path


def load_existing_metadata(output_dir):
    """Load existing metadata.json if it exists."""
    metadata_path = output_dir / "metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def download_thing(thing_id, token, output_base=None, force=False):
    """
    Download a complete Thing from Thingiverse.

    Args:
        thing_id: The Thingiverse Thing ID
        token: API authentication token
        output_base: Base directory for output (default: current directory)
        force: Force re-download even if unchanged

    Returns:
        Path to the created directory
    """
    if output_base is None:
        output_base = Path.cwd()
    else:
        output_base = Path(output_base)

    print(f"Fetching Thing {thing_id}...")

    # Get Thing details
    thing = get_thing(thing_id, token)
    thing_name = thing.get('name', f'thing_{thing_id}')
    print(f"  Name: {thing_name}")

    # Create output directory
    safe_name = sanitize_filename(thing_name, for_directory=True)
    output_dir = output_base / safe_name
    output_dir.mkdir(parents=True, exist_ok=True)

    files_dir = output_dir / "files"
    files_dir.mkdir(exist_ok=True)

    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # Check for existing metadata and compare modification times
    existing_metadata = load_existing_metadata(output_dir)
    thing_modified = thing.get('modified')

    if existing_metadata and not force:
        existing_thing = existing_metadata.get('thing', {})
        existing_modified = existing_thing.get('modified')

        if existing_modified and thing_modified and existing_modified == thing_modified:
            print(f"  Thing unchanged since last download (modified: {thing_modified})")
            print("  Skipping download. Use --force to re-download.")
            return output_dir

    # Get and download files
    print("Fetching files list...")
    try:
        files = get_thing_files(thing_id, token)
        print(f"  Found {len(files)} files")

        for i, file_info in enumerate(files, 1):
            file_name = file_info.get('name', f'file_{i}')
            download_url = file_info.get('download_url') or file_info.get('public_url')

            if download_url:
                dest = files_dir / sanitize_filename(file_name)
                # Skip if file already exists
                if dest.exists() and not force:
                    print(f"  Skipping (exists): {file_name}")
                    continue
                print(f"  Downloading: {file_name}")
                try:
                    download_file(download_url, dest, token)
                except Exception as e:
                    print(f"    Error downloading {file_name}: {e}")
            else:
                print(f"  No download URL for: {file_name}")
    except Exception as e:
        print(f"  Error fetching files: {e}")
        files = []

    # Get and download images
    print("Fetching images list...")
    try:
        images = get_thing_images(thing_id, token)
        print(f"  Found {len(images)} images")

        for i, img in enumerate(images, 1):
            img_name = img.get('name', f'image_{i}')

            # Try to get the largest available image
            sizes = img.get('sizes', [])
            download_url = None

            # Prefer display, then preview, then thumb
            for size_pref in ['display', 'preview', 'thumb']:
                for size_info in sizes:
                    if size_info.get('type') == size_pref and size_info.get('url'):
                        download_url = size_info['url']
                        break
                if download_url:
                    break

            # Fallback to direct URL
            if not download_url:
                download_url = img.get('url')

            if download_url:
                # Sanitize filename and ensure it has an extension
                safe_name = sanitize_filename(img_name, for_image=True)
                # Get extension from URL or default to .jpg
                url_path = urlparse(download_url).path
                url_ext = os.path.splitext(url_path)[1].lower()
                current_ext = os.path.splitext(safe_name)[1].lower()
                # Only consider valid image extensions
                valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
                if current_ext not in valid_extensions:
                    safe_name += url_ext if url_ext in valid_extensions else '.jpg'
                # Store sanitized name for README
                img['_safe_name'] = safe_name

                dest = images_dir / safe_name
                # Skip if file already exists
                if dest.exists() and not force:
                    print(f"  Skipping (exists): {safe_name}")
                    continue
                print(f"  Downloading: {safe_name}")
                try:
                    download_file(download_url, dest)
                except Exception as e:
                    print(f"    Error downloading {safe_name}: {e}")
            else:
                print(f"  No download URL for: {img_name}")
    except Exception as e:
        print(f"  Error fetching images: {e}")
        images = []

    # Get derivatives (remixes)
    print("Fetching remixes...")
    try:
        derivatives = get_thing_derivatives(thing_id, token)
        print(f"  Found {len(derivatives)} remixes")
    except Exception as e:
        print(f"  Error fetching remixes: {e}")
        derivatives = []

    # Get makes
    print("Fetching makes...")
    try:
        makes = get_thing_makes(thing_id, token)
        print(f"  Found {len(makes)} makes")
    except Exception as e:
        print(f"  Error fetching makes: {e}")
        makes = []

    # Get comments
    print("Fetching comments...")
    try:
        comments = get_thing_comments(thing_id, token)
        print(f"  Found {len(comments)} comments")
    except Exception as e:
        print(f"  Error fetching comments: {e}")
        comments = []

    # Save raw JSON metadata
    print("Saving metadata...")
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({
            "thing": thing,
            "files": files,
            "images": images,
            "derivatives": derivatives,
            "makes": makes,
            "comments": comments
        }, f, indent=2, default=str)

    # Create README
    print("Creating README.md...")
    create_readme(thing, files, images, derivatives, len(makes), len(comments), output_dir)

    # Create COMMENTS.md
    print("Creating COMMENTS.md...")
    create_comments_file(thing, comments, output_dir)

    # Create LICENSE.md
    print("Creating LICENSE.md...")
    create_license_file(thing, output_dir)

    print(f"\nDone! Thing downloaded to: {output_dir}")
    return output_dir


def download_user_things(username, token, output_dir, throttle=DEFAULT_THROTTLE_SECONDS, force=False):
    """Download all published things by a user."""
    print(f"Fetching things for user: {username}")

    try:
        things = get_user_things(username, token)
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching user things: {e}")
        return []

    if not things:
        print(f"No things found for user: {username}")
        return []

    print(f"Found {len(things)} things by {username}")

    downloaded = []
    for i, thing in enumerate(things, 1):
        thing_id = thing.get('id')
        thing_name = thing.get('name', f'thing_{thing_id}')

        print(f"\n[{i}/{len(things)}] Downloading: {thing_name} (ID: {thing_id})")

        try:
            result = download_thing(thing_id, token, output_dir, force=force)
            downloaded.append(result)
        except requests.exceptions.HTTPError as e:
            print(f"  Error downloading thing {thing_id}: {e}")
            if e.response is not None:
                print(f"  Response: {e.response.text}")
        except Exception as e:
            print(f"  Error downloading thing {thing_id}: {e}")

        # Throttle between downloads
        if i < len(things):
            print(f"  Waiting {throttle}s before next download...")
            time.sleep(throttle)

    print(f"\nCompleted: Downloaded {len(downloaded)} of {len(things)} things")
    return downloaded


def main():
    parser = argparse.ArgumentParser(
        description="Download Things from Thingiverse",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --thing 11190
  %(prog)s --user tbuser
  %(prog)s --thing 11190 --output ./downloads
  %(prog)s --thing 11190 --force              # Re-download even if unchanged
  %(prog)s --user tbuser --output ./downloads --throttle 2.0
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--thing", "-t",
        metavar="ID",
        help="Download a specific thing by ID"
    )
    group.add_argument(
        "--user", "-u",
        metavar="USERNAME",
        help="Download all published things by a user"
    )

    parser.add_argument(
        "--output", "-o",
        metavar="DIR",
        default=".",
        help="Output directory (default: current directory)"
    )

    parser.add_argument(
        "--throttle",
        type=float,
        default=DEFAULT_THROTTLE_SECONDS,
        metavar="SECONDS",
        help=f"Seconds to wait between downloads (default: {DEFAULT_THROTTLE_SECONDS})"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-download even if thing is unchanged"
    )

    parser.add_argument(
        "--token",
        metavar="TOKEN",
        help=f"Thingiverse API token (or set {ENV_TOKEN_NAME} env var)"
    )

    args = parser.parse_args()

    # Get auth token
    try:
        token = get_auth_token(args.token)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Create output directory if needed
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.thing:
            download_thing(args.thing, token, output_dir, force=args.force)
        elif args.user:
            download_user_things(args.user, token, output_dir, args.throttle, force=args.force)
    except requests.exceptions.HTTPError as e:
        print(f"API Error: {e}")
        if e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDownload interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
