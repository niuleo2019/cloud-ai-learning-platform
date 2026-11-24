import json
import urllib.error
import urllib.parse
import urllib.request

ONLINE_DICTIONARY_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"


def lookup_online_word(word: str, max_meanings: int = 4, timeout: float = 6.0) -> dict:
    """Look up a word in the free online dictionary (fallback when Longman has no entry)."""
    clean_word = word.strip().lower()
    url = ONLINE_DICTIONARY_URL.format(word=urllib.parse.quote(clean_word))
    request = urllib.request.Request(url, headers={"User-Agent": "vocab-app"})

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            entries = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {"found": False, "word": clean_word}
        raise
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return {"found": False, "word": clean_word, "error": "online dictionary unavailable"}

    meanings: list[dict] = []
    phonetic = ""
    for entry in entries if isinstance(entries, list) else []:
        phonetic = phonetic or entry.get("phonetic") or ""
        for meaning in entry.get("meanings", []):
            for definition in meaning.get("definitions", []):
                meanings.append(
                    {
                        "part_of_speech": meaning.get("partOfSpeech", ""),
                        "definition": definition.get("definition", ""),
                        "example": definition.get("example", ""),
                    }
                )
                if len(meanings) >= max_meanings:
                    break
            if len(meanings) >= max_meanings:
                break

    if not meanings:
        return {"found": False, "word": clean_word}

    return {"found": True, "word": clean_word, "phonetic": phonetic, "meanings": meanings, "source": "Online dictionary"}
