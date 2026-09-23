"""Offline observations for eSpeak and installed Microsoft Mandarin SAPI voices.

No NVDA profile is loaded, no audio is played, no voice is downloaded. Compare
the SAME global text policy to independent homophone anchors. A mismatch is
reported, never converted into an engine-specific runtime workaround or hidden.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import sys
import wave
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.generate_final_renderer_fixture import build_fixture  # noqa: E402

OUTPUT = ROOT / "artifacts/global-voice-probes"


def cases():
	# Share the SAME reviewed inputs and explicit strict/extended modes with
	# the VE probe. Do not silently run extended cases with the lexicon off.
	for item in build_fixture()["transformations"]:
		yield {
			"id": item["id"],
			"source": item["source"],
			"normalized": item["transformed"],
			"anchor": item["commonAnchor"],
			"reading": item["expectedReading"],
			"strict": item["strict"],
			"extended": item["extended"],
		}


def espeak_probe(samples):
	directory = ROOT / "vendor/nvda-2026.2/source/synthDrivers"
	path = directory / "espeak.dll"
	dll = ctypes.CDLL(str(path))
	dll.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
	dll.espeak_Initialize.restype = ctypes.c_int
	dll.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
	dll.espeak_SetVoiceByName.restype = ctypes.c_int
	dll.espeak_TextToPhonemes.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_int, ctypes.c_int]
	dll.espeak_TextToPhonemes.restype = ctypes.c_char_p
	dll.espeak_Terminate.argtypes = []
	dll.espeak_Terminate.restype = ctypes.c_int
	# Synchronous retrieval, DONT_EXIT. This API only emits phoneme strings.
	if dll.espeak_Initialize(2, 300, os.fsencode(directory), 0x8000) <= 0:
		raise RuntimeError("eSpeak initialization failed")
	try:
		if dll.espeak_SetVoiceByName(b"cmn") != 0:
			raise RuntimeError("eSpeak Mandarin voice unavailable")

		def phonemes(text):
			buffer = ctypes.create_string_buffer(text.encode("utf-8"))
			pointer = ctypes.cast(buffer, ctypes.c_void_p)
			parts = []
			for _ in range(len(text) + 2):
				previous = pointer.value
				value = dll.espeak_TextToPhonemes(ctypes.byref(pointer), 1, 2)
				parts.append(value.decode("utf-8") if value else "")
				if not pointer.value:
					return parts
				if pointer.value == previous:
					raise RuntimeError("eSpeak text pointer did not advance")
			raise RuntimeError("eSpeak exceeded bounded sentence traversal")

		results = []
		for sample in samples:
			values = {role: phonemes(sample[role]) for role in ("source", "normalized", "anchor")}
			results.append({**sample, "phonemes": values, "anchorMatches": values["normalized"] == values["anchor"]})
		return {
			"engine": "eSpeak NG",
			"voice": "cmn",
			"dllSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
			"cases": results,
		}
	finally:
		dll.espeak_Terminate()


def sapi_probe(samples):
	import pythoncom
	from win32com.client import dynamic

	pythoncom.CoInitialize()
	try:
		voice = dynamic.Dispatch("SAPI.SpVoice")
		tokens = voice.GetVoices()
		results = []
		for index in range(tokens.Count):
			token = tokens.Item(index)
			identifier = token.Id
			# Diagnostic scope only: built-in local Mandarin SAPI tokens, never
			# arbitrary third-party/cloud enumerators or the user's live synth.
			if "TTS_MS_ZH-CN_" not in identifier.upper():
				continue
			voice.Voice = token
			voice.Rate, voice.Volume = 0, 100
			directory = OUTPUT / f"sapi-{index}"
			directory.mkdir(parents=True, exist_ok=True)
			entries = []
			for sample in samples:
				values = {}
				for role in ("source", "normalized", "anchor"):
					path = directory / f"{sample['id']}-{role}.wav"
					stream = dynamic.Dispatch("SAPI.SpFileStream")
					stream.Format.Type = 22  # SAFT22kHz16BitMono.
					stream.Open(str(path), 3, False)
					try:
						voice.AudioOutputStream = stream
						voice.Speak(sample[role], 0)
					finally:
						stream.Close()
					with wave.open(str(path), "rb") as wav:
						pcm = wav.readframes(wav.getnframes())
						values[role] = {
							"frames": wav.getnframes(),
							"rate": wav.getframerate(),
							"pcmSha256": hashlib.sha256(pcm).hexdigest(),
						}
				entries.append({**sample, "audio": values, "anchorMatches": values["normalized"] == values["anchor"]})
			results.append({"engine": "SAPI5", "voice": token.GetDescription(), "token": identifier, "cases": entries})
		return results
	finally:
		pythoncom.CoUninitialize()


def main():
	OUTPUT.mkdir(parents=True, exist_ok=True)
	samples = list(cases())
	observations = [espeak_probe(samples), *sapi_probe(samples)]
	for result in observations:
		result["anchorMatches"] = sum(case["anchorMatches"] for case in result["cases"])
		result["comparisons"] = len(result["cases"])
	from scripts.run_tests import source_hashes

	report = {
		"testedAtUtc": datetime.now(UTC).isoformat(),
		"completed": True,
		"policy": "Same engine-independent runtime mapping for every probe",
		"scope": (
			"Offline engine observations, not live NVDA, listening or an all-voices certification. "
			"PCM differences can include prosody, not just incorrect phonemes."
		),
		"sourceSha256": source_hashes(),
		"observations": observations,
	}
	path = OUTPUT / "report.json"
	path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
	for result in observations:
		print(
			f"{result['engine']} / {result['voice']}: "
			f"{result['anchorMatches']}/{result['comparisons']} independent anchor matches"
		)
	print(path)


if __name__ == "__main__":
	main()
