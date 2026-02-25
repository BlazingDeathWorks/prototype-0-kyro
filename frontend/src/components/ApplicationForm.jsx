import React, { useState, useRef } from 'react';
import { Upload, FileText, ArrowRight, X, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';

const ApplicationForm = ({ onSubmit, isLoading }) => {
    const [resume, setResume] = useState(null);
    const [urls, setUrls] = useState('');
    const fileInputRef = useRef(null);
    const [error, setError] = useState('');

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            if (file.type === 'application/pdf' || file.name.endsWith('.pdf') || file.name.endsWith('.docx') || file.name.endsWith('.txt')) {
                setResume(file);
                setError('');
            } else {
                setError('Please upload a valid resume (PDF, DOCX, TXT)');
                setResume(null);
            }
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        const file = e.dataTransfer.files[0];
        if (file) {
            if (file.type === 'application/pdf' || file.name.endsWith('.pdf') || file.name.endsWith('.docx') || file.name.endsWith('.txt')) {
                setResume(file);
                setError('');
            } else {
                setError('Please upload a valid resume (PDF, DOCX, TXT)');
            }
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!resume) {
            setError('Please upload a resume');
            return;
        }
        if (!urls.trim()) {
            setError('Please enter at least one URL');
            return;
        }
        onSubmit(resume, urls);
    };

    return (
        <div className="aesthetic-card">
            <form onSubmit={handleSubmit}>

                {/* Resume Section */}
                <div className="input-group">
                    <label className="label-text">Resume Document</label>
                    <div
                        className="file-upload-box"
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={handleDrop}
                        onClick={() => !resume && fileInputRef.current.click()}
                    >
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            style={{ display: 'none' }}
                            accept=".pdf,.docx,.doc,.txt"
                        />

                        {resume ? (
                            <div className="file-name-display" onClick={(e) => e.stopPropagation()}>
                                <FileText size={18} color="#fff" />
                                <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>{resume.name}</span>
                                <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); setResume(null); }}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', marginLeft: '10px', color: '#666' }}
                                >
                                    <X size={16} />
                                </button>
                            </div>
                        ) : (
                            <div className="file-upload-content">
                                <Upload size={24} color="#666" style={{ marginBottom: '10px' }} />
                                <p style={{ fontSize: '0.9rem', color: '#ccc' }}>Click to Upload Resume</p>
                                <p style={{ fontSize: '0.75rem', color: '#666', marginTop: '4px' }}>PDF, DOCX OR TXT</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* URLs Section */}
                <div className="input-group">
                    <label className="label-text">Job Application Links</label>
                    <textarea
                        className="custom-textarea"
                        placeholder="https://jobs.lever.co/company/job1&#10;https://boards.greenhouse.io/company/job2"
                        value={urls}
                        onChange={(e) => setUrls(e.target.value)}
                        spellCheck="false"
                    ></textarea>
                    <div style={{ textAlign: 'right', marginTop: '8px', fontSize: '0.7rem', color: '#666' }}>
                        ENTER ONE URL PER LINE
                    </div>
                </div>

                {error && (
                    <div style={{
                        background: 'rgba(255, 68, 68, 0.1)',
                        border: '1px solid rgba(255, 68, 68, 0.2)',
                        color: '#ff6666',
                        padding: '12px',
                        borderRadius: '8px',
                        fontSize: '0.85rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        marginBottom: '20px'
                    }}>
                        <AlertCircle size={16} />
                        {error}
                    </div>
                )}

                <button
                    type="submit"
                    disabled={isLoading}
                    className="btn-primary"
                >
                    {isLoading ? (
                        <span style={{
                            width: '20px',
                            height: '20px',
                            border: '2px solid rgba(0,0,0,0.1)',
                            borderTopColor: '#000',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite'
                        }}></span>
                    ) : (
                        <>
                            Initialize Agent <ArrowRight size={18} />
                        </>
                    )}
                </button>

                {/* Simple inline animation for spinner */}
                <style>{`
          @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        `}</style>
            </form>
        </div>
    );
};

export default ApplicationForm;
