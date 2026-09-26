# Build metadata compatible with the NVDA Add-on Template/SCons ecosystem.
addon_info = {
	"addon_name": "contextualPronunciation",
	"addon_summary": "Context-aware pronunciation normalization",
	"addon_description": (
		"Corrects selected Chinese polyphones and preserves lexical apostrophes "
		"before text reaches the active speech synthesizer."
	),
	"addon_version": "0.7.4",
	"addon_changelog": (
		"First public repository release: add community documentation, reproducible GitHub builds, "
		"release checksums and Add-on Store submission metadata. Preserve the 0.7.3 pronunciation engine."
	),
	"addon_author": "ChenZ2000 and contributors",
	"addon_docFileName": "readme.html",
	"addon_url": "https://github.com/ChenZ2000/contextualPronunciation",
	"addon_sourceURL": "https://github.com/ChenZ2000/contextualPronunciation",
	"addon_minimumNVDAVersion": "2026.2",
	"addon_lastTestedNVDAVersion": "2026.2",
	"addon_updateChannel": "stable",
	"addon_license": "GNU General Public License version 2 or later",
	"addon_licenseURL": "https://www.gnu.org/licenses/gpl-2.0.html",
}

pythonSources = ["addon/globalPlugins/contextualPronunciation/**/*.py"]
i18nSources = pythonSources + ["buildVars.py"]
excludedFiles = [".git", ".github", "__pycache__", "*.pyc", "tests", "dist"]
baseLanguage = "en"
markdownExtensions = []
brailleTables = {
	"zhcn-contextual-2018.ctb": {
		"displayName": "Chinese common braille 2018 - contextual phrases (experimental)",
		"contracted": False,
		"input": False,
		"output": True,
	},
}
symbolDictionaries = {
	"lexicalApostrophe": {
		"displayName": "Preserve apostrophes inside words",
		"mandatory": True,
	},
}
speechDictionaries = {}
