import React, { useState, useRef, useEffect } from 'react';
import './index.css';

// Helper for generating session IDs
const generateSessionId = () => Math.random().toString(36).substring(2, 15);

function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { id: '1', role: 'ai', text: 'Hi there! I am CarePilot, your personal career assistant at Portfolio Builders. How can I help you today?' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // State for backend context
  const [sessionId] = useState(generateSessionId());
  const [currentScore, setCurrentScore] = useState(0);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    
    // Add user message to UI
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      // Send to FastAPI Backend
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage,
          current_score: currentScore,
          current_page_url: window.location.href
        })
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      
      // Update score from backend
      setCurrentScore(data.new_score);
      
      // Add AI response to UI
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'ai', text: data.reply }]);
      
      // Optional: Handle trigger_form here
      if (data.trigger_form) {
        console.log("Form triggered due to high lead score!");
        // You could trigger a modal or show a specific link to the user
      }

    } catch (error) {
      console.error('Error communicating with CarePilot API:', error);
      setMessages(prev => [...prev, { 
        id: Date.now().toString(), 
        role: 'ai', 
        text: 'Sorry, I am having trouble connecting to my servers right now. Please try again later.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="carepilot-widget-root">
      
      {/* Chat Window */}
      <div className={`carepilot-window ${isOpen ? 'is-open' : ''}`}>
        <div className="carepilot-header">
          <div className="carepilot-header-title">
            <span className="carepilot-status-dot"></span>
            CarePilot AI
          </div>
          <button className="carepilot-close-btn" onClick={() => setIsOpen(false)} aria-label="Close Chat">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="carepilot-messages">
          {messages.map(msg => (
            <div key={msg.id} className={`carepilot-message ${msg.role}`}>
              {msg.text}
            </div>
          ))}
          {isLoading && (
            <div className="carepilot-message ai">
              <div className="carepilot-loading-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="carepilot-input-area">
          <form className="carepilot-input-form" onSubmit={handleSubmit}>
            <input 
              type="text" 
              className="carepilot-input" 
              placeholder="Type your message..." 
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={isLoading}
            />
            <button type="submit" className="carepilot-send-btn" disabled={!inputValue.trim() || isLoading}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </form>
        </div>
      </div>

      {/* Floating Toggle Button */}
      <button 
        className="carepilot-toggle" 
        onClick={() => setIsOpen(!isOpen)}
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
