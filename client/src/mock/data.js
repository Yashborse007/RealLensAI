/**
 * RealLens AI - Frontend Mock Data Repository
 * Dedicated Mock Layer for UI state rendering prior to live API integration.
 * NOTE: Contains structured sample schema matching expected API contracts.
 */

export const MOCK_DASHBOARD_STATS = {
  totalAnalyses: 148,
  realMediaCount: 104,
  potentialDeepfakesCount: 44,
  reportsGenerated: 38,
  processingCount: 2,
  weeklyGrowthRate: "+12.4%",
};

export const MOCK_DISTRIBUTION_DATA = [
  { name: 'Mon', images: 12, video: 8, audio: 4, deepfakes: 5 },
  { name: 'Tue', images: 18, video: 14, audio: 6, deepfakes: 8 },
  { name: 'Wed', images: 15, video: 11, audio: 8, deepfakes: 7 },
  { name: 'Thu', images: 22, video: 16, audio: 10, deepfakes: 11 },
  { name: 'Fri', images: 28, video: 19, audio: 12, deepfakes: 9 },
  { name: 'Sat', images: 14, video: 9, audio: 5, deepfakes: 3 },
  { name: 'Sun', images: 10, video: 7, audio: 3, deepfakes: 1 },
];

export const MOCK_MEDIA_TYPE_BREAKDOWN = [
  { name: 'Image Forensics', value: 58, color: '#00f0ff' },
  { name: 'Video Frames', value: 54, color: '#6366f1' },
  { name: 'Audio Spectral', value: 36, color: '#a855f7' },
];

export const MOCK_AUTHENTICITY_SUMMARY = [
  { name: 'Authentic / Real', value: 104, color: '#10b981' },
  { name: 'Deepfake / Manipulated', value: 44, color: '#f43f5e' },
];

export const MOCK_RECENT_ANALYSES = [
  {
    id: 'ana-8901',
    fileName: 'executive_keynote_speech.mp4',
    mediaType: 'video',
    fileSize: '42.8 MB',
    uploadedAt: '2026-09-19T14:32:00Z',
    status: 'completed',
    result: 'manipulated',
    confidenceScore: 0.91,
    flagsDetected: ['Facial warping boundary anomaly', 'Lip-sync temporal frame mismatch'],
    thumbnailUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80',
  },
  {
    id: 'ana-8902',
    fileName: 'press_briefing_audio_clip.wav',
    mediaType: 'audio',
    fileSize: '8.4 MB',
    uploadedAt: '2026-09-19T12:15:00Z',
    status: 'completed',
    result: 'authentic',
    confidenceScore: 0.96,
    flagsDetected: [],
    thumbnailUrl: null,
  },
  {
    id: 'ana-8903',
    fileName: 'identity_document_scan.png',
    mediaType: 'image',
    fileSize: '3.1 MB',
    uploadedAt: '2026-09-19T10:48:00Z',
    status: 'completed',
    result: 'authentic',
    confidenceScore: 0.94,
    flagsDetected: [],
    thumbnailUrl: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=400&q=80',
  },
  {
    id: 'ana-8904',
    fileName: 'viral_social_interview.mp4',
    mediaType: 'video',
    fileSize: '118.2 MB',
    uploadedAt: '2026-09-18T22:05:00Z',
    status: 'completed',
    result: 'manipulated',
    confidenceScore: 0.88,
    flagsDetected: ['Synthetic voice spectrogram overlap', 'Eye blink frequency distortion'],
    thumbnailUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80',
  },
  {
    id: 'ana-8905',
    fileName: 'security_camera_snapshot.jpg',
    mediaType: 'image',
    fileSize: '1.9 MB',
    uploadedAt: '2026-09-18T18:40:00Z',
    status: 'completed',
    result: 'suspicious',
    confidenceScore: 0.64,
    flagsDetected: ['High-frequency noise inconsistency'],
    thumbnailUrl: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80',
  },
  {
    id: 'ana-8906',
    fileName: 'broadcast_news_anchor.mp4',
    mediaType: 'video',
    fileSize: '89.5 MB',
    uploadedAt: '2026-09-18T15:20:00Z',
    status: 'processing',
    result: 'pending',
    confidenceScore: 0.0,
    flagsDetected: [],
    thumbnailUrl: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80',
  }
];

export const MOCK_DETAILED_ANALYSIS = {
  id: 'ana-8901',
  fileName: 'executive_keynote_speech.mp4',
  mediaType: 'video',
  fileSize: '42.8 MB',
  mimeType: 'video/mp4',
  duration: '00:01:45',
  fps: 30,
  resolution: '1920x1080',
  uploadedAt: '2026-09-19T14:32:00Z',
  processedAt: '2026-09-19T14:32:48Z',
  status: 'completed',
  result: 'manipulated',
  confidenceScore: 0.91,
  metadata: {
    cameraModel: 'Unknown / Stripped EXIF',
    encoding: 'H.264 / AAC',
    hashSHA256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    software: 'Modified with Neural Re-enactment Pipeline v2.4',
  },
  evidence: [
    {
      type: 'Spatial facial artifact',
      severity: 'high',
      description: 'Face boundary blending inconsistent with background lighting keyframes.',
      metricValue: '88.4% variance in high-frequency noise tensor',
    },
    {
      type: 'Temporal frame alignment',
      severity: 'high',
      description: 'Lip gesture movement lags behind audio formant transition by 140ms.',
      metricValue: '140ms acoustic-visual offset detected',
    },
    {
      type: 'Ocular micro-movement',
      severity: 'medium',
      description: 'Blink pattern displays abnormal inter-blink intervals (<0.8 seconds).',
      metricValue: 'Inter-blink anomaly index: 0.72',
    },
    {
      type: 'Audio spectral analysis',
      severity: 'low',
      description: 'Sub-bass frequencies (<80Hz) contain artificial high-harmonic repetition.',
      metricValue: 'Spectral centroid anomaly: 420Hz spike',
    }
  ],
  framesAnalyzed: 3150,
  flaggedFramesCount: 412,
  sampleHeatmaps: [
    { frameIndex: 120, timecode: '00:04.0', note: 'Boundary artifact on jawline' },
    { frameIndex: 450, timecode: '00:15.0', note: 'Spectral warping around eyes' },
    { frameIndex: 890, timecode: '00:29.6', note: 'Lip sync disparity spike' },
  ]
};

export const MOCK_REPORTS = [
  {
    id: 'rep-101',
    analysisId: 'ana-8901',
    fileName: 'RealLens_Forensic_Report_ana-8901.pdf',
    title: 'Executive Keynote Speech Verification Report',
    mediaType: 'video',
    result: 'manipulated',
    confidenceScore: 0.91,
    generatedAt: '2026-09-19T14:33:10Z',
    fileSize: '1.4 MB',
    author: 'Security Analyst Team',
  },
  {
    id: 'rep-102',
    analysisId: 'ana-8902',
    fileName: 'RealLens_Forensic_Report_ana-8902.pdf',
    title: 'Press Briefing Audio Authenticity Certificate',
    mediaType: 'audio',
    result: 'authentic',
    confidenceScore: 0.96,
    generatedAt: '2026-09-19T12:16:05Z',
    fileSize: '890 KB',
    author: 'Forensic System Autogen',
  },
  {
    id: 'rep-103',
    analysisId: 'ana-8903',
    fileName: 'RealLens_Forensic_Report_ana-8903.pdf',
    title: 'ID Document Scan Fornsics Audit',
    mediaType: 'image',
    result: 'authentic',
    confidenceScore: 0.94,
    generatedAt: '2026-09-19T10:49:00Z',
    fileSize: '1.1 MB',
    author: 'Forensic System Autogen',
  },
  {
    id: 'rep-104',
    analysisId: 'ana-8904',
    fileName: 'RealLens_Forensic_Report_ana-8904.pdf',
    title: 'Viral Social Interview Manipulation Findings',
    mediaType: 'video',
    result: 'manipulated',
    confidenceScore: 0.88,
    generatedAt: '2026-09-18T22:07:30Z',
    fileSize: '2.1 MB',
    author: 'Cyber Incident Response Unit',
  }
];

export const MOCK_USER_PROFILE = {
  id: 'usr-007',
  name: 'Alexander Vance',
  email: 'a.vance@cyber-forensics.org',
  role: 'Lead Forensic Investigator',
  organization: 'Digital Authenticity Taskforce',
  avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80',
  memberSince: 'January 2026',
  apiKey: 'rl_live_8f92a014e3b7c919024a1b8c',
  usageStats: {
    monthlyQuota: 500,
    usedThisMonth: 148,
    storageUsed: '14.2 GB',
    storageLimit: '100 GB',
  }
};
