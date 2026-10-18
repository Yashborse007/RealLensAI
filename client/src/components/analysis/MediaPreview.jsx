import React, { useState, useEffect } from 'react';
import { 
  File, 
  Trash2, 
  Play, 
  Pause, 
  Image as ImageIcon, 
  Video as VideoIcon, 
  Mic as AudioIcon,
  Sparkles,
  Info
} from 'lucide-react';
import Button from '../common/Button';

export default function MediaPreview({
  file,
  mediaType, // 'image' | 'video' | 'audio'
  onRemove,
  onAnalyze,
  isAnalyzing = false,
}) {
  const [previewUrl, setPreviewUrl] = useState(null);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }

    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file]);

  if (!file) return null;

  const fileSizeFormatted = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;

  return (
    <div className="glass-card rounded-2xl p-6 space-y-6 animate-fade-in border border-cyan-500/30">
      
      {/* File Metadata Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="p-3 rounded-xl bg-cyan-950 text-cyan-400 border border-cyan-800/60">
            {mediaType === 'image' && <ImageIcon className="w-6 h-6" />}
            {mediaType === 'video' && <VideoIcon className="w-6 h-6" />}
            {mediaType === 'audio' && <AudioIcon className="w-6 h-6" />}
          </div>
          <div>
            <h4 className="font-bold text-base text-white font-['Outfit'] truncate max-w-xs sm:max-w-md">
              {file.name}
            </h4>
            <div className="flex items-center space-x-3 text-xs text-slate-400 mt-0.5 font-mono">
              <span>Size: {fileSizeFormatted}</span>
              <span>&bull;</span>
              <span className="uppercase text-cyan-400">{mediaType}</span>
              <span>&bull;</span>
              <span>{file.type || 'Standard Format'}</span>
            </div>
          </div>
        </div>

        <button
          onClick={onRemove}
          disabled={isAnalyzing}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-400 hover:text-rose-300 hover:bg-rose-950/60 border border-rose-900/60 transition-colors self-start sm:self-center disabled:opacity-50"
        >
          <Trash2 className="w-4 h-4" />
          <span>Remove File</span>
        </button>
      </div>

      {/* Media Preview Box */}
      <div className="relative rounded-xl overflow-hidden bg-slate-950/90 border border-slate-800 flex items-center justify-center min-h-[220px] max-h-[420px]">
        
        {mediaType === 'image' && previewUrl && (
          <img
            src={previewUrl}
            alt="Uploaded forensic media preview"
            className="max-h-[380px] w-auto object-contain rounded-lg shadow-xl"
          />
        )}

        {mediaType === 'video' && previewUrl && (
          <video
            src={previewUrl}
            controls
            className="max-h-[380px] w-full rounded-lg shadow-xl"
          >
            Your browser does not support HTML5 video preview.
          </video>
        )}

        {mediaType === 'audio' && previewUrl && (
          <div className="w-full p-8 text-center space-y-6">
            <div className="w-16 h-16 mx-auto rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800/60 flex items-center justify-center">
              <AudioIcon className="w-8 h-8 animate-pulse" />
            </div>
            
            {/* Waveform Visualization Placeholder */}
            <div className="h-16 flex items-center justify-center space-x-1 px-4">
              {[40, 70, 30, 85, 95, 60, 40, 80, 100, 45, 65, 90, 35, 50, 75, 60, 85, 40].map((h, i) => (
                <div
                  key={i}
                  style={{ height: `${h}%` }}
                  className="w-1.5 rounded-full bg-cyan-500/60 transition-all duration-300"
                />
              ))}
            </div>

            <audio src={previewUrl} controls className="w-full max-w-md mx-auto" />
          </div>
        )}

      </div>

      {/* Action Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
        <div className="flex items-center space-x-2 text-xs text-slate-400">
          <Info className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>Ready to pass through PyTorch spatial & temporal neural models.</span>
        </div>

        <Button
          variant="primary"
          size="lg"
          isLoading={isAnalyzing}
          onClick={onAnalyze}
          icon={Sparkles}
          className="w-full sm:w-auto"
        >
          {isAnalyzing ? 'Analyzing Tensors...' : 'Analyze Media Authenticity'}
        </Button>
      </div>

    </div>
  );
}
