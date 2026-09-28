# Problem Statement

## Background

India processed over 13 billion UPI transactions in FY2023, making it the world's largest real-time payments network. This scale has been exploited by organised cyber-fraud rings — most infamously the **Jamtara SIM-swap network** in Jharkhand, which became a blueprint for coordinated UPI fraud across the country. These rings operate with a deliberate organisational structure: a **kingpin** recruits and directs multiple layers of **mule accounts** to receive, split, and launder stolen funds before victims or banks can freeze them. Call logs, OTP relay chains, spoofed caller IDs, and shared SIM/device pools are the operational tools of these networks.

Cyber-crime investigators — police officers at state cyber-crime cells, financial intelligence units, and bank fraud teams — receive complaints that arrive as raw, disconnected data: a victim's transaction record here, a call log there, a list of suspected account numbers somewhere else. Connecting these fragments into an actionable case picture currently requires **weeks of manual cross-referencing** across spreadsheets, with no tooling to visualise the network, rank leads by urgency, or produce a court-ready brief.

---

## The Problem

Cyber-fraud investigators spend **days to weeks manually tracing relationships** between bank accounts, SIM cards, devices, and suspected individuals across siloed data sources, with no network visualisation, no automated signal detection, and no structured output format. In the dataset modelled by this project — 87 fraud cases spanning Jharkhand, Maharashtra, Karnataka, West Bengal, Delhi, Gujarat, Bihar, Uttar Pradesh, and Rajasthan — **approximately 41% of fraud cases had no complaint filed at all**, and of those that were reported, **roughly 75% remain either "Not Reported" or "Unsolved — Under Investigation"**. Cases like CASE008 (Circular Layering, Ranchi, ₹12.5L) and CASE054 (Layering Chain, Deoghar, ₹14L) sit unresolved because investigators have no way to rapidly see that a single device is linked to multiple identities, that funds are cycling through a closed account loop, or that a cluster of SMS calls immediately preceded every fraudulent transaction.

The specific failure modes are:

- **No graph visibility** — investigators cannot see that device `D0002` is shared across 3 identities, or that accounts `A1001 → A1002 → A1005` form a fan-out distribution network, without manually building these connections in a spreadsheet.
- **No pattern vocabulary** — terms like "Circular Layering", "Fan-Out Distribution", "Layering Chain", and "SIM-Swap Ring" are understood by experienced investigators but are never automatically identified from raw transaction and call data.
- **No hierarchy mapping** — the **kingpin → mule (level 1) → mule (level 2) → victim** chain is the organisational fact that determines arrest priority, yet it is buried in identity records that are never joined to call and transaction evidence.
- **No risk prioritisation** — with dozens of open cases, investigators have no scoring mechanism to decide which case to work on first. A CRITICAL case (score ≥ 60) and a LOW case look identical in a raw CSV file.
- **No FIR-ready output** — every case requires an investigator to manually write a case brief summarising entities, evidence, and recommended actions. This is the final bottleneck before any legal action.

---

## Who is Affected

**Primary users:** Cyber-crime investigators at state police cyber-cells (e.g., Jharkhand, Maharashtra, West Bengal), financial intelligence analysts at banks, and RBI-regulated payment system operators who must respond to fraud complaints under the DPSS framework.

**Secondary users:** Courts and public prosecutors who receive FIRs — they need structured, reproducible evidence chains, not hand-assembled spreadsheets.

**Victims:** UPI users who lose funds to these networks. In the dataset, individual case losses range from ₹97,647 (CASE089) to ₹13,99,826 (CASE054). Across the 87 modelled fraud cases alone, the total funds moved through fraudulent networks exceeds **₹4.7 crore** — and the real-world Jamtara ring affected over **95,000 UPI transactions in FY2023 alone**.

---

## Why It Matters

1. **Scale and velocity:** A single SIM-swap ring can execute dozens of fraudulent transactions within hours of account takeover. Manual investigation cannot match this speed — by the time connections are traced, funds have been layered through 3–6 accounts and withdrawn.

2. **Geographic spread:** The dataset covers fraud activity across **14 cities in 10 states**, with Jharkhand cities (Jamtara, Deoghar, Dhanbad, Ranchi) accounting for roughly **32% of all fraud cases** — consistent with the real-world Jamtara cluster. No single jurisdiction has full visibility; cases cross state lines.

3. **Organisational complexity:** Fraud networks use **up to 8 identities and 6 mule layers** per case (e.g., CASE002, CASE062, CASE073). Each additional layer increases the manual tracing workload exponentially. Without automated graph construction, the inner layers are almost never reached before cases go cold.

4. **Evidence decay:** Call records, device logs, and transaction metadata have retention windows. Every week an investigator spends manually assembling a network picture is a week of evidence potentially expiring.

5. **Justice gap:** Of 87 fraud cases in the modelled dataset, only **6 are "Closed — Recovered"** and **8 have a chargesheet filed** — a resolution rate of roughly **16%**. This is not primarily a legal problem; it is an intelligence tooling problem.

---

## Why Existing Solutions Fall Short

| Approach | What investigators currently do | Why it fails |
|---|---|---|
| **Manual spreadsheet analysis** | Cross-reference transaction CSVs, call logs, and identity records by hand | Cannot detect graph patterns (cycles, fan-outs, layering chains) across hundreds of rows; errors accumulate; takes days per case |
| **Generic BI dashboards** | Pivot tables in Excel / basic dashboards | Show counts and amounts but cannot trace network relationships or map the kingpin–mule hierarchy |
| **Bank fraud systems** | Banks flag individual suspicious transactions via rule engines | Operate per-transaction, per-account; cannot see the cross-account, cross-device network that spans multiple banks and telecom operators |
| **Manual FIR writing** | Investigators type case briefs from memory and notes | Inconsistent, slow, omits evidence, not reproducible by a different officer |
| **Standalone graph tools (e.g., Maltego)** | Specialist OSINT tools used by some state units | Expensive, require significant training, do not ingest Indian banking/UPI data formats, and produce no investigation priority score |

What is missing is a **purpose-built, India-specific cyber-fraud intelligence platform** that automatically ingests multi-source case data, constructs the relationship graph, runs behavioural signal detection, scores investigation priority, maps the organisational hierarchy, and generates a structured brief — in seconds, not weeks.
