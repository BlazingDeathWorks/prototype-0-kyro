import React, { useState } from 'react';
import axios from 'axios';
import ApplicationForm from './components/ApplicationForm';
import StatusDashboard from './components/StatusDashboard';
import { motion, AnimatePresence } from 'framer-motion';

function App() {
  const [jobId, setJobId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (resume, urls) => {
    setIsLoading(true);
    const formData = new FormData();
    formData.append('resume', resume);
    formData.append('urls', urls);

    try {
      const response = await axios.post('http://localhost:8000/apply', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setJobId(response.data.job_id);
    } catch (error) {
      console.error('Error submitting application:', error);
      alert('Failed to start applications. Check console for details.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="ambient-bg"></div>

      <div className="main-layout">
        <AnimatePresence mode="wait">
          {!jobId ? (
            <motion.div
              key="form"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <header className="app-header">
                <h1 className="title">
                  Project Kyro
                </h1>
                <p className="subtitle">
                  Autonomous Application Agent
                </p>
              </header>

              <ApplicationForm onSubmit={handleSubmit} isLoading={isLoading} />
            </motion.div>
          ) : (
            <motion.div
              key="dashboard"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 300, color: '#fff' }}>Active Batch</h1>
                <button
                  onClick={() => setJobId(null)}
                  className="btn-ghost"
                >
                  START NEW BATCH
                </button>
              </div>

              <StatusDashboard jobId={jobId} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
}

export default App;
