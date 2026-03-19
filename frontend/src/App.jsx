import React, { useState, useEffect, useRef } from 'react';
import { Radio, Map as MapIcon, Send, Loader2, Sparkles, Activity, Globe } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getAlerts, postIntelligence } from './api';
import './index.css';

// --- Sub-Components ---

const ThreatMatrix = ({ alerts }) => (
  <div className="widget-card">
    <div className="widget-title">
      <Activity size={14} />
      Threat Matrix
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {alerts.length === 0 ? (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-faint)', textAlign: 'center', py: 4 }}>Monitoring vault...</div>
      ) : (
        alerts.slice(0, 5).map((alert, i) => (
          <div key={i} style={{ 
            fontSize: '0.8rem', 
            padding: '10px', 
            background: 'var(--surface-muted)', 
            borderRadius: '10px',
            borderLeft: `3px solid ${alert.severity === 'CRITICAL' ? 'var(--danger)' : 'var(--warning)'}`
          }}>
            <div style={{ fontWeight: 700, marginBottom: '2px' }}>{alert.source_entity}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{alert.description}</div>
          </div>
        ))
      )}
    </div>
  </div>
);

const StratMap = () => (
  <div className="widget-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
    <div className="widget-title">
      <Globe size={14} />
      Geospatial
    </div>
    <div style={{ flex: 1, background: '#f3f4f6', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '150px' }}>
      <div style={{ textAlign: 'center' }}>
        <MapIcon size={24} color="#9ca3af" />
        <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '8px', fontWeight: 600 }}>MAP_CORE_IDLE</div>
      </div>
    </div>
  </div>
);

// --- Main App ---

function App() {
  const [messages, setMessages] = useState([{ type: 'bot', text: 'System initialized. Sovereign Inference Layer operational. Awaiting strategic query.' }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [time, setTime] = useState(new Date().toLocaleTimeString());
  const scrollRef = useRef();

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    const fetchLoop = async () => {
      const data = await getAlerts();
      if (data.active_threats) setAlerts(data.active_threats);
    };
    fetchLoop();
    const alertTimer = setInterval(fetchLoop, 10000);
    return () => { clearInterval(timer); clearInterval(alertTimer); };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userQuery = input;
    setMessages(prev => [...prev, { type: 'user', text: userQuery }]);
    setInput('');
    setLoading(true);

    try {
      const result = await postIntelligence({ 
        query: userQuery, 
        messages: messages.slice(-5).map(m => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.text })) 
      });
      setMessages(prev => [...prev, { type: 'bot', text: result.synthesis }]);
    } catch (err) {
      setMessages(prev => [...prev, { type: 'bot', text: 'Error: Connection lost. Re-establishing link...' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <nav className="nav-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '32px', height: '32px', background: 'var(--primary)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800 }}>A</div>
          <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>ANVAY AI <span style={{ color: 'var(--text-faint)', fontWeight: 400 }}>/ JARVIS</span></div>
        </div>
        <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem', fontWeight: 600 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: 6, height: 6, background: '#10b981', borderRadius: '50%' }}></div>VAULT</div>
          <div className="mono">{time}</div>
        </div>
      </nav>

      <div className="main-layout">
        <div className="chat-container" ref={scrollRef}>
          <div className="chat-content">
            {messages.map((m, i) => (
              <div key={i} className={m.type === 'user' ? 'message-user' : 'message-bot'}>
                {m.type === 'bot' && (
                  <div className="bot-avatar">
                    <Sparkles size={16} />
                  </div>
                )}
                <div className="bot-text" style={{ whiteSpace: 'pre-wrap' }}>
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="message-bot">
                <div className="bot-avatar"><Loader2 size={16} className="animate-spin" /></div>
                <div className="bot-text" style={{ color: 'var(--text-faint)' }}>Reasoning over ontology...</div>
              </div>
            )}
          </div>
        </div>

        <aside className="intelligence-sidebar">
          <ThreatMatrix alerts={alerts} />
          <StratMap />
          <div style={{ marginTop: 'auto', padding: '10px', fontSize: '0.7rem', color: 'var(--text-faint)', textAlign: 'center', borderTop: '1px solid var(--border)' }}>
            SOVEREIGN INTELLIGENCE PROTOCOL V2.5
          </div>
        </aside>
      </div>

      <div className="input-container">
        <div className="input-box">
          <input 
            type="text" 
            className="prompt-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask JARVIS anything..."
          />
          <button 
            className="send-btn" 
            onClick={handleSend}
            disabled={!input.trim() || loading}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
