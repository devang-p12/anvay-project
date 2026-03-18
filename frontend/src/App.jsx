import React, { useState, useEffect, useRef } from 'react';
import { Shield, Radio, MessageSquare, Map as MapIcon, ChevronRight, Send, ExternalLink, Loader2 } from 'lucide-react';
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
      <Radio className="pulse" size={16} color="#ff9800" />
    </div>
    <div style={{ padding: '15px', overflowY: 'auto', flex: 1 }}>
      <AnimatePresence mode="popLayout">
        {alerts.length === 0 ? (
          <div style={{ opacity: 0.3, textAlign: 'center', marginTop: '40px', fontSize: '0.8rem' }}>Monitoring for anomalies...</div>
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
                background: alert.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.1)', 
                borderLeft: `3px solid ${alert.severity === 'CRITICAL' ? '#ef4444' : '#f59e0b'}`, 
                borderRadius: '4px' 
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '5px' }}>
                <span style={{ color: alert.severity === 'CRITICAL' ? '#ef4444' : '#f59e0b', fontWeight: 'bold' }}>{alert.severity}</span>
                <span style={{ opacity: 0.5 }}>{new Date(alert.timestamp * 1000).toLocaleTimeString()}</span>
              </div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{alert.source_entity} &rarr; {alert.target_entity}</div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '4px' }}>{alert.description}</div>
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
      <MapIcon size={16} color="#00e5ff" />
    </div>
    <div style={{ flex: 1, position: 'relative', background: '#0a0c10' }}>
       <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
          <div className="pulse" style={{ color: '#00e5ff', fontSize: '0.8rem', letterSpacing: '2px' }}>INITIALIZING SATELLITE LINK...</div>
          <div style={{ fontSize: '0.65rem', opacity: 0.4, marginTop: '8px' }}>ACQUIRING GDELT COORDINATES</div>
       </div>
    </div>
  </motion.div>
);

const JarvisTerminal = () => {
  const [messages, setMessages] = useState([{ type: 'bot', text: 'System initialized. Sovereign Inference Layer operational. Awaiting strategic query.' }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef();

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userQuery = input;
    setMessages(prev => [...prev, { type: 'user', text: userQuery }]);
    setInput('');
    setLoading(true);

    const result = await postIntelligence(userQuery);
    
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
        <div className="panel-title">JARVIS Reasoning Hub</div>
        <MessageSquare size={16} color="#00e5ff" />
      </div>
      <div style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {messages.map((m, i) => (
              <div key={i} style={{ 
                alignSelf: m.type === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
                padding: '12px 16px',
                borderRadius: '12px',
                background: m.type === 'user' ? 'rgba(0, 229, 255, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                border: `1px solid ${m.type === 'user' ? 'rgba(0, 229, 255, 0.2)' : 'var(--glass-border)'}`,
                fontSize: '0.9rem',
                lineHeight: '1.5'
              }}>
                <div style={{ color: m.type === 'user' ? '#00e5ff' : '#ff9800', fontSize: '0.7rem', fontWeight: 700, marginBottom: '4px', textTransform: 'uppercase' }}>
                  {m.type === 'user' ? 'You' : 'JARVIS'}
                </div>
                <div className={m.type === 'bot' ? 'mono' : ''} style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
              </div>
            ))}
            {loading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#00e5ff', fontSize: '0.8rem' }}>
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
              style={{ width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)', padding: '12px 45px 12px 15px', borderRadius: '8px', color: 'white', outline: 'none' }}
           />
           <div 
              onClick={handleSend}
              style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', cursor: 'pointer', opacity: input.trim() ? 1 : 0.3 }}
           >
              <Send size={18} color="#ff9800" />
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
            <div style={{ fontWeight: 700, letterSpacing: '2px', fontSize: '1.1rem' }}>ANVAY AI</div>
            <div style={{ fontSize: '0.65rem', color: '#ff9800', fontWeight: 600 }}>SOVEREIGN INTELLIGENCE CORP</div>
          </div>
        </div>

        <div className="nav-status">
          <div className="status-item">
             <div className="status-dot"></div>
             KAFKA VAULT: ACTIVE
          </div>
          <div className="status-item">
             <div className="status-dot"></div>
             NEO4J: SYNCED
          </div>
          <div className="status-item">
             <div className="status-dot"></div>
             LLM: OPTIMIZED
          </div>
          <div className="status-item" style={{ borderLeft: '1px solid var(--glass-border)', paddingLeft: '20px', marginLeft: '10px' }}>
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
