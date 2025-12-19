#!/usr/bin/env python3
"""Validate generated series.yaml files against JSON Schema."""

import argparse
import json
import sys
from pathlib import Path

import jsonschema
import yaml


def find_project_root() -> Path:
    """Find the SiliconSchema project root directory."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "common" / "schema").exists():
            return parent
    raise RuntimeError("Could not find SiliconSchema project root")


def load_yaml(path: Path) -> dict:
    """Load a YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(path: Path) -> dict:
    """Load a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_chip(chip_dir: Path, schema: dict) -> tuple[bool, list[str]]:
    """Validate a single chip's series.yaml against the schema.
    
    Returns:
        Tuple of (success, list of error messages)
    """
    series_yaml_path = chip_dir / "series.yaml"
    errors = []
    
    if not series_yaml_path.exists():
        return True, [f"Skipped: no series.yaml found"]
    
    try:
        data = load_yaml(series_yaml_path)
    except yaml.YAMLError as e:
        return False, [f"YAML parse error: {e}"]
    
    validator = jsonschema.Draft202012Validator(schema)
    validation_errors = list(validator.iter_errors(data))
    
    if validation_errors:
        for error in validation_errors:
            path = '.'.join(str(p) for p in error.absolute_path) or '(root)'
            errors.append(f"  {path}: {error.message}")
        return False, errors
    
    return True, []


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate series.yaml files against JSON Schema"
    )
    parser.add_argument(
        "--chip", "-c",
        help="Validate only the specified chip (directory name under chips/)",
        default=None
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed validation output"
    )
    args = parser.parse_args()
    
    try:
        root = find_project_root()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    chips_dir = root / "chips"
    output_dir = root / "out"
    schema_path = root / "common" / "schema" / "chip-series.schema.json"
    
    print(f"SiliconSchema Validator")
    print(f"  Project root: {root}")
    print(f"  Output directory: {output_dir}")
    print(f"  Schema: {schema_path}")
    print()
    
    # Load schema
    try:
        schema = load_json(schema_path)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading schema: {e}", file=sys.stderr)
        return 1
    
    all_success = True
    validated = 0
    failed = 0
    
    if args.chip:
        # Validate single chip
        chip_output_dir = output_dir / args.chip
        if not chip_output_dir.exists():
            print(f"Error: output directory '{args.chip}' not found in out/", file=sys.stderr)
            return 1
        chip_dirs = [chip_output_dir]
    else:
        # Validate all chips in output directory
        if not output_dir.exists():
            print(f"Error: output directory not found. Run 'uv run build-schema' first.", file=sys.stderr)
            return 1
        chip_dirs = sorted(d for d in output_dir.iterdir() if d.is_dir())
    
    print("Validating chips...")
    for chip_dir in chip_dirs:
        success, messages = validate_chip(chip_dir, schema)
        
        if success:
            if messages:  # Skipped
                print(f"  ⊘ {chip_dir.name}: {messages[0]}")
            else:
                print(f"  ✓ {chip_dir.name}: valid")
                validated += 1
        else:
            print(f"  ✗ {chip_dir.name}: INVALID")
            for msg in messages:
                print(f"    {msg}")
            failed += 1
            all_success = False
    
    print()
    print(f"Summary: {validated} valid, {failed} invalid")
    
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
