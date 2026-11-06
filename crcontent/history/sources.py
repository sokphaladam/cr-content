"""Where research sources come from (spec 5.4), behind one shape: a provider takes a query and returns
(sources, note). note is "" when it worked, else what went wrong in plain words; a failed provider never invents a
source. Providers: Gemini with Google Search grounding (real pages Google retrieved, with the text each supports) and
the Wikipedia API (article intros). add_url() is a source the creator adds by hand."""
import hashlib
import json
import os
import re
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

import requests

from ..commons import HEADERS
from ..config import CACHE_DIR
from .models import ResearchSource

CACHE = CACHE_DIR / "research"
WIKI_API = "https://en.wikipedia.org/w/api.php"
EXCERPT_MAX = 1500
TRACKING = re.compile(r"^(utm_|fbclid|gclid)")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normal_url(url: str) -> str:
    """The same page however it was linked: no scheme, www, fragment, tracking parameters or trailing slash."""
    parts = urlsplit(url.strip())
    query = "&".join(q for q in parts.query.split("&") if q and not TRACKING.match(q))
    host = parts.netloc.lower().removeprefix("www.").removeprefix("m.")
    return urlunsplit(("", host, parts.path.rstrip("/"), query, ""))


def source_id(url: str, title: str = "") -> str:
    return "src-" + hashlib.sha256((normal_url(url) or title).encode()).hexdigest()[:10]


def role_of(url: str) -> str:
    """A first guess from the address; the creator can change it."""
    host = urlsplit(url).netloc.lower()
    if "wikipedia.org" in host:
        return "reference"
    if re.search(r"(museum|archive|archives|library|heritage|\.gov\b|\.gov\.|unesco|smithsonian|si\.edu|rmg\.co\.uk|"
                 r"loc\.gov|bl\.uk|nationalarchives|europeana|getty\.edu|metmuseum)", host):
        return "museum_or_archive"
    if re.search(r"(\.edu\b|\.ac\.|universit|jstor|doi\.org|journal|academic|cambridge\.org|oup\.com|springer|"
                 r"tandfonline|sciencedirect|wiley|nature\.com|science\.org|pnas\.org|sagepub)", host):
        return "scholarly_secondary"
    return "reference"


def _cached(name: str, key: str, fetch):
    path = CACHE / f"{name}-{hashlib.sha256(key.encode()).hexdigest()[:20]}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = fetch()
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


# ---------- Wikipedia ----------

def names(text: str, limit: int = 3) -> list[str]:
    """The proper names in narration, most mentioned first ("Mahendraparvata", "Phnom Kulen"): what to look up on
    Wikipedia for a script. A capitalised word that only starts a sentence ("Under", "It") is not a name."""
    found: dict[str, int] = {}
    openers = []  # sentence-first words: names only if they also appear mid-sentence
    for m in re.finditer(r"[A-Z][\w'-]+(?:\s+(?:of\s+|the\s+)?[A-Z][\w'-]+)*", text):
        name = m.group(0).removesuffix("'s")
        if m.start() == 0 or re.search(r"[.!?:]\s*$", text[:m.start()]):
            first, _, name = name.partition(" ")  # the sentence's first word is capitalised anyway ("Under Cambodia")
            openers.append(first.removesuffix("'s"))
        if name:
            found[name] = found.get(name, 0) + 1
    for w in openers:
        if w in found:
            found[w] += 1
    return sorted(found, key=lambda n: -found[n])[:limit]


def wikipedia(query: str, count: int = 3) -> tuple[list[ResearchSource], str]:
    def fetch():
        return requests.get(WIKI_API, params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": query, "gsrlimit": count,
            "prop": "extracts|info", "exintro": 1, "explaintext": 1, "exlimit": count, "inprop": "url"},
            headers=HEADERS, timeout=30).json()
    try:
        data = _cached("wiki", f"{query}|{count}", fetch)
    except (requests.RequestException, ValueError) as e:
        return [], f"Wikipedia couldn't be searched ({type(e).__name__})."
    pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        url, text = p.get("fullurl", ""), " ".join((p.get("extract") or "").split())
        if not url or not text or "(disambiguation)" in p.get("title", ""):
            continue
        out.append(ResearchSource(id=source_id(url), title=p.get("title", ""), publisher="Wikipedia", url=url,
                                  source_type="encyclopedia", provider="wikipedia", accessed_at=_now(),
                                  excerpts=[text[:EXCERPT_MAX]], source_role="reference",
                                  license_note="Text CC BY-SA 4.0"))
    return out, "" if out else f"Wikipedia had no article for {query!r}."


# ---------- Gemini + Google Search grounding ----------

GROUNDED = """You are a careful history researcher. Using Google Search, report what reliable sources (universities,
museums, archaeological projects, national archives, reputable reference works) say about the following. Give dates,
places and people precisely. Say plainly where sources disagree or where something is unknown or debated. Do not
speculate and do not add anything a source doesn't say.

"""


def _resolve(uri: str) -> str:
    """Grounding links are Google redirects: the page they point at, or the redirect itself if it can't be read."""
    try:
        r = requests.head(uri, allow_redirects=False, timeout=10)
        return r.headers.get("Location") or uri
    except requests.RequestException:
        return uri


def parse_grounding(data: dict) -> tuple[str, list[ResearchSource]]:
    """(the answer text, one source per page Google retrieved, each with the answer sentences it supports)."""
    cand = (data.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts") or [] if not p.get("thought"))
    meta = cand.get("groundingMetadata") or {}
    chunks = [(c.get("web") or {}) for c in meta.get("groundingChunks") or []]
    excerpts: dict[int, list[str]] = {}
    for s in meta.get("groundingSupports") or []:
        seg = " ".join(re.sub(r"[*#`]+", "", (s.get("segment") or {}).get("text") or "").split()).strip(" -")  # no Markdown
        for i in s.get("groundingChunkIndices") or []:
            if seg and 0 <= i < len(chunks) and seg not in excerpts.setdefault(i, []):
                excerpts[i].append(seg)
    out = []
    for i, web in enumerate(chunks):
        if not web.get("uri") or not excerpts.get(i):  # a page nothing in the answer rests on is not evidence
            continue
        url = _resolve(web["uri"])
        out.append(ResearchSource(id=source_id(url, web.get("title", "")), title=web.get("title", ""),
                                  publisher=web.get("title", "") or urlsplit(url).netloc, url=url, source_type="web",
                                  provider="google_search", accessed_at=_now(), excerpts=excerpts[i],
                                  source_role=role_of(url)))
    return text, out


def google(question: str, client=None) -> tuple[str, list[ResearchSource], str]:
    """(answer text, sources, note). Needs the Gemini key."""
    from .. import llm

    if not os.getenv("GEMINI_API_KEY") and client is None:
        return "", [], "Google Search grounding needs a Gemini key (Settings); it was skipped."
    body = {"contents": [{"role": "user", "parts": [{"text": GROUNDED + question}]}],
            "tools": [{"google_search": {}}], "generationConfig": {"maxOutputTokens": 4096}}
    try:
        client = client or llm.make_client()
        data = _cached("grounded", llm.model_name(None) + question, lambda: client.post(llm.model_name(None), body))
    except llm.APIError as e:
        return "", [], f"Google Search grounding failed: {e.message}"
    text, found = parse_grounding(data)
    return text, found, "" if found else "Google Search grounding returned no sources for this."


# ---------- by hand ----------

def add_url(url: str, note: str = "", excerpt: str = "", title: str = "") -> ResearchSource:
    """A source the creator adds. Its page title is read when possible; a page that can't be read is kept with
    retrieval_error, and only the creator's own excerpt can make it evidence."""
    if not re.match(r"^https?://", url.strip()):
        raise ValueError("A source link must start with http:// or https://")
    url = url.strip()
    error = ""
    if not title:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            m = re.search(r"<title[^>]*>(.*?)</title>", r.text[:200_000], re.I | re.S)
            title = " ".join(m.group(1).split()) if m else ""
        except requests.RequestException as e:
            error = f"couldn't be opened ({getattr(e.response, 'status_code', '') or type(e).__name__})"
    return ResearchSource(id=source_id(url), title=title or urlsplit(url).netloc, publisher=urlsplit(url).netloc,
                          url=url, source_type="user", provider="user", accessed_at=_now(), note=note.strip(),
                          excerpts=[excerpt.strip()[:EXCERPT_MAX]] if excerpt.strip() else [],
                          source_role=role_of(url), retrieval_error=error)


def merge(existing: list[ResearchSource], new: list[ResearchSource]) -> list[ResearchSource]:
    """Add `new` sources, merging duplicates (the same page however linked) into the one already there."""
    out = [s.model_copy(deep=True) for s in existing]
    by_url = {normal_url(s.url): s for s in out if s.url}
    by_id = {s.id: s for s in out}
    for s in new:
        same = by_url.get(normal_url(s.url)) if s.url else by_id.get(s.id)
        if same is None:
            same = by_id.get(s.id)
        if same is None:
            s = s.model_copy(deep=True)
            out.append(s)
            by_id[s.id] = s
            if s.url:
                by_url[normal_url(s.url)] = s
            continue
        same.excerpts += [x for x in s.excerpts if x not in same.excerpts]
        if s.title and "." in same.title and " " not in same.title:  # grounding titles are bare domains
            same.title = s.title
        if same.retrieval_error and not s.retrieval_error:
            same.retrieval_error = ""
    return out
