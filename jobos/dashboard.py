"""`jobos dashboard [out.html]`: one self-contained HTML page for the tracker.

A map of where your jobs are relative to your target center (radius circle when set), and an
easy-to-read tracker: pipeline counts, follow-ups due, search and status filters. No server:
the tracker is inlined as JSON and rendered with textContent only, so job-board text (titles,
notes) can never run as HTML. Leaflet loads from cdnjs with SRI; without network the map hides
and the tracker still works.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import geo, tracker
from .targeting import Targets

FIELDS = ["company", "title", "location", "status", "date_applied", "follow_up", "url", "notes", "category"]


def _stage(status: str) -> str:
    """Bucket free-text statuses ("Skipped - no visa") into the canonical pipeline stage."""
    s = (status or "").strip().lower()
    for st in tracker.STATUSES:
        if s.startswith(st.lower()):
            return st
    return "Other"


def snapshot(rows: list[dict], targets: Targets | None = None, today: str | None = None) -> dict:
    jobs = []
    for r in rows:
        job = {k: (r.get(k) or "") for k in FIELDS}
        job["notes"] = job["notes"][-400:]                       # newest notes; keep the page small
        job["stage"] = _stage(job["status"])
        if not job["url"].lower().startswith(("http://", "https://")):
            job["url"] = ""                                       # no javascript: or data: links
        segs = geo.segments(job["location"])
        p = geo.geocode(segs[0]) if segs else None
        job["lat"], job["lon"] = (p if p else (None, None))
        jobs.append(job)
    t = targets or Targets()
    center = list(t.center) if t.center and len(t.center) == 2 else None
    return {
        "generated": today or date.today().isoformat(),
        "center": center,
        "radius_miles": t.radius_miles if (center and t.radius_miles) else None,
        "stages": tracker.STATUSES + ["Other"],
        "active": sorted(tracker.ACTIVE),
        "jobs": jobs,
    }


def _json_for_html(data: dict) -> str:
    """JSON that is safe inside <script type="application/json">: no '<', '>', '&' survive."""
    s = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
             .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def render(rows: list[dict], targets: Targets | None = None, today: str | None = None) -> str:
    return _TEMPLATE.replace("__DATA__", _json_for_html(snapshot(rows, targets, today)))


def write(rows: list[dict], out: Path, targets: Targets | None = None) -> Path:
    if targets is None:
        try:
            targets = Targets.load()
        except Exception:                                      # no or partial settings: still render
            targets = Targets()
    out.write_text(render(rows, targets), encoding="utf-8")
    return out


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Tracker</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"
      integrity="sha512-h9FcoyWjHcOcmEVkxOfTLnmZFWIH0iZhZT1H2TbOq55xssQGEJHEaIm+PgoUaZbRvQTNTluNOEfb1ZRy6D3BOw=="
      crossorigin="anonymous" referrerpolicy="no-referrer">
<style>
:root{--bg:#f7f7f5;--panel:#ffffff;--text:#1d1d1b;--muted:#6b6b66;--line:#e3e2dd;--accent:#2f5bd3;
  --applied:#2f5bd3;--progress:#0f8a5f;--offer:#b8860b;--closed:#9a9a94;--other:#7a5af5;--due:#c2410c}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#141413;--panel:#1d1d1b;--text:#ecebe6;
  --muted:#a3a29c;--line:#33332f;--accent:#7b9cff;--applied:#7b9cff;--progress:#3fcf95;--offer:#e3b341;
  --closed:#6f6f6a;--other:#a78bfa;--due:#fb923c}}
:root[data-theme="dark"]{--bg:#141413;--panel:#1d1d1b;--text:#ecebe6;--muted:#a3a29c;--line:#33332f;--accent:#7b9cff;
  --applied:#7b9cff;--progress:#3fcf95;--offer:#e3b341;--closed:#6f6f6a;--other:#a78bfa;--due:#fb923c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px;max-width:1100px;margin:auto}
h1{font-size:20px;margin:0}
.muted{color:var(--muted)}
main{max-width:1100px;margin:auto;padding:0 16px 32px;display:grid;gap:16px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.pipe{display:flex;flex-wrap:wrap;gap:8px}
.chip{border:1px solid var(--line);border-radius:999px;padding:4px 10px;background:transparent;color:var(--text);cursor:pointer;font:inherit}
.chip b{font-variant-numeric:tabular-nums}
.chip[aria-pressed="true"]{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
#map{height:380px;border-radius:8px}
#map.hidden{display:none}
.controls{display:flex;gap:8px;flex-wrap:wrap}
input[type=search]{flex:1;min-width:180px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--text);font:inherit}
button.theme{border:1px solid var(--line);background:var(--panel);color:var(--text);border-radius:8px;padding:6px 10px;cursor:pointer;font:inherit}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:middle}
.due{color:var(--due);font-weight:600}
a{color:var(--accent)}
@media (max-width:640px){
  thead{display:none} table,tbody,tr,td{display:block;width:100%}
  tr{border-bottom:1px solid var(--line);padding:8px 0} td{border:0;padding:2px 0}
  td[data-k]:before{content:attr(data-k) ": ";color:var(--muted);font-size:12px}
  td[data-k]:empty{display:none}
  #map{height:280px}
}
</style>
</head>
<body>
<header>
  <div><h1>Job tracker</h1><div class="muted" id="sub"></div></div>
  <button class="theme" id="theme" type="button" aria-label="Toggle light or dark theme">Theme</button>
</header>
<main>
  <section class="panel"><div class="pipe" id="pipe" aria-label="Pipeline by status"></div></section>
  <section class="panel" id="due-panel" hidden><strong>Follow-ups due</strong><ul id="due"></ul></section>
  <section class="panel" id="map-panel"><div id="map" role="region" aria-label="Map of job locations"></div>
    <div class="muted" id="map-note"></div></section>
  <section class="panel">
    <div class="controls"><input type="search" id="q" placeholder="Search company, title, location, notes" aria-label="Search"></div>
    <table><thead><tr><th>Company</th><th>Role</th><th>Location</th><th>Status</th><th>Applied</th><th>Follow-up</th></tr></thead>
    <tbody id="rows"></tbody></table>
    <div class="muted" id="count"></div>
  </section>
</main>
<script type="application/json" id="data">__DATA__</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"
        integrity="sha512-puJW3E/qXDqYp9IfhAI54BJEaWIfloJ7JWs7OeD5i6ruC9JZL1gERT1wjtwXFlh7CjE7ZJ+/vcRZRkIYIb6p4g=="
        crossorigin="anonymous" referrerpolicy="no-referrer"></script>
<script>
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("data").textContent);
  var root = document.documentElement;
  try { var saved = localStorage.getItem("jobos-theme"); if (saved) root.setAttribute("data-theme", saved); } catch (e) {}
  document.getElementById("theme").addEventListener("click", function () {
    var dark = root.getAttribute("data-theme") ? root.getAttribute("data-theme") === "dark"
             : window.matchMedia("(prefers-color-scheme: dark)").matches;
    var next = dark ? "light" : "dark"; root.setAttribute("data-theme", next);
    try { localStorage.setItem("jobos-theme", next); } catch (e) {}
  });

  function el(tag, text, cls) { var e = document.createElement(tag); if (text != null) e.textContent = text; if (cls) e.className = cls; return e; }
  function color(stage) {
    var v = {Applied:"--applied", Assessment:"--progress", Interviewing:"--progress", Offer:"--offer",
             Rejected:"--closed", Withdrawn:"--closed", Skipped:"--closed", Blocked:"--other", Found:"--muted", Queued:"--muted"}[stage] || "--other";
    return getComputedStyle(root).getPropertyValue(v).trim() || "#888";
  }
  var today = D.generated, active = {}; D.active.forEach(function (s) { active[s] = true; });
  var isDue = function (j) { return active[j.stage] && j.follow_up && j.follow_up <= today; };
  document.getElementById("sub").textContent = D.jobs.length + " jobs \u00b7 snapshot " + today;

  var filter = {stage: null, q: ""};
  var counts = {}; D.jobs.forEach(function (j) { counts[j.stage] = (counts[j.stage] || 0) + 1; });
  var pipe = document.getElementById("pipe");
  D.stages.forEach(function (s) {
    if (!counts[s]) return;
    var b = el("button", null, "chip"); b.type = "button"; b.setAttribute("aria-pressed", "false");
    var dot = el("span", null, "dot"); dot.style.background = color(s); b.appendChild(dot);
    b.appendChild(document.createTextNode(s + " ")); b.appendChild(el("b", String(counts[s])));
    b.addEventListener("click", function () {
      filter.stage = filter.stage === s ? null : s;
      Array.prototype.forEach.call(pipe.children, function (c) { c.setAttribute("aria-pressed", String(c === b && filter.stage === s)); });
      draw();
    });
    pipe.appendChild(b);
  });

  var due = D.jobs.filter(isDue).sort(function (a, b) { return a.follow_up < b.follow_up ? -1 : 1; });
  if (due.length) {
    document.getElementById("due-panel").hidden = false;
    var ul = document.getElementById("due");
    due.forEach(function (j) { ul.appendChild(el("li", j.follow_up + " \u2014 " + j.company + ", " + j.title)); });
  }

  document.getElementById("q").addEventListener("input", function (e) { filter.q = e.target.value.toLowerCase(); draw(); });
  function visible(j) {
    if (filter.stage && j.stage !== filter.stage) return false;
    if (!filter.q) return true;
    return [j.company, j.title, j.location, j.status, j.notes].join(" ").toLowerCase().indexOf(filter.q) >= 0;
  }

  var tbody = document.getElementById("rows"), layer = null, map = null;
  function draw() {
    tbody.textContent = "";
    var shown = D.jobs.filter(visible);
    shown.forEach(function (j) {
      var tr = document.createElement("tr");
      var c1 = el("td", j.company); c1.setAttribute("data-k", "Company");
      var c2 = el("td"); c2.setAttribute("data-k", "Role");
      if (j.url) { var a = el("a", j.title); a.href = j.url; a.target = "_blank"; a.rel = "noopener noreferrer"; c2.appendChild(a); }
      else c2.textContent = j.title;
      if (j.notes) c2.title = j.notes;
      var c3 = el("td", j.location); c3.setAttribute("data-k", "Location");
      var c4 = el("td"); c4.setAttribute("data-k", "Status");
      var dot = el("span", null, "dot"); dot.style.background = color(j.stage); c4.appendChild(dot); c4.appendChild(document.createTextNode(j.status));
      var c5 = el("td", j.date_applied); c5.setAttribute("data-k", "Applied");
      var c6 = el("td", j.follow_up, isDue(j) ? "due" : ""); c6.setAttribute("data-k", "Follow-up");
      [c1, c2, c3, c4, c5, c6].forEach(function (c) { tr.appendChild(c); });
      tbody.appendChild(tr);
    });
    document.getElementById("count").textContent = "Showing " + shown.length + " of " + D.jobs.length;
    drawPins(shown);
  }

  function drawPins(shown) {
    if (!map) return;
    if (layer) layer.remove();
    layer = L.layerGroup().addTo(map);
    var pts = [];
    shown.forEach(function (j) {
      if (j.lat == null) return;
      var m = L.circleMarker([j.lat, j.lon], {radius: 7, color: color(j.stage), fillOpacity: .85, weight: 1});
      var box = document.createElement("div");
      box.appendChild(el("strong", j.company)); box.appendChild(document.createElement("br"));
      box.appendChild(document.createTextNode(j.title)); box.appendChild(document.createElement("br"));
      box.appendChild(el("span", j.status + " \u00b7 " + j.location, "muted"));
      m.bindPopup(box); m.addTo(layer); pts.push([j.lat, j.lon]);
    });
    var placed = shown.filter(function (j) { return j.lat != null; }).length;
    document.getElementById("map-note").textContent = placed + " of " + shown.length + " shown jobs placed on the map" +
      (shown.length > placed ? " (remote or unrecognized locations are listed below only)" : "");
    if (!D.center && pts.length) map.fitBounds(pts, {padding: [24, 24], maxZoom: 9});
  }

  if (window.L) {
    var start = D.center || [39.5, -98.35];
    map = L.map("map", {scrollWheelZoom: false}).setView(start, D.center ? 10 : 4);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      {maxZoom: 18, attribution: "\u00a9 OpenStreetMap contributors"}).addTo(map);
    if (D.center) {
      L.circleMarker(D.center, {radius: 5, color: "#111", fillColor: "#fff", fillOpacity: 1, weight: 2}).addTo(map).bindTooltip("Your center");
      if (D.radius_miles) {
        var c = L.circle(D.center, {radius: D.radius_miles * 1609.344, color: color("Applied"), weight: 1, fillOpacity: .06}).addTo(map);
        map.fitBounds(c.getBounds(), {padding: [16, 16]});
      }
    }
  } else {
    document.getElementById("map").classList.add("hidden");
    document.getElementById("map-note").textContent = "Map unavailable offline; the tracker below still works.";
  }
  draw();
})();
</script>
</body>
</html>
"""
