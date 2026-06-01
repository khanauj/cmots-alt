"""Web viewer — browsable HTML grids for the Stock Master and MF Scheme Master.

Server-rendered shell + client-side fetch against the existing JSON routes
(`/stocks`, `/mutual-funds`). No new data path: this is a thin view over the
same gold reads the API already serves. Mounted at `/ui`.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CMOTS-alt — Master Data Viewer</title>
<style>
  :root { --hd:#1F4E78; --bd:#d9d9d9; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; color:#222; }
  header { background: var(--hd); color:#fff; padding: 12px 18px; }
  header h1 { margin:0; font-size:18px; }
  header span { opacity:.8; font-size:12px; }
  .tabs { display:flex; gap:4px; padding: 10px 18px 0; background:#f3f5f8; border-bottom:1px solid var(--bd); }
  .tab { padding:8px 16px; cursor:pointer; border:1px solid var(--bd); border-bottom:none;
         border-radius:6px 6px 0 0; background:#e7ebf0; font-weight:600; font-size:14px; }
  .tab.active { background:#fff; color:var(--hd); }
  .toolbar { display:flex; gap:10px; align-items:center; padding:12px 18px; flex-wrap:wrap; }
  .toolbar input, .toolbar select { padding:7px 10px; border:1px solid var(--bd); border-radius:6px; font-size:14px; }
  #search { width:280px; }
  .btn { padding:7px 14px; border:1px solid var(--hd); background:var(--hd); color:#fff;
         border-radius:6px; cursor:pointer; font-size:14px; }
  .btn.ghost { background:#fff; color:var(--hd); }
  .btn:disabled { opacity:.4; cursor:not-allowed; }
  .meta { font-size:13px; color:#555; margin-left:auto; }
  .wrap { padding: 0 18px 24px; }
  table { border-collapse: collapse; width:100%; font-size:13px; }
  th, td { border:1px solid var(--bd); padding:6px 9px; text-align:left; white-space:nowrap; }
  th { background:var(--hd); color:#fff; position:sticky; top:0; }
  tbody tr:nth-child(even){ background:#f7f9fc; }
  tbody tr:hover{ background:#eef4ff; }
  td.num { text-align:right; font-variant-numeric: tabular-nums; }
  .pill { padding:1px 8px; border-radius:10px; font-size:11px; background:#e7ebf0; }
  .empty { padding:30px; text-align:center; color:#888; }
</style></head>
<body>
<header><h1>CMOTS-alt &mdash; Master Data Viewer</h1>
  <span>Stock Master &amp; Mutual Fund Master &middot; live gold data</span></header>
<div class="tabs">
  <div class="tab active" data-view="stocks" onclick="switchView('stocks')">Stock Master</div>
  <div class="tab" data-view="mf" onclick="switchView('mf')">Mutual Funds Master</div>
</div>
<div class="toolbar">
  <input id="search" placeholder="Search name / symbol…" oninput="debounced()">
  <select id="extra"></select>
  <button class="btn ghost" id="prev" onclick="page(-1)">&larr; Prev</button>
  <button class="btn ghost" id="next" onclick="page(1)">Next &rarr;</button>
  <select id="limit" onchange="reset()">
    <option>25</option><option selected>50</option><option>100</option><option>200</option>
  </select>
  <span class="meta" id="meta"></span>
</div>
<div class="wrap"><table><thead id="thead"></thead><tbody id="tbody"></tbody></table>
  <div class="empty" id="empty" style="display:none">No rows.</div></div>

<script>
const COLS = {
  stocks: [["co_code","co_code",1],["nse_symbol","NSE Symbol",0],["bse_code","BSE Code",1],
           ["company_name","Company Name",0],["isin","ISIN",0],
           ["sector_name","Sector",0],["mcap_class","Mcap",0]],
  mf:     [["scheme_code","Scheme Code",1],["scheme_name","Scheme Name",0],
           ["amc_name","AMC",0],["category","Category",0]],
};
const ENDPOINT = { stocks: "/stocks", mf: "/mutual-funds" };
let view = "stocks", offset = 0;

function switchView(v){
  view = v; offset = 0;
  document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("active", t.dataset.view===v));
  document.getElementById("search").value = "";
  const extra = document.getElementById("extra");
  if (v === "stocks") extra.innerHTML = '<option value="">All sectors</option>';
  else extra.innerHTML = '<option value="">All categories</option>'+
    ['Equity','Debt','Hybrid','Other','Solution'].map(c=>`<option>${c}</option>`).join("");
  load();
}
function reset(){ offset = 0; load(); }
function page(d){ const lim=+document.getElementById("limit").value;
  offset = Math.max(0, offset + d*lim); load(); }

let t; function debounced(){ clearTimeout(t); t=setTimeout(reset, 300); }

async function load(){
  const lim = +document.getElementById("limit").value;
  const q = document.getElementById("search").value.trim();
  const extra = document.getElementById("extra").value;
  const p = new URLSearchParams({ limit: lim, offset });
  if (q) p.set("search", q);
  if (extra && view==="stocks") p.set("sector", extra);
  if (extra && view==="mf") p.set("category", extra);
  const rows = await (await fetch(ENDPOINT[view] + "?" + p)).json();

  const cols = COLS[view];
  document.getElementById("thead").innerHTML =
    "<tr>" + cols.map(c=>`<th>${c[1]}</th>`).join("") + "</tr>";
  document.getElementById("tbody").innerHTML = rows.map(r =>
    "<tr>" + cols.map(c => {
      let v = r[c[0]]; v = (v===null||v===undefined) ? "" : v;
      if (c[0]==="mcap_class" && v) v = `<span class="pill">${v}</span>`;
      return `<td class="${c[2]?'num':''}">${v}</td>`;
    }).join("") + "</tr>").join("");
  document.getElementById("empty").style.display = rows.length ? "none":"block";
  document.getElementById("prev").disabled = offset === 0;
  document.getElementById("next").disabled = rows.length < lim;
  document.getElementById("meta").textContent =
    `${ENDPOINT[view]} · rows ${rows.length ? offset+1 : 0}–${offset+rows.length}`;
}
switchView(new URLSearchParams(location.search).get("view") === "mf" ? "mf" : "stocks");
</script>
</body></html>"""


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False, summary="Master data viewer")
async def master_viewer() -> str:
    return _PAGE
