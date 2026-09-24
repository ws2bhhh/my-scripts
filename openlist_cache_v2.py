import os
import sqlite3
import time

import requests

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
DB_FILE = "openlist_cache.db"
# Site URL and API token are now entered interactively from the console.
# Multiple sites are supported and stored in the local SQLite database.
# -------------------------------------------------------------------


def init_db():
    """Initializes the local SQLite cache database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Drop legacy single-site 'files' table if it lacks the 'site_id' column
    cursor.execute("PRAGMA table_info(files)")
    cols = [row[1] for row in cursor.fetchall()]
    if cols and "site_id" not in cols:
        print("[*] Legacy cache schema detected. Recreating 'files' table.")
        cursor.execute("DROP TABLE files")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            base_url TEXT NOT NULL UNIQUE,
            api_token TEXT DEFAULT ''
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            site_id INTEGER NOT NULL,
            path TEXT NOT NULL,
            name TEXT NOT NULL,
            size INTEGER,
            is_dir INTEGER,
            modified TEXT,
            PRIMARY KEY (site_id, path)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON files(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_path ON files(path)")
    conn.commit()
    conn.close()


# -------------------------------------------------------------------
# Site management
# -------------------------------------------------------------------
def add_site():
    """Adds a new site (or updates the token of an existing one)."""
    base_url = input("Enter site base URL (e.g., https://example.com): ").strip()
    if not base_url:
        print("[!] URL cannot be empty.")
        return

    api_token = input("Enter API token (leave empty if not required): ").strip()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sites WHERE base_url = ?", (base_url,))
    row = cursor.fetchone()
    if row:
        cursor.execute(
            "UPDATE sites SET api_token = ? WHERE id = ?", (api_token, row[0])
        )
        print(f"[+] Updated token for existing site (id={row[0]}).")
    else:
        cursor.execute(
            "INSERT INTO sites (base_url, api_token) VALUES (?, ?)",
            (base_url, api_token),
        )
        print(f"[+] Site added with id={cursor.lastrowid}.")
    conn.commit()
    conn.close()


def list_sites():
    """Returns all configured sites as a list of (id, base_url, api_token)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, base_url, api_token FROM sites ORDER BY id")
    sites = cursor.fetchall()
    conn.close()
    return sites


def select_site(prompt="Select a site"):
    """Interactive prompt to choose one of the configured sites."""
    sites = list_sites()
    if not sites:
        print("[!] No sites configured. Please add a site first.")
        return None

    print(f"\n{prompt}:")
    for sid, url, _ in sites:
        print(f"  {sid}. {url}")

    raw = input("Enter site ID (or press Enter to cancel): ").strip()
    if not raw:
        return None
    if not raw.isdigit():
        print("[!] Invalid input.")
        return None

    sid = int(raw)
    for s_id, url, token in sites:
        if s_id == sid:
            return s_id, url, token

    print("[!] Site not found.")
    return None


# -------------------------------------------------------------------
# OpenList API
# -------------------------------------------------------------------
def fetch_openlist_dir(base_url, api_token, path="/"):
    """Fetches items for a given directory path from an OpenList API."""
    url = f"{base_url.rstrip('/')}/api/fs/list"
    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["Authorization"] = api_token

    payload = {"path": path, "password": "", "page": 1, "per_page": 0, "refresh": False}

    time.sleep(0.5)

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()
        if data.get("code") == 200:
            return data.get("data", {}).get("content", [])
        else:
            print(f"[!] Error fetching {path}: {data.get('message')}")
            return []
    except Exception as e:
        print(f"[!] Request failed for {path}: {e}")
        return []


# -------------------------------------------------------------------
# Caching
# -------------------------------------------------------------------
def cache_files(site_id, base_url, api_token, root_path="/"):
    """Recursively fetches and caches metadata for a site starting from root_path."""
    init_db()

    # Standardize root path
    root_path = "/" + root_path.strip("/")
    if root_path == "/":
        clean_root = "/"
    else:
        clean_root = root_path

    print(f"[*] Starting cache sync for site '{base_url}' from root path: {clean_root}")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Clear existing cached entries under root_path for this site before sync
    cursor.execute(
        "DELETE FROM files WHERE site_id = ? AND (path = ? OR path LIKE ?)",
        (site_id, clean_root, f"{clean_root if clean_root != '/' else ''}/%"),
    )
    conn.commit()

    def _traverse(path):
        print(f"[*] Scanning: {path}")
        items = fetch_openlist_dir(base_url, api_token, path)

        records = []
        subdirs = []

        for item in items:
            item_name = item.get("name")

            if path == "/":
                full_path = f"/{item_name}"
            else:
                full_path = f"{path.rstrip('/')}/{item_name}"

            is_dir = 1 if item.get("is_dir") else 0
            size = item.get("size", 0)
            modified = item.get("modified", "")

            records.append((site_id, full_path, item_name, size, is_dir, modified))

            if is_dir:
                subdirs.append(full_path)

        if records:
            cursor.executemany(
                """
                INSERT OR REPLACE INTO files (site_id, path, name, size, is_dir, modified)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                records,
            )
            conn.commit()

        for subdir in subdirs:
            _traverse(subdir)

    _traverse(clean_root)
    conn.close()
    print("\n[+] Caching completed successfully.")


# -------------------------------------------------------------------
# Search
# -------------------------------------------------------------------
def search_local_files(query, search_scope="/", site_id=None):
    """Searches local cache by keyword within an optional path range and site."""
    if not os.path.exists(DB_FILE):
        print("[!] Local cache not found. Please run the sync/cache function first.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Standardize search scope
    search_scope = "/" + search_scope.strip("/")
    if search_scope == "/":
        path_filter = "/%"
    else:
        path_filter = f"{search_scope}/%"

    # Case-insensitive search on file name restricted to path prefix
    if site_id is None:
        cursor.execute(
            """
            SELECT f.site_id, s.base_url, f.path, f.size, f.is_dir, f.modified
            FROM files f
            JOIN sites s ON f.site_id = s.id
            WHERE f.name LIKE ? AND f.path LIKE ?
            ORDER BY f.is_dir DESC, f.name ASC
        """,
            (f"%{query}%", path_filter),
        )
    else:
        cursor.execute(
            """
            SELECT f.site_id, s.base_url, f.path, f.size, f.is_dir, f.modified
            FROM files f
            JOIN sites s ON f.site_id = s.id
            WHERE f.name LIKE ? AND f.path LIKE ? AND f.site_id = ?
            ORDER BY f.is_dir DESC, f.name ASC
        """,
            (f"%{query}%", path_filter, site_id),
        )

    results = cursor.fetchall()
    conn.close()

    scope_label = f"site_id={site_id}" if site_id is not None else "all sites"
    print(
        f"\nSearch results for '{query}' in scope '{search_scope}' ({scope_label}) - {len(results)} found:"
    )
    print("-" * 110)
    for _sid, base_url, path, size, is_dir, modified in results:
        type_str = "[DIR] " if is_dir else "[FILE]"
        size_mb = f"{size / (1024 * 1024):.2f} MB" if not is_dir else "-"
        print(f"{base_url:<30} {type_str:<7} {size_mb:<10} {path}")
    print("-" * 110)


# -------------------------------------------------------------------
# Main menu
# -------------------------------------------------------------------
def main():
    init_db()

    while True:
        print("\n--- OpenList Local Cache & Search ---")
        print("1. Add / update a site")
        print("2. List configured sites")
        print("3. Cache files from a site path")
        print("4. Search cached files")
        print("5. Remove a site and its cached data")
        print("0. Exit")

        choice = input("\nSelect an option (0-5): ").strip()

        if choice == "1":
            add_site()

        elif choice == "2":
            sites = list_sites()
            if not sites:
                print("[!] No sites configured yet.")
            else:
                print("\nConfigured sites:")
                for sid, url, token in sites:
                    masked = "***" if token else "(none)"
                    print(f"  {sid}. {url}  [token: {masked}]")

        elif choice == "3":
            sel = select_site("Select a site to cache")
            if sel:
                sid, url, token = sel
                target_path = (
                    input("Enter path to cache (default '/'): ").strip() or "/"
                )
                cache_files(sid, url, token, target_path)

        elif choice == "4":
            keyword = input("Enter search term: ").strip()
            scope = (
                input("Enter path range to search in (default '/'): ").strip() or "/"
            )
            scope_site = input(
                "Restrict to a specific site ID? (leave empty for all): "
            ).strip()
            site_id = int(scope_site) if scope_site.isdigit() else None
            search_local_files(keyword, scope, site_id)

        elif choice == "5":
            sel = select_site("Select a site to remove")
            if sel:
                sid, url, _ = sel
                confirm = (
                    input(f"Remove site '{url}' and all its cached data? (y/N): ")
                    .strip()
                    .lower()
                )
                if confirm == "y":
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM files WHERE site_id = ?", (sid,))
                    cursor.execute("DELETE FROM sites WHERE id = ?", (sid,))
                    conn.commit()
                    conn.close()
                    print("[+] Site removed.")

        elif choice == "0":
            print("Goodbye.")
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
