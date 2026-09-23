#!/usr/bin/env python3
"""Read-only capability and acoustic probe for Vocalizer Expressive 2.2.

This helper deliberately does not import NVDA's high-level synth driver.  The
high-level driver constructs ``nvwave.WavePlayer`` and can therefore compete
with a running NVDA instance for the user's audio device.  Instead, render mode
loads the driver's bundled low-level ``ve2`` wrapper in this helper process and
captures the PCM callback directly to WAV files.

The helper never installs an add-on, edits NVDA configuration, writes into an
NVDA/add-on directory, or plays audio.  Its only writes are the report/WAV files
under ``--output-dir``.

Examples::

    python tools/probe_vocalizer_expressive2.py static
    python tools/probe_vocalizer_expressive2.py inventory
    python tools/probe_vocalizer_expressive2.py render --voice Ting-Ting \
        --fixture tests/fixtures/vocalizer_expressive2/renderer_cases.json

The numeric ``usPhoneme`` values returned by Vocalizer are engine-private IDs,
not IPA.  They are still useful for equality comparisons made with the same
engine build, voice, operating point, sample rate and surrounding carrier text.
Human listening remains the final oracle for a renderer candidate.
"""

from __future__ import annotations

import argparse
import ast
import ctypes.wintypes
import hashlib
import importlib.util
import json
import os
import platform
import re
import sys
import wave
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

DRIVER_ADDON_NAME = "vocalizer_expressive2_driver"
VOICE_ADDON_PREFIXES = (
	"vocalizer-expressive2-voice",
	"vocalizer-expressive-voice",
)
DEFAULT_FIXTURE = Path("tests/fixtures/vocalizer_expressive2/renderer_cases.json")
DEFAULT_OUTPUT_DIR = Path("artifacts/vocalizer_expressive2_probe")
SAMPLE_RATE = 22_050
PCM_CHANNELS = 1
PCM_SAMPLE_WIDTH_BYTES = 2
PCM_BUFFER_BYTES = 8_192
MARK_BUFFER_ITEMS = 100


def _default_nvda_config_dir() -> Path:
	app_data = os.environ.get("APPDATA")
	if not app_data:
		raise RuntimeError("APPDATA is not set; pass --nvda-config-dir explicitly")
	return Path(app_data) / "nvda"


def _default_driver_root(nvda_config_dir: Path) -> Path:
	return nvda_config_dir / "addons" / DRIVER_ADDON_NAME


def _read_manifest_fields(manifest_path: Path) -> dict[str, str]:
	"""Read only the simple top-level key/value fields used by this probe.

	NVDA manifests allow triple-quoted multiline values, which standard library
	``configparser`` does not parse in the same way as NVDA's ConfigObj.  A small
	line parser is sufficient for the non-multiline fields we report.
	"""
	result: dict[str, str] = {}
	for line in manifest_path.read_text(encoding="utf-8-sig").splitlines():
		match = re.match(r"^([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
		if not match:
			continue
		value = match.group(2)
		if value.startswith('"""'):
			continue
		result[match.group(1)] = value.strip('"')
	return result


def _extract_supported_commands(source_path: Path) -> list[str]:
	tree = ast.parse(source_path.read_text(encoding="utf-8-sig"), filename=str(source_path))
	for node in tree.body:
		if not isinstance(node, ast.ClassDef) or node.name != "SynthDriver":
			continue
		for statement in node.body:
			if not isinstance(statement, ast.Assign):
				continue
			if not any(
				isinstance(target, ast.Name) and target.id == "supportedCommands" for target in statement.targets
			):
				continue
			if not isinstance(statement.value, (ast.Set, ast.Tuple, ast.List)):
				return []
			result = []
			for item in statement.value.elts:
				if isinstance(item, ast.Name):
					result.append(item.id)
				else:
					result.append(ast.unparse(item))
			return sorted(result)
	return []


def _source_capabilities(source_path: Path) -> dict[str, Any]:
	source = source_path.read_text(encoding="utf-8-sig")
	supported = _extract_supported_commands(source_path)
	return {
		"supportedCommands": supported,
		"declaresPhonemeCommand": "PhonemeCommand" in supported,
		"hasPhonemeFallbackBranch": "isinstance(command, PhonemeCommand)" in source,
		"phonemeFallbackUsesTextOnly": bool(
			re.search(
				r"isinstance\(command,\s*PhonemeCommand\).*?chunks\.append\(command\.text",
				source,
				flags=re.DOTALL,
			),
		),
		"stripsEachTextChunk": "command = command.strip()" in source,
		"insertsChunkSeparatorBetweenTextChunks": "chunks.append(speech.CHUNK_SEPARATOR)" in source,
		"removesRawEscapeFromText": 'command.replace("\\x1b", "")' in source,
		"usesPcmCallback": "VE_MSG_OUTBUFDONE" in source and "self._player.feed" in source,
		"loadsPerVoiceRuleset": "TEXT_RULESET_CONTENT_TYPE" in source and "resourceLoad" in source,
		"loadsPerVoiceBinaryDictionary": "BIN_DICT_CONTENT_TYPE" in source and "resourceLoad" in source,
	}


def _detect_running_nvda() -> list[dict[str, Any]]:
	"""Best-effort process inventory without pywin32 or psutil dependencies."""
	if os.name != "nt":
		return []
	try:
		import subprocess

		completed = subprocess.run(
			[
				"powershell.exe",
				"-NoProfile",
				"-NonInteractive",
				"-Command",
				"Get-CimInstance Win32_Process -Filter \"Name='nvda.exe'\" | "
				"Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress",
			],
			check=False,
			capture_output=True,
			text=True,
			encoding="utf-8",
			errors="replace",
			timeout=10,
		)
		if completed.returncode or not completed.stdout.strip():
			return []
		data = json.loads(completed.stdout)
		if isinstance(data, dict):
			data = [data]
		return [item for item in data if isinstance(item, dict)]
	except Exception:
		return []


def static_report(nvda_config_dir: Path, driver_root: Path) -> dict[str, Any]:
	manifest = driver_root / "manifest.ini"
	driver_source = driver_root / "synthDrivers" / "vocalizer_expressive2" / "__init__.py"
	ve_types = driver_root / "synthDrivers" / "vocalizer_expressive2" / "ve2" / "veTypes.py"
	missing = [str(path) for path in (manifest, driver_source, ve_types) if not path.is_file()]
	if missing:
		raise FileNotFoundError(f"Vocalizer driver files not found: {missing}")

	voice_roots = _find_voice_roots(nvda_config_dir)
	return {
		"probeMode": "static",
		"driverRoot": str(driver_root.resolve()),
		"manifest": _read_manifest_fields(manifest),
		"python": {
			"executable": sys.executable,
			"version": platform.python_version(),
			"architecture": platform.architecture()[0],
		},
		"runningNvda": _detect_running_nvda(),
		"voiceResourceRoots": [str(path.resolve()) for path in voice_roots],
		"sourceCapabilities": _source_capabilities(driver_source),
		"lowLevelCallbackCapabilities": {
			"pcm": True,
			"textUnitMarkers": True,
			"wordMarkers": True,
			"phonemeMarkers": True,
			"bookmarkMarkers": True,
			"phonemeMarkerMeaning": "engine-private numeric ID; not IPA",
		},
		"safety": {
			"importsNvdaHighLevelDriver": False,
			"opensAudioOutputDevice": False,
			"editsNvdaConfiguration": False,
			"writesIntoAddons": False,
		},
	}


def _find_voice_roots(nvda_config_dir: Path) -> list[Path]:
	addons_dir = nvda_config_dir / "addons"
	result: list[Path] = []
	if addons_dir.is_dir():
		for child in addons_dir.iterdir():
			if child.is_dir() and child.name.startswith(VOICE_ADDON_PREFIXES):
				result.append(child)

	program_data = os.environ.get("PROGRAMDATA")
	if program_data:
		for version in ("2.2", "21"):
			candidate = Path(program_data) / "Freedom Scientific" / "VocalizerExpressive" / version / "languages"
			try:
				if candidate.is_dir() and any(candidate.iterdir()):
					result.append(candidate)
			except OSError:
				pass
	return sorted(result, key=lambda item: str(item).casefold())


def _load_low_level_ve2(driver_root: Path):
	"""Load the installed low-level wrapper without importing SynthDriver."""
	package_dir = driver_root / "synthDrivers" / "vocalizer_expressive2" / "ve2"
	init_path = package_dir / "__init__.py"
	if not init_path.is_file():
		raise FileNotFoundError(f"Low-level Vocalizer wrapper not found: {init_path}")
	module_name = "_vespeechdic_vocalizer_ve2"
	spec = importlib.util.spec_from_file_location(
		module_name,
		init_path,
		submodule_search_locations=[str(package_dir)],
	)
	if spec is None or spec.loader is None:
		raise ImportError(f"Could not create an import spec for {init_path}")
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	# The installed 2026.6.6 wrapper refers to ``wintypes.HMODULE`` in its
	# shutdown path without importing ``ctypes.wintypes`` into its own globals.
	# NVDA's wider import environment can mask this; the isolated loader cannot.
	# Injecting the standard-library module fixes cleanup without touching the
	# installed source or changing any engine behaviour.
	if not hasattr(module, "wintypes"):
		module.wintypes = ctypes.wintypes
	return module


def _decode_c_string(value: Any) -> str:
	if isinstance(value, bytes):
		return value.split(b"\0", 1)[0].decode("utf-8", "replace")
	return bytes(value).split(b"\0", 1)[0].decode("utf-8", "replace")


def _initialize_engine(ve2: Any, resource_paths: Sequence[Path]) -> None:
	if not resource_paths:
		raise RuntimeError("No Vocalizer voice resource add-ons were found")
	# ``ve2.initialize`` mutates the list by inserting the common resource path.
	ve2.initialize([str(path) for path in resource_paths])


def inventory_report(nvda_config_dir: Path, driver_root: Path) -> dict[str, Any]:
	base = static_report(nvda_config_dir, driver_root)
	ve2 = _load_low_level_ve2(driver_root)
	resource_paths = _find_voice_roots(nvda_config_dir)
	initialized = False
	try:
		_initialize_engine(ve2, resource_paths)
		initialized = True
		languages = []
		for language in ve2.getLanguageList():
			language_name = _decode_c_string(language.szLanguage)
			voices = []
			for voice in ve2.getVoiceList(language.szLanguage):
				voice_name = _decode_c_string(voice.szVoiceName)
				voices.append(
					{
						"name": voice_name,
						"version": _decode_c_string(voice.szVersion),
						"language": _decode_c_string(voice.szLanguage),
						"age": _decode_c_string(voice.szVoiceAge),
						"type": _decode_c_string(voice.szVoiceType),
						"operatingPoints": ve2.getSpeechDBList(language_name, voice_name),
					},
				)
			languages.append(
				{
					"name": language_name,
					"tlw": _decode_c_string(language.szLanguageTLW),
					"version": _decode_c_string(language.szVersion),
					"voices": voices,
				},
			)
		product = ve2.getProductVersion()
		additional = ve2.getAdditionalProductInfo()
		base.update(
			{
				"probeMode": "inventory",
				"engineProductVersion": f"{product.major}.{product.minor}.{product.maint}",
				"engineBuild": {
					"year": int(additional.buildYar),
					"month": int(additional.buildMonth),
					"day": int(additional.buildDay),
					"info": _decode_c_string(additional.buildInfoStr),
				},
				"languages": languages,
			},
		)
		return base
	finally:
		if initialized:
			ve2.terminate()


class PcmAndMarkerCapture:
	def __init__(self, ve2: Any) -> None:
		self._ve2 = ve2
		self._pcm_buffer = (ve2.c_byte * PCM_BUFFER_BYTES)()
		self._marker_buffer = (ve2.VE_MARKINFO * MARK_BUFFER_ITEMS)()
		self.pcm = bytearray()
		self.markers: list[dict[str, int]] = []
		self.callback = ve2.VE_CBOUTNOTIFY(self._callback)

	def reset(self) -> None:
		self.pcm.clear()
		self.markers.clear()

	def _callback(self, instance: Any, user_data: Any, message: Any) -> int:
		try:
			message_type = int(message.contents.eMessage)
			if message_type not in (self._ve2.VE_MSG_OUTBUFREQ, self._ve2.VE_MSG_OUTBUFDONE):
				return self._ve2.NUAN_OK
			out_data = self._ve2.cast(message.contents.pParam, self._ve2.POINTER(self._ve2.VE_OUTDATA))
			if message_type == self._ve2.VE_MSG_OUTBUFREQ:
				out_data.contents.pOutPcmBuf = self._ve2.cast(self._pcm_buffer, self._ve2.c_void_p)
				out_data.contents.cntPcmBufLen = self._ve2.c_size_t(PCM_BUFFER_BYTES)
				out_data.contents.pMrkList = self._ve2.cast(
					self._marker_buffer,
					self._ve2.POINTER(self._ve2.VE_MARKINFO),
				)
				# Match the installed driver: input is buffer capacity in bytes; output
				# is treated as an item count.  Bounds below protect against a broken SDK.
				out_data.contents.cntMrkListLen = self._ve2.c_size_t(
					MARK_BUFFER_ITEMS * self._ve2.sizeof(self._ve2.VE_MARKINFO),
				)
				return self._ve2.NUAN_OK

			pcm_byte_count = min(int(out_data.contents.cntPcmBufLen), PCM_BUFFER_BYTES)
			if pcm_byte_count > 0:
				self.pcm.extend(self._ve2.string_at(out_data.contents.pOutPcmBuf, pcm_byte_count))
			marker_count = min(int(out_data.contents.cntMrkListLen), MARK_BUFFER_ITEMS)
			for index in range(marker_count):
				marker = out_data.contents.pMrkList[index]
				self.markers.append(
					{
						"type": int(marker.eMrkType),
						"info": int(marker.ulMrkInfo),
						"sourcePosition": int(marker.cntSrcPos),
						"sourceTextLength": int(marker.cntSrcTextLen),
						"destinationPosition": int(marker.cntDestPos),
						"destinationLength": int(marker.cntDestLen),
						"phoneme": int(marker.usPhoneme),
						"bookmarkId": int(marker.ulMrkId),
						"parameter": int(marker.ulParam),
					},
				)
		except Exception as error:
			# ctypes callbacks must never let an exception escape through the DLL.
			print(f"Vocalizer callback error: {error!r}", file=sys.stderr)
		return self._ve2.NUAN_OK


def _safe_case_id(raw: str) -> str:
	result = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
	if not result:
		raise ValueError(f"Case ID has no filesystem-safe characters: {raw!r}")
	return result


def _write_wav(path: Path, pcm: bytes) -> None:
	with wave.open(str(path), "wb") as wav_file:
		wav_file.setnchannels(PCM_CHANNELS)
		wav_file.setsampwidth(PCM_SAMPLE_WIDTH_BYTES)
		wav_file.setframerate(SAMPLE_RATE)
		wav_file.writeframes(pcm)


def _load_cases(fixture_path: Path | None, cli_cases: Iterable[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
	metadata: dict[str, Any] = {}
	cases: list[dict[str, Any]] = []
	if fixture_path is not None:
		fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
		if not isinstance(fixture, dict) or not isinstance(fixture.get("cases"), list):
			raise ValueError(f"Fixture must be an object with a cases array: {fixture_path}")
		metadata = {key: value for key, value in fixture.items() if key != "cases"}
		cases.extend(fixture["cases"])
	for item in cli_cases:
		case_id, separator, text = item.partition("=")
		if not separator or not case_id or not text:
			raise ValueError(f"--case must have the form ID=TEXT, got {item!r}")
		cases.append({"id": case_id, "text": text})
	if not cases:
		raise ValueError("Render mode needs --fixture and/or at least one --case ID=TEXT")

	seen: set[str] = set()
	for case in cases:
		if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not isinstance(case.get("text"), str):
			raise ValueError("Each case must contain string id and text fields")
		if case["id"] in seen:
			raise ValueError(f"Duplicate case id: {case['id']}")
		seen.add(case["id"])
		if "targetCharIndex" in case:
			index = case["targetCharIndex"]
			if not isinstance(index, int) or index < 0 or index >= len(case["text"]):
				raise ValueError(f"Invalid targetCharIndex in case {case['id']}")
	return cases, metadata


def _marker_type_name(ve2: Any, marker_type: int) -> str:
	return {
		ve2.VE_MRK_TEXTUNIT: "textUnit",
		ve2.VE_MRK_WORD: "word",
		ve2.VE_MRK_PHONEME: "phoneme",
		ve2.VE_MRK_BOOKMARK: "bookmark",
		ve2.VE_MRK_PROMPT: "prompt",
	}.get(marker_type, f"unknown:{marker_type}")


def _possible_target_marker_views(text: str, target_index: int, markers: Sequence[dict[str, int]]) -> dict[str, Any]:
	"""Return several coordinate interpretations without pretending SDK certainty.

	Vocalizer marker position units are not documented in the bundled wrapper.
	Depending on the engine and input encoding they can behave like UTF-8 bytes,
	Unicode code points, or UTF-16 code units.  The report exposes all three views;
	the one producing a plausible target phoneme sequence can be selected during
	fixture calibration.
	"""
	spans = {
		"codePoints": (target_index, target_index + 1),
		"utf8Bytes": (
			len(text[:target_index].encode("utf-8")),
			len(text[: target_index + 1].encode("utf-8")),
		),
		"utf16CodeUnits": (
			len(text[:target_index].encode("utf-16-le")) // 2,
			len(text[: target_index + 1].encode("utf-16-le")) // 2,
		),
	}
	views: dict[str, Any] = {}
	for name, (start, end) in spans.items():
		selected = []
		for marker in markers:
			if marker["typeName"] != "phoneme":
				continue
			marker_start = marker["sourcePosition"]
			marker_end = marker_start + max(marker["sourceTextLength"], 1)
			if marker_start < end and marker_end > start:
				selected.append(marker)
		views[name] = {
			"span": [start, end],
			"phonemes": [marker["phoneme"] for marker in selected],
			"markers": selected,
		}
	return views


def _compare_target_views(case_reports: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
	groups: dict[str, list[dict[str, Any]]] = {}
	for report in case_reports:
		group = report.get("compareGroup")
		if isinstance(group, str) and report.get("targetMarkerViews"):
			groups.setdefault(group, []).append(report)

	comparisons = []
	for group, members in sorted(groups.items()):
		anchors = [member for member in members if member.get("role") == "anchor"]
		for coordinate in ("codePoints", "utf8Bytes", "utf16CodeUnits"):
			anchor_sequences = {
				member["id"]: member["targetMarkerViews"][coordinate]["phonemes"]
				for member in anchors
				if member["targetMarkerViews"][coordinate]["phonemes"]
			}
			if not anchor_sequences:
				continue
			for member in members:
				sequence = member["targetMarkerViews"][coordinate]["phonemes"]
				comparisons.append(
					{
						"group": group,
						"coordinate": coordinate,
						"caseId": member["id"],
						"phonemes": sequence,
						"matchingAnchorIds": [
							anchor_id
							for anchor_id, anchor_sequence in anchor_sequences.items()
							if sequence and sequence == anchor_sequence
						],
					},
				)
	return comparisons


def _compare_complete_outputs(case_reports: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Compare complete phoneme streams and PCM against anchors in each group.

	Vocalizer 2.2 emits useful source spans on word markers, but its phoneme
	markers set ``cntSrcPos`` and ``cntSrcTextLen`` to zero.  Complete-stream
	comparison is therefore the most robust automatic check when paired fixture
	texts differ only at the target character/apostrophe.  It also catches
	coarticulation and pause differences that a target-only check would miss.
	"""
	groups: dict[str, list[dict[str, Any]]] = {}
	for report in case_reports:
		group = report.get("compareGroup")
		if isinstance(group, str):
			groups.setdefault(group, []).append(report)
	comparisons: list[dict[str, Any]] = []
	for group, members in sorted(groups.items()):
		anchors = [member for member in members if member.get("role") == "anchor"]
		for member in members:
			phonemes = member["allPhonemes"]
			comparisons.append(
				{
					"group": group,
					"caseId": member["id"],
					"phonemes": phonemes,
					"matchingCompletePhonemeAnchorIds": [
						anchor["id"] for anchor in anchors if phonemes and phonemes == anchor["allPhonemes"]
					],
					"matchingPcmAnchorIds": [
						anchor["id"] for anchor in anchors if member["pcmSha256"] == anchor["pcmSha256"]
					],
				},
			)
	return comparisons


def render_report(
	nvda_config_dir: Path,
	driver_root: Path,
	voice_name: str,
	cases: Sequence[dict[str, Any]],
	fixture_metadata: dict[str, Any],
	output_dir: Path,
) -> dict[str, Any]:
	base = inventory_report(nvda_config_dir, driver_root)
	available_voice_names = {voice["name"] for language in base["languages"] for voice in language["voices"]}
	if voice_name not in available_voice_names:
		raise ValueError(f"Voice {voice_name!r} is unavailable; found {sorted(available_voice_names)}")

	output_dir.mkdir(parents=True, exist_ok=True)
	ve2 = _load_low_level_ve2(driver_root)
	resource_paths = _find_voice_roots(nvda_config_dir)
	initialized = False
	instance = None
	case_reports: list[dict[str, Any]] = []
	try:
		_initialize_engine(ve2, resource_paths)
		initialized = True
		capture = PcmAndMarkerCapture(ve2)
		instance, actual_voice_name = ve2.open(voice_name, capture.callback)
		actual_voice_name = (
			_decode_c_string(actual_voice_name) if not isinstance(actual_voice_name, str) else actual_voice_name
		)
		for case in cases:
			capture.reset()
			ve2.processText2Speech(instance, case["text"])
			case_id = _safe_case_id(case["id"])
			wav_name = f"{case_id}.wav"
			wav_path = output_dir / wav_name
			pcm = bytes(capture.pcm)
			_write_wav(wav_path, pcm)
			markers = []
			for marker in capture.markers:
				markers.append({**marker, "typeName": _marker_type_name(ve2, marker["type"])})
			report = {
				**case,
				"wav": wav_name,
				"pcmBytes": len(pcm),
				"durationSeconds": len(pcm) / (SAMPLE_RATE * PCM_SAMPLE_WIDTH_BYTES * PCM_CHANNELS),
				"pcmSha256": hashlib.sha256(pcm).hexdigest(),
				"markers": markers,
				"allPhonemes": [marker["phoneme"] for marker in markers if marker["typeName"] == "phoneme"],
			}
			if "targetCharIndex" in case:
				report["targetCharacter"] = case["text"][case["targetCharIndex"]]
				report["targetMarkerViews"] = _possible_target_marker_views(
					case["text"],
					case["targetCharIndex"],
					markers,
				)
			case_reports.append(report)
		base.update(
			{
				"probeMode": "render",
				"voice": actual_voice_name,
				"sampleFormat": {
					"sampleRate": SAMPLE_RATE,
					"channels": PCM_CHANNELS,
					"sampleWidthBytes": PCM_SAMPLE_WIDTH_BYTES,
				},
				"fixtureMetadata": fixture_metadata,
				"cases": case_reports,
				"targetMarkerComparisons": _compare_target_views(case_reports),
				"completeOutputComparisons": _compare_complete_outputs(case_reports),
				"interpretationWarning": (
					"Numeric phoneme markers are engine-private IDs. Exact equality within this "
					"single run is evidence, not a cross-version phonetic specification. Listen "
					"to each WAV before selecting a renderer."
				),
			},
		)
		return base
	finally:
		if instance is not None:
			ve2.close(instance)
		if initialized:
			ve2.terminate()


def _write_json_report(report: dict[str, Any], path: Path | None) -> None:
	serialized = json.dumps(report, ensure_ascii=False, indent=2)
	if path is not None:
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(serialized + "\n", encoding="utf-8")
		print(f"{report.get('probeMode', 'probe')}: {len(report.get('cases', []))} cases; report: {path}")
	else:
		print(serialized)


def build_argument_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"mode",
		choices=("static", "inventory", "render"),
		nargs="?",
		default="static",
		help="static never loads vendor DLLs; inventory enumerates; render writes WAV/marker artifacts",
	)
	parser.add_argument("--nvda-config-dir", type=Path, help="default: %%APPDATA%%/nvda")
	parser.add_argument("--driver-root", type=Path, help="installed vocalizer_expressive2_driver root")
	parser.add_argument("--voice", default="Ting-Ting", help="voice used by render mode")
	parser.add_argument("--fixture", type=Path, help=f"render fixture (recommended: {DEFAULT_FIXTURE})")
	parser.add_argument("--case", action="append", default=[], metavar="ID=TEXT", help="additional render case")
	parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
	parser.add_argument("--report", type=Path, help="optional JSON report path")
	return parser


def main(argv: Sequence[str] | None = None) -> int:
	args = build_argument_parser().parse_args(argv)
	nvda_config_dir = (args.nvda_config_dir or _default_nvda_config_dir()).resolve()
	driver_root = (args.driver_root or _default_driver_root(nvda_config_dir)).resolve()
	try:
		if args.mode == "static":
			report = static_report(nvda_config_dir, driver_root)
		elif args.mode == "inventory":
			report = inventory_report(nvda_config_dir, driver_root)
		else:
			fixture = args.fixture
			if fixture is None and DEFAULT_FIXTURE.is_file():
				fixture = DEFAULT_FIXTURE
			cases, fixture_metadata = _load_cases(fixture, args.case)
			report = render_report(
				nvda_config_dir,
				driver_root,
				args.voice,
				cases,
				fixture_metadata,
				args.output_dir.resolve(),
			)
			if args.report is None:
				args.report = args.output_dir / "report.json"
		_write_json_report(report, args.report.resolve() if args.report else None)
		return 0
	except Exception as error:
		print(f"probe failed: {error}", file=sys.stderr)
		return 2


if __name__ == "__main__":
	raise SystemExit(main())
