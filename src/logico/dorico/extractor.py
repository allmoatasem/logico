"""Extract musical data from a parsed Dorico project into the common model."""

from __future__ import annotations

from ..dorico.dtn import DtnEntity, DtnKV, DtnFile
from ..dorico.parser import DoricoProject
from ..model import (
    Articulation,
    ArticulationType,
    Dynamic,
    DynamicType,
    Hairpin,
    KeySignatureEvent,
    Note,
    Project,
    TempoEvent,
    TimeSignatureEvent,
    Track,
    diatonic_to_midi,
)

# Map Dorico note names to fifths value
_NOTE_TO_FIFTHS = {
    "C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "C#": 7,
    "F": -1, "Bb": -2, "Eb": -3, "Ab": -4, "Db": -5, "Gb": -6, "Cb": -7,
}

# Map Dorico note names to diatonic step
_NOTE_NAME_TO_STEP = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}

# Map Dorico accidental IDs to alteration values
_ACCIDENTAL_TO_ALT = {
    "accidental.12et.western.natural": 0,
    "accidental.12et.western.sharp": 1,
    "accidental.12et.western.flat": -1,
    "accidental.12et.western.doublesharp": 2,
    "accidental.12et.western.doubleflat": -2,
}


def extract_project(dorico: DoricoProject) -> Project:
    """Extract a Project from a parsed Dorico file."""
    s = dorico.score
    k, v = s.keys, s.values
    root = s.root

    project = Project(source_format="dorico")

    # Title
    info = root.get_entity("info", k)
    if info:
        project.title = info.get_kv("title", k, v) or ""

    # Extract flows
    flows_entity = root.get_entity("flows", k)
    if not flows_entity:
        return project

    flows_arr = flows_entity.get_entity("array", k)
    if not flows_arr:
        return project

    # Process first flow (primary flow)
    for flow_node in flows_arr.children:
        if not isinstance(flow_node, DtnEntity):
            continue
        _extract_flow(flow_node, s, project)
        break  # Only first flow for now

    # Extract players/instruments for track names
    _extract_players(root, s, project)

    return project


def _extract_flow(flow: DtnEntity, s: DtnFile, project: Project) -> None:
    """Extract tempo, time sig, key sig, and notes from a flow."""
    k, v = s.keys, s.values

    # Extract element tables (time sig, key sig)
    et = flow.get_entity("elementTables", k)
    if et:
        et_arr = et.get_entity("array", k)
        if et_arr:
            for child in et_arr.children:
                if not isinstance(child, DtnEntity):
                    continue
                name = child.key(k)
                if name == "BarDivisionElementTableDefinition":
                    _extract_time_signatures(child, s, project)
                elif name == "TonalityDivisionElementTableDefinition":
                    _extract_key_signatures(child, s, project)

    # Extract blocks for note data
    blocks = flow.get_entity("blocks", k)
    if blocks:
        blocks_arr = blocks.get_entity("array", k)
        if blocks_arr:
            for block in blocks_arr.children:
                if not isinstance(block, DtnEntity):
                    continue
                bkvs = block.get_all_kvs(k, v)
                stream_type = bkvs.get("parentEventStreamType", "")
                if stream_type == "kVoiceStream":
                    _extract_voice_events(block, s, project)

    # Extract flow player/instrument mapping for track creation
    fp = flow.get_entity("flowPlayers", k)
    if fp:
        fp_arr = fp.get_entity("array", k)
        if fp_arr:
            for fp_node in fp_arr.children:
                if isinstance(fp_node, DtnEntity):
                    _extract_flow_player_streams(fp_node, s, project)


def _extract_time_signatures(
    table: DtnEntity, s: DtnFile, project: Project
) -> None:
    """Extract time signatures from BarDivisionElementTableDefinition."""
    k, v = s.keys, s.values
    arr = table.get_entity("array", k)
    if not arr:
        return

    for elem in arr.children:
        if not isinstance(elem, DtnEntity):
            continue

        bd = elem.get_entity("barDivisionData", k)
        if not bd:
            continue

        ts_container = bd.get_entity("timeSignature", k)
        if not ts_container:
            continue

        # Navigate: timeSignature > timeSignaturesAndDivisions > timeSignatureAndDivision > timeSignature
        tsad = ts_container.get_entity("timeSignaturesAndDivisions", k)
        if not tsad:
            continue

        for tsd_child in tsad.children:
            if not isinstance(tsd_child, DtnEntity):
                continue
            if tsd_child.key(k) != "timeSignatureAndDivision":
                continue

            inner_ts = tsd_child.get_entity("timeSignature", k)
            if not inner_ts:
                continue

            ts_kvs = inner_ts.get_all_kvs(k, v)
            num_str = ts_kvs.get("numerator", "4")
            den_str = ts_kvs.get("denominator", "4")

            try:
                numerator = int(num_str)
                denominator = int(den_str)
            except ValueError:
                continue

            project.time_signatures.append(
                TimeSignatureEvent(position=0, numerator=numerator, denominator=denominator)
            )


def _extract_key_signatures(
    table: DtnEntity, s: DtnFile, project: Project
) -> None:
    """Extract key signatures from TonalityDivisionElementTableDefinition."""
    k, v = s.keys, s.values
    arr = table.get_entity("array", k)
    if not arr:
        return

    for elem in arr.children:
        if not isinstance(elem, DtnEntity):
            continue

        td = elem.get_entity("tonalityDivisionData", k)
        if not td:
            continue

        ks_entity = td.get_entity("keySignature", k)
        if not ks_entity:
            continue

        root_entity = ks_entity.get_entity("root", k)
        if not root_entity:
            continue

        ks_kvs = root_entity.get_all_kvs(k, v)
        tonality_type = ks_kvs.get("tonalityType", "kKeySigMajor")
        mode = "minor" if "Minor" in tonality_type else "major"

        inner_root = root_entity.get_entity("root", k)
        if inner_root:
            root_kvs = inner_root.get_all_kvs(k, v)
            note_name = root_kvs.get("noteName", "C")
            accidental_id = root_kvs.get("accidentalID", "")

            # Build the key name with accidental
            alt = _ACCIDENTAL_TO_ALT.get(accidental_id, 0)
            if alt == 1:
                note_name += "#"
            elif alt == -1:
                note_name += "b"
            elif alt == 2:
                note_name += "##"
            elif alt == -2:
                note_name += "bb"

            fifths = _NOTE_TO_FIFTHS.get(note_name, 0)

            project.key_signatures.append(
                KeySignatureEvent(position=0, fifths=fifths, mode=mode)
            )


def _extract_voice_events(
    block: DtnEntity, s: DtnFile, project: Project
) -> None:
    """Extract note events from a voice stream block."""
    k, v = s.keys, s.values

    events = block.get_entity("events", k)
    if not events:
        return

    ev_arr = events.get_entity("array", k)
    if not ev_arr:
        return

    for ev in ev_arr.children:
        if not isinstance(ev, DtnEntity):
            continue

        ev_kvs = ev.get_all_kvs(k, v)
        ev_name = ev.key(k)

        # Note events in Dorico are typically NoteEventDefinition or similar
        if "Note" in ev_name or "note" in ev_name:
            _extract_note_event(ev, ev_kvs, s, project)


def _extract_note_event(
    event: DtnEntity,
    kvs: dict[str, str],
    s: DtnFile,
    project: Project,
) -> None:
    """Extract a single note event."""
    k, v = s.keys, s.values

    position = int(kvs.get("position", "0"))
    duration = int(kvs.get("duration", "0"))

    # Pitch data
    pitch_entity = event.get_entity("pitch", k)
    if not pitch_entity:
        return

    pitch_kvs = pitch_entity.get_all_kvs(k, v)
    step = int(pitch_kvs.get("diatonicStep", "0"))
    alteration = int(pitch_kvs.get("chromaticAlteration", "0"))
    octave = int(pitch_kvs.get("octave", "4"))

    midi_pitch = diatonic_to_midi(step, alteration, octave)
    velocity = int(kvs.get("velocity", "80"))

    note = Note(
        pitch=midi_pitch,
        velocity=velocity,
        position=position,
        duration=duration,
        diatonic_step=step,
        chromatic_alteration=alteration,
        octave=octave,
    )

    # Add to first track (or create one if needed)
    if not project.tracks:
        project.tracks.append(Track(name="", instrument=""))
    project.tracks[0].notes.append(note)


def _extract_flow_player_streams(
    fp: DtnEntity, s: DtnFile, project: Project
) -> None:
    """Extract flow player instrument info for track mapping."""
    # This sets up the track structure based on instruments in the flow
    pass


def _extract_players(root: DtnEntity, s: DtnFile, project: Project) -> None:
    """Extract player/instrument names from scorePlayers."""
    k, v = s.keys, s.values

    players = root.get_entity("scorePlayers", k)
    if not players:
        return

    arr = players.get_entity("array", k)
    if not arr:
        return

    for player_node in arr.children:
        if not isinstance(player_node, DtnEntity):
            continue

        pkvs = player_node.get_all_kvs(k, v)
        display_name = pkvs.get("displayName", pkvs.get("baseName", "Unknown"))

        # Get instrument info
        instruments = player_node.get_entity("instruments", k)
        instrument_id = ""
        if instruments:
            inst_arr = instruments.get_entity("array", k) or instruments
            for inst in (inst_arr.children if hasattr(inst_arr, 'children') else []):
                if isinstance(inst, DtnEntity):
                    inst_kvs = inst.get_all_kvs(k, v)
                    instrument_id = inst_kvs.get("entityID", "")
                    break

        # Create or update track
        track_exists = any(t.name == display_name for t in project.tracks)
        if not track_exists:
            if project.tracks and project.tracks[0].name == "":
                # Update the unnamed track created during note extraction
                project.tracks[0].name = display_name
                project.tracks[0].instrument = instrument_id
            else:
                project.tracks.append(
                    Track(name=display_name, instrument=instrument_id)
                )
