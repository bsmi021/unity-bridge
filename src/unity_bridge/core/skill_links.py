"""Cross-agent directory linking for the bundled unity-bridge-cli skill.

Codex and GitHub Copilot both scan ``.agents/skills/<name>`` natively (the
open Agent Skills standard), so they need no extra files once the bridge
skill is installed there. Claude Code only scans ``.claude/skills/<name>``,
so reusing one physical skill directory across agents requires a real
directory link (a symlink, or an NTFS junction on Windows when symlink
privilege is unavailable) from the Claude Code path back to the canonical
``.agents/skills/<name>`` directory.
"""

import platform
import subprocess
from pathlib import Path

_REPARSE_POINT_ATTR = 0x400
_INVALID_FILE_ATTRIBUTES = -1


class SkillLinkError(Exception):
    """Raised when a skill directory link cannot be created, or the target
    path is occupied by unrelated content this function must not touch."""


def is_directory_link(path: Path) -> bool:
    """Return True if path is a symlink or (on Windows) an NTFS junction."""
    if path.is_symlink():
        return True
    if platform.system() != "Windows":
        return False

    import ctypes

    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    return attrs != _INVALID_FILE_ATTRIBUTES and bool(attrs & _REPARSE_POINT_ATTR)


def create_directory_link(link_path: Path, target_path: Path) -> str:
    """Point link_path at target_path, reusing an existing correct link.

    Prefers a real symlink; falls back to an NTFS junction on Windows when
    symlink creation fails (no admin rights / Developer Mode disabled).

    Args:
        link_path: Path to create (or verify) as a link.
        target_path: Existing directory the link should point at.

    Returns:
        "up_to_date" if link_path already points at target_path, otherwise
        "symlink" or "junction" for the link type actually created.

    Raises:
        SkillLinkError: link_path exists and is not a link this function
            manages, or no link could be created by any available method.
    """
    target = target_path.resolve()

    if link_path.exists() or link_path.is_symlink():
        if not is_directory_link(link_path):
            raise SkillLinkError(
                f"{link_path} already exists and is not a symlink/junction -- "
                "remove or back it up before linking a skill there."
            )
        if link_path.resolve() == target:
            return "up_to_date"
        _remove_directory_link(link_path)

    link_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        link_path.symlink_to(target, target_is_directory=True)
        return "symlink"
    except OSError as symlink_error:
        if platform.system() != "Windows":
            raise SkillLinkError(str(symlink_error)) from symlink_error
        return _create_windows_junction(link_path, target, symlink_error)


def _remove_directory_link(link_path: Path) -> None:
    """Remove a symlink/junction without touching the linked-to content.

    ``unlink()`` removes directory symlinks and junctions on modern
    Windows/Python; ``rmdir()`` is the fallback for combinations where it
    doesn't (Windows requires the "directory delete" API for some reparse
    point configurations).
    """
    try:
        link_path.unlink()
    except OSError:
        link_path.rmdir()


def _create_windows_junction(link_path: Path, target: Path, symlink_error: OSError) -> str:
    """Create an NTFS junction as the no-privilege fallback for os.symlink."""
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link_path), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SkillLinkError(
            f"Could not create a symlink ({symlink_error}) or an NTFS junction "
            f"for {link_path}: {detail}. Enable Windows Developer Mode or run "
            f'as Administrator, or create the junction manually: '
            f'mklink /J "{link_path}" "{target}"'
        )
    return "junction"
