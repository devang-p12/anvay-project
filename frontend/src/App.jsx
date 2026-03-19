import React, { useState, useEffect, useRef } from 'react';
import { Radio, MessageSquare, Map as MapIcon, Send, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getAlerts, postIntelligence } from './api';
import './index.css';

// --- Sub-Components ---

const ThreatMatrix = ({ alerts }) => (
  <motion.div 
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    className="glass-panel" 
    style={{ gridRow: '2' }}
  >
    <div className="panel-header">
      <div className="panel-title">Threat Matrix</div>
      <Radio className="pulse" size={16} color="var(--warning)" />
    </div>
    <div style={{ padding: '15px', overflowY: 'auto', flex: 1 }}>
      <AnimatePresence mode="popLayout">
        {alerts.length === 0 ? (
          <div className="faint" style={{ textAlign: 'center', marginTop: '40px', fontSize: '0.85rem' }}>Monitoring for anomalies...</div>
        ) : (
          alerts.map((alert, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              style={{ 
                marginBottom: '15px', 
                padding: '12px', 
                background: alert.severity === 'CRITICAL' ? 'var(--danger-weak)' : 'var(--warning-weak)', 
                borderLeft: `3px solid ${alert.severity === 'CRITICAL' ? 'var(--danger)' : 'var(--warning)'}`, 
                borderRadius: '10px',
                border: '1px solid var(--border)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '5px' }}>
                <span style={{ color: alert.severity === 'CRITICAL' ? 'var(--danger)' : 'var(--warning)', fontWeight: 800, letterSpacing: '0.06em' }}>{alert.severity}</span>
                <span className="faint">{new Date(alert.timestamp * 1000).toLocaleTimeString()}</span>
              </div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{alert.source_entity} &rarr; {alert.target_entity}</div>
              <div className="muted" style={{ fontSize: '0.8rem', marginTop: '4px' }}>{alert.description}</div>
            </motion.div>
          ))
        )}
      </AnimatePresence>
    </div>
  </motion.div>
);

const StratMap = () => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="glass-panel" 
    style={{ gridRow: '2' }}
  >
    <div className="panel-header">
      <div className="panel-title">Geospatial Intelligence</div>
      <MapIcon size={16} color="var(--primary)" />
    </div>
    <div style={{ flex: 1, position: 'relative', background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)' }}>
       <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
          <div className="pulse" style={{ color: 'var(--primary)', fontSize: '0.9rem', fontWeight: 700, letterSpacing: '0.10em' }}>INITIALIZING MAP…</div>
          <div className="faint" style={{ fontSize: '0.75rem', marginTop: '8px' }}>Awaiting coordinates from ingested reports</div>
       </div>
    </div>
  </motion.div>
);

const JarvisTerminal = () => {
  const [messages, setMessages] = useState([{ type: 'bot', text: 'System initialized. Sovereign Inference Layer operational. Awaiting strategic query.' }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('general'); // general | graph_heavy
  const scrollRef = useRef();

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userQuery = input;
    const nextMessages = [...messages, { type: 'user', text: userQuery }];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    const wireMessages = nextMessages
      .slice(-10)
      .map((m) => ({
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.text,
      }));

    const result = await postIntelligence({ query: userQuery, messages: wireMessages, mode });
    
    setMessages(prev => [...prev, { 
      type: 'bot', 
      text: result.synthesis,
      data: result.graph_paths
    }]);
    setLoading(false);
  };

  return (
    <div className="glass-panel" style={{ gridRow: '2' }}>
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="panel-title">JARVIS Reasoning Hub</div>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="input"
            style={{ width: '170px', padding: '8px 10px', borderRadius: '10px' }}
            aria-label="Chat mode"
          >
            <option value="general">General Chat</option>
            <option value="graph_heavy">Graph-Heavy</option>
          </select>
        </div>
        <MessageSquare size={16} color="var(--primary)" />
      </div>
      <div style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {messages.map((m, i) => (
              <div key={i} style={{ 
                alignSelf: m.type === 'user' ? 'flex-end' : 'flex-start',
              }}>
                <div className={`message ${m.type === 'user' ? 'message-user' : ''}`}>
                <div className={`message-label ${m.type === 'user' ? 'message-label-user' : 'message-label-bot'}`}>
                  {m.type === 'user' ? 'You' : 'JARVIS'}
                </div>
                <div className={m.type === 'bot' ? 'mono' : ''} style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="muted" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
                <Loader2 size={16} className="animate-spin" />
                <span>Reasoning over graph...</span>
              </div>
            )}
        </div>
        <div style={{ position: 'relative' }}>
           <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Query the Intelligence Graph..." 
              className="input"
           />
           <div 
              onClick={handleSend}
              className="btn-icon"
              style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', opacity: input.trim() ? 1 : 0.4 }}
           >
              <Send size={18} color="var(--primary)" />
           </div>
        </div>
      </div>
    </div>
  );
};

// --- Main App ---

function App() {
  const [time, setTime] = useState(new Date().toLocaleTimeString());
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    
    // Poll alerts every 10 seconds
    const fetchLoop = async () => {
      const data = await getAlerts();
      if (data.active_threats) setAlerts(data.active_threats);
    };
    fetchLoop();
    const alertTimer = setInterval(fetchLoop, 10000);

    return () => {
      clearInterval(timer);
      clearInterval(alertTimer);
    };
  }, []);

  return (
    <div className="dashboard-container">
      <nav className="navbar">
        <div className="logo-section">
          <div className="logo-icon">A</div>
          <div>
            <div style={{ fontWeight: 800, letterSpacing: '0.08em', fontSize: '1.05rem' }}>ANVAY AI</div>
            <div className="muted" style={{ fontSize: '0.8rem', fontWeight: 600 }}>Ontology Intelligence Engine</div>
          </div>
        </div>

        <div className="nav-status">
          <div className="status-item chip">
             <div className="status-dot"></div>
             KAFKA VAULT: ACTIVE
          </div>
          <div className="status-item chip">
             <div className="status-dot"></div>
             NEO4J: SYNCED
          </div>
          <div className="status-item chip">
             <div className="status-dot"></div>
             LLM: OPTIMIZED
          </div>
          <div className="status-item chip">
             <span className="mono">{time}</span>
          </div>
        </div>
      </nav>

      <ThreatMatrix alerts={alerts} />
      <StratMap />
      <JarvisTerminal />
    </div>
  );
}

export default App;
