import os
import sys
from pathlib import Path
import struct
import ast


def _unquote(s: str) -> str:
    # s includes the surrounding quotes; use ast.literal_eval for C-like escapes
    return ast.literal_eval(s)


def parse_po(po_path: Path):
    messages = {}
    with po_path.open("r", encoding="utf-8") as f:
        msgid = ""
        msgid_plural = None
        msgstrs = {}
        state = None  # 'msgid' | 'msgid_plural' | 'msgstr' | ('msgstr', idx)

        def finalize():
            nonlocal msgid, msgid_plural, msgstrs
            if msgid != "":
                if msgid_plural is not None:
                    # plural: original is msgid + \0 + msgid_plural
                    orig = msgid + "\x00" + msgid_plural
                    trans = "\x00".join(v for k, v in sorted(msgstrs.items()))
                else:
                    orig = msgid
                    trans = msgstrs.get(0, "") if msgstrs else ""
                messages[orig] = trans
            else:
                # header (msgid == ""): still store it
                header = msgstrs.get(0, "") if msgstrs else ""
                messages[""] = header
            msgid = ""
            msgid_plural = None
            msgstrs = {}

        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                # empty or comment: end of an entry
                if state is not None and not line:
                    finalize()
                    state = None
                continue
            if line.startswith("msgid "):
                if state is not None:
                    finalize()
                msgid = _unquote(line[5:].strip())
                msgid_plural = None
                msgstrs = {}
                state = "msgid"
                continue
            if line.startswith("msgid_plural "):
                msgid_plural = _unquote(line[len("msgid_plural ") :].strip())
                state = "msgid_plural"
                continue
            if line.startswith("msgstr["):
                idx_end = line.index("]")
                idx = int(line[len("msgstr[") : idx_end])
                eq = line.index("=", idx_end)
                msgstrs[idx] = _unquote(line[eq + 1 :].strip())
                state = ("msgstr", idx)
                continue
            if line.startswith("msgstr "):
                msgstrs[0] = _unquote(line[6:].strip())
                state = ("msgstr", 0)
                continue
            if line.startswith('"'):
                # continuation line
                text = _unquote(line)
                if state == "msgid":
                    msgid += text
                elif state == "msgid_plural":
                    msgid_plural = (msgid_plural or "") + text
                elif isinstance(state, tuple) and state[0] == "msgstr":
                    idx = state[1]
                    msgstrs[idx] = msgstrs.get(idx, "") + text
                continue
        # EOF finalize any pending
        if state is not None:
            finalize()
    return messages


def write_mo(messages: dict, mo_path: Path):
    # Ensure header exists
    if "" not in messages:
        messages[""] = (
            "Project-Id-Version: \n\n" "Content-Type: text/plain; charset=UTF-8\n"
        )
    # Sort by msgid for deterministic output
    ids = sorted(messages.keys())
    strs = [messages[_id] for _id in ids]

    # Prepare binary tables
    keystart = 7 * 4 + len(ids) * 8 * 2  # header + 2 tables
    o_offsets = []
    t_offsets = []
    data = bytearray()

    # originals
    o_cursor = keystart
    for s in ids:
        b = s.encode("utf-8")
        o_offsets.append((len(b), o_cursor))
        o_cursor += len(b) + 1
        data += b + b"\x00"

    # translations
    t_cursor = o_cursor
    for s in strs:
        b = s.encode("utf-8")
        t_offsets.append((len(b), t_cursor))
        t_cursor += len(b) + 1
        data += b + b"\x00"

    with mo_path.open("wb") as fp:
        # magic, version, n, orig_tab_ofs, trans_tab_ofs, hash_size, hash_ofs
        fp.write(
            struct.pack(
                "Iiiiiii",
                0x950412DE,
                0,
                len(ids),
                28,
                28 + len(ids) * 8,
                0,
                28 + len(ids) * 16,
            )
        )
        for l, o in o_offsets:
            fp.write(struct.pack("ii", l, o))
        for l, o in t_offsets:
            fp.write(struct.pack("ii", l, o))
        fp.write(data)


def compile_po_to_mo(po_path: Path) -> Path:
    mo_path = po_path.with_suffix(".mo")
    messages = parse_po(po_path)
    write_mo(messages, mo_path)
    return mo_path


def main() -> int:
    base = Path(__file__).parent
    targets = [
        base / "locales" / "zh_CN" / "LC_MESSAGES" / "messages.po",
        base / "locales" / "en_EN" / "LC_MESSAGES" / "messages.po",
    ]
    for po in targets:
        if po.exists():
            mo = compile_po_to_mo(po)
            print(f"Compiled: {mo}")
        else:
            print(f"Skipped (missing): {po}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
