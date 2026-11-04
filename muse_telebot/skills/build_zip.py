"""Dong goi cac skill (thu muc co SKILL.md + skill.yaml) vao dist/muse_skills.zip de gui len profile Muse.
Bot (muse_skills.py) goi build() truoc moi lan cai nen sua skill xong khong can chay tay."""
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "dist" / "muse_skills.zip"


def build():
    """Tao lai OUT tu cac thu muc skill. Tra ve (duong dan zip, ten cac skill)."""
    skills = sorted(p.parent for p in HERE.glob("*/skill.yaml") if (p.parent / "SKILL.md").exists())
    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for skill in skills:
            for f in sorted(skill.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    z.write(f, f.relative_to(HERE).as_posix())
    return OUT, [s.name for s in skills]


if __name__ == "__main__":
    out, names = build()
    print(f"{out}: {', '.join(names)}")
