import os
import sys
import json
import re
import urllib.request

def fetch_json(url):
    print(f"Fetching {url}...")
    headers = {
        'User-Agent': 'Pica-CI-Asset-Fetcher',
        'Accept': 'application/vnd.github.v3+json'
    }
    # Pass GITHUB_TOKEN if available to avoid rate limits
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
        
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def download_file(url, path):
    print(f"Downloading {url} to {path}...")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Use headers for download as well in case of private repos, 
    # though usually browser_download_url is public
    headers = {'User-Agent': 'Pica-CI-Asset-Fetcher'}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
       headers["Authorization"] = f"token {token}"
    
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        with open(path, 'wb') as out_file:
            out_file.write(response.read())

def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_assets.py <package_dir> [build_json_path]")
        sys.exit(1)
    
    pkg_dir = sys.argv[1]
    if len(sys.argv) > 2:
        build_json_path = sys.argv[2]
    else:
        build_json_path = os.path.join(pkg_dir, "build.json")
    
    if not os.path.exists(build_json_path):
        print(f"No build.json found at {build_json_path}, skipping asset fetch.")
        return

    print(f"Processing {pkg_dir}...")
    with open(build_json_path, 'r') as f:
        build_config = json.load(f)

    source = build_config.get("source", {})
    if not source or source.get("provider") != "github":
        print("No GitHub source provider defined, skipping.")
        return

    repo = source.get("repo")
    release_cfg = source.get("release", {})
    tag_cfg = release_cfg.get("tag", {})
    tag_regex = tag_cfg.get("regex")
    allow_prerelease = release_cfg.get("allow_prerelease", False)

    # Fetch releases
    api_url = f"https://api.github.com/repos/{repo}/releases"
    try:
        releases = fetch_json(api_url)
    except Exception as e:
        print(f"Error fetching releases from {repo}: {e}")
        sys.exit(1)

    target_release = None
    for r in releases:
        # Check prerelease constraint
        if r.get("prerelease") and not allow_prerelease:
            continue
        # Check tag regex if specified
        if tag_regex:
            if not re.match(tag_regex, r.get("tag_name", "")):
                continue
        target_release = r
        break

    if not target_release:
        print(f"No matching release found for {repo} with regex {tag_regex}")
        sys.exit(1)

    print(f"Successfully matched release: {target_release['tag_name']}")

    assets_cfg = release_cfg.get("assets", [])
    matrix = build_config.get("build", {}).get("matrix", [])

    # Ensure binary directory is empty before starting to avoid stale assets
    binary_base = os.path.join(pkg_dir, "binary")
    
    found_any = False
    for asset_meta in assets_cfg:
        asset_regex = asset_meta.get("regex")
        capture_to = asset_meta.get("capture_to", {})
        fixed_target = asset_meta.get("target", {})
        required = asset_meta.get("required", True)

        found_this_asset_meta = False
        for a in target_release.get("assets", []):
            match = re.match(asset_regex, a["name"])
            if match:
                # Resolve target platform/arch
                target_platform = fixed_target.get("platform")
                target_arch = fixed_target.get("arch")

                # Override with capture groups if defined
                if capture_to:
                    for key, group_idx in capture_to.items():
                        val = match.group(int(group_idx))
                        if key == "arch":
                            target_arch = val
                        elif key == "platform":
                            target_platform = val

                # If we have an arch but no platform, look it up in the matrix
                if target_arch and not target_platform:
                    for m in matrix:
                        if m.get("arch") == target_arch:
                            target_platform = m.get("platform")
                            break
                
                # Fallbacks
                if not target_platform: target_platform = "all"
                if not target_arch: target_arch = "all"

                dest_dir = os.path.join(pkg_dir, "binary", target_platform, target_arch)
                dest_path = os.path.join(dest_dir, a["name"])
                
                try:
                    download_file(a["browser_download_url"], dest_path)
                    found_any = True
                    found_this_asset_meta = True
                except Exception as e:
                    print(f"Failed to download {a['name']}: {e}")
                    if required:
                        sys.exit(1)

        if not found_this_asset_meta and required:
            print(f"Required asset matching '{asset_regex}' was not found in release.")
            sys.exit(1)

    if not found_any:
        print("Warning: No assets were downloaded for this package.")

if __name__ == "__main__":
    main()
