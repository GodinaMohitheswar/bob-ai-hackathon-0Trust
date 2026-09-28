#!/usr/bin/env node
/**
 * FRAUDGRAPH MCP Server
 *
 * Exposes a single read-only tool — get_case_investigation — that calls
 * the existing FRAUDGRAPH FastAPI backend and returns a sanitised
 * investigation report.
 *
 * Sensitive fields (Aadhaar numbers, IFSC codes, raw account numbers,
 * originating IPs, bank details) are stripped before the data leaves
 * this server.  The synthetic is_fraudulent label is never used for
 * scoring — that logic lives entirely inside risk_scoring.py.
 *
 * Transport: stdio (Bob spawns this process directly).
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// -----------------------------------------------------------------
// Configuration
// -----------------------------------------------------------------

const BACKEND_URL =
  process.env.FRAUDGRAPH_BACKEND_URL ?? "http://127.0.0.1:8000";

// -----------------------------------------------------------------
// Types returned by the FastAPI /cases/{case_id}/brief-data endpoint
// -----------------------------------------------------------------

interface EvidenceFinding {
  pattern_type: string;
  severity: string;
  description: string;
  entities?: string[];
  evidence?: string[];
  // presence of these fields varies by finding type
  [key: string]: unknown;
}

interface BackendBriefData {
  case_id: string;
  investigation: {
    score: number;
    priority: string;
    evidence_count: number;
  };
  network: {
    case_id: string;
    nodes: number;
    edges: number;
    node_types: Record<string, number>;
    relationship_types: Record<string, number>;
  };
  hierarchy: Array<{
    identity_id: string;
    name: string;
    role: string;
    mule_level: number | null;
    phone: string;
    account_id: string;
    city: string | null;
    state: string | null;
  }>;
  evidence: EvidenceFinding[];
  recommended_actions: string[];
  disclaimer: string;
}

// -----------------------------------------------------------------
// Field allow-lists  (everything NOT on these lists is dropped)
// -----------------------------------------------------------------

/** Allowed top-level keys on each consolidated evidence finding. */
const ALLOWED_FINDING_KEYS = new Set([
  "pattern_type",
  "severity",
  "description",
  "entities",
  "evidence",
  // layering-chain specific
  "path",
  "depth",
  // device-cluster specific
  "device_ids",
  "identity_ids",
  "device_count",
  // transaction-cluster specific
  "transaction_ids",
  "transaction_count",
  "total_amount",
  // communication-loop specific
  "loop_length",
  // prior-fraud specific
  "identity_count",
  // recommended investigative actions
  "recommended_actions",
]);

/** Allowed keys on each hierarchy entry (the identity roster). */
const ALLOWED_HIERARCHY_KEYS = new Set([
  "identity_id",
  "name",
  "role",
  "mule_level",
  "phone",
  "city",
  "state",
]);
// NOTE: account_id is intentionally excluded — raw account numbers
// are considered sensitive bank details.

// -----------------------------------------------------------------
// Sanitise helpers
// -----------------------------------------------------------------

/** Keep only the allow-listed keys from an object. */
function pick<T extends Record<string, unknown>>(
  obj: T,
  allowed: Set<string>
): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).filter(([k]) => allowed.has(k))
  );
}

/** Sanitise a single finding — drop sensitive / irrelevant keys. */
function sanitiseFinding(finding: EvidenceFinding): Record<string, unknown> {
  const clean = pick(finding as unknown as Record<string, unknown>, ALLOWED_FINDING_KEYS);

  // Remove originating IPs that may appear inside the evidence array.
  if (Array.isArray(clean.evidence)) {
    clean.evidence = (clean.evidence as string[]).filter(
      (line: string) =>
        !line.toLowerCase().startsWith("ip:") &&
        !line.toLowerCase().includes("originating ip")
    );
  }

  return clean;
}

/** Sanitise the hierarchy (identity roster). */
function sanitiseHierarchy(
  hierarchy: BackendBriefData["hierarchy"]
): Record<string, unknown>[] {
  return hierarchy.map((entry) =>
    pick(entry as unknown as Record<string, unknown>, ALLOWED_HIERARCHY_KEYS)
  );
}

// -----------------------------------------------------------------
// Backend fetch helpers
// -----------------------------------------------------------------

async function fetchBriefData(caseId: string): Promise<BackendBriefData> {
  const url = `${BACKEND_URL}/cases/${encodeURIComponent(caseId)}/brief-data`;

  let response: Response;
  try {
    response = await fetch(url);
  } catch (err) {
    throw new Error(
      `Cannot reach FRAUDGRAPH backend at ${BACKEND_URL}. ` +
        `Is the FastAPI server running? (${String(err)})`
    );
  }

  if (response.status === 404) {
    throw new Error(`Case "${caseId}" was not found in the FRAUDGRAPH dataset.`);
  }

  if (!response.ok) {
    throw new Error(
      `Backend returned HTTP ${response.status} for case "${caseId}".`
    );
  }

  return (await response.json()) as BackendBriefData;
}

// -----------------------------------------------------------------
// Build the sanitised investigation report
// -----------------------------------------------------------------

function buildReport(data: BackendBriefData): Record<string, unknown> {
  return {
    case_id: data.case_id,

    investigation: {
      score: data.investigation.score,
      priority: data.investigation.priority,
      evidence_count: data.investigation.evidence_count,
    },

    // Network topology summary — counts only, no raw IDs.
    network_summary: {
      total_nodes: data.network.nodes,
      total_edges: data.network.edges,
      node_types: data.network.node_types,
      relationship_types: data.network.relationship_types,
    },

    // Consolidated investigative evidence — sensitive fields stripped.
    evidence_findings: data.evidence.map(sanitiseFinding),

    // Identity roster — account numbers, Aadhaar, IFSC removed.
    hierarchy: sanitiseHierarchy(data.hierarchy),

    // Deduplicated case-level recommended actions (ordered by signal weight).
    recommended_actions: data.recommended_actions ?? [],

    disclaimer: data.disclaimer,
  };
}

// -----------------------------------------------------------------
// MCP Server
// -----------------------------------------------------------------

const server = new McpServer({
  name: "fraudgraph-mcp",
  version: "1.0.0",
});

server.registerTool(
  "get_case_investigation",
  {
    description:
      "Retrieve a sanitised investigation report for a FRAUDGRAPH case. " +
      "Returns the investigation score, priority, consolidated evidence " +
      "findings, network topology summary, and identity hierarchy. " +
      "Sensitive fields such as Aadhaar numbers, IFSC codes, and raw bank " +
      "account numbers are removed before the data is returned.",
    inputSchema: z.object({
      case_id: z
        .string()
        .min(1)
        .describe(
          'The FRAUDGRAPH case identifier, e.g. "CASE008". ' +
            "Must match a case loaded by the backend."
        ),
    }),
  },
  async ({ case_id }) => {
    try {
      const rawData = await fetchBriefData(case_id);
      const report = buildReport(rawData);

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(report, null, 2),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text",
            text:
              err instanceof Error
                ? err.message
                : `Unexpected error: ${String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// -----------------------------------------------------------------
// Entry point
// -----------------------------------------------------------------

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("fraudgraph-mcp running on stdio");
}

main().catch((err) => {
  console.error("Fatal error in fraudgraph-mcp:", err);
  process.exit(1);
});
