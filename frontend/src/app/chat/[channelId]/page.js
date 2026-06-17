'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useChat } from '@/context/ChatContext';
import { xhrGet, xhrPost } from '@/lib/xhr';
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

  const renderContent = () => {
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
    return <div className="message-content"><p>{message.content}</p></div>;
  };

  if (message.message_type === 'system') {
    return <div className="system-message">{message.content}</div>;
  }

  return (
    <div className="message-group">
      <div className="message-avatar">
        <div className="user-avatar">
          <div className="avatar-circle">
            {getAvatarInitials(message.sender_display_name || message.sender_username)}
          </div>
        </div>
      </div>
      <div className="message-body">
        <div className="message-header">
          <span className="message-sender">
            {message.sender_display_name || message.sender_username}
          </span>
          <span className="message-time">{formatTime(message.created_at)}</span>
        </div>
        {renderContent()}
      </div>
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
    setCurrentChannel, clearChannelUnread,
  } = useChat();

  const [messageInput, setMessageInput] = useState('');
  const [channelInfo, setChannelInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);
  const [sending, setSending] = useState(false);
  const [aiSummary, setAiSummary] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
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

  // Load more (older) messages
  const loadMore = async () => {
    if (!hasMore || !messages.length) return;
    const oldest = messages[0]?.created_at;
    const data = await fetchMessages(channelId, oldest);
    setMessages(prev => [...(data.messages || []), ...prev]);
    setHasMore(data.has_more || false);
  };

  // Handle message send
  const handleSend = async () => {
    const content = messageInput.trim();
    if (!content || sending) return;

    setSending(true);
    setMessageInput('');

    try {
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
    setMessageInput(e.target.value);
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
      <div className="message-input-container">
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
    </>
  );
}
