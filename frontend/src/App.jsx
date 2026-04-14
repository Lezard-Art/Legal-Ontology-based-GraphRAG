import React, { useState, useEffect, useRef, useCallback } from 'react'
import cytoscape from 'cytoscape'

const API = '/api'

// ─── Color palette ───
const COLORS = {
  Party: '#3b82f6',
  Role: '#14b8a6',
  Asset: '#eab308',
  Obligation: '#ef4444',
  Power: '#a855f7',
  Clause: '#6b7280',
  Contract: '#1e293b',
}

const TAG_COLORS = {
  obligation: '#fecaca', power: '#e9d5ff', definition: '#dbeafe',
  party_identification: '#bfdbfe', asset_description: '#fef08a',
  condition: '#fde68a', temporal_provision: '#d1fae5', termination: '#fca5a5',
  governing_law: '#c7d2fe', preamble: '#e2e8f0', confidentiality: '#ddd6fe',
  consideration: '#fed7aa', prohibition: '#fca5a5', permission: '#bbf7d0',
  right: '#bbf7d0', boilerplate: '#f1f5f9', other: '#f1f5f9',
  dispute_resolution: '#c7d2fe', indemnification: '#fecdd3',
  limitation_of_liability: '#fecdd3', force_majeure: '#fde68a',
  assignment: '#e2e8f0', amendment: '#e2e8f0', notice: '#e2e8f0',
  severability: '#f1f5f9', entire_agreement: '#f1f5f9', signature: '#f1f5f9',
}

// ─── Styles ───
const styles = {
  app: { fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', color: '#1e293b', minHeight: '100vh', background: '#f8fafc' },
  header: { background: '#1e293b', color: 'white', padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  headerTitle: { fontSize: '18px', fontWeight: 600, margin: 0 },
  nav: { display: 'flex', gap: '8px' },
  navBtn: (active) => ({ background: active ? '#3b82f6' : 'transparent', color: 'white', border: '1px solid #475569', borderRadius: '6px', padding: '6px 14px', cursor: 'pointer', fontSize: '13px' }),
  tabBtn: (active) => ({ background: active ? '#3b82f6' : '#e2e8f0', color: active ? 'white' : '#1e293b', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '6px 14px', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }),
  main: { maxWidth: '1400px', margin: '0 auto', padding: '24px' },
  card: { background: 'white', borderRadius: '8px', border: '1px solid #e2e8f0', padding: '20px', marginBottom: '16px' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '14px' },
  th: { textAlign: 'left', padding: '10px 12px', borderBottom: '2px solid #e2e8f0', color: '#64748b', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' },
  td: { padding: '10px 12px', borderBottom: '1px solid #f1f5f9' },
  btn: { background: '#3b82f6', color: 'white', border: 'none', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer', fontSize: '13px', fontWeight: 500 },
  btnDanger: { background: '#ef4444', color: 'white', border: 'none', borderRadius: '6px', padding: '6px 12px', cursor: 'pointer', fontSize: '12px' },
  btnSecondary: { background: '#e2e8f0', color: '#1e293b', border: 'none', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer', fontSize: '13px' },
  input: { width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '14px', boxSizing: 'border-box' },
  textarea: { width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', fontFamily: 'inherit', minHeight: '300px', boxSizing: 'border-box', resize: 'vertical' },
  label: { display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '4px' },
  badge: (color) => ({ display: 'inline-block', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 500, background: color || '#e2e8f0' }),
  splitPane: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', alignItems: 'stretch', height: '520px' },
  graphContainer: { width: '100%', minWidth: 0, height: '100%', border: '1px solid #e2e8f0', borderRadius: '8px', background: '#fafbfc', overflow: 'hidden' },
  tagSpan: (tag) => ({ background: TAG_COLORS[tag] || '#f1f5f9', padding: '2px 4px', borderRadius: '3px', cursor: 'pointer' }),
  legend: { display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px', fontSize: '12px' },
  legendItem: (color) => ({ display: 'flex', alignItems: 'center', gap: '4px' }),
  legendDot: (color) => ({ width: '10px', height: '10px', borderRadius: '50%', background: color }),
}


// ═══════════════════════════════════════════════════════════════
// CONTRACT LIST VIEW
// ═══════════════════════════════════════════════════════════════

function ContractList({ onSelect, onRefresh, contracts }) {
  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!confirm('Delete this contract?')) return
    await fetch(`${API}/contracts/${id}`, { method: 'DELETE' })
    onRefresh()
  }

  return (
    <div>
      <h2 style={{ fontSize: '16px', marginBottom: '16px' }}>Contracts ({contracts.length})</h2>
      {contracts.length === 0 ? (
        <div style={styles.card}>
          <p style={{ color: '#64748b', textAlign: 'center', margin: '40px 0' }}>
            No contracts yet. Use the "Parse" tab to add one, or the seeder script.
          </p>
        </div>
      ) : (
        <div style={styles.card}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Name</th>
                <th style={styles.th}>Governing Law</th>
                <th style={styles.th}>Jurisdiction</th>
                <th style={styles.th}>Effective</th>
                <th style={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {contracts.map(c => (
                <tr key={c.id} onClick={() => onSelect(c.id)} style={{ cursor: 'pointer' }}>
                  <td style={styles.td}><strong>{c.name}</strong></td>
                  <td style={styles.td}>{c.governing_law || '—'}</td>
                  <td style={styles.td}>{c.jurisdiction || '—'}</td>
                  <td style={styles.td}>{c.effective_date || '—'}</td>
                  <td style={styles.td}>
                    <button style={styles.btnDanger} onClick={(e) => handleDelete(c.id, e)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════
// GRAPH COMPONENT (Cytoscape)
// ═══════════════════════════════════════════════════════════════

function ContractGraph({ graphData, onNodeClick }) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !graphData) return

    const elements = [
      ...graphData.nodes.map(n => ({
        data: { id: n.id, label: n.label, nodeType: n.type, ...n.data },
      })),
      ...graphData.edges.map((e, i) => ({
        data: { id: `e${i}`, source: e.source, target: e.target, label: e.label, edgeType: e.type },
      })),
    ]

    if (cyRef.current) cyRef.current.destroy()

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        { selector: 'node', style: {
          'label': 'data(label)', 'text-wrap': 'wrap', 'text-max-width': '120px',
          'font-size': '11px', 'text-valign': 'center', 'text-halign': 'center',
          'width': '60px', 'height': '60px', 'border-width': 2, 'border-color': '#94a3b8',
        }},
        { selector: 'node[nodeType="Party"]', style: {
          'background-color': COLORS.Party, 'color': '#fff', 'shape': 'rectangle',
          'width': '80px', 'height': '40px',
        }},
        { selector: 'node[nodeType="Role"]', style: {
          'background-color': COLORS.Role, 'color': '#fff', 'shape': 'round-rectangle',
          'width': '80px', 'height': '36px',
        }},
        { selector: 'node[nodeType="Asset"]', style: {
          'background-color': COLORS.Asset, 'shape': 'diamond',
        }},
        { selector: 'node[nodeType="Obligation"]', style: {
          'background-color': COLORS.Obligation, 'color': '#fff', 'shape': 'round-rectangle',
          'width': '100px', 'height': '36px',
        }},
        { selector: 'node[nodeType="Power"]', style: {
          'background-color': COLORS.Power, 'color': '#fff', 'shape': 'round-rectangle',
          'width': '100px', 'height': '36px',
        }},
        { selector: 'node[nodeType="Clause"]', style: {
          'background-color': COLORS.Clause, 'color': '#fff', 'shape': 'rectangle',
          'width': '70px', 'height': '30px', 'font-size': '9px',
        }},
        { selector: 'node[nodeType="Contract"]', style: {
          'background-color': COLORS.Contract, 'color': '#fff', 'shape': 'rectangle',
          'width': '100px', 'height': '44px', 'font-size': '12px', 'font-weight': 'bold',
        }},
        { selector: 'edge', style: {
          'label': 'data(label)', 'font-size': '9px', 'color': '#64748b',
          'width': 1.5, 'line-color': '#94a3b8', 'target-arrow-color': '#94a3b8',
          'target-arrow-shape': 'triangle', 'curve-style': 'bezier',
          'text-background-color': '#fff', 'text-background-opacity': 0.8,
          'text-background-padding': '2px',
        }},
        { selector: 'edge[edgeType="owes"]', style: {
          'line-color': COLORS.Obligation, 'target-arrow-color': COLORS.Obligation, 'width': 2.5,
        }},
        { selector: 'edge[edgeType="empowers"]', style: {
          'line-color': COLORS.Power, 'target-arrow-color': COLORS.Power, 'width': 2,
          'line-style': 'dashed',
        }},
        { selector: 'edge[edgeType="sourcedFrom"]', style: {
          'line-color': '#d1d5db', 'target-arrow-color': '#d1d5db', 'width': 1,
          'line-style': 'dotted',
        }},
      ],
      layout: { name: 'cose', animate: false, nodeDimensionsIncludeLabels: true, idealEdgeLength: 120, nodeRepulsion: 8000 },
    })

    cyRef.current.on('tap', 'node', (evt) => {
      if (onNodeClick) onNodeClick(evt.target.data())
    })

    return () => { if (cyRef.current) cyRef.current.destroy() }
  }, [graphData])

  return <div ref={containerRef} style={styles.graphContainer} />
}


// ═══════════════════════════════════════════════════════════════
// CONTRACT DETAIL VIEW
// ═══════════════════════════════════════════════════════════════

function ContractDetail({ contractId, onBack }) {
  const [contract, setContract] = useState(null)
  const [graphData, setGraphData] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [validation, setValidation] = useState(null)
  const [activeTab, setActiveTab] = useState('graph')

  useEffect(() => {
    fetch(`${API}/contracts/${contractId}`).then(r => r.json()).then(setContract)
    fetch(`${API}/contracts/${contractId}/graph`).then(r => r.json()).then(setGraphData)
  }, [contractId])

  const handleValidate = async () => {
    const res = await fetch(`${API}/contracts/${contractId}/validate`)
    setValidation(await res.json())
  }

  if (!contract) return <p>Loading...</p>

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <button style={styles.btnSecondary} onClick={onBack}>&larr; Back</button>
        <h2 style={{ fontSize: '16px', margin: 0 }}>{contract.name}</h2>
        <button style={styles.btn} onClick={handleValidate}>Validate</button>
      </div>

      {validation && (
        <div style={{ ...styles.card, borderLeft: `4px solid ${validation.valid ? '#22c55e' : '#ef4444'}` }}>
          <strong>{validation.valid ? 'Valid' : 'Invalid'}</strong>
          {validation.errors.map((e, i) => <p key={i} style={{ color: '#ef4444', margin: '4px 0', fontSize: '13px' }}>{e}</p>)}
          {validation.warnings.map((w, i) => <p key={i} style={{ color: '#eab308', margin: '4px 0', fontSize: '13px' }}>{w}</p>)}
        </div>
      )}

      {/* Metadata */}
      <div style={styles.card}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', fontSize: '13px' }}>
          <div><span style={{ color: '#64748b' }}>Governing Law:</span><br/>{contract.governing_law || '—'}</div>
          <div><span style={{ color: '#64748b' }}>Jurisdiction:</span><br/>{contract.jurisdiction || '—'}</div>
          <div><span style={{ color: '#64748b' }}>Effective:</span><br/>{contract.effective_date || '—'}</div>
          <div><span style={{ color: '#64748b' }}>Expires:</span><br/>{contract.expiration_date || '—'}</div>
        </div>
        <div style={{ display: 'flex', gap: '8px', marginTop: '12px', fontSize: '13px' }}>
          <span style={styles.badge(COLORS.Party + '33')}>{contract.parties?.length || 0} parties</span>
          <span style={styles.badge(COLORS.Role + '33')}>{contract.roles?.length || 0} roles</span>
          <span style={styles.badge(COLORS.Obligation + '33')}>{contract.obligations?.length || 0} obligations</span>
          <span style={styles.badge(COLORS.Power + '33')}>{contract.powers?.length || 0} powers</span>
          <span style={styles.badge(COLORS.Clause + '33')}>{contract.clauses?.length || 0} clauses</span>
        </div>
      </div>

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
        {['graph', 'text', 'obligations', 'json'].map(tab => (
          <button key={tab} style={styles.tabBtn(activeTab === tab)}
            onClick={() => setActiveTab(tab)}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Graph Tab */}
      {activeTab === 'graph' && (
        <div>
          <div style={styles.legend}>
            {Object.entries(COLORS).map(([type, color]) => (
              <span key={type} style={styles.legendItem(color)}>
                <span style={styles.legendDot(color)} /> {type}
              </span>
            ))}
          </div>
          <div style={styles.splitPane}>
            <ContractGraph graphData={graphData} onNodeClick={setSelectedNode} />
            <div style={{ ...styles.card, overflow: 'auto', minWidth: 0, height: '100%', boxSizing: 'border-box' }}>
              <h3 style={{ fontSize: '14px', marginTop: 0 }}>
                {selectedNode ? `${selectedNode.nodeType}: ${selectedNode.label}` : 'Click a node'}
              </h3>
              {selectedNode && (
                <pre style={{ fontSize: '11px', background: '#f8fafc', padding: '10px', borderRadius: '6px', overflow: 'auto', maxHeight: '400px', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {JSON.stringify(selectedNode, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Annotated Text Tab */}
      {activeTab === 'text' && (
        <div style={styles.card}>
          <h3 style={{ fontSize: '14px', marginTop: 0 }}>Annotated Contract Text</h3>
          {contract.clauses?.length > 0 ? (
            <div style={{ fontSize: '13px', lineHeight: '1.8' }}>
              {contract.clauses.map(cl => (
                <div key={cl.id} style={{ marginBottom: '12px', padding: '8px', borderRadius: '6px',
                  background: TAG_COLORS[cl.ontology_tag] || '#f8fafc', borderLeft: '3px solid #94a3b8' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>
                    <strong>§{cl.section_number || '?'}</strong> {cl.heading && `— ${cl.heading}`}
                    <span style={{ ...styles.badge(TAG_COLORS[cl.ontology_tag]), marginLeft: '8px' }}>
                      {cl.ontology_tag || 'untagged'}
                    </span>
                  </div>
                  <div>{cl.text}</div>
                </div>
              ))}
            </div>
          ) : (
            <div>
              <p style={{ color: '#64748b' }}>No clauses extracted. Showing raw source text:</p>
              <pre style={{ fontSize: '12px', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
                {contract.source_text || 'No source text available.'}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Obligations Tab */}
      {activeTab === 'obligations' && (
        <div>
          <div style={styles.card}>
            <h3 style={{ fontSize: '14px', marginTop: 0 }}>Obligations</h3>
            {contract.obligations?.map(obl => {
              const debtor = contract.roles?.find(r => r.id === obl.debtor_role_id)
              const creditor = contract.roles?.find(r => r.id === obl.creditor_role_id)
              return (
                <div key={obl.id} style={{ padding: '10px', borderBottom: '1px solid #f1f5f9' }}>
                  <div style={{ fontSize: '13px' }}>
                    <span style={styles.badge(COLORS.Role + '33')}>{debtor?.label || '?'}</span>
                    <span style={{ margin: '0 6px', color: '#ef4444' }}>&rarr;</span>
                    <span style={styles.badge(COLORS.Role + '33')}>{creditor?.label || '?'}</span>
                  </div>
                  <p style={{ margin: '4px 0 0', fontSize: '13px' }}>{obl.description}</p>
                  {obl.temporal_constraint && (
                    <p style={{ margin: '2px 0 0', fontSize: '12px', color: '#64748b' }}>
                      Temporal: {obl.temporal_constraint.description || JSON.stringify(obl.temporal_constraint)}
                    </p>
                  )}
                  {obl.surviving && <span style={styles.badge('#fef08a')}>Surviving</span>}
                </div>
              )
            })}
          </div>

          <div style={styles.card}>
            <h3 style={{ fontSize: '14px', marginTop: 0 }}>Powers</h3>
            {contract.powers?.map(pwr => {
              const creditor = contract.roles?.find(r => r.id === pwr.creditor_role_id)
              const debtor = contract.roles?.find(r => r.id === pwr.debtor_role_id)
              return (
                <div key={pwr.id} style={{ padding: '10px', borderBottom: '1px solid #f1f5f9' }}>
                  <div style={{ fontSize: '13px' }}>
                    <span style={styles.badge(COLORS.Power + '33')}>{creditor?.label || '?'}</span>
                    <span style={{ margin: '0 6px', color: '#a855f7' }}>⚡ over</span>
                    <span style={styles.badge(COLORS.Role + '33')}>{debtor?.label || '?'}</span>
                  </div>
                  <p style={{ margin: '4px 0 0', fontSize: '13px' }}>{pwr.description}</p>
                </div>
              )
            })}
            {(!contract.powers || contract.powers.length === 0) && (
              <p style={{ color: '#64748b', fontSize: '13px' }}>No powers extracted.</p>
            )}
          </div>
        </div>
      )}

      {/* Raw JSON Tab */}
      {activeTab === 'json' && (
        <div style={styles.card}>
          <h3 style={{ fontSize: '14px', marginTop: 0 }}>JSON-LD (raw data)</h3>
          <pre style={{ fontSize: '11px', background: '#f8fafc', padding: '12px', borderRadius: '6px',
            overflow: 'auto', maxHeight: '600px' }}>
            {JSON.stringify(contract, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════
// PARSE VIEW
// ═══════════════════════════════════════════════════════════════

function ParseView({ onSaved }) {
  const [text, setText] = useState('')
  const [name, setName] = useState('')
  const [file, setFile] = useState(null)
  const [mode, setMode] = useState('file') // 'file' | 'text'
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef(null)

  const hasInput = mode === 'file' ? !!file : !!text

  const handleFile = (f) => {
    if (!f) return
    const ext = f.name.split('.').pop().toLowerCase()
    if (!['pdf', 'docx'].includes(ext)) {
      setError('Only .pdf and .docx files are supported.')
      return
    }
    if (f.size > 10 * 1024 * 1024) {
      setError('File exceeds 10 MB limit.')
      return
    }
    setFile(f)
    setError(null)
    if (!name) setName(f.name.replace(/\.(pdf|docx)$/i, ''))
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) handleFile(f)
  }

  const buildFormData = () => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('contract_name', name || file.name || 'Untitled')
    return fd
  }

  const handleParse = async () => {
    setLoading(true)
    setError(null)
    setPreview(null)
    try {
      let res
      if (mode === 'file' && file) {
        res = await fetch(`${API}/parse-file`, { method: 'POST', body: buildFormData() })
      } else {
        res = await fetch(`${API}/parse`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, contract_name: name || 'Untitled' }),
        })
      }
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || 'Parse failed')
      } else if (data.error) {
        setError(data.error)
      } else {
        setPreview(data)
      }
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  const handleSave = async () => {
    setLoading(true)
    setError(null)
    try {
      let res
      if (mode === 'file' && file) {
        res = await fetch(`${API}/parse-file-and-save`, { method: 'POST', body: buildFormData() })
      } else {
        res = await fetch(`${API}/parse-and-save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, contract_name: name || 'Untitled' }),
        })
      }
      if (!res.ok) {
        const err = await res.json()
        setError(err.detail || 'Save failed')
      } else {
        onSaved()
      }
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  return (
    <div>
      <h2 style={{ fontSize: '16px', marginBottom: '16px' }}>Parse Contract with LLM</h2>

      <div style={styles.card}>
        <div style={{ marginBottom: '12px' }}>
          <label style={styles.label}>Contract Name</label>
          <input style={styles.input} value={name} onChange={e => setName(e.target.value)}
            placeholder="e.g. Meat Sale Agreement — AgriCorp / FreshMart" />
        </div>

        {/* Mode switcher */}
        <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
          <button style={styles.tabBtn(mode === 'file')} onClick={() => setMode('file')}>
            Upload File
          </button>
          <button style={styles.tabBtn(mode === 'text')} onClick={() => setMode('text')}>
            Paste Text
          </button>
        </div>

        {mode === 'file' ? (
          <div style={{ marginBottom: '12px' }}>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: `2px dashed ${dragging ? '#3b82f6' : '#d1d5db'}`,
                borderRadius: '8px',
                padding: '32px 16px',
                textAlign: 'center',
                cursor: 'pointer',
                background: dragging ? '#eff6ff' : '#fafbfc',
                transition: 'all 0.15s',
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx"
                style={{ display: 'none' }}
                onChange={(e) => handleFile(e.target.files?.[0])}
              />
              {file ? (
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 500, color: '#1e293b' }}>{file.name}</div>
                  <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                    {(file.size / 1024).toFixed(0)} KB
                    <span style={{ marginLeft: '8px', color: '#3b82f6', cursor: 'pointer' }}
                      onClick={(e) => { e.stopPropagation(); setFile(null) }}>
                      Remove
                    </span>
                  </div>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: '14px', color: '#64748b' }}>
                    Drop a <strong>.pdf</strong> or <strong>.docx</strong> file here, or click to browse
                  </div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>Max 10 MB</div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div style={{ marginBottom: '12px' }}>
            <label style={styles.label}>Paste contract text</label>
            <textarea style={styles.textarea} value={text} onChange={e => setText(e.target.value)}
              placeholder="Paste the full contract text here..." />
          </div>
        )}

        <div style={{ display: 'flex', gap: '8px' }}>
          <button style={styles.btn} onClick={handleParse} disabled={loading || !hasInput}>
            {loading ? 'Parsing...' : 'Preview Parse'}
          </button>
          <button style={{ ...styles.btn, background: '#22c55e' }} onClick={handleSave}
            disabled={loading || !hasInput}>
            {loading ? 'Saving...' : 'Parse & Save'}
          </button>
        </div>
        {error && <p style={{ color: '#ef4444', marginTop: '8px', fontSize: '13px' }}>{error}</p>}
      </div>

      {preview && (
        <div style={styles.card}>
          <h3 style={{ fontSize: '14px', marginTop: 0 }}>Parse Preview</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <h4 style={{ fontSize: '13px', color: '#64748b' }}>Parties & Roles</h4>
              {preview.parties?.map((p, i) => (
                <div key={i} style={{ fontSize: '13px', marginBottom: '4px' }}>
                  <span style={styles.badge(COLORS.Party + '33')}>{p.name}</span> ({p.type})
                </div>
              ))}
              {preview.roles?.map((r, i) => (
                <div key={i} style={{ fontSize: '13px', marginBottom: '4px' }}>
                  <span style={styles.badge(COLORS.Role + '33')}>{r.label}</span>
                  {r.party_name && ` — ${r.party_name}`}
                </div>
              ))}
            </div>
            <div>
              <h4 style={{ fontSize: '13px', color: '#64748b' }}>Obligations ({preview.obligations?.length || 0})</h4>
              {preview.obligations?.map((o, i) => (
                <div key={i} style={{ fontSize: '12px', marginBottom: '6px', padding: '6px',
                  background: '#fef2f2', borderRadius: '4px' }}>
                  <strong>{o.debtor_role}</strong> &rarr; <strong>{o.creditor_role}</strong><br/>
                  {o.description}
                </div>
              ))}
            </div>
          </div>
          <div style={{ marginTop: '12px' }}>
            <h4 style={{ fontSize: '13px', color: '#64748b' }}>Clauses ({preview.clauses?.length || 0})</h4>
            {preview.clauses?.map((c, i) => (
              <div key={i} style={{ fontSize: '12px', marginBottom: '4px' }}>
                <span style={styles.badge(TAG_COLORS[c.ontology_tag])}>{c.ontology_tag}</span>
                {' '}{c.text?.substring(0, 100)}...
              </div>
            ))}
          </div>
          <details style={{ marginTop: '12px' }}>
            <summary style={{ cursor: 'pointer', fontSize: '13px', color: '#64748b' }}>Raw JSON</summary>
            <pre style={{ fontSize: '11px', background: '#f8fafc', padding: '10px', borderRadius: '6px',
              overflow: 'auto', maxHeight: '300px' }}>
              {JSON.stringify(preview, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════

export default function App() {
  const [view, setView] = useState('list')  // list | detail | parse
  const [contracts, setContracts] = useState([])
  const [selectedId, setSelectedId] = useState(null)

  const loadContracts = useCallback(() => {
    fetch(`${API}/contracts`).then(r => r.json()).then(setContracts).catch(() => {})
  }, [])

  useEffect(() => { loadContracts() }, [loadContracts])

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.headerTitle}>Contract Ontology Database</h1>
        <nav style={styles.nav}>
          <button style={styles.navBtn(view === 'list')} onClick={() => { setView('list'); loadContracts() }}>
            Contracts
          </button>
          <button style={styles.navBtn(view === 'parse')} onClick={() => setView('parse')}>
            Parse
          </button>
        </nav>
      </header>
      <main style={styles.main}>
        {view === 'list' && (
          <ContractList
            contracts={contracts}
            onSelect={(id) => { setSelectedId(id); setView('detail') }}
            onRefresh={loadContracts}
          />
        )}
        {view === 'detail' && selectedId && (
          <ContractDetail
            contractId={selectedId}
            onBack={() => { setView('list'); loadContracts() }}
          />
        )}
        {view === 'parse' && (
          <ParseView onSaved={() => { setView('list'); loadContracts() }} />
        )}
      </main>
    </div>
  )
}
