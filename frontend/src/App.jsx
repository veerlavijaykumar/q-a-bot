import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  FileText,
  Database,
  Sliders,
  Sparkles,
  Search,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Cpu,
  Trash2,
  Eye,
  Info,
  ExternalLink,
  Layers,
  ShieldCheck,
  Send,
  Zap,
  BookOpen,
  ArrowRight,
  HelpCircle,
  ThumbsUp,
  ThumbsDown,
  Download
} from 'lucide-react';

const SUGGESTED_PROMPTS = [
  {
    title: "GATE CS Syllabus",
    desc: "What subjects and topics are included in the GATE CS syllabus?",
    query: "What subjects and topics are included in the GATE CS syllabus?",
    icon: BookOpen
  },
  {
    title: "Aptitude Exam Guide",
    desc: "Summarize the key mathematical formulas and aptitude topics.",
    query: "Summarize the key mathematical formulas and quantitative aptitude topics.",
    icon: FileText
  },
  {
    title: "Operating Systems & Compilers",
    desc: "What topics appear in Compiler Design and Operating Systems?",
    query: "What topics are covered under Compiler Design and Operating Systems in the document?",
    icon: Layers
  },
  {
    title: "Mars Refusal Test",
    desc: "Test strict anti-hallucination refusal for out-of-context facts.",
    query: "What is the capital of Mars and what is its atmosphere composed of?",
    icon: AlertTriangle
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'knowledge' | 'chunks' | 'tuner'
  const [systemStatus, setSystemStatus] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [chunks, setChunks] = useState([]);
  const [chunksFilter, setChunksFilter] = useState('');
  const [selectedDocFilter, setSelectedDocFilter] = useState('');
  
  // Chat state
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [topK, setTopK] = useState(5);
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash');
  const [expandedEvidence, setExpandedEvidence] = useState({});
  const [copiedIndex, setCopiedIndex] = useState(null);

  // Modals & Feedback
  const [showArchModal, setShowArchModal] = useState(false);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [isRebuildingIndex, setIsRebuildingIndex] = useState(false);
  const [toast, setToast] = useState(null);
  
  const chatBottomRef = useRef(null);
  const fileInputRef = useRef(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Fetch initial system status and document list
  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch status', err);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents');
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
      }
    } catch (err) {
      console.error('Failed to fetch documents', err);
    }
  };

  const fetchChunks = async () => {
    try {
      const res = await fetch('/api/chunks?limit=100');
      if (res.ok) {
        const data = await res.json();
        setChunks(data.chunks || []);
      }
    } catch (err) {
      console.error('Failed to fetch chunks', err);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchDocuments();
    fetchChunks();
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Handle Query Submission
  const handleSendMessage = async (textToSend = null) => {
    const question = (textToSend || inputValue).trim();
    if (!question || isLoading) return;

    const userMessage = {
      sender: 'user',
      text: question,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    if (!textToSend) setInputValue('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          top_k: Number(topK),
          model: selectedModel
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to generate answer');
      }

      const data = await res.json();
      const botMessage = {
        sender: 'bot',
        text: data.answer,
        isRefusal: data.is_refusal,
        results: data.results || [],
        citations: data.allowed_citations || [],
        retrievalMs: data.retrieval_ms,
        generationMs: data.generation_ms,
        totalMs: data.total_ms,
        modelUsed: data.model_used,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      showToast(err.message, 'error');
      setMessages(prev => [
        ...prev,
        {
          sender: 'bot',
          text: `⚠️ Error: ${err.message}`,
          isError: true,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Rebuild Index Action
  const handleRebuildIndex = async () => {
    setIsRebuildingIndex(true);
    try {
      const res = await fetch('/api/indexing/rebuild', { method: 'POST' });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Indexing failed');
      }
      const data = await res.json();
      showToast(`Index rebuilt successfully! Embedded ${data.chunks_count} chunks in ${data.duration_seconds}s.`);
      fetchStatus();
      fetchChunks();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsRebuildingIndex(false);
    }
  };

  // Handle Document Upload
  const handleFileUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      });
      if (!res.ok) throw new Error('File upload failed');
      const data = await res.json();
      showToast(data.message);
      fetchDocuments();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Delete Document
  const handleDeleteDoc = async (filename) => {
    if (!window.confirm(`Are you sure you want to delete ${filename}?`)) return;
    try {
      const res = await fetch(`/api/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete file');
      showToast(`Deleted ${filename}`);
      fetchDocuments();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Preview Document Extracted Text
  const handlePreviewDoc = async (filename) => {
    setPreviewLoading(true);
    setPreviewDoc(null);
    try {
      const res = await fetch(`/api/documents/${encodeURIComponent(filename)}/preview`);
      if (!res.ok) throw new Error('Failed to load preview');
      const data = await res.json();
      setPreviewDoc(data);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Copy answer text
  const handleCopyAnswer = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    showToast('Answer copied to clipboard!');
    setTimeout(() => setCopiedIndex(null), 2500);
  };

  // Format markdown helper
  const renderFormattedAnswer = (text) => {
    const lines = text.split('\n');
    return lines.map((line, i) => {
      // Bold bullets
      if (line.trim().startsWith('* ') || line.trim().startsWith('- ')) {
        const content = line.trim().replace(/^[\*\-]\s+/, '');
        return (
          <li key={i} style={{ marginBottom: '6px' }}>
            <span dangerouslySetInnerHTML={{
              __html: content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            }} />
          </li>
        );
      }
      if (line.trim() === '') {
        return <div key={i} style={{ height: '8px' }} />;
      }
      return (
        <p key={i} style={{ marginBottom: '8px' }}>
          <span dangerouslySetInnerHTML={{
            __html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          }} />
        </p>
      );
    });
  };

  // Filtered Chunks
  const filteredChunks = chunks.filter(chunk => {
    const matchesSearch = !chunksFilter || chunk.text.toLowerCase().includes(chunksFilter.toLowerCase());
    const matchesDoc = !selectedDocFilter || chunk.metadata.source === selectedDocFilter;
    return matchesSearch && matchesDoc;
  });

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-wrapper" onClick={() => setActiveTab('chat')}>
          <div className="brand-icon">
            <Cpu size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="brand-title">DocuMind AI</span>
              <span className="brand-tag">RAG v2.5</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Enterprise Document Intelligence & Verification
            </div>
          </div>
        </div>

        {/* Center Live Telemetry */}
        <div className="header-center">
          <div className="badge badge-success">
            <div className="live-dot" />
            <span>FAISS Online</span>
          </div>

          {systemStatus?.vector_store?.loaded && (
            <div className="badge badge-accent">
              <Database size={13} />
              <span>{systemStatus.vector_store.vector_count} Vectors Indexed</span>
            </div>
          )}

          <div className="badge badge-muted">
            <Zap size={13} style={{ color: '#8b5cf6' }} />
            <span>{selectedModel}</span>
          </div>
        </div>

        {/* Right Action Buttons */}
        <div className="header-actions">
          <button
            className="btn-secondary"
            onClick={() => setShowArchModal(true)}
            title="Inspect RAG Architecture"
          >
            <Layers size={16} />
            <span>Architecture Flow</span>
          </button>

          <button
            className="btn-primary"
            onClick={handleRebuildIndex}
            disabled={isRebuildingIndex}
            title="Rebuild FAISS Vector Index"
          >
            <RefreshCw size={15} className={isRebuildingIndex ? 'spinning' : ''} />
            <span>{isRebuildingIndex ? 'Rebuilding...' : 'Re-index'}</span>
          </button>
        </div>
      </header>

      {/* Main Split Body */}
      <div className="app-body">
        {/* Left Navigation Sidebar */}
        <aside className="app-sidebar">
          <div>
            <div className="sidebar-section-title">Navigation</div>
            <nav className="nav-tabs">
              <button
                className={`nav-tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
                onClick={() => setActiveTab('chat')}
              >
                <MessageSquare size={18} />
                <span>Ask Assistant</span>
              </button>

              <button
                className={`nav-tab-btn ${activeTab === 'knowledge' ? 'active' : ''}`}
                onClick={() => setActiveTab('knowledge')}
              >
                <FileText size={18} />
                <span>Knowledge Base ({documents.length})</span>
              </button>

              <button
                className={`nav-tab-btn ${activeTab === 'chunks' ? 'active' : ''}`}
                onClick={() => setActiveTab('chunks')}
              >
                <Database size={18} />
                <span>Vector Chunks ({chunks.length})</span>
              </button>

              <button
                className={`nav-tab-btn ${activeTab === 'tuner' ? 'active' : ''}`}
                onClick={() => setActiveTab('tuner')}
              >
                <Sliders size={18} />
                <span>RAG Tuner & Guardrails</span>
              </button>
            </nav>
          </div>

          {/* Quick RAG Metrics Card */}
          <div>
            <div className="sidebar-section-title">System Metrics</div>
            <div className="stats-card">
              <div className="stats-row">
                <span className="stats-label">Vector Store:</span>
                <span className="stats-value">FAISS FlatIP</span>
              </div>
              <div className="stats-row">
                <span className="stats-label">Similarity Metric:</span>
                <span className="stats-value">Cosine (L2-Norm)</span>
              </div>
              <div className="stats-row">
                <span className="stats-label">Embedding Dim:</span>
                <span className="stats-value">3,072 dims</span>
              </div>
              <div className="stats-row">
                <span className="stats-label">Chunk Boundary:</span>
                <span className="stats-value">500 ch / 100 ov</span>
              </div>
              <div className="stats-row">
                <span className="stats-label">Strict Refusal:</span>
                <span className="stats-value" style={{ color: 'var(--success)' }}>Active ✓</span>
              </div>
            </div>
          </div>

          {/* Suggested Starter Prompts */}
          <div>
            <div className="sidebar-section-title">Quick HR Demo Prompts</div>
            <div className="sample-questions">
              {SUGGESTED_PROMPTS.map((p, i) => (
                <button
                  key={i}
                  className="sample-q-pill"
                  onClick={() => {
                    setActiveTab('chat');
                    handleSendMessage(p.query);
                  }}
                >
                  <div style={{ fontWeight: 600, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <p.icon size={13} style={{ color: 'var(--accent-primary)' }} />
                    {p.title}
                  </div>
                  <div style={{ fontSize: '0.75rem', marginTop: '3px', opacity: 0.85 }}>
                    {p.desc}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* Main Center Area */}
        <main className="app-main">
          {/* TAB 1: Chat Workspace */}
          {activeTab === 'chat' && (
            <div className="chat-workspace">
              <div className="chat-history">
                {messages.length === 0 ? (
                  <div className="welcome-hero animate-fade-in">
                    <div className="hero-badge">
                      <Sparkles size={16} />
                      <span>RAG-Powered AI Verification</span>
                    </div>
                    <h1 className="hero-title">
                      Verified Answers From <span className="text-gradient">Your Documents</span>
                    </h1>
                    <p className="hero-desc">
                      Ask questions grounded strictly in your indexed PDF, DOCX, and TXT files.
                      Answers feature source citations, similarity telemetry, and strict anti-hallucination guardrails.
                    </p>

                    <div className="hero-features">
                      <div className="feature-card">
                        <div className="feature-icon">
                          <ShieldCheck size={22} />
                        </div>
                        <div className="feature-title">Strict Anti-Hallucination</div>
                        <div className="feature-desc">
                          If facts are not substantiated by retrieved document chunks, the system automatically triggers a verified refusal response.
                        </div>
                      </div>

                      <div className="feature-card">
                        <div className="feature-icon">
                          <BookOpen size={22} />
                        </div>
                        <div className="feature-title">Audited Citations</div>
                        <div className="feature-desc">
                          Every generated sentence is mapped to specific filenames and exact page numbers for complete enterprise auditability.
                        </div>
                      </div>

                      <div className="feature-card">
                        <div className="feature-icon">
                          <Database size={22} />
                        </div>
                        <div className="feature-title">FAISS Vector Search</div>
                        <div className="feature-desc">
                          Gemini 3072-dimensional embeddings matched at sub-millisecond latency using normalized inner-product cosine similarity.
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`message-row ${msg.sender === 'user' ? 'user' : 'bot'} animate-fade-in`}
                    >
                      {msg.sender === 'bot' && (
                        <div className="message-avatar bot-avatar">
                          <Sparkles size={18} />
                        </div>
                      )}

                      {msg.sender === 'user' ? (
                        <div className="user-bubble">
                          {msg.text}
                          <div style={{ fontSize: '0.72rem', opacity: 0.7, textAlign: 'right', marginTop: '4px' }}>
                            {msg.timestamp}
                          </div>
                        </div>
                      ) : (
                        <div className="bot-card">
                          <div className="bot-card-header">
                            <div className="bot-model-info">
                              <span style={{ fontWeight: 700, fontSize: '0.92rem' }}>DocuMind Assistant</span>
                              <span className="badge badge-muted">{msg.modelUsed || selectedModel}</span>
                              {msg.isRefusal ? (
                                <span className="badge badge-warning">
                                  <AlertTriangle size={12} />
                                  <span>Strict Refusal Enforced</span>
                                </span>
                              ) : (
                                <span className="badge badge-success">
                                  <ShieldCheck size={12} />
                                  <span>Grounded in Evidence</span>
                                </span>
                              )}
                            </div>

                            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                              {msg.timestamp}
                            </div>
                          </div>

                          <div className="bot-card-body">
                            {renderFormattedAnswer(msg.text)}
                          </div>

                          {/* Citations List if available */}
                          {msg.citations && msg.citations.length > 0 && !msg.isRefusal && (
                            <div>
                              <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '4px' }}>
                                CITED SOURCES:
                              </div>
                              <div className="citations-list">
                                {msg.citations.map((cite, cIdx) => (
                                  <div key={cIdx} className="citation-chip">
                                    <FileText size={12} />
                                    <span>{cite}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Retrieved Chunks Evidence Accordion */}
                          {msg.results && msg.results.length > 0 && (
                            <div className="evidence-section">
                              <button
                                className="evidence-toggle-btn"
                                onClick={() =>
                                  setExpandedEvidence(prev => ({ ...prev, [idx]: !prev[idx] }))
                                }
                              >
                                {expandedEvidence[idx] ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                                <span>
                                  {expandedEvidence[idx] ? 'Hide' : 'Inspect'} {msg.results.length} Retrieved Context Chunks
                                </span>
                              </button>

                              {expandedEvidence[idx] && (
                                <div className="evidence-cards-grid animate-fade-in">
                                  {msg.results.map((res, rIdx) => {
                                    const percentMatch = Math.round(res.score * 100);
                                    return (
                                      <div key={rIdx} className="evidence-card">
                                        <div className="evidence-card-header">
                                          <div className="evidence-source-title">
                                            <FileText size={14} />
                                            <span>{res.metadata.source}</span>
                                            {res.metadata.page && (
                                              <span className="badge badge-muted" style={{ padding: '2px 6px', fontSize: '0.72rem' }}>
                                                Page {res.metadata.page}
                                              </span>
                                            )}
                                          </div>

                                          <div className="score-meter">
                                            <span>Cosine Score: {res.score.toFixed(4)} ({percentMatch}%)</span>
                                            <div className="score-bar-bg">
                                              <div
                                                className="score-bar-fill"
                                                style={{ width: `${Math.min(100, Math.max(10, percentMatch))}%` }}
                                              />
                                            </div>
                                          </div>
                                        </div>

                                        <div className="evidence-text-snippet">
                                          {res.text}
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Bot Card Actions & Telemetry Footer */}
                          <div className="bot-card-actions">
                            <div className="telemetry-row">
                              {msg.totalMs && (
                                <span>⚡ Latency: {msg.totalMs}ms (Retrieval: {msg.retrievalMs}ms, Gen: {msg.generationMs}ms)</span>
                              )}
                            </div>

                            <div className="action-buttons-row">
                              <button
                                className="btn-icon"
                                onClick={() => handleCopyAnswer(msg.text, idx)}
                                title="Copy answer"
                              >
                                {copiedIndex === idx ? <Check size={15} style={{ color: 'var(--success)' }} /> : <Copy size={15} />}
                              </button>
                            </div>
                          </div>
                        </div>
                      )}

                      {msg.sender === 'user' && (
                        <div className="message-avatar user-avatar">
                          U
                        </div>
                      )}
                    </div>
                  ))
                )}

                {isLoading && (
                  <div className="message-row bot animate-fade-in">
                    <div className="message-avatar bot-avatar">
                      <Sparkles size={18} />
                    </div>
                    <div className="bot-card" style={{ maxWidth: '400px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <RefreshCw size={16} className="spinning" style={{ color: 'var(--accent-primary)' }} />
                        <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                          Retrieving FAISS chunks & generating grounded answer...
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={chatBottomRef} />
              </div>

              {/* Chat Input Dock */}
              <div className="chat-input-area">
                <div className="chat-input-wrapper">
                  <div className="chat-input-box">
                    <input
                      type="text"
                      className="chat-input-field"
                      placeholder="Ask any question grounded in your documents (e.g. GATE CS syllabus, Aptitude formulas)..."
                      value={inputValue}
                      onChange={e => setInputValue(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                      disabled={isLoading}
                    />

                    <button
                      className="chat-submit-btn"
                      onClick={() => handleSendMessage()}
                      disabled={!inputValue.trim() || isLoading}
                      title="Send question"
                    >
                      <Send size={18} />
                    </button>
                  </div>

                  <div className="input-footer-controls">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <span>Retrieval Top-K: <strong style={{ color: 'var(--text-main)' }}>{topK} Chunks</strong></span>
                      <span>Model: <strong style={{ color: 'var(--text-main)' }}>{selectedModel}</strong></span>
                    </div>

                    {messages.length > 0 && (
                      <button
                        className="btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                        onClick={() => setMessages([])}
                      >
                        Clear Conversation
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Knowledge Base Management */}
          {activeTab === 'knowledge' && (
            <div className="kb-container animate-fade-in">
              <div className="view-header">
                <div>
                  <h2 className="view-title">Document Knowledge Base</h2>
                  <p className="view-subtitle">
                    Manage files ingested into the RAG pipeline. Supported: PDF, TXT, DOCX, and Scanned OCR images.
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <input
                    type="file"
                    ref={fileInputRef}
                    style={{ display: 'none' }}
                    onChange={handleFileUpload}
                    multiple
                    accept=".pdf,.txt,.docx,.png,.jpg,.jpeg,.tif,.tiff,.bmp"
                  />
                  <button
                    className="btn-secondary"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <UploadCloud size={16} />
                    <span>Upload Documents</span>
                  </button>

                  <button
                    className="btn-primary"
                    onClick={handleRebuildIndex}
                    disabled={isRebuildingIndex}
                  >
                    <RefreshCw size={15} className={isRebuildingIndex ? 'spinning' : ''} />
                    <span>{isRebuildingIndex ? 'Syncing...' : 'Re-index FAISS'}</span>
                  </button>
                </div>
              </div>

              {/* Upload Dropzone */}
              <div
                className="dropzone"
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="dropzone-icon">
                  <UploadCloud size={28} />
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-main)' }}>
                    Drop documents here or click to browse
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Supports PDF (with automatic Tesseract OCR), TXT, DOCX, and PNG/JPG images
                  </div>
                </div>
              </div>

              {/* Documents Grid */}
              <div>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={16} style={{ color: 'var(--accent-primary)' }} />
                  <span>Active Ingested Documents ({documents.length})</span>
                </div>

                <div className="doc-grid">
                  {documents.map((doc, idx) => (
                    <div key={idx} className="doc-card">
                      <div className="doc-card-top">
                        <div className="doc-icon-box">
                          <FileText size={20} />
                        </div>
                        <div className="doc-info">
                          <div className="doc-filename" title={doc.filename}>{doc.filename}</div>
                          <div className="doc-meta">
                            {doc.size_formatted} • {doc.extension.toUpperCase()}
                          </div>
                        </div>
                      </div>

                      <div className="doc-card-bottom">
                        <button
                          className="btn-secondary"
                          style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                          onClick={() => handlePreviewDoc(doc.filename)}
                        >
                          <Eye size={13} />
                          <span>Preview</span>
                        </button>

                        <button
                          className="btn-icon"
                          style={{ color: 'var(--danger)' }}
                          onClick={() => handleDeleteDoc(doc.filename)}
                          title="Delete file"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Vector Chunks Inspector */}
          {activeTab === 'chunks' && (
            <div className="kb-container animate-fade-in">
              <div className="view-header">
                <div>
                  <h2 className="view-title">Vector Chunks Inspector</h2>
                  <p className="view-subtitle">
                    Inspect the actual semantic chunks stored in the FAISS vector index with boundary offsets.
                  </p>
                </div>
              </div>

              {/* Filter controls */}
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <div style={{ flex: 1, position: 'relative' }}>
                  <input
                    type="text"
                    className="chat-input-field"
                    style={{
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-md)',
                      padding: '10px 14px 10px 38px',
                      width: '100%'
                    }}
                    placeholder="Search chunk text keywords..."
                    value={chunksFilter}
                    onChange={e => setChunksFilter(e.target.value)}
                  />
                  <Search size={16} style={{ position: 'absolute', left: '12px', top: '14px', color: 'var(--text-dim)' }} />
                </div>

                <select
                  style={{
                    background: 'var(--bg-card)',
                    color: 'var(--text-main)',
                    border: '1px solid var(--border-subtle)',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    outline: 'none',
                    fontSize: '0.85rem'
                  }}
                  value={selectedDocFilter}
                  onChange={e => setSelectedDocFilter(e.target.value)}
                >
                  <option value="">All Documents</option>
                  {documents.map((d, i) => (
                    <option key={i} value={d.filename}>{d.filename}</option>
                  ))}
                </select>
              </div>

              {/* Chunks List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  Showing {filteredChunks.length} of {chunks.length} total indexed chunks
                </div>

                {filteredChunks.map((chunk, idx) => (
                  <div key={idx} className="evidence-card">
                    <div className="evidence-card-header">
                      <div className="evidence-source-title">
                        <FileText size={14} />
                        <span>{chunk.metadata.source}</span>
                        {chunk.metadata.page && (
                          <span className="badge badge-muted">Page {chunk.metadata.page}</span>
                        )}
                        <span className="badge badge-accent">Chunk #{chunk.metadata.chunk_index ?? idx}</span>
                      </div>

                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                        chars {chunk.metadata.start_char ?? 0}–{chunk.metadata.end_char ?? chunk.text.length}
                      </div>
                    </div>

                    <div className="evidence-text-snippet">
                      {chunk.text}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: RAG Tuner & Guardrails */}
          {activeTab === 'tuner' && (
            <div className="kb-container animate-fade-in">
              <div className="view-header">
                <div>
                  <h2 className="view-title">RAG Tuner & Hyperparameters</h2>
                  <p className="view-subtitle">
                    Configure retrieval depth, generation model parameters, and examine anti-hallucination guardrails.
                  </p>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
                <div className="bot-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Sliders size={18} style={{ color: 'var(--accent-primary)' }} />
                    Retrieval & Generation Settings
                  </h3>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <label style={{ fontSize: '0.88rem', fontWeight: 600 }}>Top-K Chunks to Retrieve:</label>
                        <span style={{ fontWeight: 700, color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>{topK}</span>
                      </div>
                      <input
                        type="range"
                        min="1"
                        max="10"
                        value={topK}
                        onChange={e => setTopK(Number(e.target.value))}
                        style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
                      />
                      <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                        Higher values provide broader context; lower values keep prompt tightly focused.
                      </div>
                    </div>

                    <div>
                      <label style={{ fontSize: '0.88rem', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                        Gemini Generation Model:
                      </label>
                      <select
                        value={selectedModel}
                        onChange={e => setSelectedModel(e.target.value)}
                        style={{
                          width: '100%',
                          background: 'rgba(15, 23, 42, 0.9)',
                          color: 'var(--text-main)',
                          border: '1px solid var(--border-card)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '10px',
                          fontSize: '0.9rem'
                        }}
                      >
                        <option value="gemini-2.5-flash">gemini-2.5-flash (Fast & Accurate, Recommended)</option>
                        <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                        <option value="gemini-1.5-pro">gemini-1.5-pro (High Reasoning)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ fontSize: '0.88rem', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                        Embedding Model (Configured):
                      </label>
                      <input
                        type="text"
                        disabled
                        value="gemini-embedding-001 (3072 dimensions)"
                        style={{
                          width: '100%',
                          background: 'rgba(0, 0, 0, 0.3)',
                          color: 'var(--text-muted)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '10px',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>
                  </div>
                </div>

                <div className="bot-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ShieldCheck size={18} style={{ color: 'var(--success)' }} />
                    Anti-Hallucination Guardrails
                  </h3>

                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.6' }}>
                    <p style={{ marginBottom: '10px' }}>
                      The system employs strict <strong>grounding guardrails</strong> in the prompt instruction set:
                    </p>
                    <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <li><strong>Context Isolation:</strong> The model is instructed to answer strictly using only supplied document chunks.</li>
                      <li><strong>Explicit Refusal:</strong> When insufficient evidence is found, it must output exactly the refusal sentence.</li>
                      <li><strong>Citation Whitelist:</strong> Only verified source combinations in <code style={{ color: '#a5b4fc' }}>ALLOWED CITATIONS</code> are permissible.</li>
                      <li><strong>Data Sanitization:</strong> Document contents are treated strictly as data, neutralizing prompt injection attacks.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* MODAL 1: RAG Architecture Flow Modal */}
      {showArchModal && (
        <div className="modal-overlay animate-fade-in" onClick={() => setShowArchModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Layers size={22} style={{ color: 'var(--accent-primary)' }} />
                <h3 style={{ fontSize: '1.25rem' }}>RAG Pipeline Architecture</h3>
              </div>
              <button className="btn-icon" onClick={() => setShowArchModal(false)}>✕</button>
            </div>

            <div className="modal-body">
              <div className="pipeline-flow">
                <div className="pipeline-step">
                  <div className="step-num-box">1</div>
                  <div className="step-content">
                    <div className="step-title">Multi-Format Document Ingestion & OCR</div>
                    <div className="step-desc">
                      Extracts structured text and metadata from PDF, TXT, and DOCX files.
                      Scanned PDFs without selectable text automatically trigger Tesseract OCR via PyMuPDF pixmaps.
                    </div>
                    <span className="step-tech-tag">PyMuPDF • pytesseract • python-docx</span>
                  </div>
                </div>

                <div className="pipeline-step">
                  <div className="step-num-box">2</div>
                  <div className="step-content">
                    <div className="step-title">Boundary-Aware Text Chunking</div>
                    <div className="step-desc">
                      Text is partitioned into ~500 character chunks with 100 character overlaps.
                      Splits prefer natural punctuation and sentence boundaries (\n, . , ! , ?) rather than arbitrary character cuts.
                    </div>
                    <span className="step-tech-tag">chunk_size=500 • overlap=100</span>
                  </div>
                </div>

                <div className="pipeline-step">
                  <div className="step-num-box">3</div>
                  <div className="step-content">
                    <div className="step-title">Batch Vector Embeddings</div>
                    <div className="step-desc">
                      Generates 3,072-dimensional vector embeddings in batches of 16 chunks with exponential backoff handling for quota rate limits.
                    </div>
                    <span className="step-tech-tag">gemini-embedding-001 • RETRIEVAL_DOCUMENT</span>
                  </div>
                </div>

                <div className="pipeline-step">
                  <div className="step-num-box">4</div>
                  <div className="step-content">
                    <div className="step-title">Persistent FAISS Vector Index</div>
                    <div className="step-desc">
                      Vectors are L2-normalized and indexed in FAISS using Inner Product (<code style={{ color: '#c7d2fe' }}>IndexFlatIP</code>),
                      yielding mathematically exact Cosine Similarity with zero database server overhead.
                    </div>
                    <span className="step-tech-tag">faiss-cpu • IndexFlatIP • chunks.json</span>
                  </div>
                </div>

                <div className="pipeline-step">
                  <div className="step-num-box">5</div>
                  <div className="step-content">
                    <div className="step-title">Semantic Query Retrieval</div>
                    <div className="step-desc">
                      The user's question is embedded using <code style={{ color: '#c7d2fe' }}>RETRIEVAL_QUERY</code> task type, normalized, and searched against FAISS for the Top-K most similar chunks.
                    </div>
                    <span className="step-tech-tag">Top-K Nearest Neighbor • Cosine Scoring</span>
                  </div>
                </div>

                <div className="pipeline-step">
                  <div className="step-num-box">6</div>
                  <div className="step-content">
                    <div className="step-title">Context Grounding & Answer Generation</div>
                    <div className="step-desc">
                      Context is assembled with allowed citations. Gemini generates the answer strictly grounded in evidence,
                      or issues a verified refusal if information is absent.
                    </div>
                    <span className="step-tech-tag">gemini-2.5-flash • Citations Whitelist</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Document Extracted Text Preview Modal */}
      {previewDoc && (
        <div className="modal-overlay animate-fade-in" onClick={() => setPreviewDoc(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileText size={20} style={{ color: 'var(--accent-primary)' }} />
                <h3 style={{ fontSize: '1.15rem' }}>Preview: {previewDoc.filename}</h3>
                <span className="badge badge-muted">{previewDoc.page_count} Pages / Records</span>
              </div>
              <button className="btn-icon" onClick={() => setPreviewDoc(null)}>✕</button>
            </div>

            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {previewDoc.pages.map((p, pIdx) => (
                <div key={pIdx} className="evidence-card">
                  <div className="evidence-card-header">
                    <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#93c5fd' }}>
                      {p.page ? `Page ${p.page}` : `Document Text`}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {p.char_count} characters
                    </span>
                  </div>
                  <div className="evidence-text-snippet" style={{ maxHeight: '250px' }}>
                    {p.text}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className={`toast toast-${toast.type} animate-fade-in`}>
          {toast.type === 'success' ? (
            <CheckCircle2 size={18} style={{ color: 'var(--success)' }} />
          ) : (
            <AlertTriangle size={18} style={{ color: 'var(--danger)' }} />
          )}
          <span>{toast.message}</span>
        </div>
      )}
    </div>
  );
}
