# ADR-0003: File Safety, Containment, and Deletion Safeguards

## Status
Accepted

## Date
2026-10-25

## Context
The workspace contains several automated file manipulation and deletion tools operating on local disk directories:
1. [delete_by_filename.py](file:///d:/Download/Gallery-dl/delete_by_filename.py): Syncs Directory A against Directory B and removes duplicate files.
2. [dumpFile.py](file:///d:/Download/Gallery-dl/gallery-dl/dumpFile.py): Flattens nested folder hierarchies into a single target directory.
3. [findNonImageFile.py](file:///d:/Download/Gallery-dl/gallery-dl/findNonImageFile.py): Isolates non-image assets (or creates `.lnk` shortcuts).
4. [clusterAndRouteFile.py](file:///d:/Download/Gallery-dl/gallery-dl/clusterAndRouteFile.py): Moves image files into DBSCAN cluster batch directories.

During system review and auditing, three critical failure modes were identified:
- **Accidental Deletion of Unrelated Files:** Matching strictly by filename in `delete_by_filename.py` caused files with generic names (e.g., `001.jpg`, `cover.png`, `image.jpg`) to be flagged for deletion even when their content, resolution, and sizes differed completely.
- **Infinite Directory Recursion:** Running `dumpFile.py` or `findNonImageFile.py` where the destination directory was a subfolder inside the source directory caused the scripts to recursively copy newly created output files back into themselves indefinitely.
- **In-Place Output Directory Destruction:** `clusterAndRouteFile.py` wiped existing output batches using `shutil.rmtree` without verifying that `output_dir` was distinct from `input_dir`, risking recursive deletion of the source dataset.

## Decision
Implement rigorous containment and content verification across all file processing utilities:
1. **Size Verification Guard in [delete_by_filename.py](file:///d:/Download/Gallery-dl/delete_by_filename.py):**
   - Store exact reference file sizes in bytes.
   - Require **both** case-insensitive filename equality AND identical byte size before marking any target file for deletion.
   - Explicitly count and log skipped size mismatches in dry-run reports.
2. **Infinite Recursion Prevention in [dumpFile.py](file:///d:/Download/Gallery-dl/gallery-dl/dumpFile.py) and [findNonImageFile.py](file:///d:/Download/Gallery-dl/gallery-dl/findNonImageFile.py):**
   - Resolve absolute canonical paths using `pathlib.Path.resolve()`.
   - Prevent execution when `source == destination`.
   - Skip traversal of any directory tree whose path is relative to the resolved destination folder (`src_file.resolve().is_relative_to(dst.resolve())`).
   - Automatically create parent destination directories inside copy helpers to avoid `FileNotFoundError`.
3. **Source/Destination Guard in [clusterAndRouteFile.py](file:///d:/Download/Gallery-dl/gallery-dl/clusterAndRouteFile.py):**
   - Validate that `os.path.abspath(output_dir) != os.path.abspath(input_dir)` prior to executing `shutil.rmtree`.
4. **Automated Verification:**
   - Establish regression test suites in `tests/test_file_utilities.py` verifying infinite recursion protection, collision renaming, and size guard rejection.

## Alternatives Considered

### 1. Full Cryptographic Hash (SHA-256) Matching
- **Pros:** 100% guarantee of identical file contents before deletion.
- **Cons:** Extremely slow on large datasets containing 20,000+ high-resolution images (requires reading tens of gigabytes of disk I/O just for a sync preview).
- **Decision:** Filename match + exact byte size equality provides a fast O(1) metadata check that spares different images sharing generic names while avoiding multi-gigabyte disk reads.

## Consequences
- No risk of deleting different images that share common filenames.
- Scripts safely terminate without infinite loops even if users specify nested output directories.
- Verified by automated unit tests in `tests/test_file_utilities.py`.
