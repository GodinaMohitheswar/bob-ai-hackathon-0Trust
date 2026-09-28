import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState("CASE008");
  const [brief, setBrief] = useState(null);
  const [firBrief, setFirBrief] = useState(null);
  const [network, setNetwork] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedEvidence, setSelectedEvidence] = useState(null);
  const [focusedIds, setFocusedIds] = useState([]);

  // ---------------------------------------------------------
  // LOAD CASE LIST
  // ---------------------------------------------------------

  useEffect(() => {
    loadCases();
  }, []);

  useEffect(() => {
    if (selectedCase) {
      loadCaseBrief(selectedCase);
    }
  }, [selectedCase]);

  async function loadCases() {
    try {
      setError("");

      const response = await fetch(`${API}/cases`);

      if (!response.ok) {
        throw new Error(
          `Failed to load cases: ${response.status}`
        );
      }

      const data = await response.json();

      let caseList = [];

      if (Array.isArray(data)) {
        caseList = data;
      } else if (Array.isArray(data.cases)) {
        caseList = data.cases;
      }

      setCases(caseList);

      const case008Exists = caseList.some(
        (item) => item.case_id === "CASE008"
      );

      if (case008Exists) {
        setSelectedCase("CASE008");
      } else if (caseList.length > 0) {
        setSelectedCase(caseList[0].case_id);
      }
    } catch (err) {
      console.error("Case loading error:", err);
      setError(err.message);
    }
  }

  // ---------------------------------------------------------
  // LOAD SELECTED CASE
  // ---------------------------------------------------------

  async function loadCaseBrief(caseId) {
    try {
      setLoading(true);
      setError("");
      setSelectedEvidence(null);
      setFocusedIds([]);

      const [briefResponse, networkResponse, firResponse] =
        await Promise.all([
          fetch(`${API}/cases/${caseId}/brief-data`),
          fetch(`${API}/cases/${caseId}/network`),
          fetch(`${API}/cases/${caseId}/fir-brief`),
        ]);

      if (!briefResponse.ok) {
        throw new Error(
          `Brief request failed: ${briefResponse.status}`
        );
      }

      if (!networkResponse.ok) {
        throw new Error(
          `Network request failed: ${networkResponse.status}`
        );
      }

      const briefData = await briefResponse.json();
      const networkData = await networkResponse.json();
      const firData = firResponse.ok
        ? await firResponse.json()
        : null;

      // -----------------------------------------------------
      // NETWORK SUMMARY
      // -----------------------------------------------------

      const networkSummary =
        briefData.network ||
        briefData.network_summary ||
        networkData.summary ||
        {};

      const nodeCount =
        networkSummary.node_count ??
        networkSummary.nodes ??
        networkData.nodes?.length ??
        0;

      const edgeCount =
        networkSummary.edge_count ??
        networkSummary.edges ??
        networkData.edges?.length ??
        0;

      // -----------------------------------------------------
      // NORMALIZE BRIEF
      // -----------------------------------------------------

      const normalizedBrief = {
        ...briefData,

        case_id:
          briefData.case_id ||
          briefData.caseId ||
          caseId,

        investigation_score:
          briefData.investigation_score ??
          briefData.score ??
          briefData.investigation?.score ??
          0,

        priority:
          briefData.priority ||
          briefData.investigation_priority ||
          briefData.investigation?.priority ||
          "LOW",

        evidence_count:
          briefData.evidence_count ??
          (Array.isArray(briefData.evidence)
            ? briefData.evidence.length
            : 0),

        evidence: Array.isArray(briefData.evidence)
          ? briefData.evidence
          : [],

        hierarchy: Array.isArray(briefData.hierarchy)
          ? briefData.hierarchy
          : [],

        network: {
          ...networkSummary,
          node_count: nodeCount,
          edge_count: edgeCount,
        },

        disclaimer:
          briefData.disclaimer ||
          "This output contains synthetic investigative signals derived from mock case records. It does not establish fraud, guilt, or criminal responsibility.",
      };

      setBrief(normalizedBrief);
      setNetwork(networkData);
      setFirBrief(firData);
    } catch (err) {
      console.error("Case data error:", err);

      setError(err.message);
      setBrief(null);
      setNetwork(null);
      setFirBrief(null);
    } finally {
      setLoading(false);
    }
  }

  // ---------------------------------------------------------
  // EVIDENCE → GRAPH FOCUS
  // ---------------------------------------------------------

  function getEvidenceFocus(evidence) {
    if (!evidence) {
      return [];
    }

    const ids = new Set();

    if (Array.isArray(evidence.entities)) {
      evidence.entities.forEach((id) => ids.add(id));
    }

    if (Array.isArray(evidence.transaction_ids)) {
      evidence.transaction_ids.forEach((id) => ids.add(id));
    }

    if (Array.isArray(evidence.device_ids)) {
      evidence.device_ids.forEach((id) => ids.add(id));
    }

    if (Array.isArray(evidence.identity_ids)) {
      evidence.identity_ids.forEach((id) => ids.add(id));
    }

    if (Array.isArray(evidence.cycle)) {
      evidence.cycle.forEach((id) => ids.add(id));
    }

    if (Array.isArray(evidence.path)) {
      evidence.path.forEach((id) => ids.add(id));
    }

    return Array.from(ids);
  }

  function handleEvidenceClick(evidence) {
    const ids = getEvidenceFocus(evidence);

    setSelectedEvidence(evidence);
    setFocusedIds(ids);
  }

  function clearFocus() {
    setSelectedEvidence(null);
    setFocusedIds([]);
  }

  // ---------------------------------------------------------
  // GRAPH NODES
  // ---------------------------------------------------------

  const graphNodes = useMemo(() => {
    if (!network?.nodes) {
      return [];
    }

    const nodes = network.nodes.filter((node) =>
      [
        "case",
        "identity",
        "account",
        "phone",
        "device",
        "transaction",
        "call",
      ].includes(node.type)
    );

    const caseNodes = nodes.filter(
      (node) => node.type === "case"
    );

    const identities = nodes.filter(
      (node) => node.type === "identity"
    );

    const accounts = nodes.filter(
      (node) => node.type === "account"
    );

    const phones = nodes.filter(
      (node) => node.type === "phone"
    );

    const devices = nodes.filter(
      (node) => node.type === "device"
    );

    const transactions = nodes.filter(
      (node) => node.type === "transaction"
    );

    const calls = nodes.filter(
      (node) => node.type === "call"
    );

    function position(index, total, y) {
      const spacing = 205;

      const startX =
        650 - ((total - 1) * spacing) / 2;

      return {
        x: startX + index * spacing,
        y,
      };
    }

    return [
      // -----------------------------------------------------
      // CASE
      // -----------------------------------------------------

      ...caseNodes.map((node) => ({
        id: node.id,

        position: {
          x: 650,
          y: 20,
        },

        data: {
          label: `${node.id}\n${
            node.pattern_type || "CASE"
          }`,
        },

        className: [
          "graph-node",
          "graph-case",
          focusedIds.includes(node.id)
            ? "graph-focused"
            : "",
        ]
          .filter(Boolean)
          .join(" "),
      })),

      // -----------------------------------------------------
      // IDENTITIES
      // -----------------------------------------------------

      ...identities.map((node, index) => ({
        id: node.id,

        position: position(
          index,
          identities.length,
          140
        ),

        data: {
          label: `${node.name || node.id}\n${
            node.role || "identity"
          }`,
        },

        className: [
          "graph-node",
          "graph-identity",

          node.role === "kingpin"
            ? "graph-kingpin"
            : "",

          node.role === "mule"
            ? "graph-mule"
            : "",

          node.role === "victim"
            ? "graph-victim"
            : "",

          focusedIds.includes(node.id)
            ? "graph-focused"
            : "",
        ]
          .filter(Boolean)
          .join(" "),
      })),

      // -----------------------------------------------------
      // ACCOUNTS
      // -----------------------------------------------------

      ...accounts.map((node, index) => ({
        id: node.id,

        position: position(
          index,
          accounts.length,
          285
        ),

        data: {
          label: `ACCOUNT\n${node.id}`,
        },

        className: [
          "graph-node",
          "graph-account",

          focusedIds.includes(node.id)
            ? "graph-focused"
            : "",
        ]
          .filter(Boolean)
          .join(" "),
      })),

      // -----------------------------------------------------
      // PHONES
      // -----------------------------------------------------

      ...phones.map((node, index) => ({
        id: node.id,

        position: position(
          index,
          phones.length,
          430
        ),

        data: {
          label: `PHONE\n${node.id}`,
        },

        className: [
          "graph-node",
          "graph-phone",

          focusedIds.includes(node.id)
            ? "graph-focused"
            : "",
        ]
          .filter(Boolean)
          .join(" "),
      })),

      // -----------------------------------------------------
      // DEVICES
      // -----------------------------------------------------

      ...devices.map((node, index) => ({
        id: node.id,

        position: position(
          index,
          devices.length,
          575
        ),

        data: {
          label: `DEVICE\n${node.id}${
            node.device_risk_flag
              ? "\n⚠ RISK FLAG"
              : ""
          }`,
        },

        className: [
          "graph-node",
          "graph-device",

          node.device_risk_flag
            ? "graph-risk"
            : "",

          focusedIds.includes(node.id)
            ? "graph-focused"
            : "",
        ]
          .filter(Boolean)
          .join(" "),
      })),

      // -----------------------------------------------------
      // TRANSACTIONS
      // -----------------------------------------------------

      ...transactions.map((node, index) => ({
        id: node.id,

        position: position(
          index,
          transactions.length,
          720
        ),

        data: {
          label: `TX ${node.id}\n₹${Number(
            node.amount ??
            node.value ??
            node.transaction_amount ??
            0
          ).toLocaleString("en-IN")}\n${
            node.channel || "TX"
          }`,
        },

        className: [
          "graph-node",
          "graph-transaction",

          focusedIds.includes(node.id)
            ? "graph-focused"
            : "",
        ]
          .filter(Boolean)
          .join(" "),
      })),

      // -----------------------------------------------------
      // CALLS
      // -----------------------------------------------------

      ...calls.map((node, index) => ({
        id: node.id,

        position: position(
          index,
          calls.length,
          865
        ),

        data: {
          label: `CALL ${node.id}\n${
            node.call_type || "call"
          }${
            node.caller_id_spoof_suspected
              ? "\n⚠ SPOOF"
              : ""
          }`,
        },

        className: [
          "graph-node",
          "graph-call",

          focusedIds.includes(node.id)
            ? "graph-focused"
            : "",
        ]
          .filter(Boolean)
          .join(" "),
      })),
    ];
  }, [network, focusedIds]);

  // ---------------------------------------------------------
  // GRAPH EDGES
  // ---------------------------------------------------------

  const graphEdges = useMemo(() => {
    if (!network?.edges) {
      return [];
    }

    return network.edges
      .filter(
        (edge) =>
          edge.source &&
          edge.target
      )
      .map((edge, index) => {
        const edgeId =
          `${edge.source}-${edge.target}-${index}`;

        const isFocused =
          focusedIds.includes(edge.source) &&
          focusedIds.includes(edge.target);

        return {
          id: edgeId,

          source: edge.source,

          target: edge.target,

          label:
            edge.relationship_type ||
            edge.relationship ||
            edge.type ||
            "",

          animated:
            edge.relationship_type ===
              "transaction" ||
            edge.relationship ===
              "transaction",

          markerEnd: {
            type: MarkerType.ArrowClosed,
          },

          className: isFocused
            ? "graph-edge-focused"
            : "",
        };
      });
  }, [network, focusedIds]);

  // ---------------------------------------------------------
  // EVIDENCE
  // ---------------------------------------------------------

  const evidence = brief?.evidence || [];

  // ---------------------------------------------------------
  // UI
  // ---------------------------------------------------------

  return (
    <div className="app">

      {/* =====================================================
          TOP BAR
      ===================================================== */}

      <header className="topbar">

        <div>
          <div className="brand">
            FRAUDGRAPH
          </div>

          <div className="brand-subtitle">
            Cyber Fraud Investigation &
            Network Intelligence
          </div>
        </div>

        <div className="case-selector">

          <label htmlFor="case-select">
            Investigation Case
          </label>

          <select
            id="case-select"
            value={selectedCase}
            onChange={(event) =>
              setSelectedCase(
                event.target.value
              )
            }
          >
            {cases.map((item) => (
              <option
                key={item.case_id}
                value={item.case_id}
              >
                {item.case_id}
              </option>
            ))}
          </select>

        </div>

      </header>

      {/* =====================================================
          MAIN
      ===================================================== */}

      <main>

        {/* LOADING */}

        {loading && (
          <div className="status-box">
            Loading investigation data...
          </div>
        )}

        {/* ERROR */}

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        {/* ===================================================
            DASHBOARD
        =================================================== */}

        {brief && !loading && (
          <>

            {/* HERO */}

            <section className="hero">

              <div>

                <div className="eyebrow">
                  ACTIVE INVESTIGATION
                </div>

                <h1>
                  {brief.case_id}
                </h1>

                <p>
                  Network-based analysis of
                  identities, accounts, devices,
                  transactions and communications.
                </p>

              </div>

              <div className="hero-priority">

                <span>
                  Investigation Priority
                </span>

                <strong>
                  {brief.priority}
                </strong>

              </div>

            </section>

            {/* METRICS */}

            <section className="metrics">

              <div className="metric-card">

                <span>
                  Investigation Score
                </span>

                <strong>
                  {brief.investigation_score}/100
                </strong>

              </div>

              <div className="metric-card">

                <span>
                  Priority
                </span>

                <strong>
                  {brief.priority}
                </strong>

              </div>

              <div className="metric-card">

                <span>
                  Evidence Signals
                </span>

                <strong>
                  {brief.evidence_count}
                </strong>

              </div>

              <div className="metric-card">

                <span>
                  Network Nodes
                </span>

                <strong>
                  {brief.network?.node_count || 0}
                </strong>

              </div>

            </section>

            {/* =================================================
                EVIDENCE + GRAPH
            ================================================= */}

            <section className="content-grid">

              {/* EVIDENCE */}

              <div className="panel evidence-panel">

                <div className="panel-header">

                  <div>

                    <span className="eyebrow">
                      EVIDENCE ENGINE
                    </span>

                    <h2>
                      Investigative Signals
                    </h2>

                  </div>

                  {selectedEvidence && (
                    <button
                      className="clear-focus"
                      onClick={clearFocus}
                    >
                      Clear Focus
                    </button>
                  )}

                </div>

                <p className="panel-help">
                  Click a signal to highlight
                  its related entities in the
                  network.
                </p>

                <div className="evidence-list">

                  {evidence.map(
                    (item, index) => {

                      const isSelected =
                        selectedEvidence ===
                        item;

                      return (
                        <button
                          key={`${item.pattern_type}-${index}`}
                          className={`evidence-card ${
                            isSelected
                              ? "evidence-selected"
                              : ""
                          }`}
                          onClick={() =>
                            handleEvidenceClick(
                              item
                            )
                          }
                        >

                          <div className="evidence-top">

                            <span className="evidence-number">
                              {String(
                                index + 1
                              ).padStart(
                                2,
                                "0"
                              )}
                            </span>

                            <span
                              className={`severity ${
                                item.severity?.toLowerCase() ||
                                "medium"
                              }`}
                            >
                              {item.severity ||
                                "MEDIUM"}
                            </span>

                          </div>

                          <h3>
                            {item.pattern_type}
                          </h3>

                          <p>
                            {item.description}
                          </p>

                          {item.transaction_ids
                            ?.length > 0 && (
                            <div className="evidence-meta">
                              {
                                item
                                  .transaction_ids
                                  .length
                              }{" "}
                              transaction
                              {item.transaction_ids
                                .length !== 1
                                ? "s"
                                : ""}
                            </div>
                          )}

                          {item.device_ids
                            ?.length > 0 && (
                            <div className="evidence-meta">
                              {
                                item.device_ids
                                  .length
                              }{" "}
                              flagged device
                              {item.device_ids
                                .length !== 1
                                ? "s"
                                : ""}
                            </div>
                          )}

                          {isSelected &&
                            item.recommended_actions
                              ?.length > 0 && (
                            <div className="evidence-actions">
                              <div className="evidence-actions-label">
                                Recommended Actions
                              </div>
                              <ol className="evidence-actions-list">
                                {item.recommended_actions.map(
                                  (action, ai) => (
                                    <li key={ai}>
                                      {action}
                                    </li>
                                  )
                                )}
                              </ol>
                            </div>
                          )}

                        </button>
                      );
                    }
                  )}

                </div>

              </div>

              {/* GRAPH */}

              <div className="panel network-panel">

                <div className="panel-header">

                  <div>

                    <span className="eyebrow">
                      RELATIONSHIP GRAPH
                    </span>

                    <h2>
                      Fraud Network
                    </h2>

                  </div>

                  <div className="network-summary">

                    {focusedIds.length > 0
                      ? `${focusedIds.length} entities focused`
                      : `${
                          brief.network
                            ?.node_count ||
                          0
                        } nodes`}

                  </div>

                </div>

                <div className="network-graph">

                  {graphNodes.length > 0 ? (
                    <ReactFlow
                      nodes={graphNodes}
                      edges={graphEdges}
                      fitView
                      fitViewOptions={{
                        padding: 0.18,
                        maxZoom: 1.05,
                      }}
                      minZoom={0.2}
                      maxZoom={1.5}
                      nodesDraggable
                      nodesConnectable={false}
                      elementsSelectable
                    >

                      <Background
                        gap={24}
                        size={1}
                      />

                      <Controls />

                      <MiniMap
                        pannable
                        zoomable
                      />

                    </ReactFlow>
                  ) : (
                    <div className="status-box">
                      No network nodes available
                      for this case.
                    </div>
                  )}

                </div>

                <div className="graph-legend">

                  <span>
                    <i className="legend-dot identity" />
                    Identity
                  </span>

                  <span>
                    <i className="legend-dot account" />
                    Account
                  </span>

                  <span>
                    <i className="legend-dot phone" />
                    Phone
                  </span>

                  <span>
                    <i className="legend-dot device" />
                    Device
                  </span>

                  <span>
                    <i className="legend-dot transaction" />
                    Transaction
                  </span>

                  <span>
                    <i className="legend-dot call" />
                    Call
                  </span>

                </div>

              </div>

            </section>

            {/* =================================================
                HIERARCHY
            ================================================= */}

            <section className="panel hierarchy-panel">

              <div className="panel-header">

                <div>

                  <span className="eyebrow">
                    INVESTIGATION HIERARCHY
                  </span>

                  <h2>
                    Kingpin → Mule → Victim
                  </h2>

                </div>

              </div>

              <div className="hierarchy-grid">

                {(brief.hierarchy || []).map(
                  (person) => (

                    <div
                      className={`hierarchy-card ${
                        person.role ===
                        "kingpin"
                          ? "hierarchy-kingpin"
                          : person.role ===
                            "victim"
                          ? "hierarchy-victim"
                          : "hierarchy-mule"
                      }`}
                      key={
                        person.identity_id
                      }
                    >

                      <span className="role">

                        {person.role}

                        {person.mule_level
                          ? ` · Level ${person.mule_level}`
                          : ""}

                      </span>

                      <strong>
                        {person.name}
                      </strong>

                      <span>
                        {person.identity_id}
                      </span>

                      <span>
                        {person.account_id}
                      </span>

                      <span>
                        {person.phone}
                      </span>

                    </div>

                  )
                )}

              </div>

            </section>

            {/* =================================================
                RECOMMENDED ACTIONS
            ================================================= */}

            {(brief.recommended_actions || [])
              .length > 0 && (
              <section className="panel actions-panel">

                <div className="panel-header">
                  <div>
                    <span className="eyebrow">
                      INVESTIGATIVE ACTIONS
                    </span>
                    <h2>
                      Recommended Next Steps
                    </h2>
                  </div>
                  <div className="network-summary">
                    {
                      (brief.recommended_actions || [])
                        .length
                    }{" "}
                    actions
                  </div>
                </div>

                <p className="panel-help">
                  Ordered by evidence signal weight.
                  Actions are procedural recommendations
                  only — they do not establish guilt or
                  fraud.
                </p>

                <ol className="actions-list">
                  {(brief.recommended_actions || []).map(
                    (action, index) => (
                      <li
                        key={index}
                        className="action-item"
                      >
                        <span className="action-number">
                          {String(index + 1).padStart(
                            2,
                            "0"
                          )}
                        </span>
                        <span className="action-text">
                          {action}
                        </span>
                      </li>
                    )
                  )}
                </ol>

              </section>
            )}

            {/* =================================================
                FIR BRIEF
            ================================================= */}

            {firBrief && (
              <section className="panel fir-panel" id="fir-print-section">

                {/* --- Header --- */}
                <div className="fir-header">

                  <div className="fir-header-left">

                    <span className="eyebrow">
                      FIR-READY CASE BRIEF
                    </span>

                    <h2>
                      {firBrief.case_id} —{" "}
                      {firBrief.fir_meta?.jurisdiction_city},{" "}
                      {firBrief.fir_meta?.jurisdiction_state}
                    </h2>

                    <div className="fir-meta-row">

                      {firBrief.fir_meta?.complaint_id && (
                        <span className="fir-meta-chip">
                          Complaint: {firBrief.fir_meta.complaint_id}
                        </span>
                      )}

                      {firBrief.fir_meta?.complaint_date && (
                        <span className="fir-meta-chip">
                          Date: {firBrief.fir_meta.complaint_date}
                        </span>
                      )}

                      <span className="fir-meta-chip">
                        Status: {firBrief.fir_meta?.case_status || "Unknown"}
                      </span>

                      <span className={`fir-priority-chip priority-${(firBrief.fir_meta?.priority || "low").toLowerCase()}`}>
                        {firBrief.fir_meta?.priority} · {firBrief.fir_meta?.investigation_score}/100
                      </span>

                    </div>

                  </div>

                  <button
                    className="fir-print-btn"
                    onClick={() => window.print()}
                  >
                    Print Brief
                  </button>

                </div>

                {/* --- Narrative --- */}
                <div className="fir-section">
                  <div className="fir-section-title">
                    Case Narrative
                    {firBrief.narrative_source === "watsonx" ? (
                      <span className="narrative-source-badge source-watsonx">
                        IBM watsonx.ai · Granite
                      </span>
                    ) : (
                      <span className="narrative-source-badge source-template">
                        Template
                      </span>
                    )}
                  </div>
                  <p className="fir-narrative">
                    {firBrief.narrative}
                  </p>
                </div>

                {/* --- Victim --- */}
                {firBrief.victim && (
                  <div className="fir-section">
                    <div className="fir-section-title">
                      Complainant / Victim
                    </div>
                    <div className="fir-person-row fir-victim-row">
                      <span className="fir-role-badge fir-role-victim">
                        VICTIM
                      </span>
                      <span className="fir-person-name">
                        {firBrief.victim.name}
                      </span>
                      <span className="fir-person-meta">
                        {firBrief.victim.identity_id}
                      </span>
                      <span className="fir-person-meta">
                        {firBrief.victim.phone}
                      </span>
                      <span className="fir-person-meta">
                        {firBrief.victim.city}, {firBrief.victim.state}
                      </span>
                    </div>
                  </div>
                )}

                {/* --- Accused --- */}
                {firBrief.accused?.length > 0 && (
                  <div className="fir-section">
                    <div className="fir-section-title">
                      Accused Persons
                    </div>
                    <table className="fir-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Name</th>
                          <th>Role</th>
                          <th>Mule Level</th>
                          <th>Identity ID</th>
                          <th>Phone</th>
                          <th>Location</th>
                        </tr>
                      </thead>
                      <tbody>
                        {firBrief.accused.map(
                          (person, i) => (
                            <tr key={person.identity_id}>
                              <td>{i + 1}</td>
                              <td className="fir-name-cell">
                                {person.name}
                              </td>
                              <td>
                                <span className={`fir-role-badge fir-role-${person.role}`}>
                                  {person.role?.toUpperCase()}
                                </span>
                              </td>
                              <td>
                                {person.mule_level
                                  ? `Level ${person.mule_level}`
                                  : "—"}
                              </td>
                              <td className="fir-mono">
                                {person.identity_id}
                              </td>
                              <td className="fir-mono">
                                {person.phone}
                              </td>
                              <td>
                                {person.city}, {person.state}
                              </td>
                            </tr>
                          )
                        )}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* --- Transaction Exhibit --- */}
                {firBrief.transaction_exhibit?.length > 0 && (
                  <div className="fir-section">
                    <div className="fir-section-title">
                      Transaction Exhibit
                    </div>
                    <table className="fir-table">
                      <thead>
                        <tr>
                          <th>Ex.</th>
                          <th>Transaction ID</th>
                          <th>Sender Account</th>
                          <th>Receiver Account</th>
                          <th>Amount</th>
                          <th>Channel</th>
                          <th>Status</th>
                          <th>New Beneficiary</th>
                        </tr>
                      </thead>
                      <tbody>
                        {firBrief.transaction_exhibit.map(
                          (tx) => (
                            <tr key={tx.transaction_id}>
                              <td>{tx.exhibit_no}</td>
                              <td className="fir-mono">
                                {tx.transaction_id}
                              </td>
                              <td className="fir-mono">
                                {tx.sender_account}
                              </td>
                              <td className="fir-mono">
                                {tx.receiver_account}
                              </td>
                              <td className="fir-amount">
                                {tx.amount}
                              </td>
                              <td>{tx.channel}</td>
                              <td>{tx.status}</td>
                              <td>
                                {tx.new_beneficiary
                                  ? <span className="fir-flag">YES</span>
                                  : "No"}
                              </td>
                            </tr>
                          )
                        )}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* --- Legal Sections --- */}
                {firBrief.legal_sections?.length > 0 && (
                  <div className="fir-section">
                    <div className="fir-section-title">
                      Applicable Legal Provisions
                    </div>
                    <table className="fir-table">
                      <thead>
                        <tr>
                          <th>Act</th>
                          <th>Section</th>
                          <th>Description</th>
                        </tr>
                      </thead>
                      <tbody>
                        {firBrief.legal_sections.map(
                          (sec, i) => (
                            <tr key={i}>
                              <td className="fir-act">
                                {sec.act}
                              </td>
                              <td className="fir-mono fir-section-ref">
                                {sec.section}
                              </td>
                              <td className="fir-law-desc">
                                {sec.description}
                              </td>
                            </tr>
                          )
                        )}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* --- Disclaimer --- */}
                <div className="fir-disclaimer">
                  <strong>Important: </strong>
                  {firBrief.disclaimer}
                </div>

              </section>
            )}

            {/* Fallback: show compact brief if FIR data not yet loaded */}
            {!firBrief && brief && (
              <section className="panel brief-panel">
                <div className="panel-header">
                  <div>
                    <span className="eyebrow">CASE BRIEF</span>
                    <h2>Investigation Summary</h2>
                  </div>
                </div>
                <div className="brief-content">
                  <div><span>Priority</span><strong>{brief.priority}</strong></div>
                  <div><span>Score</span><strong>{brief.investigation_score}/100</strong></div>
                  <div><span>Evidence</span><strong>{brief.evidence_count}</strong></div>
                  <div><span>Network</span><strong>{brief.network?.node_count || 0} nodes / {brief.network?.edge_count || 0} edges</strong></div>
                </div>
              </section>
            )}

            {/* =================================================
                DISCLAIMER
            ================================================= */}

            <div className="disclaimer">

              <strong>
                Investigation note:
              </strong>{" "}

              {brief.disclaimer ||
                "This output contains synthetic investigative signals derived from mock case records. It does not establish fraud, guilt, or criminal responsibility."}

            </div>

          </>
        )}

      </main>

    </div>
  );
}

export default App;