"""Turn a run into the files that share it (a Confluence page, a Jira issue, any other tool).

    <run_dir>/share/
        manifest.json        {"title", "body_storage", "body_markdown", "attachments": [...]}
        page.storage.html    page body in Confluence storage format: verdict, build info, one
                             table per feature (ID, name, steps, expected, result, screenshot)
        page.md              the same body in Markdown (for tools that take Markdown)
        attachments/         flat folder of files to upload: one result screenshot per test
                             (<case>_<test>.jpg) + the video / step pictures of the cases
                             chosen by report.share_media (failed (default) | all | none),
                             named <case>_...; the page shows them in one collapsed "Expand"
                             block per case under each table

Same rows as the HTML report (sbtest/reporting/report.py). The upload itself is done by the
agent (the sbtest-run skill); nothing here talks to Confluence or Jira.
"""
from __future__ import annotations

import html
import json
import shutil
from collections import defaultdict
from pathlib import Path

from sbtest.reporting.cases import load_cases
from sbtest.reporting.report import RESULT_LABEL, Row, _copy_images, build_info, build_rows, summary, write_markdown
from sbtest.utils import slug

SHARE_MEDIA = ("failed", "all", "none")

COLORS = {"passed": "Green", "failed": "Red", "error": "Red", "skipped": "Grey"}


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def _status(result: str) -> str:
    return (f'<ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">{COLORS.get(result, "Grey")}'
            f'</ac:parameter><ac:parameter ac:name="title">{esc(RESULT_LABEL.get(result, result.upper()))}'
            '</ac:parameter></ac:structured-macro>')


def _shares_media(r: Row, mode: str) -> bool:
    """Does this case share its step pictures / video (mode failed | all | none)?"""
    return (any(x.get("files") for x in r.executed) or bool(r.video_rel or r.video_file)) and (
        mode == "all" or (mode == "failed" and r.result in ("failed", "error")))


def _steps_block(r: Row, files: list[str]) -> str:
    """Collapsed "Expand" block with the video and the step pictures of one case."""
    n = sum(len(x["files"]) for x in r.executed)
    body = []
    if r.video_file:   # the Multimedia macro plays an attached video on the page
        files.append(r.video_file)
        body.append('<p><ac:structured-macro ac:name="multimedia"><ac:parameter ac:name="name">'
                    f'<ri:attachment ri:filename="{esc(r.video_file)}"/></ac:parameter>'
                    '<ac:parameter ac:name="width">800</ac:parameter></ac:structured-macro></p>')
    for x in r.executed:
        if not x.get("files"):
            continue
        body.append(f"<p><strong>[{esc(x['status'])}] {esc(x['title'])}</strong></p><p>")
        for label, name in x["files"]:
            files.append(name)
            body.append(f'<ac:image ac:width="600" ac:title="{esc(label)}"><ri:attachment ri:filename="{esc(name)}"/></ac:image> ')
        body.append("</p>")
    what = " + ".join(x for x in ("video" if r.video_file else "", f"step pictures ({n})" if n else "") if x)
    title = f"{r.case_id} {r.title} - {what} - {RESULT_LABEL.get(r.result, r.result.upper())}"
    return ('<ac:structured-macro ac:name="expand"><ac:parameter ac:name="title">' + esc(title[:200])
            + '</ac:parameter><ac:rich-text-body>' + "".join(body) + "</ac:rich-text-body></ac:structured-macro>")


def build(rows: list[Row], meta: dict, share_media: str = "failed") -> dict:
    """-> {"title", "storage", "files": [attachment names]} (images already in attachments/)."""
    s = summary(rows, meta)
    c = s["counts"]
    title = f"Sanity {s['build']} - {(meta.get('started') or '')[:16].replace('T', ' ')} - {s['verdict']}"
    color = "Green" if s["verdict"] == "PASSED" else "Red"
    st = [f'<p><ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">{color}</ac:parameter>'
          f'<ac:parameter ac:name="title">BUILD {esc(s["verdict"])}</ac:parameter></ac:structured-macro> '
          + " ".join(f"{_status(k)} {c.get(k, 0)}" for k in ("passed", "failed", "error", "skipped"))
          + f" &#160; {s['total']} cases</p>",
          "<table><tbody>" + "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in build_info(meta))
          + "</tbody></table>"]
    by_feature: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        by_feature[r.feature].append(r)
    files = []
    for feature, group in by_feature.items():
        ok = sum(r.result == "passed" for r in group)
        run = sum(r.result in ("passed", "failed", "error") for r in group)
        st.append(f"<h2>{esc(feature.capitalize())} ({ok}/{run} passed)</h2>")
        st.append("<table><tbody><tr><th>ID</th><th>Name / description</th><th>Steps</th><th>Expected</th>"
                  "<th>Result</th><th>Screenshot</th></tr>")
        for r in group:
            steps = "<ol>" + "".join(f"<li>{esc(x)}</li>" for x in r.steps) + "</ol>" if r.steps else ""
            exp = "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in r.expected) + "</ul>" if r.expected else ""
            res = _status(r.result) + f" {r.duration:.1f}s"
            if r.result in ("failed", "error"):
                res += f"<p><strong>Failed at:</strong> {esc(r.failed_step or '-')}</p><p>{esc(r.error[:500])}</p>"
            elif r.result == "skipped":
                res += f"<p>{esc(r.error[:200])}</p>"
            shot = ""
            if r.image:
                name = Path(r.image).name
                files.append(name)
                shot = f'<ac:image ac:width="300"><ri:attachment ri:filename="{esc(name)}"/></ac:image>'
            desc = esc(r.title) + (f"<br/><em>{esc(r.description)}</em>" if r.description else "")
            if _shares_media(r, share_media):
                res += "<p><em>Step pictures below the table.</em></p>"
            st.append(f"<tr><td><strong>{esc(r.case_id)}</strong></td><td>{desc}</td><td>{steps}</td><td>{exp}</td>"
                      f"<td>{res}</td><td>{shot}</td></tr>")
        st.append("</tbody></table>")
        st.extend(_steps_block(r, files) for r in group if _shares_media(r, share_media))
    return {"title": title, "storage": "".join(st), "files": sorted(set(files))}


def _flatten_media(rows: list[Row], out: Path, mode: str) -> None:
    """Attachments have no folders (Confluence, Jira): attachments/steps/<test>/02-1_click.jpg ->
    attachments/<case>_02-1_click.jpg, kept only for the chosen cases (``files`` per step)."""
    for r in rows:
        keep = _shares_media(r, mode) if mode != "none" else False
        for x in r.executed:
            x["files"] = []
            for label, rel in x.get("imgs") or []:
                src = out / rel.replace("img/", "attachments/", 1)
                if not keep or not src.exists():
                    continue
                name = f"{slug(r.case_id, 30)}_{src.name}"
                shutil.copyfile(src, out / "attachments" / name)
                x["files"].append((label, name))
        if mode == "failed" and r.result not in ("failed", "error"):
            for x in r.executed:
                x["files"] = []
    shutil.rmtree(out / "attachments" / "steps", ignore_errors=True)


def export(run_dir: Path, share_media: str | None = None) -> Path:
    """Write <run_dir>/share/ and return its path. ``share_media``: failed | all | none
    (default: report.share_media of the config)."""
    if share_media is None:
        from sbtest.config import load_config

        share_media = load_config().get("report.share_media") or "failed"
    if share_media not in SHARE_MEDIA:
        raise ValueError(f"share_media: one of {SHARE_MEDIA}, not {share_media!r}")
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    rows = build_rows(results, load_cases())
    out = run_dir / "share"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    _copy_images(rows, out)                       # -> out/img/*.jpg
    (out / "img").rename(out / "attachments")
    for r in rows:
        r.image = r.image.replace("img/", "attachments/", 1) if r.image else ""
    for r in rows:   # _shares_media looks at "files": mark which executed steps have pictures at all
        for x in r.executed:
            x["files"] = list(x.get("imgs") or [])
    _flatten_media(rows, out, share_media)
    for r in rows:   # videos of the chosen cases -> attachments/<case>_<video>.mp4
        if r.video_rel and _shares_media(r, share_media):
            r.video_file = f"{slug(r.case_id, 30)}_{Path(r.video_rel).name}"
            shutil.copyfile(out / r.video_rel, out / "attachments" / r.video_file)
    shutil.rmtree(out / "videos", ignore_errors=True)
    page = build(rows, results["meta"], share_media)
    (out / "page.storage.html").write_text(page["storage"], encoding="utf-8")
    write_markdown(rows, results["meta"], out)
    (out / "report.md").rename(out / "page.md")
    shown = [r for r in rows if any(x.get("files") for x in r.executed) or r.video_file]
    if shown:   # Markdown pages get the step pictures as a plain list
        md = ["", "## Step pictures", ""]
        for r in shown:
            md += [f"### {r.case_id} {r.title} - {RESULT_LABEL.get(r.result, r.result.upper())}", ""]
            if r.video_file:
                md += [f"[video](attachments/{r.video_file})", ""]
            for x in r.executed:
                if x.get("files"):
                    md += [f"**[{x['status']}] {x['title']}**", ""]
                    md += [f"![{label}](attachments/{name})" for label, name in x["files"]] + [""]
        with (out / "page.md").open("a", encoding="utf-8") as f:
            f.write("\n".join(md))
    manifest = {"title": page["title"], "body_storage": "page.storage.html", "body_markdown": "page.md",
                "attachments": [f"attachments/{name}" for name in page["files"]]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out
