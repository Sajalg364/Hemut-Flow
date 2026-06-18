'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useChat } from '@/context/ChatContext';
import { xhrGet, xhrPost, xhrPut, xhrDelete } from '@/lib/xhr';
import { getAuthHeaders } from '@/lib/auth';
import { API_URL } from '@/lib/constants';

// Shipment Card Component
function ShipmentCard({ shipment }) {
  if (!shipment) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString('en-IN', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  };

  return (
    <div className="shipment-card">
      <div className="shipment-card-header">
        <span className="shipment-id">📦 {shipment.id}</span>
        <span className={`shipment-status ${shipment.status}`}>
          {shipment.status.replace('_', ' ')}
        </span>
      </div>
      <div className="shipment-route">
        <span>{shipment.origin}</span>
        <span className="arrow">→</span>
        <span>{shipment.destination}</span>
      </div>
      <div className="shipment-details">
        <div className="shipment-detail">
          <span className="label">Carrier</span>
          <span className="value">{shipment.carrier || 'N/A'}</span>
        </div>
        <div className="shipment-detail">
          <span className="label">ETA</span>
          <span className="value">{formatDate(shipment.eta)}</span>
        </div>
        <div className="shipment-detail">
          <span className="label">Weight</span>
          <span className="value">{shipment.weight_kg ? `${shipment.weight_kg} kg` : 'N/A'}</span>
        </div>
        <div className="shipment-detail">
          <span className="label">Items</span>
          <span className="value">{shipment.items_description || 'N/A'}</span>
        </div>
      </div>
    </div>
  );
}

// AI Summary Panel Component
function AISummaryPanel({ summary, loading: aiLoading }) {
  if (aiLoading) {
    return (
      <div className="ai-summary-panel">
        <div className="ai-summary-header">
          <span>🤖 AI Summary</span>
        </div>
        <div className="ai-loading">
          <div className="ai-dots">
            <span></span><span></span><span></span>
          </div>
          <span>Generating summary...</span>
        </div>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="ai-summary-panel">
      <div className="ai-summary-header">
        <span>🤖 AI Channel Summary</span>
      </div>
      <div className="ai-summary-content" dangerouslySetInnerHTML={{
        __html: summary
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\n/g, '<br/>')
      }} />
    </div>
  );
}

// Message Bubble Component
function MessageBubble({ message, isOwn }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const getAvatarInitials = (name) => {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  };

  const formatTime = (dateStr) => {
    return new Date(dateStr).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleEditSave = async () => {
    if (!editContent.trim() || editContent === message.content) {
      setIsEditing(false);
      return;
    }
    try {
      setIsSaving(true);
      await xhrPut(`${API_URL}/channels/${message.channel_id}/messages/${message.id}`, { content: editContent }, getAuthHeaders());
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to edit message', err);
      alert('Failed to edit message');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await xhrDelete(`${API_URL}/channels/${message.channel_id}/messages/${message.id}`, getAuthHeaders());
      setShowDeleteModal(false);
    } catch (err) {
      console.error('Failed to delete message', err);
      alert('Failed to delete message');
    } finally {
      setIsDeleting(false);
    }
  };

  const renderContent = () => {
    if (message.is_deleted) {
      return <div className="message-content"><p style={{ fontStyle: 'italic', color: 'var(--text-tertiary)' }}>This message was deleted.</p></div>;
    }

    if (isEditing) {
      return (
        <div className="message-content edit-mode" style={{ width: '100%', marginTop: '4px' }}>
          <textarea 
            value={editContent} 
            onChange={e => setEditContent(e.target.value)}
            style={{ width: '100%', minHeight: '60px', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontFamily: 'inherit', resize: 'vertical' }}
            disabled={isSaving}
          />
          <div style={{ display: 'flex', gap: '8px', marginTop: '8px', justifyContent: 'flex-end' }}>
            <button onClick={() => { setIsEditing(false); setEditContent(message.content); }} disabled={isSaving} className="btn-ghost" style={{ padding: '6px 16px', fontSize: '0.8rem', borderRadius: '4px' }}>Cancel</button>
            <button onClick={handleEditSave} disabled={isSaving} className="btn-primary" style={{ padding: '6px 16px', fontSize: '0.8rem', borderRadius: '4px', width: 'auto', minWidth: '70px', border: 'none', cursor: 'pointer' }}>{isSaving ? 'Saving' : 'Save'}</button>
          </div>
        </div>
      );
    }

    if (message.message_type === 'shipment' && message.metadata_json) {
      return (
        <>
          <div className="message-content"><p>{message.content}</p></div>
          <ShipmentCard shipment={message.metadata_json} />
        </>
      );
    }
    if (message.message_type === 'ai_summary') {
      return <AISummaryPanel summary={message.content} />;
    }
    if (message.message_type === 'system') {
      return <div className="system-message">{message.content}</div>;
    }
    return (
      <div className="message-content">
        <p>{message.content}</p>
      </div>
    );
  };

  if (message.message_type === 'system') {
    return <div className="system-message">{message.content}</div>;
  }

  return (
    <div className="message-group group" style={{ position: 'relative' }}>
      <div className="message-avatar">
        <div className="user-avatar">
          <div className="avatar-circle">
            {getAvatarInitials(message.sender_display_name || message.sender_username)}
          </div>
        </div>
      </div>
      <div className="message-body" style={{ width: '100%' }}>
        <div className="message-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="message-sender">
            {message.sender_display_name || message.sender_username}
          </span>
          <span className="message-time">{formatTime(message.created_at)}</span>
          {message.is_edited && !message.is_deleted && <span className="message-edited" style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>(edited)</span>}
          
          {/* Action Icons for Own Messages */}
          {isOwn && !message.is_deleted && !isEditing && (
            <div className="message-actions hidden-actions" style={{ display: 'flex', gap: '4px', marginLeft: 'auto', opacity: 0, transition: 'opacity 0.2s' }}>
              <button onClick={() => setIsEditing(true)} title="Edit Message" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)', padding: '2px' }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
              </button>
              <button onClick={() => setShowDeleteModal(true)} title="Delete Message" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--error-color)', padding: '2px' }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
              </button>
            </div>
          )}
        </div>
        {renderContent()}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="modal-overlay" onClick={() => setShowDeleteModal(false)} style={{ zIndex: 1000 }}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px' }}>
            <div className="modal-header">
              <h3>Delete Message</h3>
              <button className="btn-ghost" onClick={() => setShowDeleteModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem', color: 'var(--text-secondary)' }}>✕</button>
            </div>
            <div style={{ margin: '20px 0' }}>
              <p>Are you sure you want to delete this message?</p>
              <div style={{ marginTop: '12px', padding: '12px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '6px', fontSize: '0.9rem', color: 'var(--text-secondary)', fontStyle: 'italic', wordBreak: 'break-word' }}>
                "{message.content}"
              </div>
              <p style={{ marginTop: '12px', fontSize: '0.9rem', color: 'var(--text-tertiary)' }}>
                This action cannot be undone.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
                className="btn-ghost"
                style={{ padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--text-primary)' }}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                style={{ padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', backgroundColor: 'var(--error-color)', color: 'white', border: 'none' }}
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ChannelPage() {
  const { channelId } = useParams();
  const { user } = useAuth();
  const {
    messages, setMessages, fetchMessages, sendMessage,
    subscribeToChannel, sendTyping, typingUsers,
    channels, dmConversations, fetchChannels,
    setCurrentChannel, clearChannelUnread, leaveChannel,
  } = useChat();

  const router = useRouter();

  const [messageInput, setMessageInput] = useState('');
  const [channelInfo, setChannelInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);
  const [sending, setSending] = useState(false);
  const [aiSummary, setAiSummary] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [showLeaveModal, setShowLeaveModal] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [showCommandSuggestions, setShowCommandSuggestions] = useState(false);
  const [commandFilter, setCommandFilter] = useState('');
  const messagesEndRef = useRef(null);
  
  const COMMANDS = [
    { cmd: '/summarize', desc: 'Get an AI summary of this channel' },
    { cmd: '/shipment', desc: 'Lookup details for a shipment (e.g. /shipment SHIP-1042)' }
  ];
  const messagesContainerRef = useRef(null);
  const loadMoreRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  // Load channel info and messages
  useEffect(() => {
    const loadChannel = async () => {
      setLoading(true);
      setMessages([]);
      setAiSummary(null);

      // Track which channel is active for unread logic
      setCurrentChannel(channelId);

      try {
        // Get channel info
        const { data: chInfo } = await xhrGet(
          `${API_URL}/channels/${channelId}`,
          getAuthHeaders()
        );
        setChannelInfo(chInfo);

        // Get messages (also clears unread on backend)
        const data = await fetchMessages(channelId);
        setMessages(data.messages || []);
        setHasMore(data.has_more || false);

        // Clear unread badge in the sidebar immediately
        clearChannelUnread(channelId);

        // Subscribe to real-time updates
        subscribeToChannel(channelId);
      } catch (err) {
        console.error('Failed to load channel:', err);
      } finally {
        setLoading(false);
      }
    };

    if (channelId) loadChannel();

    // Cleanup: reset active channel when navigating away
    return () => {
      setCurrentChannel(null);
    };
  }, [channelId, fetchMessages, subscribeToChannel, setMessages, setCurrentChannel, clearChannelUnread]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Load more (older) messages with preserved scroll position
  const loadMore = useCallback(async () => {
    if (!hasMore || !messages.length) return;
    const oldest = messages[0]?.created_at;

    const container = messagesContainerRef.current;
    const previousScrollHeight = container ? container.scrollHeight : 0;

    const data = await fetchMessages(channelId, oldest);
    setMessages(prev => [...(data.messages || []), ...prev]);
    setHasMore(data.has_more || false);

    // Restore scroll position so view doesn't jump
    setTimeout(() => {
      if (container) {
        container.scrollTop = container.scrollHeight - previousScrollHeight;
      }
    }, 0);
  }, [hasMore, messages, channelId, fetchMessages, setMessages]);

  // Infinite scroll observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore) {
          loadMore();
        }
      },
      { threshold: 0.1 }
    );

    const currentRef = loadMoreRef.current;
    if (currentRef) observer.observe(currentRef);

    return () => {
      if (currentRef) observer.unobserve(currentRef);
    };
  }, [hasMore, loadMore]);

  const handleSend = async () => {
    if (!messageInput.trim()) return;

    const content = messageInput.trim();
    setMessageInput('');

    try {
      setSending(true);
      setShowCommandSuggestions(false);

      // Handle /shipment slash command
      const shipmentMatch = content.match(/^\/shipment\s+(\S+)/i);
      if (shipmentMatch) {
        const shipmentId = shipmentMatch[1];
        try {
          const { data: shipment } = await xhrGet(
            `${API_URL}/shipments/${shipmentId}`,
            getAuthHeaders()
          );
          await sendMessage(channelId, `Shipment lookup: ${shipmentId}`, 'shipment', shipment);
        } catch {
          await sendMessage(channelId, `⚠️ Shipment "${shipmentId}" not found. Try: SHIP-1001, SHIP-1002, SHIP-1042`, 'text');
        }
        setSending(false);
        return;
      }

      // Handle /summarize slash command
      if (content.match(/^\/summarize/i)) {
        setAiLoading(true);
        try {
          const hoursMatch = content.match(/(\d+)\s*h/i);
          const hours = hoursMatch ? parseInt(hoursMatch[1]) : 24;
          const { data } = await xhrPost(
            `${API_URL}/ai/summarize`,
            { channel_id: channelId, hours },
            getAuthHeaders()
          );
          setAiSummary(data.summary);
        } catch (err) {
          setAiSummary('⚠️ Failed to generate summary. Please try again.');
        } finally {
          setAiLoading(false);
        }
        setSending(false);
        return;
      }

      // Normal message
      await sendMessage(channelId, content);
    } catch (err) {
      console.error('Failed to send message:', err);
      setMessageInput(content); // Restore on failure
    } finally {
      setSending(false);
    }
  };

  // Handle keyboard
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Handle typing indicator
  const handleInputChange = (e) => {
    const val = e.target.value;
    setMessageInput(val);
    
    // Command suggestions
    if (val.startsWith('/')) {
      setShowCommandSuggestions(true);
      setCommandFilter(val.substring(1).toLowerCase());
    } else {
      setShowCommandSuggestions(false);
    }

    // Throttle typing indicator
    if (!typingTimeoutRef.current) {
      sendTyping(channelId);
      typingTimeoutRef.current = setTimeout(() => {
        typingTimeoutRef.current = null;
      }, 2000);
    }
  };

  // Get channel display name
  const getChannelDisplayName = () => {
    if (!channelInfo) return 'Loading...';
    if (channelInfo.is_dm) {
      const dm = dmConversations.find(d => d.channel_id === channelId);
      return dm?.other_user?.display_name || dm?.other_user?.username || 'Direct Message';
    }
    return `# ${channelInfo.name}`;
  };

  // Get typing indicator text
  const typingUser = typingUsers[channelId];
  const typingText = typingUser && typingUser.user_id !== user?.id
    ? `${typingUser.username} is typing...`
    : '';

  if (loading) {
    return (
      <div className="empty-state">
        <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3, borderTopColor: 'var(--accent-primary)' }}></div>
        <p style={{ marginTop: 16 }}>Loading messages...</p>
      </div>
    );
  }

  return (
    <>
      {/* Chat Header */}
      <div className="chat-header">
        <div className="chat-header-info">
          <h3>{getChannelDisplayName()}</h3>
          {channelInfo?.description && !channelInfo.is_dm && (
            <span className="channel-desc">| {channelInfo.description}</span>
          )}
        </div>
        <div className="chat-header-actions">
          {!channelInfo?.is_dm && (
            <>
              <button
                className="btn btn-ghost"
                style={{ fontSize: '0.8rem', color: 'var(--accent-danger)' }}
                onClick={() => setShowLeaveModal(true)}
                title="Leave Channel"
              >
                Leave
              </button>
              <button
              className="btn btn-ghost"
              onClick={async () => {
                setAiLoading(true);
                try {
                  const { data } = await xhrPost(
                    `${API_URL}/ai/summarize`,
                    { channel_id: channelId, hours: 24 },
                    getAuthHeaders()
                  );
                  setAiSummary(data.summary);
                } catch {
                  setAiSummary('⚠️ Failed to generate summary.');
                } finally {
                  setAiLoading(false);
                }
              }}
              title="Summarize channel (last 24h)"
              style={{ fontSize: '0.8rem' }}
            >
              🤖 Summarize
              </button>
            </>
          )}
        </div>
      </div>

      {/* AI Summary */}
      {(aiSummary || aiLoading) && (
        <div style={{ padding: '0 24px' }}>
          <AISummaryPanel summary={aiSummary} loading={aiLoading} />
          {aiSummary && (
            <button
              className="btn-ghost"
              onClick={() => setAiSummary(null)}
              style={{ fontSize: '0.75rem', marginBottom: 8, color: 'var(--text-tertiary)' }}
            >
              ✕ Dismiss summary
            </button>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="messages-container" ref={messagesContainerRef}>
        {/* Infinite Scroll trigger element */}
        <div ref={loadMoreRef} style={{ height: '10px', width: '100%' }} />

        {hasMore && (
          <button
            className="btn btn-ghost"
            onClick={loadMore}
            style={{ alignSelf: 'center', margin: '8px 0' }}
          >
            Load older messages
          </button>
        )}

        {messages.length === 0 && !loading && (
          <div className="empty-state">
            <div className="empty-state-icon">💬</div>
            <h3>No messages yet</h3>
            <p>Be the first to send a message in this channel!</p>
            <p style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
              Try: <code>/shipment SHIP-1042</code> or <code>/summarize</code>
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isOwn={msg.sender_id === user?.id}
          />
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Typing Indicator */}
      <div className="typing-indicator">
        {typingText && (
          <>
            <div className="typing-dots">
              <span></span><span></span><span></span>
            </div>
            <span>{typingText}</span>
          </>
        )}
      </div>

      {/* Message Input */}
      <div className="message-input-container" style={{ position: 'relative' }}>
        
        {/* Command Suggestions Popup */}
        {showCommandSuggestions && (
          <div className="command-suggestions" style={{
            position: 'absolute',
            bottom: '100%',
            left: 0,
            right: 0,
            backgroundColor: 'var(--bg-elevated)',
            border: '1px solid var(--border-default)',
            borderRadius: '8px 8px 0 0',
            marginBottom: '8px',
            boxShadow: 'var(--shadow-md)',
            zIndex: 10,
            maxHeight: '200px',
            overflowY: 'auto'
          }}>
            {COMMANDS.filter(c => c.cmd.toLowerCase().includes(commandFilter)).map((c) => (
              <div 
                key={c.cmd} 
                style={{ padding: '10px 16px', cursor: 'pointer', borderBottom: '1px solid var(--border-subtle)' }}
                onClick={() => {
                  setMessageInput(c.cmd + ' ');
                  setShowCommandSuggestions(false);
                  document.getElementById('message-input').focus();
                }}
                onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--bg-hover)'}
                onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <strong style={{ color: 'var(--accent-primary)' }}>{c.cmd}</strong> <span style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem', marginLeft: '8px' }}>{c.desc}</span>
              </div>
            ))}
            {COMMANDS.filter(c => c.cmd.toLowerCase().includes(commandFilter)).length === 0 && (
              <div style={{ padding: '10px 16px', color: 'var(--text-tertiary)', fontSize: '0.9rem' }}>
                No commands found
              </div>
            )}
          </div>
        )}

        <div className="message-input-wrapper">
          <textarea
            placeholder={`Message ${getChannelDisplayName()}... (try /shipment SHIP-1042 or /summarize)`}
            value={messageInput}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            id="message-input"
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!messageInput.trim() || sending}
            id="send-message-btn"
          >
            {sending ? '...' : '➤'}
          </button>
        </div>
      </div>

      {/* Leave Channel Confirmation Modal */}
      {showLeaveModal && (
        <div className="modal-overlay" onClick={() => setShowLeaveModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px' }}>
            <div className="modal-header">
              <h3>Leave Channel</h3>
              <button className="btn-ghost" onClick={() => setShowLeaveModal(false)}>✕</button>
            </div>
            <div style={{ margin: '20px 0' }}>
              <p>Are you sure you want to leave <strong>{getChannelDisplayName()}</strong>?</p>
              <p style={{ marginTop: '8px', fontSize: '0.9rem', color: 'var(--text-tertiary)' }}>
                You won't receive any more messages or alerts from this channel unless you rejoin.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                className="btn btn-ghost"
                onClick={() => setShowLeaveModal(false)}
                disabled={leaving}
              >
                Cancel
              </button>
              <button
                className="btn"
                style={{ backgroundColor: 'var(--accent-danger)', color: 'white' }}
                onClick={async () => {
                  setLeaving(true);
                  try {
                    await leaveChannel(channelId);
                    router.push('/chat');
                  } catch (err) {
                    alert('Failed to leave channel');
                    setLeaving(false);
                  }
                }}
                disabled={leaving}
              >
                {leaving ? 'Leaving...' : 'Leave Channel'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
