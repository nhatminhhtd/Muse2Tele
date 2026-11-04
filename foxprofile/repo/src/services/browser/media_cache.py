import os
import shutil

# Sites that keep downloaded video as IndexedDB blobs. TikTok Web caches every
# clip it prefetches there, which grew a profile to several GB. It is only a
# cache: cookies and logins live elsewhere in the profile, so it is safe to drop.
MEDIA_CACHE_SITES = ("https+++www.tiktok.com",)

# Profiles whose cached media is smaller than this are left alone.
MEDIA_CACHE_LIMIT_MB = int(os.getenv("FOXPROFILE_MEDIA_CACHE_LIMIT_MB", "500"))


def _size(path: str) -> int:
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def prune(profile_dir: str, limit_mb: int = MEDIA_CACHE_LIMIT_MB) -> int:
    """Delete oversized IndexedDB media caches; returns the bytes freed.

    Must run while the profile's browser is not running. A database is removed
    whole (sqlite, -wal, -shm and its .files blobs), never just the blobs, so no
    row is left pointing at a missing file.
    """
    freed = 0
    for site in MEDIA_CACHE_SITES:
        idb = os.path.join(profile_dir, "storage", "default", site, "idb")
        if not os.path.isdir(idb):
            continue
        for entry in os.listdir(idb):
            if not entry.endswith(".files"):
                continue
            blobs = os.path.join(idb, entry)
            if _size(blobs) < limit_mb * 1024 * 1024:
                continue
            stem = entry[: -len(".files")]
            targets = [blobs] + [
                os.path.join(idb, stem + suffix) for suffix in (".sqlite", ".sqlite-wal", ".sqlite-shm")
            ]
            for target in targets:
                if not os.path.exists(target):
                    continue
                size = _size(target)
                try:
                    if os.path.isdir(target):
                        shutil.rmtree(target)
                    else:
                        os.remove(target)
                    freed += size
                except OSError:
                    pass
    return freed
