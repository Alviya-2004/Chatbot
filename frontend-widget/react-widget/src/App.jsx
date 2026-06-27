import React, { useState, useEffect } from 'react';
import './index.css';
import UserWidget from './UserWidget';

function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [proactiveBubble, setProactiveBubble] = useState(false);

  // Proactive Bubble Trigger (8-12 seconds on homepage)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!isOpen) {
        setProactiveBubble(true);
      }
    }, 10000); // 10 seconds
    return () => clearTimeout(timer);
  }, [isOpen]);

  const handleOpenWidget = () => {
    setIsOpen(true);
    setProactiveBubble(false);
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
      <div className={`carepilot-window ${isOpen ? 'is-open' : ''}`}>
        <UserWidget setIsOpen={setIsOpen} />
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
