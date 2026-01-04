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


def get_sip_mpis(mpi_data: dict) -> set[str]:
    """Get set of MPI identifiers that have sip: true."""
    sip_mpis = set()
    mpis = mpi_data.get('mpis', {})
    for mpi_name, mpi_config in mpis.items():
        if mpi_config.get('sip', False):
            sip_mpis.add(mpi_name)
    return sip_mpis


def validate_memory_sip(chip_data: dict, sip_mpis: set[str]) -> list[str]:
    """Validate that memory configurations only use SiP MPI interfaces.
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    variants = chip_data.get('variants', [])
    
    for variant in variants:
        part_number = variant.get('part_number', 'unknown')
        memory_list = variant.get('memory', [])
        
        for mem in memory_list:
            mpi = mem.get('mpi')
            if mpi and mpi not in sip_mpis:
                errors.append(
                    f"Variant '{part_number}': memory uses '{mpi}' which is not a SiP interface. "
                    f"Only SiP MPIs ({', '.join(sorted(sip_mpis)) or 'none'}) can have memory defined."
                )
    
    return errors


def validate_chip(chip_dir: Path, schema: dict, mpi_dir: Path = None) -> tuple[bool, list[str]]:
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
    
    # JSON Schema validation
    validator = jsonschema.Draft202012Validator(schema)
    validation_errors = list(validator.iter_errors(data))
    
    if validation_errors:
        for error in validation_errors:
            path = '.'.join(str(p) for p in error.absolute_path) or '(root)'
            errors.append(f"  {path}: {error.message}")
        return False, errors
    
    return True, []


def validate_chip_source(chip_source_dir: Path, mpi_dir: Path) -> tuple[bool, list[str]]:
    """Validate chip source (chip.yaml) for SiP memory constraints.
    
    Returns:
        Tuple of (success, list of error messages)
    """
    chip_yaml_path = chip_source_dir / "chip.yaml"
    errors = []
    
    if not chip_yaml_path.exists():
        return True, []
    
    try:
        chip_data = load_yaml(chip_yaml_path)
    except yaml.YAMLError as e:
        return False, [f"chip.yaml parse error: {e}"]
    
    # Get shared_pinmux to find the correct MPI config
    shared_pinmux = chip_data.get('shared_pinmux')
    if not shared_pinmux:
        # No shared pinmux, skip MPI validation
        return True, []
    
    # Load MPI config
    mpi_yaml_path = mpi_dir / shared_pinmux / "mpi.yaml"
    if not mpi_yaml_path.exists():
        # No MPI config, skip validation
        return True, []
    
    try:
        mpi_data = load_yaml(mpi_yaml_path)
    except yaml.YAMLError as e:
        return False, [f"mpi.yaml parse error: {e}"]
    
    # Get SiP MPIs
    sip_mpis = get_sip_mpis(mpi_data)
    
    # Validate memory configurations
    memory_errors = validate_memory_sip(chip_data, sip_mpis)
    if memory_errors:
        return False, memory_errors
    
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
    mpi_dir = root / "common" / "mpi"
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
        chip_source_dir = chips_dir / args.chip
        if not chip_output_dir.exists():
            print(f"Error: output directory '{args.chip}' not found in out/", file=sys.stderr)
            return 1
        chip_dirs = [(chip_output_dir, chip_source_dir)]
    else:
        # Validate all chips in output directory
        if not output_dir.exists():
            print(f"Error: output directory not found. Run 'uv run build-schema' first.", file=sys.stderr)
            return 1
        chip_dirs = [
            (d, chips_dir / d.name) 
            for d in sorted(output_dir.iterdir()) 
            if d.is_dir()
        ]
    
    print("Validating chips...")
    for chip_output_dir, chip_source_dir in chip_dirs:
        chip_name = chip_output_dir.name
        
        # Validate generated series.yaml
        success, messages = validate_chip(chip_output_dir, schema, mpi_dir)
        
        # Also validate source chip.yaml for SiP constraints
        if success and chip_source_dir.exists():
            sip_success, sip_errors = validate_chip_source(chip_source_dir, mpi_dir)
            if not sip_success:
                success = False
                messages = sip_errors
        
        if success:
            if messages:  # Skipped
                print(f"  ⊘ {chip_name}: {messages[0]}")
            else:
                print(f"  ✓ {chip_name}: valid")
                validated += 1
        else:
            print(f"  ✗ {chip_name}: INVALID")
            for msg in messages:
                print(f"    {msg}")
            failed += 1
            all_success = False
    
    print()
    print(f"Summary: {validated} valid, {failed} invalid")
    
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
