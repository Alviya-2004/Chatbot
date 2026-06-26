import React, { useState, useRef, useEffect } from 'react';
import './index.css';
import AdminPanel from './AdminPanel';

// Helper for generating local visitor IDs
const getVisitorId = () => {
  let id = localStorage.getItem('carepilot_visitor_id');
  if (!id) {
    id = Math.random().toString(36).substring(2, 15);
    localStorage.setItem('carepilot_visitor_id', id);
  }
  return id;
};

function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [view, setView] = useState('chat'); // 'chat' or 'admin'
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [proactiveBubble, setProactiveBubble] = useState(false);

  const defaultReplies = [
    { text: "🎨 UI/UX Program", query: "Tell me about UI/UX Portfolio Building Program" },
    { text: "💼 Internships", query: "Are there internships for AICTE or FYUGP?" },
    { text: "🎓 Scholarships", query: "How can I apply for the Scholarship Program?" },
    { text: "📞 Talk to Counsellor", query: "I want to talk to a human counsellor" }
  ];
  const [suggestedReplies, setSuggestedReplies] = useState(defaultReplies);
  
  // Backend session & scoring state
  const [sessionId, setSessionId] = useState('');
  const [currentScore, setCurrentScore] = useState(0);
  const [leadCategory, setLeadCategory] = useState('Cold lead');

  // Lead form states
  const [showForm, setShowForm] = useState(false);
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [leadForm, setLeadForm] = useState({
    name: '',
    phone: '',
    email: '',
    status: 'Student',
    urgency: 'Exploring',
    program: 'UI/UX Portfolio Building Program'
  });

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, showForm, formSubmitted]);

  // Proactive Bubble Trigger (8-12 seconds on homepage)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!isOpen && messages.length === 0) {
        setProactiveBubble(true);
      }
    }, 10000); // 10 seconds
    return () => clearTimeout(timer);
  }, [isOpen, messages]);

  // Initialize Session on open/mount
  const initSession = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/chat/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          visitor_id: getVisitorId(),
          source_page: window.location.href
        })
      });
      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);
        setMessages([{ id: 'welcome', role: 'ai', text: data.reply }]);
      }
    } catch (error) {
      console.error('Failed to initialize CarePilot session:', error);
      setMessages([{
        id: 'error',
        role: 'ai',
        text: 'Hello! I am CarePilot AI. I am having trouble connecting to my backend right now, but feel free to check our website or message us at +91 7994721792!'
      }]);
    }
  };

  useEffect(() => {
    if (isOpen && !sessionId) {
      initSession();
    }
  }, [isOpen]);

  const handleOpenWidget = () => {
    setIsOpen(true);
    setProactiveBubble(false);
  };

  const handleRestartChat = () => {
    if (confirm("Would you like to clear history and restart your career guide conversation?")) {
      setSessionId('');
      setCurrentScore(0);
      setLeadCategory('Cold lead');
      setShowForm(false);
      setFormSubmitted(false);
      setMessages([]);
      setSuggestedReplies(defaultReplies);
      initSession();
    }
  };

  const submitQuery = async (queryText) => {
    if (isLoading) return;
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', text: queryText }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: queryText,
          current_score: currentScore,
          current_page_url: window.location.href
        })
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentScore(data.new_score);
        setLeadCategory(data.lead_category);
        
        setMessages(prev => [...prev, { id: Date.now().toString(), role: 'ai', text: data.reply }]);
        
        // Trigger lead form if backend flag is true and form hasn't been done
        if (data.trigger_form && !formSubmitted) {
          setShowForm(true);
        }

        // Update dynamic suggested replies
        if (data.suggested_replies && data.suggested_replies.length > 0) {
          const newReplies = data.suggested_replies.map(reply => ({ text: reply, query: reply }));
          setSuggestedReplies(newReplies);
        } else {
          setSuggestedReplies([]); // Hide if none returned
        }
      }
    } catch (e) {
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'ai', text: 'Sorry, I lost my connection. Please check again in a moment.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    const query = inputValue.trim();
    setInputValue('');
    submitQuery(query);
  };

  const handleLeadSubmit = async (e) => {
    e.preventDefault();
    if (!leadForm.name || !leadForm.phone || !leadForm.email) return;

    try {
      const response = await fetch('http://localhost:8000/api/leads/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: leadForm.name,
          phone: leadForm.phone,
          email: leadForm.email,
          current_status: leadForm.status,
          urgency: leadForm.urgency,
          interested_program: leadForm.program,
          lead_score: currentScore,
          source_page: window.location.href,
          conversation_summary: `Student ${leadForm.name} is looking to learn more about the ${leadForm.program}. Current Status: ${leadForm.status}. Urgency: ${leadForm.urgency}.`
        })
      });

      if (response.ok) {
        setFormSubmitted(true);
        setShowForm(false);
        
        // Push a success confirmation bubble into chat
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'ai',
          text: `Thank you, ${leadForm.name}! Your career profile is saved. I've notified our admissions counselor. Would you like to connect directly on WhatsApp now to get immediate batch schedules and brochures?`
        }]);

        // Trigger mock WhatsApp API alert in background
        const leadData = await response.json();
        fetch('http://localhost:8000/api/leads/send-whatsapp-notification', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lead_id: leadData.id })
        });
      }
    } catch (e) {
      alert("Failed to submit profile. Please try again.");
    }
  };

  // Compile pre-filled WhatsApp link
  const getWhatsAppLink = () => {
    const baseText = `Hi Portfolio Builders! My name is ${leadForm.name || 'Student'}. I just completed the CarePilot AI career assessment and I am interested in details regarding the ${leadForm.program || 'programs'}. Please connect me with a counselor.`;
    return `https://wa.me/917994721792?text=${encodeURIComponent(baseText)}`;
  };

  return (
    <div className="carepilot-widget-root">
      
      {/* Proactive Greeting Bubble */}
      {proactiveBubble && !isOpen && (
        <div className="carepilot-proactive-bubble" onClick={handleOpenWidget}>
          <div className="carepilot-bubble-text">
            <strong>CarePilot AI</strong>
            <p>👋 Need help choosing a course or securing an internship? Let's check!</p>
          </div>
          <button className="carepilot-bubble-close" onClick={(e) => { e.stopPropagation(); setProactiveBubble(false); }}>&times;</button>
        </div>
      )}

      {/* Main Container */}
      <div className={`carepilot-window ${isOpen ? 'is-open' : ''} ${view === 'admin' ? 'admin-layout' : ''}`}>
        
        {view === 'admin' ? (
          <AdminPanel onClose={() => setView('chat')} />
        ) : (
          <>
            {/* Header */}
            <div className="carepilot-header">
              <div className="carepilot-header-title">
                <span className="carepilot-status-dot"></span>
                <div>
                  <h4>CarePilot AI</h4>
                  <span className="subtitle">Your 24/7 Career Guide</span>
                </div>
              </div>
              <div className="carepilot-header-actions">
                {sessionId && (
                  <button className="carepilot-action-icon" onClick={handleRestartChat} title="Reset Chat">
                    🔄
                  </button>
                )}
                {/* Admin Mode Switcher */}
                <button className="carepilot-action-icon" onClick={() => setView('admin')} title="Admin Panel">
                  ⚙️
                </button>
                <button className="carepilot-close-btn" onClick={() => setIsOpen(false)} aria-label="Close Chat">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>
            </div>

            {/* Chat Body */}
            <div className="carepilot-messages">
              {messages.map(msg => (
                <div key={msg.id} className={`carepilot-message ${msg.role}`}>
                  {msg.text}
                </div>
              ))}

              {/* Inline Interactive Lead Collection Form */}
              {showForm && !formSubmitted && (
                <div className="carepilot-lead-form-card">
                  <h5>Let's Personalize Your Career Roadmap</h5>
                  <p>Our counselor will share fee, batch dates and syllabus details on WhatsApp.</p>
                  <form onSubmit={handleLeadSubmit}>
                    <input 
                      type="text" 
                      placeholder="Your Full Name" 
                      value={leadForm.name} 
                      onChange={e => setLeadForm({...leadForm, name: e.target.value})}
                      required 
                    />
                    <input 
                      type="email" 
                      placeholder="Email Address" 
                      value={leadForm.email} 
                      onChange={e => setLeadForm({...leadForm, email: e.target.value})}
                      required 
                    />
                    <input 
                      type="tel" 
                      placeholder="WhatsApp Phone Number" 
                      value={leadForm.phone} 
                      onChange={e => setLeadForm({...leadForm, phone: e.target.value})}
                      required 
                    />
                    
                    <div className="select-group">
                      <label>I am currently a:</label>
                      <select value={leadForm.status} onChange={e => setLeadForm({...leadForm, status: e.target.value})}>
                        <option value="Student">Student (Final Year / College)</option>
                        <option value="Graduate">Recent Graduate</option>
                        <option value="Working Professional">Working Professional / Career Switcher</option>
                        <option value="Parent">Parent</option>
                      </select>
                    </div>

                    <div className="select-group">
                      <label>Urgency to start:</label>
                      <select value={leadForm.urgency} onChange={e => setLeadForm({...leadForm, urgency: e.target.value})}>
                        <option value="Immediate">Immediate (Next Batch)</option>
                        <option value="Next 3 Months">In Next 3 Months</option>
                        <option value="Exploring">Just Exploring</option>
                      </select>
                    </div>

                    <div className="select-group">
                      <label>Preferred Course/Program:</label>
                      <select value={leadForm.program} onChange={e => setLeadForm({...leadForm, program: e.target.value})}>
                        <option value="UI/UX Portfolio Building Program">UI/UX Portfolio Building Program</option>
                        <option value="Full Stack Development Course">Full Stack Development Course</option>
                        <option value="AICTE Internship">AICTE Internship Support</option>
                        <option value="FYUGP Internship">FYUGP Internship Support</option>
                        <option value="Free Portfolio Review">Free Portfolio/Resume Review</option>
                      </select>
                    </div>

                    <button type="submit" className="form-submit-btn">Get Detailed Syllabus & Schedules</button>
                  </form>
                </div>
              )}

              {/* WhatsApp Redirect CTA Card */}
              {formSubmitted && (
                <div className="carepilot-whatsapp-cta-card">
                  <div className="icon">🟢</div>
                  <h5>Direct Counsel Handoff</h5>
                  <p>Admissions is online. Chat with us on WhatsApp for rapid confirmation.</p>
                  <a href={getWhatsAppLink()} target="_blank" rel="noopener noreferrer" className="whatsapp-cta-button">
                    Start WhatsApp Chat
                  </a>
                </div>
              )}

              {isLoading && (
                <div className="carepilot-message ai">
                  <div className="carepilot-loading-dots">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Suggested Reply Chips */}
            {!showForm && !formSubmitted && suggestedReplies.length > 0 && !isLoading && (
              <div className="carepilot-quick-replies">
                {suggestedReplies.map((reply, idx) => (
                  <button key={idx} onClick={() => submitQuery(reply.query)}>{reply.text}</button>
                ))}
              </div>
            )}

            {/* Input Form */}
            <div className="carepilot-input-area">
              <form className="carepilot-input-form" onSubmit={handleSubmit}>
                <input 
                  type="text" 
                  className="carepilot-input" 
                  placeholder="Ask CarePilot career questions..." 
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  disabled={isLoading || showForm}
                />
                <button type="submit" className="carepilot-send-btn" disabled={!inputValue.trim() || isLoading || showForm}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                  </svg>
                </button>
              </form>
              <div className="lead-indicator-footer">
                Lead Score: {currentScore}/100 • {leadCategory}
              </div>
            </div>
          </>
        )}

      </div>

      {/* Floating Toggle Button */}
      <button 
        className="carepilot-toggle" 
        onClick={() => {
          if (isOpen) {
            setIsOpen(false);
          } else {
            handleOpenWidget();
          }
        }}
        aria-label="Toggle CarePilot Chat"
      >
        {isOpen ? (
           <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
             <line x1="18" y1="6" x2="6" y2="18"></line>
             <line x1="6" y1="6" x2="18" y2="18"></line>
           </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        )}
      </button>
      
    </div>
  );
}

export default App;
