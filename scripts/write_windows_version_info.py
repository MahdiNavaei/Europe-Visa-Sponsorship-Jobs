"""Generate a PyInstaller Windows version-resource file for Career Radar.

The generated file is consumed by ``pyinstaller --version-file`` so SignPath can
verify product/version metadata before signing the launcher.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def _numeric_version(value: str) -> tuple[int, int, int, int]:
    parts = value.strip().split(".")
    if not 1 <= len(parts) <= 4 or any(not re.fullmatch(r"\d+", part) for part in parts):
        raise ValueError(f"Windows version must contain 1-4 numeric components: {value!r}")
    numbers = [int(part) for part in parts]
    if any(number < 0 or number > 65535 for number in numbers):
        raise ValueError("Windows version components must be between 0 and 65535")
    return tuple((numbers + [0, 0, 0, 0])[:4])  # type: ignore[return-value]


def render(version: str) -> str:
    numeric = _numeric_version(version)
    numeric_literal = ", ".join(str(part) for part in numeric)
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({numeric_literal}),
    prodvers=({numeric_literal}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Career Radar'),
          StringStruct('FileDescription', 'Career Radar Windows desktop application'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'CareerRadar'),
          StringStruct('LegalCopyright', 'Copyright (c) 2026 Mahdi Navaei'),
          StringStruct('OriginalFilename', 'CareerRadar.exe'),
          StringStruct('ProductName', 'Career Radar'),
          StringStruct('ProductVersion', '{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(args.version), encoding="utf-8")
    print(f"wrote Windows version metadata for {args.version} to {output}")


if __name__ == "__main__":
    main()
