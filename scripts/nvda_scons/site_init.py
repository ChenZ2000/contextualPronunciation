"""Opt-in build-environment adapter for a project-local LLVM, not an NVDA patch.

SCons deliberately does not inherit the calling shell's PATH. Supply only the
explicit compiler directory; preserve all upstream C/C++ code, flags and tools.
"""

import os
from pathlib import Path

import SCons.Platform.win32
import SCons.Tool
import SCons.Tool.msvc

_nvda_root = Path.cwd()
SCons.Tool.DefaultToolpath.insert(0, str(_nvda_root / "site_scons/site_tools"))
_llvm_bin = Path(os.environ["CONTEXTUAL_PRONUNCIATION_LLVM_BIN"]).resolve(strict=True)
if not (_llvm_bin / "clang-cl.exe").is_file():
	raise RuntimeError("Explicit LLVM path does not contain clang-cl.exe")

_original_generate = SCons.Platform.win32.generate


def _generate_with_local_llvm(env):
	_original_generate(env)
	env.PrependENVPath("PATH", str(_llvm_bin))


SCons.Platform.win32.generate = _generate_with_local_llvm
print(f"Explicit local LLVM for SCons: {_llvm_bin}")

# Some VS component selections provide ARM64 ATL only in the same toolset's
# Spectre-mitigated directory. This is an explicit build-only opt-in; never
# substitute a different architecture/toolset or suppress a link error.
if os.environ.get("CONTEXTUAL_PRONUNCIATION_SPECTRE_ATL") == "1":
	_original_msvc_generate = SCons.Tool.msvc.generate

	def _generate_with_available_atl(env):
		_original_msvc_generate(env)
		if env.get("TARGET_ARCH") != "arm64":
			return
		for directory in env.get("ENV", {}).get("LIB", "").split(os.pathsep):
			path = Path(directory)
			if path.name.lower() != "arm64" or path.parent.name.lower() != "lib":
				continue
			toolset = path.parent.parent
			if toolset.parent.name.lower() != "msvc":
				continue
			normal = toolset / "atlmfc/lib/arm64/atls.lib"
			fallback = toolset / "atlmfc/lib/spectre/arm64"
			if not normal.is_file() and (fallback / "atls.lib").is_file():
				env.AppendENVPath("LIB", str(fallback))
				print(f"Explicit same-toolset ARM64 Spectre ATL fallback: {fallback}")

	SCons.Tool.msvc.generate = _generate_with_available_atl
