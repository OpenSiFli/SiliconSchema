#!/usr/bin/env python3
"""Build series.yaml files by merging chip.yaml with shared pinmux definitions."""

import argparse
import sys
from pathlib import Path

import yaml


def find_project_root() -> Path:
    """Find the SiliconSchema project root directory."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "common" / "pinmux").exists():
            return parent
    raise RuntimeError("Could not find SiliconSchema project root")


def load_yaml(path: Path) -> dict:
    """Load a YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: dict) -> None:
    """Save data to a YAML file with anchors and aliases."""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, 
                  default_flow_style=False, 
                  allow_unicode=True,
                  sort_keys=False,
                  width=120)


class SeriesYamlDumper(yaml.SafeDumper):
    """Custom YAML dumper that generates anchors for pads."""
    pass


def represent_pad_dict(dumper: SeriesYamlDumper, data: dict) -> yaml.Node:
    """Custom representer for pad dictionaries."""
    return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())


SeriesYamlDumper.add_representer(dict, represent_pad_dict)


def generate_series_yaml(chip_yaml: dict, pinmux_data: dict) -> str:
    """Generate series.yaml content with YAML anchors and aliases.
    
    This function generates the YAML string manually to properly handle
    anchors and aliases for pad references.
    """
    lines = []
    
    # Header
    lines.append(f"schema_version: {chip_yaml['schema_version']}")
    lines.append(f"model_id: {chip_yaml['model_id']}")
    lines.append(f"lifecycle: {chip_yaml['lifecycle']}")
    lines.append("")
    
    # Docs
    lines.append("docs:")
    for doc in chip_yaml['docs']:
        for doc_type, locales in doc.items():
            locale_parts = []
            for lang, url in locales.items():
                locale_parts.append(f'{lang}: "{url}"')
            lines.append(f"  - {doc_type}: {{{', '.join(locale_parts)}}}")
    lines.append("")
    
    # Pads with anchors
    lines.append("pads:")
    pinmux_map = pinmux_data.get('pinmux', {})
    
    for pad_name, pad_def in chip_yaml['pads'].items():
        # Add anchor
        lines.append(f"  {pad_name}: &{pad_name}")
        lines.append(f"    type: {pad_def['type']}")
        
        # Add description if present
        if 'description' in pad_def:
            lines.append(f"    description: \"{pad_def['description']}\"")
        
        # Add notes if present
        if 'notes' in pad_def:
            lines.append(f"    notes: \"{pad_def['notes']}\"")
        
        # Merge pinmux from shared file if available
        if pad_name in pinmux_map:
            lines.append("    pinmux:")
            for entry in pinmux_map[pad_name]:
                func = entry['function']
                sel = entry['select']
                lines.append(f"      - {{function: {func}, select: {sel}}}")
    
    lines.append("")
    
    # Variants
    lines.append("variants:")
    first_pins_anchor = None
    
    for i, variant in enumerate(chip_yaml['variants']):
        lines.append(f"  - part_number: {variant['part_number']}")
        lines.append(f"    description: \"{variant['description']}\"")
        lines.append(f"    package: {variant['package']}")
        
        # Handle pins with anchor/alias
        pins = variant['pins']
        
        # Check if this variant uses an alias (has same pins as first variant)
        is_first_with_pins = first_pins_anchor is None
        if is_first_with_pins:
            # First variant with full pins definition - create anchor
            first_pins_anchor = f"{chip_yaml['model_id']}_QFN68_PINS"
            lines.append(f"    pins: &{first_pins_anchor}")
            for pin in pins:
                pad_name = pin['pad']
                lines.append(f"      - {{number: \"{pin['number']}\", pad: *{pad_name}}}")
        else:
            # Subsequent variant - use alias
            lines.append(f"    pins: *{first_pins_anchor}")
    
    lines.append("")
    return '\n'.join(lines)


def build_chip(chip_dir: Path, pinmux_dir: Path, output_dir: Path) -> bool:
    """Build series.yaml for a single chip."""
    chip_yaml_path = chip_dir / "chip.yaml"
    series_yaml_path = output_dir / chip_dir.name / "series.yaml"
    
    if not chip_yaml_path.exists():
        print(f"  Skipping {chip_dir.name}: no chip.yaml found")
        return True
    
    print(f"  Building {chip_dir.name}...")
    
    # Load chip definition
    chip_data = load_yaml(chip_yaml_path)
    
    # Load shared pinmux if specified
    pinmux_data = {}
    if 'shared_pinmux' in chip_data:
        pinmux_name = chip_data['shared_pinmux']
        pinmux_path = pinmux_dir / pinmux_name / "pinmux.yaml"
        if pinmux_path.exists():
            pinmux_data = load_yaml(pinmux_path)
            print(f"    Loaded shared pinmux: {pinmux_name}")
        else:
            print(f"    Warning: shared pinmux '{pinmux_name}' not found at {pinmux_path}")
    
    # Generate series.yaml
    series_content = generate_series_yaml(chip_data, pinmux_data)
    
    # Write output
    with open(series_yaml_path, 'w', encoding='utf-8') as f:
        f.write(series_content)
    
    print(f"    Generated: {series_yaml_path}")
    return True


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build series.yaml files from chip.yaml and shared pinmux definitions"
    )
    parser.add_argument(
        "--chip", "-c",
        help="Build only the specified chip (directory name under chips/)",
        default=None
    )
    args = parser.parse_args()
    
    try:
        root = find_project_root()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    chips_dir = root / "chips"
    pinmux_dir = root / "common" / "pinmux"
    output_dir = root / "out"
    
    print(f"SiliconSchema Build")
    print(f"  Project root: {root}")
    print(f"  Chips directory: {chips_dir}")
    print(f"  Pinmux directory: {pinmux_dir}")
    print(f"  Output directory: {output_dir}")
    print()
    
    success = True
    
    if args.chip:
        # Build single chip
        chip_dir = chips_dir / args.chip
        if not chip_dir.exists():
            print(f"Error: chip directory '{args.chip}' not found", file=sys.stderr)
            return 1
        # Create output directory
        (output_dir / args.chip).mkdir(parents=True, exist_ok=True)
        success = build_chip(chip_dir, pinmux_dir, output_dir)
    else:
        # Build all chips
        print("Building all chips...")
        for chip_dir in sorted(chips_dir.iterdir()):
            if chip_dir.is_dir():
                # Create output directory
                (output_dir / chip_dir.name).mkdir(parents=True, exist_ok=True)
                if not build_chip(chip_dir, pinmux_dir, output_dir):
                    success = False
    
    print()
    if success:
        print("Build completed successfully!")
        return 0
    else:
        print("Build completed with errors.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
