'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ChatProvider, useChat } from '@/context/ChatContext';
import Link from 'next/link';

function Sidebar() {
  const { user, logout } = useAuth();
  const { channels, dmConversations, allUsers, onlineUsers, createChannel, startDM, fetchChannels } = useChat();
  const pathname = usePathname();
  const router = useRouter();
  const [showCreateChannel, setShowCreateChannel] = useState(false);
  const [showNewDM, setShowNewDM] = useState(false);
  const [newChannelName, setNewChannelName] = useState('');
  const [newChannelDesc, setNewChannelDesc] = useState('');

  const handleCreateChannel = async (e) => {
    e.preventDefault();
    if (!newChannelName.trim()) return;
    try {
      const channel = await createChannel(newChannelName.trim(), newChannelDesc.trim());
      setShowCreateChannel(false);
      setNewChannelName('');
      setNewChannelDesc('');
      router.push(`/chat/${channel.id}`);
    } catch (err) {
      alert(err?.message || 'Failed to create channel');
    }
  };

  const handleStartDM = async (userId) => {
    try {
      const result = await startDM(userId);
      setShowNewDM(false);
      router.push(`/chat/${result.channel_id}`);
    } catch (err) {
      alert('Failed to start conversation');
    }
  };

  const getAvatarInitials = (name) => {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  };

  return (
    <div className="sidebar">
      {/* Sidebar Header */}
      <div className="sidebar-header">
        <h2>🚛 Hemut</h2>
      </div>

      {/* Sidebar Content */}
      <div className="sidebar-content">
        {/* Channels Section */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <span>Channels</span>
            <button onClick={() => setShowCreateChannel(true)} title="Create Channel">+</button>
          </div>

          {channels.map(channel => (
            <Link
              key={channel.id}
              href={`/chat/${channel.id}`}
              className={`channel-item ${pathname === `/chat/${channel.id}` ? 'active' : ''}`}
            >
              <span className="channel-icon">#</span>
              <span className="channel-name">{channel.name}</span>
              {channel.unread_count > 0 && (
                <span className="unread-badge">{channel.unread_count}</span>
              )}
            </Link>
          ))}
        </div>

        {/* DM Section */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <span>Direct Messages</span>
            <button onClick={() => setShowNewDM(true)} title="New Message">+</button>
          </div>

          {dmConversations.map(dm => (
            <Link
              key={dm.channel_id}
              href={`/chat/${dm.channel_id}`}
              className={`dm-item ${pathname === `/chat/${dm.channel_id}` ? 'active' : ''}`}
            >
              <div className="user-avatar small">
                <div className="avatar-circle">
                  {getAvatarInitials(dm.other_user?.display_name || dm.other_user?.username)}
                </div>
                <div className={`presence-dot ${dm.other_user?.status || 'offline'}`}></div>
              </div>
              <span className="channel-name">{dm.other_user?.display_name || dm.other_user?.username}</span>
              {dm.unread_count > 0 && (
                <span className="unread-badge">{dm.unread_count}</span>
              )}
            </Link>
          ))}
        </div>
      </div>

      {/* User Info */}
      <div className="sidebar-user">
        <div className="user-avatar">
          <div className="avatar-circle">
            {getAvatarInitials(user?.display_name || user?.username)}
          </div>
          <div className="presence-dot online"></div>
        </div>
        <div className="sidebar-user-info">
          <div className="username">{user?.display_name || user?.username}</div>
          <div className="status">● Online</div>
        </div>
        <button className="btn-icon" onClick={logout} title="Logout">
          ⏻
        </button>
      </div>

      {/* Create Channel Modal */}
      {showCreateChannel && (
        <div className="modal-overlay" onClick={() => setShowCreateChannel(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create a Channel</h3>
              <button className="btn-icon" onClick={() => setShowCreateChannel(false)}>✕</button>
            </div>
            <form onSubmit={handleCreateChannel}>
              <div className="form-group">
                <label>Channel Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. route-north"
                  value={newChannelName}
                  onChange={(e) => setNewChannelName(e.target.value)}
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>Description (optional)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="What's this channel about?"
                  value={newChannelDesc}
                  onChange={(e) => setNewChannelDesc(e.target.value)}
                />
              </div>
              <button type="submit" className="btn btn-primary">Create Channel</button>
            </form>
          </div>
        </div>
      )}

      {/* New DM Modal */}
      {showNewDM && (
        <div className="modal-overlay" onClick={() => setShowNewDM(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>New Direct Message</h3>
              <button className="btn-icon" onClick={() => setShowNewDM(false)}>✕</button>
            </div>
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {allUsers.map(u => (
                <div
                  key={u.id}
                  className="dm-item"
                  onClick={() => handleStartDM(u.id)}
                  style={{ borderRadius: 'var(--radius-md)', margin: '2px 0' }}
                >
                  <div className="user-avatar">
                    <div className="avatar-circle">
                      {getAvatarInitials(u.display_name || u.username)}
                    </div>
                    <div className={`presence-dot ${u.status || 'offline'}`}></div>
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{u.display_name || u.username}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>@{u.username}</div>
                  </div>
                </div>
              ))}
              {allUsers.length === 0 && (
                <div className="empty-state" style={{ padding: '20px' }}>
                  <p>No other users found. Invite teammates to get started!</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ChatLayout({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="loading-content">
          <div className="spinner"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <ChatProvider>
      <div className="chat-layout">
        <Sidebar />
        <div className="chat-main">
          {children}
        </div>
      </div>
    </ChatProvider>
  );
}
