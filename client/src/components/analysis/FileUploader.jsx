import React, { useState, useRef } from 'react';
import { UploadCloud, Image as ImageIcon, Video as VideoIcon, Mic as AudioIcon, FileCheck, AlertCircle } from 'lucide-react';
import Button from '../common/Button';

export default function FileUploader({
  onFileSelect,
  activeType = 'image', // 'image' | 'video' | 'audio'
  disabled = false,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const fileInputRef = useRef(null);

  // Accepted MIME types based on modality
  const acceptTypes = {
    image: 'image/jpeg,image/png,image/webp,image/gif',
    video: 'video/mp4,video/webm,video/quicktime,video/x-msvideo',
    audio: 'audio/wav,audio/mpeg,audio/mp3,audio/ogg,audio/flac',
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const validateAndProcessFile = (file) => {
    setErrorMsg(null);
    if (!file) return;

    // Check mime type category match
    const category = file.type.split('/')[0];
    if (activeType === 'image' && category !== 'image') {
      setErrorMsg(`Selected file is not an image (${file.type}). Please select a valid image file.`);
      return;
    }
    if (activeType === 'video' && category !== 'video') {
      setErrorMsg(`Selected file is not a video (${file.type}). Please select a valid video file.`);
      return;
    }
    if (activeType === 'audio' && category !== 'audio') {
      setErrorMsg(`Selected file is not an audio file (${file.type}). Please select a valid audio file.`);
      return;
    }

    // Check size limits (e.g. 200MB max)
    const maxSize = 200 * 1024 * 1024;
    if (file.size > maxSize) {
      setErrorMsg(`File size exceeds 200MB limit. Current size: ${(file.size / (1024 * 1024)).toFixed(1)}MB.`);
      return;
    }

    onFileSelect(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndProcessFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndProcessFile(e.target.files[0]);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all cursor-pointer select-none glass-card ${
          isDragging
            ? 'border-cyan-400 bg-cyan-950/40 shadow-2xl shadow-cyan-500/20 scale-[1.01]'
            : 'border-slate-800 hover:border-cyan-500/40 hover:bg-slate-900/60'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptTypes[activeType]}
          onChange={handleInputChange}
          disabled={disabled}
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 flex items-center justify-center shadow-lg shadow-cyan-500/10">
            {activeType === 'image' && <ImageIcon className="w-8 h-8 stroke-[1.8]" />}
            {activeType === 'video' && <VideoIcon className="w-8 h-8 stroke-[1.8]" />}
            {activeType === 'audio' && <AudioIcon className="w-8 h-8 stroke-[1.8]" />}
          </div>

          <div className="space-y-1">
            <h3 className="font-bold text-lg text-white font-['Outfit']">
              {isDragging ? 'Drop file here to analyze' : `Upload ${activeType.toUpperCase()} file for Analysis`}
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Drag and drop your file here, or browse local device storage
            </p>
          </div>

          <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-500">
            <span>Supported: {acceptTypes[activeType].replaceAll(',', ', ')}</span>
            <span>&bull;</span>
            <span>Max size: 200MB</span>
          </div>

          <Button
            variant="outline"
            size="sm"
            icon={UploadCloud}
            isDisabled={disabled}
            onClick={(e) => {
              e.stopPropagation();
              fileInputRef.current?.click();
            }}
          >
            Choose File
          </Button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}
