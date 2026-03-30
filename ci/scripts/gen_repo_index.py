#!/usr/bin/env python3
import json
import os
import tarfile
import hashlib
import sys
import datetime

REPO_JSON_PATH = 'r/repo.json'

def calculate_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def parse_manifest(manifest_content):
    """Parses a simple key=value manifest to a dict."""
    data = {}
    for line in manifest_content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, val = line.split('=', 1)
            # Remove surrounding quotes if they exist
            val = val.strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            data[key.strip()] = val
    return data

def main():
    if len(sys.argv) < 2:
        print("Usage: gen_repo_index.py <path_to_pkg_tar_gz_1> [path_to_pkg_tar_gz_2 ...]")
        return # If no new packages, do nothing

    pkg_files = sys.argv[1:]
    
    # Load existing repo.json
    repo_meta = {
        "pica_protocol": 1,
        "schema": "pica-repo-index-v1",
        "repo_name": "Pica 官方社区软件源",
        "repo_desc": "Pica Official Community Software Source",
        "generated_at": ""
    }
    repo_packages = []
    
    if os.path.exists(REPO_JSON_PATH):
        with open(REPO_JSON_PATH, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    # Preserve existing meta and extract packages
                    repo_meta.update({k: v for k, v in data.items() if k != 'packages'})
                    repo_packages = data.get('packages', [])
                elif isinstance(data, list):
                    # Migration from old flat array
                    repo_packages = data
            except json.JSONDecodeError:
                pass
                
    if not isinstance(repo_packages, list):
        print(f"Warning: packages in {REPO_JSON_PATH} is not a JSON array, resetting.")
        repo_packages = []
        
    repo_map = {item.get('pkgname'): item for item in repo_packages if isinstance(item, dict) and 'pkgname' in item}

    os.makedirs('r', exist_ok=True)

    for pkg_filepath in pkg_files:
        if not os.path.exists(pkg_filepath):
            print(f"Skipping {pkg_filepath}, file not found.")
            continue
            
        filename = os.path.basename(pkg_filepath)
        sha256sum = calculate_sha256(pkg_filepath)
        
        manifest_data = {}
        try:
            with tarfile.open(pkg_filepath, 'r:gz') as tar:
                # Find manifest file. It might be in the root of the tar or under a dir.
                # Assuming it's named 'manifest'
                manifest_member = None
                for member in tar.getmembers():
                    if member.name.endswith('manifest'):
                        manifest_member = member
                        break
                
                if manifest_member:
                    f = tar.extractfile(manifest_member)
                    content = f.read().decode('utf-8')
                    manifest_data = parse_manifest(content)
                else:
                    print(f"Warning: No 'manifest' file found in {pkg_filepath}")
                    continue
        except Exception as e:
            print(f"Error reading {pkg_filepath}: {e}")
            continue

        pkgname = manifest_data.get('pkgname')
        if not pkgname:
            print(f"Warning: 'pkgname' not found in manifest of {pkg_filepath}")
            continue
            
        # Update or add package info
        manifest_data['filename'] = filename
        manifest_data['sha256'] = sha256sum
        
        repo_map[pkgname] = manifest_data
        print(f"Processed {filename} -> {pkgname} version {manifest_data.get('pkgver')}")

    # Write back the wrapped structured JSON
    repo_meta["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    repo_meta["packages"] = list(repo_map.values())
    
    with open(REPO_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(repo_meta, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully updated {REPO_JSON_PATH} with {len(repo_meta['packages'])} packages.")

if __name__ == '__main__':
    main()
