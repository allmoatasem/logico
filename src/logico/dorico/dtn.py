"""Parser for Dorico's .dtn binary format.

The .dtn format is a custom binary serialization used by Dorico to store
score data (score.dtn) and library definitions (scorelibrary.dtn).

Structure:
  - 12-byte header: version(u32 LE), type(u32 LE), key_count(u32 LE)
  - Key string table: key_count null-terminated UTF-8 strings (field names)
  - Value string table: val_count(u32 LE) then val_count null-terminated UTF-8 strings
  - Entity tree: binary tree using opcodes FE/FF/FC/FD with LEB128 varints

Opcodes in entity tree:
  - 0xFE: Entity start (named object with children)
  - 0xFF: Array entity (same structure as FE, used for list containers)
  - 0xFC: Key-value pair (leaf node)
  - 0xFD: Null/empty child (placeholder with key and value)
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass, field
from typing import BinaryIO

# Increase recursion limit for deeply nested entity trees
sys.setrecursionlimit(10000)

# Opcodes
OP_ENTITY = 0xFE
OP_ARRAY = 0xFF
OP_KV = 0xFC
OP_NULL = 0xFD


@dataclass
class DtnKV:
    """A key-value leaf node (FC opcode)."""

    key_idx: int
    value_idx: int

    def key(self, keys: list[str]) -> str:
        return keys[self.key_idx] if self.key_idx < len(keys) else f"?{self.key_idx}"

    def value(self, values: list[str]) -> str:
        return values[self.value_idx] if self.value_idx < len(values) else f"?{self.value_idx}"


@dataclass
class DtnEntity:
    """An entity node (FE/FF opcode) with children."""

    key_idx: int
    flags: int
    is_array: bool
    children: list[DtnEntity | DtnKV | None] = field(default_factory=list)

    def key(self, keys: list[str]) -> str:
        return keys[self.key_idx] if self.key_idx < len(keys) else f"?{self.key_idx}"

    def get_kv(self, key_name: str, keys: list[str], values: list[str]) -> str | None:
        """Get a key-value child's value by key name."""
        for child in self.children:
            if isinstance(child, DtnKV) and child.key(keys) == key_name:
                return child.value(values)
        return None

    def get_entity(self, key_name: str, keys: list[str]) -> DtnEntity | None:
        """Get a child entity by key name."""
        for child in self.children:
            if isinstance(child, DtnEntity) and child.key(keys) == key_name:
                return child
        return None

    def get_entities(self, key_name: str, keys: list[str]) -> list[DtnEntity]:
        """Get all child entities with the given key name."""
        return [
            child
            for child in self.children
            if isinstance(child, DtnEntity) and child.key(keys) == key_name
        ]

    def get_all_kvs(self, keys: list[str], values: list[str]) -> dict[str, str]:
        """Get all key-value children as a dict."""
        result = {}
        for child in self.children:
            if isinstance(child, DtnKV):
                result[child.key(keys)] = child.value(values)
        return result


@dataclass
class DtnFile:
    """A parsed .dtn file."""

    version: int
    file_type: int
    keys: list[str]
    values: list[str]
    root: DtnEntity

    def dump(self, max_depth: int = 3) -> str:
        """Return a human-readable dump of the entity tree."""
        lines: list[str] = []
        self._dump_node(self.root, lines, 0, max_depth)
        return "\n".join(lines)

    def _dump_node(
        self, node: DtnEntity | DtnKV | None, lines: list[str], depth: int, max_depth: int
    ) -> None:
        indent = "  " * depth
        if node is None:
            lines.append(f"{indent}(null)")
            return
        if isinstance(node, DtnKV):
            k = node.key(self.keys)
            v = node.value(self.values)
            lines.append(f"{indent}{k} = {repr(v)}")
            return
        tag = "[]" if node.is_array else "{}"
        k = node.key(self.keys)
        lines.append(f"{indent}{k} {tag[0]}")
        if depth < max_depth:
            for child in node.children:
                self._dump_node(child, lines, depth + 1, max_depth)
        elif node.children:
            lines.append(f"{indent}  ... ({len(node.children)} children)")
        lines.append(f"{indent}{tag[1]}")


def read_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Read an unsigned LEB128 varint. Returns (value, new_position)."""
    result = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError(f"Unexpected end of data reading varint at offset {pos}")
        b = data[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if (b & 0x80) == 0:
            break
        shift += 7
    return result, pos


def _parse_children(data: bytes, pos: int, num_children: int) -> tuple[list[DtnEntity | DtnKV | None], int]:
    """Parse num_children child nodes starting at pos."""
    children: list[DtnEntity | DtnKV | None] = []
    for _ in range(num_children):
        if pos >= len(data):
            break
        opcode = data[pos]
        if opcode == OP_KV:
            pos += 1
            key_idx, pos = read_varint(data, pos)
            value_idx, pos = read_varint(data, pos)
            children.append(DtnKV(key_idx=key_idx, value_idx=value_idx))
        elif opcode in (OP_ENTITY, OP_ARRAY):
            entity, pos = _parse_entity(data, pos)
            children.append(entity)
        elif opcode == OP_NULL:
            pos += 1
            # FD has key + value varints (placeholder)
            _, pos = read_varint(data, pos)
            _, pos = read_varint(data, pos)
            children.append(None)
        else:
            raise ValueError(
                f"Unknown opcode 0x{opcode:02x} at offset 0x{pos:x}"
            )
    return children, pos


def _parse_entity(data: bytes, pos: int) -> tuple[DtnEntity, int]:
    """Parse an FE/FF entity node. Returns (entity, end_position)."""
    is_array = data[pos] == OP_ARRAY
    pos += 1  # skip opcode

    key_idx, pos = read_varint(data, pos)
    flags, pos = read_varint(data, pos)
    num_children, pos = read_varint(data, pos)

    # Skip child key list (opaque IDs, not used for navigation)
    for _ in range(num_children):
        _, pos = read_varint(data, pos)

    # Parse children by opcode
    children, pos = _parse_children(data, pos, num_children)

    return DtnEntity(
        key_idx=key_idx,
        flags=flags,
        is_array=is_array,
        children=children,
    ), pos


def parse_dtn(data: bytes) -> DtnFile:
    """Parse a .dtn binary file into a DtnFile structure."""
    if len(data) < 12:
        raise ValueError("File too small for DTN header")

    version, file_type, key_count = struct.unpack_from("<III", data, 0)
    pos = 12

    # Parse key string table
    keys: list[str] = []
    for _ in range(key_count):
        end = data.index(0, pos)
        keys.append(data[pos:end].decode("utf-8"))
        pos = end + 1

    # Parse value string table
    val_count = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    values: list[str] = []
    for _ in range(val_count):
        end = data.index(0, pos)
        values.append(data[pos:end].decode("utf-8"))
        pos = end + 1

    # Parse entity tree
    # First entity is a file-level wrapper (skip it and parse kScore directly)
    if pos >= len(data) or data[pos] != OP_ENTITY:
        raise ValueError(f"Expected FE opcode at tree start (0x{pos:x})")

    # Skip wrapper header: FE + key + flags + num_children(=0) varints
    pos += 1
    _, pos = read_varint(data, pos)  # wrapper key
    _, pos = read_varint(data, pos)  # wrapper flags/version
    wrapper_children, pos = read_varint(data, pos)  # usually 0

    # If wrapper claims 0 children, the root entity follows directly
    # If it claims children, skip its child key list
    for _ in range(wrapper_children):
        _, pos = read_varint(data, pos)

    # Parse root entity (kScore)
    if data[pos] != OP_ENTITY:
        raise ValueError(f"Expected kScore FE at 0x{pos:x}, got 0x{data[pos]:02x}")

    root, end_pos = _parse_entity(data, pos)

    return DtnFile(
        version=version,
        file_type=file_type,
        keys=keys,
        values=values,
        root=root,
    )


def parse_dtn_file(path: str) -> DtnFile:
    """Parse a .dtn file from disk."""
    with open(path, "rb") as f:
        data = f.read()
    return parse_dtn(data)
