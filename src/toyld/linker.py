#! /usr/bin/env python3

import argparse
import os
from pathlib import Path

from toyld.objfile import parse_object
from toyld.link import (
    link_executable,
    link_dynamic_shared_library,
    link_static_shared_library,
    DynamicSharedConfig,
    ExecutableConfig,
    LinkConfig,
    StaticSharedConfig,
)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Simple linker that processes input files and produces an output file.')
    parser.add_argument('input_files', nargs='+', help='Input files to process')
    parser.add_argument('--skip-symbols', action='store_true', help='Skip processing symbols', default=False)
    parser.add_argument('--skip-relocations', action='store_true', help='Skip processing relocations', default=False)
    parser.add_argument('--skip-data', action='store_true', help='Skip processing data section', default=False)
    parser.add_argument('--output', '-o', help='Specify output file name (default: a.out.lk)', default='a.out.lk')
    parser.add_argument('--byteorder', choices=['big', 'little'], default='little', help='Specify byte order for output file (default: little)')
    parser.add_argument('--wrap', '-w', action='append', help='Use a wrapper function for SYMBOL.', metavar='SYMBOL', default=[])
    parser.add_argument('--shared', action='store_true', help='Produce a shared library instead of an executable (default: false)', default=False)
    parser.add_argument('--dynamic', action='store_true', help='Produce a dynamic shared library instead of a static shared library (default: false)', default=False)
    parser.add_argument('--base-addr', type=lambda x: int(x, 16), help='Specify base address for output segments (default: 0x1000)', default=0x1000)
    parser.add_argument('--stub-format', choices=['directory', 'file'], default='directory', help='Specify format for stub libraries (default: directory)')
    parser.add_argument('--stub-output', help='Specify output file name for stub library')
    args = parser.parse_args(argv)
    is_static_shared = args.shared and not args.dynamic
    if is_static_shared and not args.stub_output:
        parser.error("--shared requires --stub-output to be specified")
    if is_static_shared and os.path.basename(args.stub_output) != os.path.basename(args.output):
        parser.error(f"--stub-output file name must be the same as output file name when --shared is specified. Expected '{os.path.basename(args.output)}', got '{os.path.basename(args.stub_output)}'")
    return args


def args_to_config(args: argparse.Namespace) -> LinkConfig:
    common = dict(
        input_files=args.input_files,
        output=args.output,
        byteorder=args.byteorder,
        wrap=args.wrap,
        base_addr=args.base_addr,
    )
    if args.shared and args.dynamic:
        return DynamicSharedConfig(**common)
    if args.shared:
        return StaticSharedConfig(
            **common,
            stub_output=args.stub_output,
            stub_format=args.stub_format,
        )
    return ExecutableConfig(
        **common,
        skip_symbols=args.skip_symbols,
        skip_relocations=args.skip_relocations,
        skip_data=args.skip_data,
    )


def copy_input_to_output(config: ExecutableConfig):
    obj = parse_object(config.input_files[0])
    Path(config.output).write_bytes(obj.serialize())


def main():
    args = parse_args()
    config = args_to_config(args)
    if isinstance(config, DynamicSharedConfig):
        link_dynamic_shared_library(config)
    elif isinstance(config, StaticSharedConfig):
        link_static_shared_library(config)
    elif len(config.input_files) == 1:
        copy_input_to_output(config)
    else:
        link_executable(config)


if __name__ == '__main__':
    main()
