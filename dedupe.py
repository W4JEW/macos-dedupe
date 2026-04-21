#!/usr/bin/env python3
"""
macOS File Deduplication Script
Finds and optionally removes duplicate files based on content hash (SHA-256).
"""

import os
import hashlib
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def calculate_hash(filepath, block_size=65536):
    """Calculate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()
    except (IOError, OSError) as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return None


def get_file_info(filepath):
    """Get file metadata."""
    stat = os.stat(filepath)
    return {
        'path': filepath,
        'size': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime),
        'created': datetime.fromtimestamp(stat.st_ctime)
    }


def find_duplicates(root_dir, exclude_dirs=None, min_size=0):
    """
    Find duplicate files in directory tree.

    Args:
        root_dir: Root directory to scan
        exclude_dirs: List of directory names to exclude
        min_size: Minimum file size in bytes (skip smaller files)

    Returns:
        Dictionary mapping hashes to lists of duplicate files
    """
    if exclude_dirs is None:
        exclude_dirs = {'.Trash', 'Library', '.git', 'node_modules',
                        '.cache', '__pycache__'}

    # First pass: group by size (fast pre-filter)
    size_map = defaultdict(list)
    file_count = 0

    print(f"Scanning {root_dir}...")

    for root, dirs, files in os.walk(root_dir):
        # Remove excluded directories from search
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for filename in files:
            filepath = os.path.join(root, filename)

            # Skip symbolic links
            if os.path.islink(filepath):
                continue

            try:
                size = os.path.getsize(filepath)
                if size >= min_size:
                    size_map[size].append(filepath)
                    file_count += 1

                    if file_count % 1000 == 0:
                        print(f"  Scanned {file_count} files...", end='\r')
            except (OSError, IOError):
                continue

    print(f"\nScanned {file_count} files total.")

    # Second pass: calculate hashes only for files with duplicate sizes
    hash_map = defaultdict(list)
    potential_dupes = sum(len(files) for files in size_map.values() if len(files) > 1)

    if potential_dupes == 0:
        print("No duplicate files found (by size).")
        return hash_map

    print(f"\nCalculating hashes for {potential_dupes} potential duplicates...")
    processed = 0

    for size, filepaths in size_map.items():
        if len(filepaths) > 1:
            for filepath in filepaths:
                file_hash = calculate_hash(filepath)
                if file_hash:
                    hash_map[file_hash].append(filepath)

                processed += 1
                if processed % 100 == 0:
                    print(f"  Processed {processed}/{potential_dupes}...", end='\r')

    print()

    # Keep only actual duplicates (hash appears more than once)
    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}

    return duplicates


def generate_report(duplicates, output_file=None):
    """Generate a detailed report of duplicates."""
    if not duplicates:
        print("\n✓ No duplicate files found!")
        return

    total_dupes = sum(len(files) - 1 for files in duplicates.values())
    total_waste = sum(
        os.path.getsize(files[0]) * (len(files) - 1)
        for files in duplicates.values()
    )

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("FILE DEDUPLICATION REPORT")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append(f"\nTotal duplicate file sets: {len(duplicates)}")
    report_lines.append(f"Total duplicate files: {total_dupes}")
    report_lines.append(f"Total wasted space: {format_size(total_waste)}\n")
    report_lines.append("=" * 80)

    for i, (file_hash, files) in enumerate(sorted(duplicates.items(),
                                                   key=lambda x: os.path.getsize(x[1][0]),
                                                   reverse=True), 1):
        size = os.path.getsize(files[0])
        waste = size * (len(files) - 1)

        report_lines.append(f"\nDuplicate Set #{i}")
        report_lines.append(f"  Hash: {file_hash[:16]}...")
        report_lines.append(f"  File size: {format_size(size)}")
        report_lines.append(f"  Copies: {len(files)}")
        report_lines.append(f"  Wasted space: {format_size(waste)}")
        report_lines.append(f"  Files:")

        for filepath in sorted(files):
            info = get_file_info(filepath)
            report_lines.append(f"    - {filepath}")
            report_lines.append(f"      Modified: {info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")

    report = "\n".join(report_lines)

    # Print to console
    print(report)

    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
        print(f"\n✓ Report saved to: {output_file}")


def format_size(bytes_size):
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def delete_duplicates(duplicates, keep_strategy='oldest', interactive=True, dry_run=False):
    """
    Delete duplicate files, keeping one copy.

    Args:
        duplicates: Dictionary of duplicate file sets
        keep_strategy: 'oldest', 'newest', or 'first' (alphabetically)
        interactive: Ask for confirmation before deleting
        dry_run: If True, only show what would be deleted without actually deleting
    """
    if not duplicates:
        return

    total_to_delete = sum(len(files) - 1 for files in duplicates.values())
    total_to_free = sum(
        os.path.getsize(files[0]) * (len(files) - 1)
        for files in duplicates.values()
    )

    if dry_run:
        print(f"\n🔍 DRY RUN - Would delete {total_to_delete} duplicate files")
        print(f"   This would free up {format_size(total_to_free)}")
    else:
        print(f"\n⚠️  About to delete {total_to_delete} duplicate files")
        print(f"   This will free up {format_size(total_to_free)}")

        if interactive:
            response = input("\nProceed with deletion? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Deletion cancelled.")
                return

    deleted_count = 0
    freed_space = 0

    for file_hash, files in duplicates.items():
        # Determine which file to keep
        if keep_strategy == 'oldest':
            files_sorted = sorted(files, key=lambda f: os.path.getmtime(f))
        elif keep_strategy == 'newest':
            files_sorted = sorted(files, key=lambda f: os.path.getmtime(f), reverse=True)
        else:  # 'first' - alphabetically
            files_sorted = sorted(files)

        keep_file = files_sorted[0]
        delete_files = files_sorted[1:]

        print(f"\n{'Would keep' if dry_run else 'Keeping'}: {keep_file}")

        for filepath in delete_files:
            # Safety check: ensure it's still a regular file (not a symlink)
            if os.path.islink(filepath):
                print(f"  ⚠️  Skipping symlink: {filepath}")
                continue

            try:
                size = os.path.getsize(filepath)

                if dry_run:
                    print(f"  🔍 Would delete: {filepath}")
                else:
                    os.remove(filepath)
                    print(f"  ✗ Deleted: {filepath}")

                deleted_count += 1
                freed_space += size
            except OSError as e:
                print(f"  ✗ Error {'checking' if dry_run else 'deleting'} {filepath}: {e}", file=sys.stderr)

    if dry_run:
        print(f"\n🔍 DRY RUN complete - Would delete {deleted_count} files")
        print(f"🔍 Would free {format_size(freed_space)}")
    else:
        print(f"\n✓ Deleted {deleted_count} files")
        print(f"✓ Freed {format_size(freed_space)}")


def main():
    parser = argparse.ArgumentParser(
        description='Find and remove duplicate files based on content hash (SHA-256)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Scan home directory, show report
  %(prog)s /path/to/dir             # Scan specific directory
  %(prog)s -d                       # Scan and delete duplicates (interactive)
  %(prog)s -d --dry-run             # Show what would be deleted without deleting
  %(prog)s -d -y --keep newest      # Delete without prompt, keep newest files
  %(prog)s -r -o report.txt         # Save report to file without deleting
        """
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default=str(Path.home()),
        help='Directory to scan (default: home directory)'
    )

    # Action group - mutually exclusive actions
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        '-r', '--report-only',
        action='store_true',
        help='Generate report only, do not delete (default action)'
    )
    action_group.add_argument(
        '-d', '--delete',
        action='store_true',
        help='Delete duplicates after showing report'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting (use with -d)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Save report to file'
    )
    parser.add_argument(
        '--keep',
        choices=['oldest', 'newest', 'first'],
        default='oldest',
        help='Which file to keep when deleting duplicates (default: oldest)'
    )
    parser.add_argument(
        '--min-size',
        type=int,
        default=1024,
        help='Minimum file size in bytes to consider (default: 1024)'
    )
    parser.add_argument(
        '--exclude',
        nargs='*',
        help='Additional directories to exclude'
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompts (use with caution!)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.dry_run and not args.delete:
        print("Error: --dry-run must be used with -d/--delete", file=sys.stderr)
        sys.exit(1)

    # Validate directory
    root_path = Path(args.directory).expanduser().resolve()
    if not root_path.is_dir():
        print(f"Error: {args.directory} is not a valid directory", file=sys.stderr)
        sys.exit(1)

    # Prepare exclude list
    exclude_dirs = {'.Trash', 'Library', '.git', 'node_modules',
                    '.cache', '__pycache__'}
    if args.exclude:
        exclude_dirs.update(args.exclude)

    print(f"Starting deduplication scan of: {root_path}")
    print(f"Minimum file size: {format_size(args.min_size)}")
    print(f"Excluded directories: {', '.join(sorted(exclude_dirs))}\n")

    # Find duplicates
    duplicates = find_duplicates(str(root_path), exclude_dirs, args.min_size)

    # Generate report
    generate_report(duplicates, args.output)

    # Handle deletion or dry run
    if args.delete:
        delete_duplicates(
            duplicates,
            args.keep,
            interactive=not args.yes,
            dry_run=args.dry_run
        )


if __name__ == '__main__':
    main()
