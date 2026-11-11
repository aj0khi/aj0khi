#!/usr/bin/env python3
"""Generate an animated SVG galaxy from a GitHub user's public repositories."""

from __future__ import annotations

import colorsys
import hashlib
import html
import json
import math
import os
import random
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


USER = os.environ.get("GITHUB_USER", "aj0khi")
WIDTH, HEIGHT = 900, 440
CX, CY = 605, 224
ARM_COUNT = 4
REPO_LIMIT = 14
LANGUAGE_COLORS = {
    "C": "#c4d2e8",
    "C++": "#ff718d",
    "CSS": "#b18cff",
    "HTML": "#ff805e",
    "Java": "#f0a94c",
    "JavaScript": "#f5df62",
    "Jupyter Notebook": "#ff83b7",
    "Python": "#64a9ff",
    "Swift": "#ff895c",
    "TypeScript": "#57adff",
}
NO_LANGUAGE = "#c0caf5"


def api_json(url: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "aj0khi-repo-galaxy",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.URLError as error:
        raise RuntimeError(f"GitHub API request failed for {url}: {error}") from error


def fetch_repositories() -> list[dict[str, Any]]:
    """Fetch every public, non-fork repository owned by the profile."""
    repos: list[dict[str, Any]] = []
    for page in range(1, 11):
        query = urllib.parse.urlencode(
            {"type": "owner", "per_page": 100, "page": page, "sort": "updated"}
        )
        batch = api_json(f"https://api.github.com/users/{USER}/repos?{query}")
        repos.extend(batch)
        if len(batch) < 100:
            break
    return [
        repo for repo in repos
        if not repo.get("fork")
        and not repo.get("archived")
        and repo["name"].lower() != USER.lower()
    ]


def languages_for(repo: dict[str, Any]) -> dict[str, int]:
    url = repo.get("languages_url")
    return api_json(url) if url else {}


def color_for(language: str | None) -> str:
    if not language:
        return NO_LANGUAGE
    if language in LANGUAGE_COLORS:
        return LANGUAGE_COLORS[language]
    hue = int(hashlib.md5(language.encode()).hexdigest(), 16) % 360 / 360
    red, green, blue = colorsys.hls_to_rgb(hue, 0.67, 0.78)
    return f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"


def repository_languages(repos: list[dict[str, Any]]) -> list[tuple[str, str, float]]:
    language_bytes: dict[str, float] = {}
    for repo in repos:
        languages = repo.get("languages", {})
        total = sum(languages.values())
        if total:
            for language, size in languages.items():
                language_bytes[language] = language_bytes.get(language, 0) + size / total
        elif repo.get("language"):
            language = repo["language"]
            language_bytes[language] = language_bytes.get(language, 0) + 1
    total = sum(language_bytes.values())
    if not total:
        return [("Projects", "#85a7ff", 1.0)]
    top = sorted(language_bytes.items(), key=lambda item: (-item[1], item[0]))[:ARM_COUNT]
    return [(language, color_for(language), size / total) for language, size in top]


def point_on_arm(arm: int, fraction: float, arm_count: int) -> tuple[float, float]:
    angle = math.radians(205) + fraction * math.tau * 1.45 + arm * math.tau / arm_count
    radius = 30 + 230 * fraction
    return CX + radius * math.cos(angle), CY + radius * math.sin(angle) * 0.69


def svg_escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def build_svg(
    repos: list[dict[str, Any]], updated: str | None = None, seed: str = USER
) -> str:
    arms = repository_languages(repos)
    rng = random.Random(seed)
    language_arm = {language: index for index, (language, _, _) in enumerate(arms)}
    arm_total = len(arms)
    paths: list[str] = []
    for arm in range(arm_total):
        coordinates = []
        for step in range(101):
            x, y = point_on_arm(arm, step / 100, arm_total)
            coordinates.append(f"{x:.1f},{y:.1f}")
        paths.append(
            f'<path id="arm-{arm}" d="M{" L".join(coordinates)}" '
            'fill="none" stroke="none"/>'
        )

    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title description">',
        "<title id=\"title\">Ajmal's live GitHub repository galaxy</title>",
        "<desc id=\"description\">One star for each public repository, arranged on "
        "arms coloured by programming language. Repository stars link to their source.</desc>",
        f"""<defs>
  <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#111b37"/><stop offset=".58" stop-color="#0b1020"/>
    <stop offset="1" stop-color="#080b15"/>
  </linearGradient>
  <radialGradient id="core">
    <stop offset="0" stop-color="#fff5c3"/><stop offset=".25" stop-color="#f7a41d"/>
    <stop offset=".68" stop-color="#d65dca"/><stop offset="1" stop-color="#715bff" stop-opacity="0"/>
  </radialGradient>
  <filter id="glow" x="-150%" y="-150%" width="400%" height="400%">
    <feGaussianBlur stdDeviation="3" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <clipPath id="card"><rect width="{WIDTH}" height="{HEIGHT}" rx="18"/></clipPath>
  {''.join(paths)}
</defs>
<style>
  text {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; }}
  .eyebrow {{ font-size: 10px; letter-spacing: 3px; fill: #84a8ff; font-weight: 700; }}
  .title {{ font-size: 25px; fill: #f5f7ff; font-weight: 750; }}
  .stat {{ font-size: 12px; fill: #b6c1df; }}
  .hint {{ font-size: 10px; fill: #8490b2; }}
  .key {{ font-size: 11px; fill: #e4e9f8; font-weight: 650; }}
  .pct {{ font-size: 10px; fill: #aab6d4; }}
  .label {{ font-size: 9px; fill: #f5f6ff; font-weight: 650; }}
  .dim {{ fill: #aab6d4; font-weight: 400; }}
  .arm {{ fill: none; stroke-width: 13; stroke-linecap: round; opacity: .14; }}
  .repo-star {{ transition: opacity .2s ease; }}
  a:hover .repo-star {{ opacity: 1; }}
  a:hover .label {{ fill: #ffe39a; }}
  @keyframes twinkle {{ 0%, 100% {{ opacity: .12; }} 50% {{ opacity: .75; }} }}
  @keyframes pulse {{ 0%, 100% {{ opacity: .75; }} 50% {{ opacity: 1; }} }}
  .twinkle-1 {{ animation: twinkle 2.5s ease-in-out infinite; }}
  .twinkle-2 {{ animation: twinkle 3.3s ease-in-out infinite .7s; }}
  .twinkle-3 {{ animation: twinkle 4.1s ease-in-out infinite 1.2s; }}
  .pulse {{ animation: pulse 2.8s ease-in-out infinite; }}
  @media (prefers-reduced-motion: reduce) {{
    .twinkle-1, .twinkle-2, .twinkle-3, .pulse {{ animation: none; }}
  }}
</style>
<rect width="{WIDTH}" height="{HEIGHT}" rx="18" fill="url(#background)" stroke="#273252"/>""",
        '<g clip-path="url(#card)">',
    ]

    for _ in range(125):
        x, y = rng.uniform(8, WIDTH - 8), rng.uniform(8, HEIGHT - 8)
        radius, opacity = rng.uniform(0.35, 1.0), rng.uniform(0.14, 0.48)
        twinkle = f' class="twinkle-{rng.randint(1, 3)}"' if rng.random() < 0.34 else ""
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.2f}" fill="#c7d6ff" '
            f'opacity="{opacity:.2f}"{twinkle}/>'
        )

    for arm, (_, color, _) in enumerate(arms):
        parts.append(f'<use href="#arm-{arm}" class="arm" stroke="{color}"/>')

    parts.extend(
        [
            f'<circle cx="{CX}" cy="{CY}" r="51" fill="#8268ff" opacity=".14" filter="url(#glow)"/>',
            f'<circle cx="{CX}" cy="{CY}" r="32" fill="url(#core)"/>',
            f'<circle cx="{CX}" cy="{CY}" r="3" fill="#fffdf3"/>',
        ]
    )

    for arm, (_, color, share) in enumerate(arms):
        for index in range(max(16, round(75 * share))):
            start = rng.random() ** 1.8 * 0.92
            end = min(start + rng.uniform(0.035, 0.075), 0.99)
            duration = rng.uniform(10, 19)
            begin = -rng.random() * duration
            opacity = rng.uniform(0.35, 0.82)
            radius = rng.uniform(0.45, 1.4)
            parts.append(
                f'<circle r="{radius:.2f}" fill="{color}" opacity="0">'
                f'<animateMotion dur="{duration:.1f}s" begin="{begin:.1f}s" '
                f'repeatCount="indefinite" keyPoints="{start:.3f};{end:.3f}" '
                'keyTimes="0;1" calcMode="linear">'
                f'<mpath href="#arm-{arm}"/></animateMotion>'
                f'<animate attributeName="opacity" dur="{duration:.1f}s" '
                f'begin="{begin:.1f}s" repeatCount="indefinite" '
                f'values="0;{opacity:.2f};{opacity:.2f};0" keyTimes="0;.2;.8;1"/>'
                "</circle>"
            )

    sorted_repos = sorted(
        repos,
        key=lambda repo: (-repo.get("stargazers_count", 0), repo["name"].lower()),
    )
    for index, repo in enumerate(sorted_repos):
        language = repo.get("language")
        arm = language_arm.get(language, index % arm_total)
        arm_repos = [
            item for item in sorted_repos
            if language_arm.get(item.get("language"), sorted_repos.index(item) % arm_total) == arm
        ]
        position = arm_repos.index(repo)
        fraction = 0.13 + (0.78 * (position + 1) / (len(arm_repos) + 1))
        x, y = point_on_arm(arm, fraction, arm_total)
        color = color_for(language)
        star_size = min(3.2 + 1.8 * math.sqrt(repo.get("stargazers_count", 0)), 9)
        url = repo.get("html_url", f"https://github.com/{USER}/{repo['name']}")
        parts.append(f'<a href="{svg_escape(url)}" target="_blank">')
        parts.append(
            f'<circle class="repo-star" cx="{x:.1f}" cy="{y:.1f}" '
            f'r="{star_size * 2.0:.1f}" fill="{color}" opacity=".18" filter="url(#glow)"/>'
        )
        parts.append(
            f'<circle class="repo-star pulse" cx="{x:.1f}" cy="{y:.1f}" '
            f'r="{star_size:.1f}" fill="{color}"/>'
        )
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{star_size * .36:.1f}" '
            'fill="#ffffff" opacity=".95"/>'
        )
        if index < 12:
            anchor = "end" if x > CX + 32 else "start"
            label_x = x - star_size - 4 if anchor == "end" else x + star_size + 4
            name = repo["name"]
            if len(name) > 22:
                name = name[:21] + "…"
            parts.append(
                f'<text class="label" x="{label_x:.1f}" y="{y + 3:.1f}" '
                f'text-anchor="{anchor}">{svg_escape(name)} '
                f'<tspan class="dim">★ {repo.get("stargazers_count", 0)}</tspan></text>'
            )
        parts.append("</a>")

    parts.append("</g>")
    parts.extend(
        [
            '<text x="26" y="33" class="eyebrow">MY GITHUB UNIVERSE</text>',
            f'<text x="26" y="65" class="title">@{svg_escape(USER)}</text>',
            f'<text x="27" y="88" class="stat">{len(repos)} public repos · '
            f'{total_stars} stars</text>',
            '<text x="27" y="109" class="hint">Each glowing point is a repository.</text>',
            '<text x="27" y="154" class="eyebrow">LANGUAGE ARMS</text>',
        ]
    )
    for index, (language, color, share) in enumerate(arms):
        y = 179 + index * 23
        parts.append(f'<circle cx="32" cy="{y - 4}" r="4" fill="{color}"/>')
        parts.append(f'<text x="45" y="{y}" class="key">{svg_escape(language)}</text>')
        parts.append(
            f'<text x="204" y="{y}" text-anchor="end" class="pct">{share:.0%}</text>'
        )
    timestamp = updated or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    parts.extend(
        [
            '<text x="27" y="354" class="hint">Hover a repository star</text>',
            '<text x="27" y="370" class="hint">and open its source.</text>',
            f'<text x="{WIDTH - 18}" y="{HEIGHT - 14}" text-anchor="end" class="hint">'
            f'updated {svg_escape(timestamp)}</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts)


def main() -> None:
    repos = fetch_repositories()
    for repo in repos:
        repo["languages"] = languages_for(repo)
        if not repo.get("language") and repo["languages"]:
            repo["language"] = max(repo["languages"], key=repo["languages"].get)

    svg = build_svg(repos)
    output = Path(os.environ.get("GALAXY_OUTPUT", "assets/galaxy.svg"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg + "\n", encoding="utf-8")
    print(f"Wrote {output} with {len(repos)} public repositories.")


if __name__ == "__main__":
    main()
