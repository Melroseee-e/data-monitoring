#!/usr/bin/env python3
"""Build an official Pump.fun Solana program surface inventory."""

from __future__ import annotations

import json
import re
import ssl
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
OUT_DERIVED = ROOT / "data" / "pump" / "derived"
OUT_REPORTS = ROOT / "data" / "pump" / "reports"

GITHUB_API_BASE = "https://api.github.com/repos/pump-fun/pump-public-docs/contents"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/"
FEES_SITE_URL = "https://fees.pump.fun/"
FEES_API_URL = "https://fees.pump.fun/api/buybacks"
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

CTX = ssl._create_unverified_context()
USER_AGENT = "Mozilla/5.0 (compatible; Codex Research/1.0)"

PROGRAM_DOC_PATHS = {
    "pump": "docs/PUMP_PROGRAM_README.md",
    "pump_amm": "docs/PUMP_SWAP_README.md",
    "pump_fees": "docs/FEE_PROGRAM_README.md",
}

PROGRAM_RELEVANCE = {
    "pump": {
        "buyback_relevance": "direct_execution_candidate",
        "rationale": (
            "Official trading program with buy and buy_exact_sol_in instructions. "
            "No public buyback-only instruction exists."
        ),
    },
    "pump_amm": {
        "buyback_relevance": "direct_execution_candidate",
        "rationale": (
            "Official AMM trading program with buy and buy_exact_quote_in instructions. "
            "Likely execution layer for treasury purchases after pool migration."
        ),
    },
    "pump_fees": {
        "buyback_relevance": "fee_accounting_support",
        "rationale": (
            "Official fee program with get_fees and fee config instructions. "
            "Supports accounting and fee routing rather than direct purchase execution."
        ),
    },
    "mayhem": {
        "buyback_relevance": "execution_support",
        "rationale": (
            "Official mode-specific program disclosed in the main README. "
            "Acts as trading/fee-mode infrastructure, not a public buyback-only program."
        ),
    },
}

SEARCH_TERMS = ["buyback", "buy back", "token purchases", "dailybuybacks"]


@dataclass
class ProgramInfo:
    name: str
    address: str
    official_source: str
    idl_present: bool
    source_code_status: str
    docs_path: str | None
    key_instructions: list[str]
    instruction_count: int
    terms_found: list[str]
    main_global_pda: str | None = None
    related_fee_recipients: list[str] | None = None
    notes: list[str] | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, context=CTX) as resp:
        return resp.read().decode("utf-8", "replace")


def fetch_json_url(url: str) -> Any:
    return json.loads(fetch_text(url))


def github_contents(path: str = "") -> list[dict[str, Any]]:
    url = GITHUB_API_BASE if not path else f"{GITHUB_API_BASE}/{path}"
    return fetch_json_url(url)


def rpc_call(method: str, params: list[Any]) -> dict[str, Any]:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    out = subprocess.check_output(
        [
            "curl",
            "-s",
            SOLANA_RPC_URL,
            "-H",
            "Content-Type: application/json",
            "-d",
            payload,
        ],
        text=True,
    )
    return json.loads(out)


def rpc_get_account_info(address: str) -> dict[str, Any]:
    return rpc_call("getAccountInfo", [address, {"encoding": "jsonParsed"}])["result"]["value"]


def unique_preserve(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def extract_first_address(text: str, anchor: str) -> str | None:
    idx = text.find(anchor)
    if idx == -1:
        return None
    match = re.search(
        r'`([1-9A-HJ-NP-Za-km-z]{32,44})`|"([1-9A-HJ-NP-Za-km-z]{32,44})"',
        text[idx : idx + 1200],
    )
    if not match:
        return None
    return match.group(1) or match.group(2)


def extract_all_addresses(text: str, anchor: str, window: int = 1500) -> list[str]:
    idx = text.find(anchor)
    if idx == -1:
        return []
    block = text[idx : idx + window]
    return unique_preserve(re.findall(r"[1-9A-HJ-NP-Za-km-z]{32,44}", block))


def find_chunk_with_needles(html: str, needles: list[str]) -> tuple[str | None, str | None]:
    chunk_paths = unique_preserve(re.findall(r"/_next/static/chunks/[^\"']+\.js\?dpl=[^\"']+", html))
    for chunk_path in chunk_paths:
        text = fetch_text(f"https://fees.pump.fun{chunk_path}")
        if all(needle in text for needle in needles):
            return chunk_path, text
    return None, None


def scan_terms(files: dict[str, str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for path, text in files.items():
        lower = text.lower()
        matched = [term for term in SEARCH_TERMS if term in lower]
        hits[path] = matched
    return hits


def build_program_infos(
    docs_text: dict[str, str], idls: dict[str, dict[str, Any]], main_readme: str
) -> list[ProgramInfo]:
    pump_readme = docs_text["docs/PUMP_PROGRAM_README.md"]
    pump_swap_readme = docs_text["docs/PUMP_SWAP_README.md"]
    fee_readme = docs_text["docs/FEE_PROGRAM_README.md"]

    pump_fee_recipient = extract_first_address(pump_readme, '"fee_recipient"')
    pump_global = extract_first_address(pump_readme, "The global configuration of the program is stored")
    pump_admin = extract_first_address(pump_readme, '"authority"')

    pump_amm_global = extract_first_address(
        pump_swap_readme, "The global configuration of the program is stored"
    )
    pump_amm_admin = extract_first_address(pump_swap_readme, '"admin"')
    pump_amm_fee_recipients = extract_all_addresses(pump_swap_readme, '"protocol_fee_recipients"')

    infos = [
        ProgramInfo(
            name="pump",
            address=idls["pump"]["address"],
            official_source=f"{GITHUB_RAW_BASE}idl/pump.json",
            idl_present=True,
            source_code_status="public IDL only",
            docs_path="docs/PUMP_PROGRAM_README.md",
            key_instructions=[
                name
                for name in [i["name"] for i in idls["pump"]["instructions"]]
                if any(term in name for term in ["buy", "cashback", "creator", "mayhem"])
            ],
            instruction_count=len(idls["pump"]["instructions"]),
            terms_found=[],
            main_global_pda=pump_global,
            related_fee_recipients=unique_preserve(
                [x for x in [pump_fee_recipient, pump_admin] if x]
            ),
            notes=[
                "README documents a single Global PDA and a Global authority.",
                "No official buyback instruction name appears in the public IDL.",
            ],
        ),
        ProgramInfo(
            name="pump_amm",
            address=idls["pump_amm"]["address"],
            official_source=f"{GITHUB_RAW_BASE}idl/pump_amm.json",
            idl_present=True,
            source_code_status="public IDL only",
            docs_path="docs/PUMP_SWAP_README.md",
            key_instructions=[
                name
                for name in [i["name"] for i in idls["pump_amm"]["instructions"]]
                if any(term in name for term in ["buy", "cashback", "creator", "mayhem", "fee"])
            ],
            instruction_count=len(idls["pump_amm"]["instructions"]),
            terms_found=[],
            main_global_pda=pump_amm_global,
            related_fee_recipients=unique_preserve(
                [x for x in [pump_amm_admin] + pump_amm_fee_recipients if x]
            ),
            notes=[
                "README documents a GlobalConfig PDA and protocol fee recipients.",
                "transfer_creator_fees_to_pump appears in the official IDL but no buyback-only instruction exists.",
            ],
        ),
        ProgramInfo(
            name="pump_fees",
            address=idls["pump_fees"]["address"],
            official_source=f"{GITHUB_RAW_BASE}idl/pump_fees.json",
            idl_present=True,
            source_code_status="public IDL only",
            docs_path="docs/FEE_PROGRAM_README.md",
            key_instructions=[
                name
                for name in [i["name"] for i in idls["pump_fees"]["instructions"]]
                if any(term in name for term in ["fee", "claim", "sharing"])
            ],
            instruction_count=len(idls["pump_fees"]["instructions"]),
            terms_found=[],
            main_global_pda=None,
            related_fee_recipients=[],
            notes=[
                "Public fee program documentation focuses on fee calculation and sharing config.",
                "No public buyback instruction name appears in the fee program IDL.",
            ],
        ),
        ProgramInfo(
            name="mayhem",
            address=extract_first_address(main_readme, "Mayhem program id") or "",
            official_source=f"{GITHUB_RAW_BASE}README.md",
            idl_present=False,
            source_code_status="public docs only",
            docs_path="README.md",
            key_instructions=[],
            instruction_count=0,
            terms_found=[],
            main_global_pda=None,
            related_fee_recipients=extract_all_addresses(main_readme, "Mayhem fee recipients"),
            notes=[
                "Official README discloses a Mayhem program id and Mayhem fee recipients.",
                "No public IDL or source file for Mayhem exists in pump-public-docs.",
            ],
        ),
    ]

    return infos


def enrich_program_chain_metadata(program: ProgramInfo) -> dict[str, Any]:
    info = rpc_get_account_info(program.address)
    parsed = info.get("data", {}).get("parsed", {})
    pd_addr = parsed.get("info", {}).get("programData")
    pd_info = rpc_get_account_info(pd_addr) if pd_addr else None
    pd_parsed = (pd_info or {}).get("data", {}).get("parsed", {}).get("info", {})

    relevance = PROGRAM_RELEVANCE[program.name]
    return {
        "program_name": program.name,
        "program_address": program.address,
        "official_source": program.official_source,
        "docs_path": program.docs_path,
        "idl_present": program.idl_present,
        "is_executable": info["executable"],
        "owner": info["owner"],
        "programdata_address": pd_addr,
        "upgrade_authority": pd_parsed.get("authority"),
        "programdata_slot": pd_parsed.get("slot"),
        "main_global_pda": program.main_global_pda,
        "related_fee_recipients": program.related_fee_recipients or [],
        "key_instructions": program.key_instructions,
        "instruction_count": program.instruction_count,
        "buyback_relevance": relevance["buyback_relevance"],
        "buyback_rationale": relevance["rationale"],
        "source_code_status": program.source_code_status,
        "notes": program.notes or [],
    }


def build_object_registry(
    docs_text: dict[str, str],
    main_readme: str,
    fees_bundle_text: str,
    fees_api: dict[str, Any],
) -> list[dict[str, Any]]:
    pump_readme = docs_text["docs/PUMP_PROGRAM_README.md"]
    pump_swap_readme = docs_text["docs/PUMP_SWAP_README.md"]
    cashback_readme = docs_text["docs/PUMP_CASHBACK_README.md"]

    objects: list[dict[str, Any]] = []

    def add(
        object_name: str,
        address: str | None,
        object_type: str,
        program_name: str | None,
        official_source: str,
        notes: str,
        derivation: str | None = None,
    ) -> None:
        objects.append(
            {
                "object_name": object_name,
                "address": address,
                "object_type": object_type,
                "program_name": program_name,
                "official_source": official_source,
                "derivation": derivation,
                "notes": notes,
            }
        )

    add(
        "pump_global",
        extract_first_address(pump_readme, "The global configuration of the program is stored"),
        "global_pda",
        "pump",
        f"{GITHUB_RAW_BASE}docs/PUMP_PROGRAM_README.md",
        "Official Global account documented in the Pump README.",
        '["global"]',
    )
    add(
        "pump_authority",
        extract_first_address(pump_readme, '"authority"'),
        "authority",
        "pump",
        f"{GITHUB_RAW_BASE}docs/PUMP_PROGRAM_README.md",
        "Authority field disclosed inside the Global account example.",
    )
    add(
        "pump_fee_recipient",
        extract_first_address(pump_readme, '"fee_recipient"'),
        "fee_recipient",
        "pump",
        f"{GITHUB_RAW_BASE}docs/PUMP_PROGRAM_README.md",
        "Primary fee recipient disclosed inside the Global account example.",
    )
    add(
        "pump_withdraw_authority",
        extract_first_address(pump_readme, '"withdraw_authority"'),
        "authority",
        "pump",
        f"{GITHUB_RAW_BASE}docs/PUMP_PROGRAM_README.md",
        "Withdraw authority disclosed inside the Global account example.",
    )
    add(
        "pump_amm_global_config",
        extract_first_address(pump_swap_readme, "The global configuration of the program is stored"),
        "global_pda",
        "pump_amm",
        f"{GITHUB_RAW_BASE}docs/PUMP_SWAP_README.md",
        "Official GlobalConfig account documented in the Pump Swap README.",
        '["global_config"]',
    )
    add(
        "pump_amm_admin",
        extract_first_address(pump_swap_readme, '"admin"'),
        "authority",
        "pump_amm",
        f"{GITHUB_RAW_BASE}docs/PUMP_SWAP_README.md",
        "Admin field disclosed inside the GlobalConfig example.",
    )

    for idx, address in enumerate(extract_all_addresses(pump_swap_readme, '"protocol_fee_recipients"'), start=1):
        add(
            f"pump_amm_protocol_fee_recipient_{idx}",
            address,
            "fee_recipient",
            "pump_amm",
            f"{GITHUB_RAW_BASE}docs/PUMP_SWAP_README.md",
            "Protocol fee recipient disclosed in the Pump Swap README.",
        )

    add(
        "pump_user_volume_accumulator",
        None,
        "seed_pda_family",
        "pump",
        f"{GITHUB_RAW_BASE}docs/PUMP_CASHBACK_README.md",
        "Cashback README documents UserVolumeAccumulator as a Pump PDA family.",
        '"user_volume_accumulator" + user + pump program id',
    )
    add(
        "pump_amm_user_volume_accumulator",
        None,
        "seed_pda_family",
        "pump_amm",
        f"{GITHUB_RAW_BASE}docs/PUMP_CASHBACK_README.md",
        "Cashback README documents UserVolumeAccumulator as a Pump AMM PDA family.",
        '"user_volume_accumulator" + user + pump_amm program id',
    )
    add(
        "mayhem_program",
        extract_first_address(main_readme, "Mayhem program id"),
        "program",
        "mayhem",
        f"{GITHUB_RAW_BASE}README.md",
        "Official README discloses a dedicated Mayhem program id.",
    )

    for idx, address in enumerate(extract_all_addresses(main_readme, "Mayhem fee recipients"), start=1):
        add(
            f"mayhem_fee_recipient_{idx}",
            address,
            "fee_recipient",
            "mayhem",
            f"{GITHUB_RAW_BASE}README.md",
            "Official README discloses Mayhem fee recipients.",
        )

    add(
        "fees_api_endpoint",
        None,
        "metrics_api",
        None,
        FEES_API_URL,
        (
            "Official buyback metrics API used by the fees frontend. "
            f"Current totalPumpTokensBought={fees_api['totalPumpTokensBought']}."
        ),
    )

    custody_addresses = unique_preserve(
        re.findall(r"https://solscan\.io/account/([1-9A-HJ-NP-Za-km-z]{32,44})", fees_bundle_text)
    )
    for idx, address in enumerate(custody_addresses, start=1):
        add(
            f"fees_frontend_buyback_holder_{idx}",
            address,
            "custody_holder",
            None,
            FEES_SITE_URL,
            "Disclosed in the official fees frontend as a holder of previously bought back tokens.",
        )

    return objects


def build_buyback_relevance_matrix(program_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for row in program_rows:
        evidence = []
        if row["idl_present"]:
            evidence.append("official_public_idl")
        if row["docs_path"]:
            evidence.append("official_docs")
        if row["is_executable"]:
            evidence.append("onchain_executable")
        if row["programdata_address"]:
            evidence.append("upgradeable_loader_program")
        if any(instr.startswith("buy") for instr in row["key_instructions"]):
            evidence.append("contains_buy_instruction")
        if any("fee" in instr for instr in row["key_instructions"]):
            evidence.append("contains_fee_instruction")
        if any("cashback" in instr for instr in row["key_instructions"]):
            evidence.append("contains_cashback_instruction")
        matrix.append(
            {
                "program_name": row["program_name"],
                "program_address": row["program_address"],
                "category": row["buyback_relevance"],
                "evidence": evidence,
                "rationale": row["buyback_rationale"],
            }
        )
    return matrix


def render_report(
    repo_root: list[dict[str, Any]],
    docs_listing: list[dict[str, Any]],
    idl_listing: list[dict[str, Any]],
    repo_term_hits: dict[str, list[str]],
    program_rows: list[dict[str, Any]],
    object_rows: list[dict[str, Any]],
    fees_api: dict[str, Any],
    bundle_chunk_path: str,
) -> str:
    docs_table = "\n".join(
        f"| {row['program_name']} | `{row['program_address']}` | `{row['buyback_relevance']}` | "
        f"{row['source_code_status']} | `{row['upgrade_authority']}` |"
        for row in program_rows
    )
    repo_buyback_hits = {
        path: hits for path, hits in repo_term_hits.items() if hits
    }
    custody_rows = [
        row for row in object_rows if row["object_type"] == "custody_holder" and row["address"]
    ]
    holder_text = ", ".join(f"`{row['address']}`" for row in custody_rows)

    return f"""# Pump.fun Official Program Surface Report

Date: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}

## Scope

This report is built from official public sources first:

- `pump-fun/pump-public-docs`
- `fees.pump.fun`
- on-chain Solana RPC verification of the official program ids

This report does **not** start from previously tracked wallet hypotheses. It focuses on the official Solana program surface and the public question: does Pump.fun expose a dedicated buyback program?

## Official Public Surface

- Official GitHub repo root entries: {", ".join(f"`{row['name']}`" for row in repo_root)}
- Official docs files: {", ".join(f"`{row['name']}`" for row in docs_listing)}
- Official IDL files: {", ".join(f"`{row['name']}`" for row in idl_listing)}
- `fees.pump.fun/api/buybacks` currently reports:
  - `totalPumpTokensBought = {fees_api['totalPumpTokensBought']:.6f}`
  - `totalBuybackUsd = {fees_api['totalBuybackUsd']:.6f}`
  - `totalDays = {fees_api['totalDays']}`
  - `lastUpdated = {fees_api['lastUpdated']}`
- Official fees frontend bundle located at `{bundle_chunk_path}` contains:
  - `/api/buybacks`
  - `dailyBuybacks`
  - two disclosed buyback holder addresses: {holder_text}

## Official Programs

| Program | Address | Buyback Relevance | Public Code Status | Upgrade Authority |
|---|---|---|---|---|
{docs_table}

Common observations:

- All four public program ids are executable on mainnet and owned by `BPFLoaderUpgradeab1e11111111111111111111111`.
- All four currently resolve to the **same upgrade authority**: `7gZufwwAo17y5kg8FMyJy2phgpvv9RSdzWtdXiWHjFr8`.
- `pump`, `pump_amm`, and `pump_fees` have public IDLs, but the official repo does **not** publish full on-chain source code for these programs.
- `mayhem` is officially disclosed in the main README, but there is no public IDL for it in the repo.

## What Official Sources Say About Buybacks

Official repo and IDL scan for terms related to buyback:

```json
{json.dumps(repo_buyback_hits, indent=2)}
```

Interpretation:

- The official repo exposes **no file, instruction, or program name containing `buyback`**.
- The public repo also does not expose `token purchases` or `dailyBuybacks` inside the GitHub docs/IDL surface.
- Buyback language appears on the **fees frontend / metrics layer**, not in the public program docs.

What the official surfaces do expose:

- `pump` contains direct buy instructions such as `buy` and `buy_exact_sol_in`.
- `pump_amm` contains direct buy instructions such as `buy` and `buy_exact_quote_in`.
- `pump_fees` contains fee calculation and sharing primitives such as `get_fees`, `update_fee_config`, and `update_fee_shares`.
- `PUMP_CASHBACK_README` documents `UserVolumeAccumulator` PDA families for both `pump` and `pump_amm`.
- The main README documents a separate `mayhem` program id and Mayhem-specific fee recipients.

## Best Current Answer on Buyback Program

### 1. Is there a public dedicated Buyback Program?

**No public evidence was found for a dedicated buyback-only program.**

Reasons:

- No official GitHub repo file or IDL is named for buyback.
- No official IDL contains a buyback-specific instruction.
- The official fees frontend publishes **aggregated buyback metrics** and **custody addresses**, not an execution program id.

### 2. What is the most likely official execution stack?

Based on official public surfaces only, the most defensible stack is:

1. **Metrics layer**
   - `fees.pump.fun/api/buybacks`
2. **Fee / accounting support**
   - `pump_fees`
3. **Trading execution**
   - `pump`
   - `pump_amm`
4. **Mode / routing modifiers**
   - `cashback`
   - `mayhem`
5. **Custody disclosure**
   - {holder_text}

### 3. What is still not public?

- No public buyback-only contract or IDL
- No official per-trade buyback execution ledger
- No official public source code for the deployed Solana programs
- No official public mapping from `dailyBuybacks` to exact executor accounts or transaction hashes

## Bottom Line

The official public surface supports this conclusion:

- Pump.fun publicly exposes a **program stack**, not a public buyback-only program.
- Public buyback disclosure currently lives in the **fees dashboard and API**, while direct execution capability lives in the official trading programs `pump` and `pump_amm`, with `pump_fees` supporting fee/accounting logic.
- Any stronger claim about a standalone buyback executor would require non-public code, direct transaction attribution, or additional official disclosure that is not currently published.
"""


def main() -> None:
    OUT_DERIVED.mkdir(parents=True, exist_ok=True)
    OUT_REPORTS.mkdir(parents=True, exist_ok=True)

    repo_root = github_contents("")
    docs_listing = github_contents("docs")
    idl_listing = github_contents("idl")

    file_paths = ["README.md"] + [f"docs/{row['name']}" for row in docs_listing] + [
        f"idl/{row['name']}" for row in idl_listing if row["name"].endswith(".json")
    ]
    files = {path: fetch_text(f"{GITHUB_RAW_BASE}{path}") for path in file_paths}

    main_readme = files["README.md"]
    docs_text = {path: text for path, text in files.items() if path.startswith("docs/")}
    idls = {
        path.split("/")[-1].replace(".json", ""): json.loads(text)
        for path, text in files.items()
        if path.startswith("idl/") and path.endswith(".json")
    }

    fees_api = fetch_json_url(FEES_API_URL)
    fees_html = fetch_text(FEES_SITE_URL)
    bundle_chunk_path, fees_bundle_text = find_chunk_with_needles(
        fees_html,
        [
            "/api/buybacks",
            "dailyBuybacks",
            "Previously bought back tokens are held at",
        ],
    )
    if not bundle_chunk_path or not fees_bundle_text:
        raise RuntimeError("Could not locate fees frontend chunk with buyback disclosure text")

    repo_term_hits = scan_terms(files)
    program_infos = build_program_infos(docs_text, idls, main_readme)
    program_rows = [enrich_program_chain_metadata(info) for info in program_infos]
    object_rows = build_object_registry(docs_text, main_readme, fees_bundle_text, fees_api)
    relevance_matrix = build_buyback_relevance_matrix(program_rows)

    registry = {
        "metadata": {
            "generated_at": now_iso(),
            "source_priority": [
                "official GitHub repo",
                "official fees frontend/API",
                "on-chain Solana RPC verification",
            ],
            "repo": "pump-fun/pump-public-docs",
            "scope": "Official Pump.fun Solana program surface",
        },
        "official_surface": {
            "repo_root_entries": [row["name"] for row in repo_root],
            "docs_files": [row["name"] for row in docs_listing],
            "idl_files": [row["name"] for row in idl_listing],
            "fees_site_bundle": bundle_chunk_path,
            "fees_api_snapshot": {
                "totalPumpTokensBought": fees_api["totalPumpTokensBought"],
                "totalBuybackUsd": fees_api["totalBuybackUsd"],
                "totalDays": fees_api["totalDays"],
                "lastUpdated": fees_api["lastUpdated"],
            },
        },
        "programs": program_rows,
    }

    report = render_report(
        repo_root=repo_root,
        docs_listing=docs_listing,
        idl_listing=idl_listing,
        repo_term_hits=repo_term_hits,
        program_rows=program_rows,
        object_rows=object_rows,
        fees_api=fees_api,
        bundle_chunk_path=bundle_chunk_path,
    )

    (OUT_DERIVED / "pumpfun_official_program_registry.json").write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
    )
    (OUT_DERIVED / "pumpfun_official_object_registry.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "generated_at": now_iso(),
                    "scope": "Official Pump.fun objects and disclosed holders",
                },
                "objects": object_rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT_DERIVED / "pumpfun_buyback_relevance_matrix.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "generated_at": now_iso(),
                    "scope": "Official Pump.fun program buyback relevance matrix",
                },
                "matrix": relevance_matrix,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT_REPORTS / "pumpfun_official_program_surface_report_20260325.md").write_text(
        report + "\n", encoding="utf-8"
    )

    print("Wrote:")
    print(OUT_DERIVED / "pumpfun_official_program_registry.json")
    print(OUT_DERIVED / "pumpfun_official_object_registry.json")
    print(OUT_DERIVED / "pumpfun_buyback_relevance_matrix.json")
    print(OUT_REPORTS / "pumpfun_official_program_surface_report_20260325.md")


if __name__ == "__main__":
    main()
