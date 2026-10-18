import React, { useState, useEffect } from 'react';
import { 
  UserCheck, 
  Key, 
  Copy, 
  Check, 
  Building, 
  Mail, 
  HardDrive, 
} from 'lucide-react';

import Card from '../components/common/Card';
import Button from '../components/common/Button';
import PageSkeleton from '../components/common/PageSkeleton';
import ErrorMessage from '../components/common/ErrorMessage';
import SampleDataNotice from '../components/common/SampleDataNotice';
import { useToast } from '../context/ToastContext';
import { getUserProfile } from '../services/api';

export default function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copiedKey, setCopiedKey] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState(null);
  const [isSampleData, setIsSampleData] = useState(false);
  const { notify } = useToast();

  useEffect(() => {
    const fetchUser = async () => {
      setLoading(true);
      try {
        const data = await getUserProfile();
        setProfile(data);
        setIsSampleData(Boolean(data?.isSampleData));
        if (data?.apiKey) setApiKey(data.apiKey);
      } catch (err) {
        setError(err?.message || "Unable to load your profile.");
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, []);

  const handleCopyKey = async () => {
    try {
      await navigator.clipboard.writeText(apiKey);
      setCopiedKey(true);
      notify('API key copied to clipboard.', 'success');
      setTimeout(() => setCopiedKey(false), 2000);
    } catch {
      notify('Clipboard access was denied. Select and copy the key manually.', 'error');
    }
  };

  if (loading) {
    return (
      <div className="py-20 flex justify-center">
        <PageSkeleton cards={2} rows={3} />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in max-w-4xl mx-auto">
      
      {/* Header */}
      <div className="pb-4 border-b border-slate-800/80">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-['Outfit'] tracking-tight">
          Profile and API access
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Review your account details and any API credentials available to you.
        </p>
      </div>
      {error && <ErrorMessage title="Profile unavailable" message={error} />}
      {isSampleData && <SampleDataNotice />}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* User Info Card */}
        <Card hoverable={false} className="border-slate-800 md:col-span-1">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="w-20 h-20 rounded-2xl bg-cyan-950 text-cyan-400 flex items-center justify-center font-bold text-2xl border-2 border-cyan-500/40 shadow-xl shadow-cyan-500/10">
              {(profile?.name || "Account")
                .split(/\s+/)
                .map((part) => part[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </div>

            <div className="space-y-1">
              <h2 className="font-extrabold text-lg text-white font-['Outfit']">
              {profile?.name || "Account"}
              </h2>
              <span className="px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 text-[10px] font-bold uppercase tracking-wider">
                {profile?.role || "User"}
              </span>
            </div>

            <div className="w-full pt-4 border-t border-slate-800 space-y-3 text-xs text-slate-300 text-left">
              <div className="flex items-center space-x-2">
                <Building className="w-4 h-4 text-slate-500 shrink-0" />
                <span className="truncate">{profile?.organization || "Organization not set"}</span>
              </div>
              <div className="flex items-center space-x-2">
                <Mail className="w-4 h-4 text-slate-500 shrink-0" />
                <span className="truncate">{profile?.email || "Email unavailable"}</span>
              </div>
              <div className="flex items-center space-x-2">
                <UserCheck className="w-4 h-4 text-slate-500 shrink-0" />
                <span>Member since: {profile?.memberSince || "Not available"}</span>
              </div>
            </div>
          </div>
        </Card>

        {/* API Credentials & Usage */}
        <div className="md:col-span-2 space-y-6">
          
          {/* API Keys */}
          <Card
            title="REST API & SDK Keys"
            subtitle="Only keys issued by the service can authenticate API requests."
            icon={Key}
            className="border-slate-800"
          >
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="profile-api-key" className="text-xs font-semibold text-slate-700">API key</label>
                <div className="flex items-center space-x-2">
                  <input
                    id="profile-api-key"
                    type="text"
                    readOnly
                    value={apiKey || "No API key has been issued"}
                    className="flex-1 px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-cyan-300 focus:outline-none"
                  />
                  {apiKey && <button
                    type="button"
                    onClick={handleCopyKey}
                    className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 transition-colors"
                    title="Copy API key"
                    aria-label="Copy API key"
                  >
                    {copiedKey ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  </button>}
                </div>
              </div>

              <div className="flex justify-between items-center pt-2">
                <p className="text-xs text-slate-500">
                  {apiKey ? "Keep this key private. Never include it in client-side code." : "API key management is not available for this account."}
                </p>
              </div>
            </div>
          </Card>

          {/* Usage metrics */}
          <Card
            title="Usage"
            subtitle="Account usage details"
            icon={HardDrive}
            className="border-slate-800"
          >
            <p className="text-sm text-slate-500">
              Usage and storage metrics are not available for this account.
            </p>
          </Card>

        </div>

      </div>

    </div>
  );
}
