import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, Clock, Loader2, ChevronDown, ChevronUp, Terminal, MonitorPlay, Maximize2 } from 'lucide-react';

const StatusDashboard = ({ jobId }) => {
    const [status, setStatus] = useState({});
    const [logs, setLogs] = useState({});
    const [sessionIds, setSessionIds] = useState({});
    const [liveViewUrls, setLiveViewUrls] = useState({});
    const [expandedLogs, setExpandedLogs] = useState({}); // Track expanded logs per URL
    const [focusedUrl, setFocusedUrl] = useState(null); // URL currently focused in modal

    useEffect(() => {
        if (!jobId) return;

        const pollStatus = async () => {
            try {
                const response = await axios.get(`http://localhost:8000/status/${jobId}`);
                setStatus(response.data.status);
                setLogs(response.data.logs);

                if (response.data.session_ids) {
                    setSessionIds(response.data.session_ids);
                }

                // Update live view URLs only if changed to prevent re-renders
                if (response.data.live_view_urls) {
                    setLiveViewUrls(prevUrls => {
                        if (JSON.stringify(prevUrls) !== JSON.stringify(response.data.live_view_urls)) {
                            return response.data.live_view_urls;
                        }
                        return prevUrls;
                    });
                }
            } catch (error) {
                console.error("Error fetching status:", error);
            }
        };

        pollStatus();
        const interval = setInterval(pollStatus, 2000);
        return () => clearInterval(interval);
    }, [jobId]);

    const toggleLogs = (url) => {
        setExpandedLogs(prev => ({
            ...prev,
            [url]: !prev[url]
        }));
    };

    const getStatusIcon = (s) => {
        switch (s) {
            case 'completed': return <CheckCircle color="#44FF88" size={16} />;
            case 'failed': return <XCircle color="#FF4444" size={16} />;
            case 'running': return <Loader2 color="#88AAFF" size={16} style={{ animation: 'spin 2s linear infinite' }} />;
            default: return <Clock color="#666" size={16} />;
        }
    };

    // Combine all info into a list of "Tasks"
    const tasks = Object.entries(status).map(([url, s]) => ({
        url,
        status: s,
        logs: logs[url] || [],
        sessionId: sessionIds[url],
        liveUrl: liveViewUrls[url]
    }));

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="dashboard-container"
            style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '20px',
                width: '100%',
                alignItems: 'center'
            }}
        >
            {/* Grid of Unified Session Cards */}
            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', // Responsive grid
                    gap: '25px',
                    width: '100%',
                }}
            >
                {tasks.map((task) => (
                    <motion.div
                        key={task.url}
                        layout
                        className="aesthetic-card"
                        style={{
                            padding: '0',
                            display: 'flex',
                            flexDirection: 'column',
                            overflow: 'hidden',
                            background: '#0F0F0F',
                            border: '1px solid #2A2A2A',
                            borderRadius: '16px'
                        }}
                    >
                        {/* 1. Header: Status & URL */}
                        <div style={{
                            padding: '12px 16px',
                            borderBottom: '1px solid #222',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            background: '#141414'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                                {getStatusIcon(task.status)}
                                <span style={{
                                    fontSize: '0.8rem',
                                    fontWeight: 500,
                                    color: '#DDD',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    maxWidth: '250px'
                                }}>
                                    {task.url}
                                </span>
                            </div>

                            {/* Focus Button */}
                            {task.liveUrl && (
                                <button
                                    onClick={() => setFocusedUrl(task.url)}
                                    className="btn-ghost"
                                    style={{ padding: '4px', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem' }}
                                >
                                    <Maximize2 size={14} /> EXPAND
                                </button>
                            )}
                        </div>

                        {/* 2. Body: Live View or Placeholder */}
                        <div style={{
                            aspectRatio: '16/9',
                            width: '100%',
                            background: '#000',
                            position: 'relative',
                            borderBottom: '1px solid #222'
                        }}>
                            {task.liveUrl ? (
                                <iframe
                                    src={task.liveUrl}
                                    style={{ width: '100%', height: '100%', border: 'none' }}
                                    title={`Live View ${task.url}`}
                                    allow="clipboard-read; clipboard-write"
                                />
                            ) : (
                                <div style={{
                                    position: 'absolute', inset: 0,
                                    display: 'flex', flexDirection: 'column',
                                    alignItems: 'center', justifyContent: 'center',
                                    color: '#444'
                                }}>
                                    {task.status === 'completed' ? (
                                        <>
                                            <CheckCircle size={40} color="#44FF88" style={{ marginBottom: '10px', opacity: 0.5 }} />
                                            <span style={{ fontSize: '0.9rem' }}>Application Completed</span>
                                        </>
                                    ) : (
                                        <>
                                            <MonitorPlay size={40} style={{ marginBottom: '10px', opacity: 0.3 }} />
                                            <span style={{ fontSize: '0.9rem' }}>Initializing Session...</span>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* 3. Footer: Logs Toggle */}
                        <div style={{ background: '#111' }}>
                            <button
                                onClick={() => toggleLogs(task.url)}
                                style={{
                                    width: '100%',
                                    padding: '10px 16px',
                                    background: 'none',
                                    border: 'none',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    cursor: 'pointer',
                                    color: '#666',
                                    fontSize: '0.75rem',
                                    fontWeight: 600,
                                    letterSpacing: '0.05em'
                                }}
                            >
                                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <Terminal size={14} />
                                    {expandedLogs[task.url] ? 'HIDE LOGS' : 'SHOW LOGS'}
                                </span>
                                {expandedLogs[task.url] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </button>

                            <AnimatePresence>
                                {expandedLogs[task.url] && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: '200px', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        style={{ overflow: 'hidden', borderTop: '1px solid #222' }}
                                    >
                                        <div style={{
                                            padding: '15px',
                                            height: '100%',
                                            overflowY: 'auto',
                                            background: '#080808',
                                            fontFamily: 'monospace',
                                            fontSize: '0.75rem',
                                            color: '#aaa',
                                            whiteSpace: 'pre-wrap',
                                            lineHeight: 1.5
                                        }}>
                                            {task.logs.length > 0 ? task.logs.join('\n') : "Waiting for logs..."}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </motion.div>
                ))}

                {tasks.length === 0 && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', color: '#666' }}>
                        Waiting for tasks to start...
                    </div>
                )}
            </div>

            {/* Focused Overlay Modal */}
            <AnimatePresence>
                {focusedUrl && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setFocusedUrl(null)}
                        style={{
                            position: 'fixed',
                            inset: 0,
                            background: 'rgba(0,0,0,0.9)',
                            backdropFilter: 'blur(10px)',
                            zIndex: 100,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '40px'
                        }}
                    >
                        <motion.div
                            // layoutId={`video-${focusedUrl}`} // Optional: remove layoutId if it causes weird jumps with new structure
                            onClick={(e) => e.stopPropagation()}
                            className="aesthetic-card"
                            style={{
                                width: '90%',
                                maxWidth: '1600px',
                                height: '80vh', // Fixed height for modal
                                padding: 0,
                                overflow: 'hidden',
                                border: '1px solid #444',
                                background: '#000',
                                position: 'relative',
                                display: 'flex',
                                flexDirection: 'column'
                            }}
                        >
                            <div style={{
                                padding: '15px 20px',
                                borderBottom: '1px solid #333',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                background: '#111'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <MonitorPlay size={18} color="#88AAFF" />
                                    <span style={{ color: '#fff', fontWeight: 600 }}>{focusedUrl}</span>
                                </div>
                                <button
                                    onClick={() => setFocusedUrl(null)}
                                    style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer' }}
                                >
                                    <XCircle size={24} />
                                </button>
                            </div>
                            <div style={{ flex: 1, position: 'relative', background: '#000' }}>
                                <iframe
                                    src={liveViewUrls[focusedUrl]}
                                    style={{ width: '100%', height: '100%', border: 'none' }}
                                    title={`Focused View ${focusedUrl}`}
                                    allow="clipboard-read; clipboard-write; keyboard-focus"
                                />
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

export default StatusDashboard;
