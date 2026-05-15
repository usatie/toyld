from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LinkConfig:
    input_files: list[str]
    output: str
    byteorder: str = 'little'
    wrap: list[str] = field(default_factory=list)
    base_addr: int = 0x1000


@dataclass
class ExecutableConfig(LinkConfig):
    skip_symbols: bool = False
    skip_relocations: bool = False
    skip_data: bool = False


@dataclass
class StaticSharedConfig(LinkConfig):
    stub_output: str | None = None
    stub_format: str = 'directory'


@dataclass
class DynamicSharedConfig(LinkConfig):
    pass
