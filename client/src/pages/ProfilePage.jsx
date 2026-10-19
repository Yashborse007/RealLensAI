import React, { useState, useEffect } from 'react';
import { Mail, UserCheck, Calendar, Shield, LogOut } from 'lucide-react';
import { getUserProfile } from '../services/api';
import PageSkeleton from '../components/common/PageSkeleton';
import ErrorMessage from '../components/common/ErrorMessage';

export default function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchUser = async () => {
      setLoading(true);
      try {
        const data = await getUserProfile();
        setProfile(data);
      } catch (err) {
        setError(err?.message || 'Unable to load your profile.');
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, []);

  const getInitials = (name) => {
    if (!name) return 'U';
    return name
      .split(/\s+/)
      .map((part) => part[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
  };

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === 'Not available') return null;
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return null;
    }
  };

  if (loading) {
    return (
      <div className="profile-page-container">
        <div style={{ padding: '5rem 0', display: 'flex', justifyContent: 'center' }}>
          <PageSkeleton cards={1} rows={4} />
        </div>
      </div>
    );
  }

  const displayName = profile?.name || 'Account';
  const displayEmail = profile?.email || null;
  const displayRole = profile?.role || 'User';
  const memberSince = formatDate(profile?.memberSince);

  return (
    <div className="profile-page-container animate-fade-in">
      <style>{`
        .profile-page-container {
          max-width: 680px;
          margin: 0 auto;
          padding: 1rem;
        }

        /* ── Page Header ───────────────────────────────────── */
        .profile-header {
          margin-bottom: 2.5rem;
          padding-bottom: 1.5rem;
          border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        .profile-header h1 {
          font-size: clamp(1.5rem, 4vw, 2rem);
          font-weight: 800;
          color: #fff;
          font-family: 'Outfit', sans-serif;
          letter-spacing: -0.02em;
          margin: 0 0 0.35rem;
        }
        .profile-header p {
          color: #94a3b8;
          font-size: 0.875rem;
          margin: 0;
        }

        /* ── Card ──────────────────────────────────────────── */
        .profile-card {
          background: linear-gradient(145deg, rgba(15,23,42,0.95), rgba(15,23,42,0.80));
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 1.5rem;
          overflow: hidden;
          box-shadow: 0 20px 60px rgba(0,0,0,0.4), 0 0 0 1px rgba(6,182,212,0.05);
          transition: box-shadow 0.3s ease;
        }
        .profile-card:hover {
          box-shadow: 0 24px 70px rgba(0,0,0,0.5), 0 0 0 1px rgba(6,182,212,0.12);
        }

        /* ── Hero Banner ───────────────────────────────────── */
        .profile-banner {
          height: 7rem;
          background: linear-gradient(135deg, #0e7490 0%, #1e3a5f 40%, #0f172a 100%);
          position: relative;
        }
        .profile-banner::after {
          content: '';
          position: absolute;
          inset: 0;
          background: radial-gradient(ellipse at 30% 50%, rgba(6,182,212,0.25) 0%, transparent 70%);
        }

        /* ── Avatar ─────────────────────────────────────────── */
        .profile-avatar-wrap {
          display: flex;
          align-items: flex-end;
          gap: 1.25rem;
          padding: 0 2rem;
          margin-top: -2.5rem;
          position: relative;
          z-index: 1;
        }
        .profile-avatar {
          width: 5rem;
          height: 5rem;
          border-radius: 1.25rem;
          background: linear-gradient(135deg, #164e63, #0e7490);
          border: 3px solid rgba(15,23,42,1);
          display: flex;
          align-items: center;
          justify-content: center;
          font-family: 'Outfit', sans-serif;
          font-size: 1.5rem;
          font-weight: 800;
          color: #67e8f9;
          flex-shrink: 0;
          box-shadow: 0 8px 24px rgba(6,182,212,0.2);
        }
        .profile-avatar-info {
          padding-bottom: 0.5rem;
        }
        .profile-avatar-name {
          font-size: clamp(1.1rem, 3vw, 1.35rem);
          font-weight: 800;
          color: #f8fafc;
          font-family: 'Outfit', sans-serif;
          letter-spacing: -0.01em;
          line-height: 1.2;
          margin: 0 0 0.35rem;
        }
        .profile-role-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.2rem 0.65rem;
          border-radius: 999px;
          background: rgba(6,182,212,0.12);
          border: 1px solid rgba(6,182,212,0.25);
          color: #67e8f9;
          font-size: 0.68rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.12em;
        }

        /* ── Body ────────────────────────────────────────────── */
        .profile-body {
          padding: 1.75rem 2rem 2rem;
        }

        /* ── Info Rows ───────────────────────────────────────── */
        .profile-section-label {
          font-size: 0.65rem;
          font-weight: 700;
          color: #475569;
          text-transform: uppercase;
          letter-spacing: 0.18em;
          margin-bottom: 1rem;
        }
        .profile-info-grid {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }
        .profile-info-row {
          display: flex;
          align-items: center;
          gap: 0.875rem;
          padding: 0.875rem 1.125rem;
          border-radius: 0.875rem;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.05);
          transition: background 0.2s, border-color 0.2s;
        }
        .profile-info-row:hover {
          background: rgba(255,255,255,0.055);
          border-color: rgba(255,255,255,0.09);
        }
        .profile-info-icon {
          width: 2.25rem;
          height: 2.25rem;
          border-radius: 0.625rem;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .profile-info-icon.cyan {
          background: rgba(6,182,212,0.12);
          color: #22d3ee;
        }
        .profile-info-icon.violet {
          background: rgba(139,92,246,0.12);
          color: #a78bfa;
        }
        .profile-info-icon.emerald {
          background: rgba(16,185,129,0.12);
          color: #34d399;
        }
        .profile-info-label {
          font-size: 0.7rem;
          color: #64748b;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          margin-bottom: 0.15rem;
        }
        .profile-info-value {
          font-size: 0.9rem;
          color: #e2e8f0;
          font-weight: 500;
          word-break: break-all;
        }
        .profile-info-value.muted {
          color: #475569;
          font-style: italic;
        }

        /* ── Divider ─────────────────────────────────────────── */
        .profile-divider {
          border: none;
          border-top: 1px solid rgba(255,255,255,0.05);
          margin: 1.5rem 0;
        }

        /* ── Responsive ──────────────────────────────────────── */
        @media (max-width: 480px) {
          .profile-page-container { padding: 0.75rem; }
          .profile-body { padding: 1.25rem 1.25rem 1.5rem; }
          .profile-avatar-wrap { padding: 0 1.25rem; gap: 1rem; }
          .profile-avatar { width: 4.25rem; height: 4.25rem; font-size: 1.25rem; }
        }
      `}</style>

      {/* ── Page Title ── */}
      <div className="profile-header">
        <h1>My Profile</h1>
        <p>Your account details and session information.</p>
      </div>

      {error && (
        <ErrorMessage title="Profile unavailable" message={error} />
      )}

      {/* ── Profile Card ── */}
      <div className="profile-card">
        {/* Banner */}
        <div className="profile-banner" />

        {/* Avatar + Name row */}
        <div className="profile-avatar-wrap">
          <div className="profile-avatar">
            {getInitials(displayName)}
          </div>
          <div className="profile-avatar-info">
            <p className="profile-avatar-name">{displayName}</p>
            <span className="profile-role-badge">
              <Shield size={10} />
              {displayRole}
            </span>
          </div>
        </div>

        {/* Body */}
        <div className="profile-body">
          <p className="profile-section-label">Account details</p>

          <div className="profile-info-grid">
            {/* Email */}
            <div className="profile-info-row">
              <div className="profile-info-icon cyan">
                <Mail size={15} />
              </div>
              <div>
                <p className="profile-info-label">Email address</p>
                {displayEmail ? (
                  <p className="profile-info-value">{displayEmail}</p>
                ) : (
                  <p className="profile-info-value muted">Not set</p>
                )}
              </div>
            </div>

            {/* Name */}
            <div className="profile-info-row">
              <div className="profile-info-icon violet">
                <UserCheck size={15} />
              </div>
              <div>
                <p className="profile-info-label">Display name</p>
                <p className="profile-info-value">{displayName}</p>
              </div>
            </div>

            {/* Member since */}
            {memberSince && (
              <div className="profile-info-row">
                <div className="profile-info-icon emerald">
                  <Calendar size={15} />
                </div>
                <div>
                  <p className="profile-info-label">Member since</p>
                  <p className="profile-info-value">{memberSince}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
