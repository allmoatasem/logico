"""Logico CLI — read, compare, and sync Logic Pro, Dorico, and StaffPad projects."""

from __future__ import annotations

import sys
from pathlib import Path

from .model import Project, Note

# Note names for display
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _detect_format(path: str) -> str:
    """Detect project format from file extension or structure."""
    p = Path(path)
    if p.suffix == ".dorico":
        return "dorico"
    if p.suffix == ".stf":
        return "staffpad"
    if p.suffix == ".logicx":
        return "logic"
    # Check if it's a directory containing a .logicx
    if p.is_dir():
        if list(p.glob("*.logicx")):
            return "logic"
        if list(p.glob("*/*.logicx")):
            return "logic"
    raise ValueError(f"Unknown format for: {path}")


def _load_project(path: str) -> Project:
    """Load a project file and extract to the common model."""
    fmt = _detect_format(path)

    if fmt == "dorico":
        from .dorico.parser import parse_dorico
        from .dorico.extractor import extract_project
        return extract_project(parse_dorico(path))

    elif fmt == "staffpad":
        from .staffpad.parser import parse_staffpad
        from .staffpad.extractor import extract_project
        return extract_project(parse_staffpad(path))

    elif fmt == "logic":
        from .logic.parser import parse_logic
        from .logic.extractor import extract_project
        return extract_project(parse_logic(path))

    raise ValueError(f"Unsupported format: {fmt}")


def _note_name(midi: int) -> str:
    """Convert MIDI note number to note name."""
    return f"{_NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def _print_project(project: Project) -> None:
    """Print a project summary."""
    print(f"  Format: {project.source_format}")
    if project.title:
        print(f"  Title: {project.title}")
    print(f"  PPQ: {project.ppq}")

    # Tempo
    if project.tempo_events:
        tempos = ", ".join(f"{t.bpm} BPM at tick {t.position}" for t in project.tempo_events)
        print(f"  Tempo: {tempos}")

    # Time signatures
    if project.time_signatures:
        ts_str = ", ".join(
            f"{ts.numerator}/{ts.denominator} at tick {ts.position}"
            for ts in project.time_signatures
        )
        print(f"  Time sig: {ts_str}")

    # Key signatures
    if project.key_signatures:
        ks_str = ", ".join(
            f"{ks.key_name} at tick {ks.position}"
            for ks in project.key_signatures
        )
        print(f"  Key sig: {ks_str}")

    # Tracks
    print(f"  Tracks: {len(project.tracks)}")
    for track in project.tracks:
        print(f"\n    [{track.name}] ({track.instrument})")
        print(f"    Notes: {len(track.notes)}")

        if track.notes:
            for note in track.notes[:20]:
                name = _note_name(note.pitch)
                print(
                    f"      {name:5s} vel={note.velocity:3d} "
                    f"pos={note.position:6d} dur={note.duration:5d}"
                )
            if len(track.notes) > 20:
                print(f"      ... and {len(track.notes) - 20} more notes")

        if track.dynamics:
            print(f"    Dynamics: {len(track.dynamics)}")
        if track.articulations:
            print(f"    Articulations: {len(track.articulations)}")


def _diff_projects(a: Project, b: Project) -> None:
    """Show differences between two projects."""
    print("\n--- DIFF ---\n")

    # Tempo
    a_tempos = {t.position: t.bpm for t in a.tempo_events}
    b_tempos = {t.position: t.bpm for t in b.tempo_events}
    if a_tempos != b_tempos:
        print(f"  Tempo differs:")
        print(f"    {a.source_format}: {a_tempos}")
        print(f"    {b.source_format}: {b_tempos}")

    # Time signatures
    a_ts = {ts.position: (ts.numerator, ts.denominator) for ts in a.time_signatures}
    b_ts = {ts.position: (ts.numerator, ts.denominator) for ts in b.time_signatures}
    if a_ts != b_ts:
        print(f"  Time signatures differ:")
        print(f"    {a.source_format}: {a_ts}")
        print(f"    {b.source_format}: {b_ts}")

    # Key signatures
    a_ks = {ks.position: (ks.fifths, ks.mode) for ks in a.key_signatures}
    b_ks = {ks.position: (ks.fifths, ks.mode) for ks in b.key_signatures}
    if a_ks != b_ks:
        print(f"  Key signatures differ:")
        print(f"    {a.source_format}: {a_ks}")
        print(f"    {b.source_format}: {b_ks}")

    # Tracks
    print(f"\n  Track counts: {a.source_format}={len(a.tracks)}, {b.source_format}={len(b.tracks)}")

    # Compare tracks by name
    a_tracks = {t.name: t for t in a.tracks}
    b_tracks = {t.name: t for t in b.tracks}

    all_names = sorted(set(a_tracks.keys()) | set(b_tracks.keys()))
    for name in all_names:
        at = a_tracks.get(name)
        bt = b_tracks.get(name)
        if at and not bt:
            print(f"\n  Track '{name}': only in {a.source_format} ({len(at.notes)} notes)")
        elif bt and not at:
            print(f"\n  Track '{name}': only in {b.source_format} ({len(bt.notes)} notes)")
        elif at and bt:
            a_notes = set((n.pitch, n.position, n.duration) for n in at.notes)
            b_notes = set((n.pitch, n.position, n.duration) for n in bt.notes)
            if a_notes != b_notes:
                only_a = a_notes - b_notes
                only_b = b_notes - a_notes
                print(f"\n  Track '{name}': note differences")
                if only_a:
                    print(f"    Only in {a.source_format}: {len(only_a)} notes")
                    for pitch, pos, dur in sorted(only_a)[:5]:
                        print(f"      {_note_name(pitch):5s} pos={pos:6d} dur={dur:5d}")
                if only_b:
                    print(f"    Only in {b.source_format}: {len(only_b)} notes")
                    for pitch, pos, dur in sorted(only_b)[:5]:
                        print(f"      {_note_name(pitch):5s} pos={pos:6d} dur={dur:5d}")
            else:
                print(f"\n  Track '{name}': identical ({len(a_notes)} notes)")

    # If no matching track names, compare by index
    if not any(n in b_tracks for n in a_tracks):
        print("\n  No matching track names. Comparing by position:")
        for i, (at, bt) in enumerate(zip(a.tracks, b.tracks)):
            a_count = len(at.notes)
            b_count = len(bt.notes)
            print(f"    Track {i}: {a.source_format}='{at.name}' ({a_count} notes) vs "
                  f"{b.source_format}='{bt.name}' ({b_count} notes)")


def cmd_read(args: list[str]) -> None:
    """Handle the 'read' command."""
    if not args:
        print("Usage: logico read <file>")
        sys.exit(1)

    path = args[0]
    print(f"Reading: {path}")
    project = _load_project(path)
    _print_project(project)


def cmd_diff(args: list[str]) -> None:
    """Handle the 'diff' command."""
    if len(args) < 2:
        print("Usage: logico diff <file1> <file2>")
        sys.exit(1)

    path_a, path_b = args[0], args[1]

    print(f"Project A: {path_a}")
    a = _load_project(path_a)
    _print_project(a)

    print(f"\nProject B: {path_b}")
    b = _load_project(path_b)
    _print_project(b)

    _diff_projects(a, b)


def _write_project(project: Project, path: str) -> None:
    """Write a project to a file."""
    fmt = _detect_format(path)

    if fmt == "staffpad":
        from .staffpad.writer import write_staffpad
        write_staffpad(project, path)
        print(f"  Written to StaffPad: {path}")
    elif fmt == "logic":
        from .logic.writer import write_logic
        write_logic(project, path)
        print(f"  Written to Logic Pro: {path}")
    elif fmt == "dorico":
        from .dorico.writer import write_dorico
        try:
            write_dorico(project, path)
            print(f"  Written to Dorico: {path}")
        except NotImplementedError as e:
            print(f"  Partial write to Dorico (notes not yet supported):")
            print(f"    {e}")
    else:
        print(f"  Writing not supported for format: {fmt}")


def cmd_sync(args: list[str]) -> None:
    """Handle the 'sync' command."""
    if len(args) < 2:
        print("Usage: logico sync <source> <destination>")
        sys.exit(1)

    source_path = args[0]
    dest_path = args[1]

    print(f"Source: {source_path}")
    source = _load_project(source_path)
    print(f"  {source.source_format}: {sum(len(t.notes) for t in source.tracks)} notes across {len(source.tracks)} tracks")

    print(f"\nDestination: {dest_path}")
    print(f"  Syncing notes...")

    _write_project(source, dest_path)

    # Verify
    print("\nVerifying...")
    result = _load_project(dest_path)
    print(f"  {result.source_format}: {sum(len(t.notes) for t in result.tracks)} notes across {len(result.tracks)} tracks")
    print("\nSync complete.")


def main() -> None:
    """CLI entry point."""
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print("Logico — Sync between Logic Pro, Dorico, and StaffPad")
        print()
        print("Commands:")
        print("  logico read <file>            Read and display a project")
        print("  logico diff <file1> <file2>   Compare two projects")
        print("  logico sync <source> <dest>   Sync notes from source to destination")
        print()
        print("Supported formats:")
        print("  .dorico   — Dorico project (read-only for now)")
        print("  .stf      — StaffPad project (read + write)")
        print("  .logicx   — Logic Pro project (read + write)")
        sys.exit(0)

    command = args[0]
    rest = args[1:]

    if command == "read":
        cmd_read(rest)
    elif command == "diff":
        cmd_diff(rest)
    elif command == "sync":
        cmd_sync(rest)
    else:
        print(f"Unknown command: {command}")
        print("Run 'logico --help' for usage")
        sys.exit(1)


if __name__ == "__main__":
    main()
