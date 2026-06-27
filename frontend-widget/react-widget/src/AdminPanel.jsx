import React, { useState, useEffect } from 'react';

function AdminPanel() {
  const [leads, setLeads] = useState([]);
  const [analytics, setAnalytics] = useState({
    total_sessions: 0,
    total_leads: 0,
    conversion_rate: 0,
    temperature_distribution: {},
    status_distribution: {},
    program_interests: {}
  });
  const [knowledge, setKnowledge] = useState([]);
  const [fallbacks, setFallbacks] = useState([]);
  const [activeTab, setActiveTab] = useState('leads');

  // Input states
  const [urlInput, setUrlInput] = useState('');
  const [urlCategory, setUrlCategory] = useState('general');
  const [fileInput, setFileInput] = useState(null);
  const [fileCategory, setFileCategory] = useState('general');
  const [resolveAnswers, setResolveAnswers] = useState({});

  // Status messages
  const [statusMsg, setStatusMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const showMsg = (msg) => {
    setStatusMsg(msg);
    setTimeout(() => setStatusMsg(''), 4000);
  };

  const showError = (msg) => {
    setErrorMsg(msg);
    setTimeout(() => setErrorMsg(''), 4000);
  };

  // Fetch Data
  const fetchData = async () => {
    try {
      // 1. Leads
      const leadsRes = await fetch('http://localhost:8000/api/leads/admin');
      if (leadsRes.ok) {
        const lData = await leadsRes.json();
        setLeads(lData);
      }

      // 2. Analytics
      const analyticsRes = await fetch('http://localhost:8000/api/admin/analytics/leads');
      if (analyticsRes.ok) setAnalytics(await analyticsRes.json());

      // 3. Knowledge Base
      const kbRes = await fetch('http://localhost:8000/api/admin/knowledge');
      if (kbRes.ok) setKnowledge(await kbRes.json());

      // 4. Fallbacks
      const fbRes = await fetch('http://localhost:8000/api/admin/analytics/unanswered-questions');
      if (fbRes.ok) setFallbacks(await fbRes.json());

    } catch (error) {
      console.error("Error loading admin data:", error);
      showError("Failed to connect to the backend server. Make sure it is running at http://localhost:8000");
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Update Lead Status
  const handleUpdateStatus = async (leadId, newStatus) => {
    try {
      const res = await fetch(`http://localhost:8000/api/leads/admin/${leadId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        showMsg("Lead status updated successfully.");
        fetchData();
      }
    } catch (e) {
      showError("Failed to update status.");
    }
  };

  // Crawl URL
  const handleAddUrl = async (e) => {
    e.preventDefault();
    if (!urlInput.trim()) return;
    showMsg("Crawling website URL... Please wait.");
    try {
      const res = await fetch('http://localhost:8000/api/admin/knowledge/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlInput, category: urlCategory })
      });
      if (res.ok) {
        setUrlInput('');
        showMsg("URL crawled and indexed successfully.");
        fetchData();
      } else {
        const err = await res.json();
        showError(err.detail || "Failed to crawl URL.");
      }
    } catch (e) {
      showError("Network error.");
    }
  };

  // Upload File
  const handleUploadFile = async (e) => {
    e.preventDefault();
    if (!fileInput) return;
    showMsg("Uploading and indexing document...");
    const formData = new FormData();
    formData.append("file", fileInput);
    formData.append("category", fileCategory);

    try {
      const res = await fetch('http://localhost:8000/api/admin/knowledge/upload', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        setFileInput(null);
        showMsg("Document uploaded and indexed successfully.");
        fetchData();
      } else {
        const err = await res.json();
        showError(err.detail || "Failed to upload file.");
      }
    } catch (e) {
      showError("Upload failed.");
    }
  };

  // Delete Document
  const handleDeleteDoc = async (id) => {
    if (!confirm("Are you sure you want to delete this document from the knowledge base?")) return;
    try {
      const res = await fetch(`http://localhost:8000/api/admin/knowledge/${id}`, { method: 'DELETE' });
      if (res.ok) {
        showMsg("Document deleted.");
        fetchData();
      }
    } catch (e) {
      showError("Delete failed.");
    }
  };

  // Reindex Store
  const handleReindex = async () => {
    showMsg("Re-indexing vector store... This may take a minute.");
    try {
      const res = await fetch('http://localhost:8000/api/admin/knowledge/reindex', { method: 'POST' });
      if (res.ok) {
        showMsg("Re-indexing complete.");
      }
    } catch (e) {
      showError("Reindexing failed.");
    }
  };

  // Resolve Fallback
  const handleResolveFallback = async (id) => {
    const answer = resolveAnswers[id];
    if (!answer || !answer.trim()) return;

    try {
      const res = await fetch(`http://localhost:8000/api/admin/analytics/unanswered-questions/${id}/resolve`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ admin_answer: answer })
      });
      if (res.ok) {
        setResolveAnswers(prev => ({ ...prev, [id]: '' }));
        showMsg("Answer saved and added to RAG knowledge index.");
        fetchData();
      }
    } catch (e) {
      showError("Resolution failed.");
    }
  };

  return (
    <div className="carepilot-admin-view">
      <div className="carepilot-admin-header">
        <h2>CarePilot AI - Team Dashboard</h2>
        <div className="carepilot-admin-nav">
          <button className={activeTab === 'leads' ? 'active' : ''} onClick={() => setActiveTab('leads')}>Leads Management</button>
          <button className={activeTab === 'knowledge' ? 'active' : ''} onClick={() => setActiveTab('knowledge')}>Knowledge Base</button>
          <button className={activeTab === 'fallbacks' ? 'active' : ''} onClick={() => setActiveTab('fallbacks')}>Unanswered FAQs ({fallbacks.length})</button>
          <a href="/" className="carepilot-admin-close" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center' }}>Go to Website</a>
        </div>
      </div>

      {statusMsg && <div className="carepilot-alert success">{statusMsg}</div>}
      {errorMsg && <div className="carepilot-alert error">{errorMsg}</div>}

      <div className="carepilot-admin-content">
        
        {/* LEADS TAB */}
        {activeTab === 'leads' && (
          <div className="admin-section">
            <div className="admin-stats-grid">
              <div className="stat-card">
                <h3>Total Chats</h3>
                <p>{analytics.total_sessions}</p>
              </div>
              <div className="stat-card">
                <h3>Leads Captured</h3>
                <p>{analytics.total_leads}</p>
              </div>
              <div className="stat-card">
                <h3>Hot / Priority Leads</h3>
                <p>
                  {(analytics.temperature_distribution?.["Hot lead"] || 0) + 
                   (analytics.temperature_distribution?.["High priority lead"] || 0)}
                </p>
              </div>
              <div className="stat-card">
                <h3>Conversion Rate</h3>
                <p>{analytics.conversion_rate}%</p>
              </div>
            </div>

            <h3 className="section-title">Captured Leads</h3>
            <div className="table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>Score</th>
                    <th>Category</th>
                    <th>Urgency</th>
                    <th>Interests</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.map(lead => (
                    <tr key={lead.id} className={`lead-row temp-${(lead.lead_temperature || '').toLowerCase().replace(' ', '-')}`}>
                      <td><strong>{lead.name}</strong></td>
                      <td>{lead.email}</td>
                      <td>{lead.phone}</td>
                      <td>{lead.lead_score}/100</td>
                      <td>
                        <span className={`tag temp-tag`}>{lead.lead_temperature}</span>
                      </td>
                      <td>{lead.urgency || 'Exploring'}</td>
                      <td>{lead.interested_program || 'General'}</td>
                      <td>
                        <select 
                          value={lead.status || 'New'} 
                          onChange={(e) => handleUpdateStatus(lead.id, e.target.value)}
                        >
                          <option value="New">New</option>
                          <option value="Contacted">Contacted</option>
                          <option value="Enrolled">Enrolled</option>
                          <option value="Junk">Junk</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                  {leads.length === 0 && (
                    <tr>
                      <td colSpan="8" style={{ textAlign: 'center', padding: '24px' }}>No student leads collected yet. Check back soon!</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* KNOWLEDGE BASE TAB */}
        {activeTab === 'knowledge' && (
          <div className="admin-section">
            <div className="knowledge-forms">
              {/* Crawl Form */}
              <div className="kb-card">
                <h4>Index Website Page</h4>
                <form onSubmit={handleAddUrl}>
                  <input 
                    type="url" 
                    placeholder="https://portfoliobuilders.in/..." 
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    required
                  />
                  <div className="form-row">
                    <select value={urlCategory} onChange={(e) => setUrlCategory(e.target.value)}>
                      <option value="general">General FAQ</option>
                      <option value="courses">Courses</option>
                      <option value="internships">Internships</option>
                    </select>
                    <button type="submit">Crawl page</button>
                  </div>
                </form>
              </div>

              {/* Upload Form */}
              <div className="kb-card">
                <h4>Upload Document</h4>
                <form onSubmit={handleUploadFile}>
                  <input 
                    type="file" 
                    accept=".txt,.md,.pdf" 
                    onChange={(e) => setFileInput(e.target.files[0])}
                    required
                  />
                  <div className="form-row">
                    <select value={fileCategory} onChange={(e) => setFileCategory(e.target.value)}>
                      <option value="general">General FAQ</option>
                      <option value="courses">Courses</option>
                      <option value="internships">Internships</option>
                    </select>
                    <button type="submit" disabled={!fileInput}>Upload</button>
                  </div>
                </form>
              </div>

              {/* Tools card */}
              <div className="kb-card flex-col center">
                <h4>System Tools</h4>
                <p className="text-secondary" style={{ fontSize: '12px', marginBottom: '16px' }}>Re-build the vector index if you upload files manually to the data folder.</p>
                <button className="secondary" onClick={handleReindex}>Trigger Vector Reindex</button>
              </div>
            </div>

            <h3 className="section-title">Indexed Documents ({knowledge.length})</h3>
            <div className="table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Source Type</th>
                    <th>URL / Location</th>
                    <th>Created At</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {knowledge.map(doc => (
                    <tr key={doc.id}>
                      <td><strong>{doc.title}</strong></td>
                      <td><span className="tag type-tag">{doc.source_type}</span></td>
                      <td style={{ fontSize: '12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {doc.source_url || doc.file_url || 'Manual Entry'}
                      </td>
                      <td>{new Date(doc.created_at).toLocaleString()}</td>
                      <td>
                        <button className="btn-delete" onClick={() => handleDeleteDoc(doc.id)}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* UNANSWERED TAB */}
        {activeTab === 'fallbacks' && (
          <div className="admin-section">
            <h3 className="section-title">Low Confidence Questions</h3>
            <p className="text-secondary" style={{ fontSize: '13px', marginBottom: '20px' }}>
              Whenever CarePilot AI answers "I'm sorry, I don't have that specific information...", the query is recorded here. Answer it below to train the bot.
            </p>

            <div className="fallback-list">
              {fallbacks.map(fb => (
                <div key={fb.id} className={`fallback-card resolved-${fb.resolved_status}`}>
                  <div className="fallback-heading">
                    <span className="fb-date">{new Date(fb.created_at).toLocaleString()}</span>
                    <span className={`tag fb-tag status-${fb.resolved_status}`}>{fb.resolved_status}</span>
                  </div>
                  <div className="fb-question">
                    <strong>Question asked:</strong> "{fb.user_question}"
                  </div>
                  <div className="fb-response">
                    <strong>Bot fallback response:</strong> "{fb.bot_response}"
                  </div>

                  {fb.resolved_status === 'unresolved' ? (
                    <div className="fb-solve-form">
                      <textarea 
                        rows="2"
                        placeholder="Write the correct, official answer here..."
                        value={resolveAnswers[fb.id] || ''}
                        onChange={(e) => setResolveAnswers(prev => ({ ...prev, [fb.id]: e.target.value }))}
                      />
                      <button onClick={() => handleResolveFallback(fb.id)}>Save & Train Bot</button>
                    </div>
                  ) : (
                    <div className="fb-solved-answer">
                      <strong>Admin Resolution Answer:</strong> "{fb.admin_answer}"
                    </div>
                  )}
                </div>
              ))}
              {fallbacks.length === 0 && (
                <div style={{ textAlign: 'center', padding: '32px' }} className="fallback-card">
                  🎉 Good job! There are no unanswered fallback questions.
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export default AdminPanel;
