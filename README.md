# README - macOS File Deduplication Tool

A Python script to find and optionally remove duplicate files on macOS based on SHA-256 content hashing. This tool uses a two-pass approach (size filtering before hashing) for efficient duplicate detection.

## ⚠️ Disclaimer

**USE THIS SCRIPT AT YOUR OWN RISK.** This tool permanently deletes files when the `-d` or `--delete` flag is used. While every effort has been made to ensure the safety and reliability of this script, the author assumes **no responsibility or liability** for any data loss, damage, or other issues that may arise from using this tool. Always:

- **Back up your data** before running deletion operations
- Use the `--dry-run` option first to preview what would be deleted
- Double-check the results before confirming deletion
- Test on non-critical files first

By using this script, you acknowledge that you understand the risks and accept full responsibility for any consequences.

## Features

- **Fast duplicate detection**: Pre-filters files by size before calculating SHA-256 hashes
- **Dry-run mode**: Preview what would be deleted without making changes
- **Multiple keep strategies**: Choose to keep oldest, newest, or first (alphabetically) file
- **Configurable exclusions**: Skip system directories like `.Trash`, `Library`, etc.
- **Detailed reporting**: Generate reports showing duplicate sets and wasted space
- **Safe operation**: Skips symlinks and requires confirmation before deletion
- **Progress indicators**: Shows scan and hash calculation progress

## Requirements

- Python 3.6 or later
- macOS (tested on macOS 10.14+)

## Installation

1. Download the script:

    ```bash
    curl -O https://raw.githubusercontent.com/W4JEW/dedupe/main/dedupe.py
    ```

2. Make it executable:

    ```bash
    chmod +x dedupe.py
    ```

3. (Optional) Move to a directory in your PATH:

```bash
mv dedupe.py /usr/local/bin/dedupe
```

## Usage

### Basic Usage

```bash
# Scan home directory and show report
./dedupe.py

# Scan a specific directory
./dedupe.py /Users/username/Downloads

# Scan current directory
./dedupe.py .
```

### Command Line Options

| Option                 | Short | Description                                                            |
| ---------------------- | ----- | ---------------------------------------------------------------------- |
| `directory`            | -     | Directory to scan (default: home directory)                            |
| `--report-only`        | `-r`  | Generate report only, don't delete (default)                           |
| `--delete`             | `-d`  | Delete duplicates after showing report                                 |
| `--dry-run`            | -     | Show what would be deleted without deleting (use with `-d`)            |
| `--output`             | `-o`  | Save report to a file                                                  |
| `--keep`               | -     | Which file to keep: `oldest`, `newest`, or `first` (default: `oldest`) |
| `--min-size`           | -     | Minimum file size in bytes (default: 1024)                             |
| `--exclude`            | -     | Additional directories to exclude                                      |
| `--yes`                | `-y`  | Skip confirmation prompts                                              |
| `--help`               | `-h`  | Show help message                                                      |

### Examples

#### Dry Run (Recommended First Step)

Preview what would be deleted without actually deleting anything:

```bash
./dedupe.py -d --dry-run ~/Documents
```

Output:

```text
🔍 DRY RUN - Would delete 42 duplicate files
   This would free up 1.23 GB

Would keep: /Users/username/Documents/important.pdf
  🔍 Would delete: /Users/username/Documents/backup/important.pdf
  🔍 Would delete: /Users/username/Documents/temp/important_copy.pdf

🔍 DRY RUN complete - Would delete 42 files
🔍 Would free 1.23 GB
```

#### Delete Duplicates (Interactive)

```bash
./dedupe.py -d ~/Pictures
```

You'll be prompted for confirmation before any files are deleted.

#### Delete Without Confirmation (Use with Caution!)

```bash
./dedupe.py -d -y ~/Downloads
```

#### Keep Newest Files Instead of Oldest

```bash
./dedupe.py -d --keep newest ~/Documents
```

#### Exclude Additional Directories

```bash
./dedupe.py --exclude "*.tmp" "temp" "cache" ~/Projects
```

#### Save Report to File

```bash
./dedupe.py -r -o duplicates_report.txt ~/Documents
```

#### Scan Only Large Files (10MB minimum)

```bash
./dedupe.py --min-size 10485760 ~/Movies
```

## How It Works

1. **Size-based Pre-filtering**: The script first groups files by size. Files with unique sizes are immediately excluded from further processing.

2. **SHA-256 Hashing**: For files with matching sizes, the script calculates SHA-256 hashes to identify true duplicates.

3. **Duplicate Set Creation**: Files with identical hashes are grouped into duplicate sets.

4. **Deletion Strategy**: Based on the `--keep` option, the script determines which file to keep and which to delete.

## Default Exclusions

The following directories are excluded by default:

- `.Trash` - macOS Trash folder
- `Library` - System and application support files
- `.git` - Git repositories
- `node_modules` - Node.js dependencies
- `.cache` - Cache directories
- `__pycache__` - Python cache

## Safety Features

- **Symbolic link handling**: Symlinks are skipped during both scanning and deletion
- **Confirmation prompts**: Requires explicit confirmation before deletion (unless `-y` is used)
- **Dry-run mode**: Preview deletions without making changes
- **Path validation**: Verifies the target directory exists before scanning
- **Error handling**: Gracefully handles permission errors and unreadable files

**Note:** Despite these safety features, data loss can still occur. Please see the [Disclaimer](#️-disclaimer) section above.

## Sample Output

```text
Starting deduplication scan of: /Users/username/Documents
Minimum file size: 1.00 KB
Excluded directories: .Trash, .cache, .git, Library, __pycache__, node_modules

Scanning /Users/username/Documents...
  Scanned 5000 files...
Scanned 5234 files total.

Calculating hashes for 234 potential duplicates...
  Processed 200/234...

================================================================================
FILE DEDUPLICATION REPORT
Generated: 2024-01-15 14:32:18
================================================================================

Total duplicate file sets: 12
Total duplicate files: 45
Total wasted space: 2.34 GB

================================================================================

Duplicate Set #1
  Hash: a3f5c8d2e1b4...
  File size: 156.78 MB
  Copies: 3
  Wasted space: 313.56 MB
  Files:
    - /Users/username/Documents/photos/vacation.jpg
      Modified: 2023-06-15 10:23:45
    - /Users/username/Documents/photos/backup/vacation.jpg
      Modified: 2023-06-15 10:23:45
    - /Users/username/Documents/temp/vacation_copy.jpg
      Modified: 2023-06-15 10:23:45
```

## Performance

The script is optimized for large directory trees:

- **Size pre-filtering**: Eliminates ~99% of files from hashing
- **Efficient hashing**: Uses 64KB blocks to minimize memory usage
- **Progress indicators**: Shows scan progress every 1000 files
- **Early termination**: Stops hash calculation early if no potential duplicates exist

## Limitations

- Cannot detect duplicate content across different file formats (e.g., a JPEG and a PNG of the same image)
- Does not compare file metadata (only content hash)
- Hardlinks are treated as separate files
- Requires read permissions for all files being scanned

## Troubleshooting

### "Error: --dry-run must be used with -d/--delete"

The `--dry-run` flag only works with the delete command:

```bash
# Wrong
./dedupe.py --dry-run ~/Documents

# Correct
./dedupe.py -d --dry-run ~/Documents
```

### Permission Denied Errors

If you see permission errors, you may need to run with elevated permissions:

```bash
sudo ./dedupe.py ~/Library/Caches
```

### Out of Memory

For extremely large files, the script may use significant memory. Reduce the block size by editing the `block_size` parameter in the `calculate_hash()` function.

## License

MIT License - Feel free to use, modify, and distribute this script.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter any issues or have questions, please open an issue on the project repository.
