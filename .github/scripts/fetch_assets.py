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
    # Use generic UA for general HTTP downloads
    headers = {'User-Agent': 'Mozilla/5.0 (Pica-CI-Asset-Fetcher)'}
    token = os.environ.get("GITHUB_TOKEN")
    # Only send token if it's GitHub
    if "github.com" in url and token:
       headers["Authorization"] = f"token {token}"
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            with open(path, 'wb') as out_file:
                out_file.write(response.read())
        return True
    except Exception as e:
        print(f"Failed to download from {url}: {e}")
        return False

def fetch_github_assets(pkg_dir, build_config):
    source = build_config.get("source", {})
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
        return False

    target_release = None
    for r in releases:
        if r.get("prerelease") and not allow_prerelease:
            continue
        if tag_regex:
            if not re.match(tag_regex, r.get("tag_name", "")):
                continue
        target_release = r
        break

    if not target_release:
        print(f"No matching GitHub release found for {repo}")
        return False

    print(f"Matched GitHub release: {target_release['tag_name']}")
    
    assets_cfg = release_cfg.get("assets", [])
    matrix = build_config.get("build", {}).get("matrix", [])
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
                target_platform = fixed_target.get("platform")
                target_arch = fixed_target.get("arch")

                if capture_to:
                    for key, group_idx in capture_to.items():
                        val = match.group(int(group_idx))
                        if key == "arch": target_arch = val
                        elif key == "platform": target_platform = val

                if target_arch and not target_platform:
                    for m in matrix:
                        if m.get("arch") == target_arch:
                            target_platform = m.get("platform")
                            break
                
                if not target_platform: target_platform = "all"
                if not target_arch: target_arch = "all"

                dest_dir = os.path.join(pkg_dir, "binary", target_platform, target_arch)
                dest_path = os.path.join(dest_dir, a["name"])
                
                if download_file(a["browser_download_url"], dest_path):
                    found_any = True
                    found_this_asset_meta = True
        
        if not found_this_asset_meta and required:
            print(f"Required GitHub asset '{asset_regex}' not found.")
            return False

    return found_any

def fetch_http_template_assets(pkg_dir, build_config):
    source = build_config.get("source", {})
    url_template = source.get("url_template")
    if not url_template:
        print("Error: 'url_template' missing for http_template provider.")
        return False

    version = source.get("version", "latest")
    matrix = build_config.get("build", {}).get("matrix", [])
    if not matrix:
        print("Warning: No matrix defined for http_template fetch.")
        return False

    found_any = False
    for m in matrix:
        arch = m.get("arch")
        platform = m.get("platform", "all")
        if not arch: continue

        # Interpolate variables in URL
        url = url_template.replace("{arch}", arch).replace("{version}", version).replace("{platform}", platform)
        
        # Get filename from URL
        filename = url.split("/")[-1]
        dest_dir = os.path.join(pkg_dir, "binary", platform, arch)
        dest_path = os.path.join(dest_dir, filename)

        if download_file(url, dest_path):
            found_any = True
        else:
            print(f"Could not download asset for {arch} from {url}")
            # If a specific arch fails, we might want to continue or fail. 
            # For mirrors, some archs might be missing. We'll continue.

    return found_any

def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_assets.py <package_dir> [build_json_path]")
        sys.exit(1)
    
    pkg_dir = sys.argv[1]
    build_json_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(pkg_dir, "build.json")
    
    if not os.path.exists(build_json_path):
        print(f"Skipping: {build_json_path} not found.")
        return

    with open(build_json_path, 'r') as f:
        build_config = json.load(f)

    provider = build_config.get("source", {}).get("provider", "github")
    success = False

    if provider == "github":
        success = fetch_github_assets(pkg_dir, build_config)
    elif provider == "http_template":
        success = fetch_http_template_assets(pkg_dir, build_config)
    else:
        print(f"Unknown provider: {provider}")
        sys.exit(1)

    if not success:
        print("Fetch failed or no assets found.")
        # sys.exit(1) # Uncomment if strict failure is needed

if __name__ == "__main__":
    main()
