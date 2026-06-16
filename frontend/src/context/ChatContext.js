'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getToken, getAuthHeaders } from '@/lib/auth';
import { xhrGet, xhrPost } from '@/lib/xhr';
import { API_URL, WS_BASE_URL } from '@/lib/constants';
import { useAuth } from './AuthContext';

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const { user, isAuthenticated } = useAuth();
  const [channels, setChannels] = useState([]);
  const [dmConversations, setDmConversations] = useState([]);
  const [currentChannel, setCurrentChannel] = useState(null);
  const [messages, setMessages] = useState([]);
  const [onlineUsers, setOnlineUsers] = useState(new Set());
  const [typingUsers, setTypingUsers] = useState({});
  const [allUsers, setAllUsers] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatRef = useRef(null);
  const subscribedChannelsRef = useRef(new Set());

  // Fetch channels
  const fetchChannels = useCallback(async () => {
    try {
      const { data } = await xhrGet(`${API_URL}/channels/`, getAuthHeaders());
      setChannels(data);
    } catch (err) {
      console.error('Failed to fetch channels:', err);
    }
  }, []);

  // Fetch DM conversations
  const fetchDMConversations = useCallback(async () => {
    try {
      const { data } = await xhrGet(`${API_URL}/dm/conversations`, getAuthHeaders());
      setDmConversations(data);
    } catch (err) {
      console.error('Failed to fetch DM conversations:', err);
    }
  }, []);

  // Fetch all users
  const fetchUsers = useCallback(async () => {
    try {
      const { data } = await xhrGet(`${API_URL}/users/`, getAuthHeaders());
      setAllUsers(data);
    } catch (err) {
      console.error('Failed to fetch users:', err);
    }
  }, []);

  // Fetch messages for a channel
  const fetchMessages = useCallback(async (channelId, before = null) => {
    try {
      let url = `${API_URL}/channels/${channelId}/messages?limit=50`;
      if (before) url += `&before=${encodeURIComponent(before)}`;
      const { data } = await xhrGet(url, getAuthHeaders());
      return data;
    } catch (err) {
      console.error('Failed to fetch messages:', err);
      return { messages: [], has_more: false };
    }
  }, []);

  // Send a message
  const sendMessage = useCallback(async (channelId, content, messageType = 'text', metadataJson = null) => {
    try {
      const { data } = await xhrPost(
        `${API_URL}/channels/${channelId}/messages`,
        { content, message_type: messageType, metadata_json: metadataJson },
        getAuthHeaders()
      );
      return data;
    } catch (err) {
      console.error('Failed to send message:', err);
      throw err;
    }
  }, []);

  // Create a channel
  const createChannel = useCallback(async (name, description = '') => {
    try {
      const { data } = await xhrPost(
        `${API_URL}/channels/`,
        { name, description },
        getAuthHeaders()
      );
      await fetchChannels();
      return data;
    } catch (err) {
      throw err;
    }
  }, [fetchChannels]);

  // Join a channel
  const joinChannel = useCallback(async (channelId) => {
    try {
      await xhrPost(`${API_URL}/channels/${channelId}/join`, {}, getAuthHeaders());
      await fetchChannels();
    } catch (err) {
      console.error('Failed to join channel:', err);
    }
  }, [fetchChannels]);

  // Start/Get DM
  const startDM = useCallback(async (targetUserId) => {
    try {
      const { data } = await xhrPost(`${API_URL}/dm/${targetUserId}`, {}, getAuthHeaders());
      await fetchDMConversations();
      return data;
    } catch (err) {
      console.error('Failed to start DM:', err);
      throw err;
    }
  }, [fetchDMConversations]);

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    const token = getToken();
    if (!token || !isAuthenticated) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE_URL}/ws?token=${token}`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      wsRef.current = ws;

      // Re-subscribe to all channels
      subscribedChannelsRef.current.forEach(channelId => {
        ws.send(JSON.stringify({ type: 'subscribe_channel', channel_id: channelId }));
      });

      // Start heartbeat
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'heartbeat' }));
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        handleWSMessage(message);
      } catch (err) {
        console.error('Failed to parse WS message:', err);
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code);
      wsRef.current = null;
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);

      // Auto-reconnect with exponential backoff
      if (isAuthenticated && event.code !== 4001) {
        const delay = Math.min(1000 * Math.pow(2, Math.random() * 3), 10000);
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, delay);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, [isAuthenticated]);

  // Handle incoming WebSocket messages
  const handleWSMessage = useCallback((message) => {
    switch (message.type) {
      case 'new_message':
        const msgData = message.data;
        setMessages(prev => {
          // Prevent duplicates
          if (prev.some(m => m.id === msgData.id)) return prev;
          return [...prev, msgData];
        });
        // Update unread counts in channels
        setChannels(prev => prev.map(ch => {
          if (ch.id === msgData.channel_id) {
            return { ...ch, unread_count: (ch.unread_count || 0) + 1 };
          }
          return ch;
        }));
        break;

      case 'presence_update':
        const presenceData = message.data;
        setOnlineUsers(prev => {
          const next = new Set(prev);
          if (presenceData.status === 'online') {
            next.add(presenceData.user_id);
          } else {
            next.delete(presenceData.user_id);
          }
          return next;
        });
        // Update allUsers status
        setAllUsers(prev => prev.map(u => {
          if (u.id === presenceData.user_id) {
            return { ...u, status: presenceData.status };
          }
          return u;
        }));
        break;

      case 'typing_indicator':
        const typingData = message.data;
        setTypingUsers(prev => ({
          ...prev,
          [typingData.channel_id]: {
            user_id: typingData.user_id,
            username: typingData.username,
            timestamp: Date.now(),
          }
        }));
        // Clear typing after 3 seconds
        setTimeout(() => {
          setTypingUsers(prev => {
            const next = { ...prev };
            if (next[typingData.channel_id]?.user_id === typingData.user_id) {
              delete next[typingData.channel_id];
            }
            return next;
          });
        }, 3000);
        break;

      case 'heartbeat_ack':
        break;

      default:
        console.log('Unknown WS message type:', message.type);
    }
  }, []);

  // Subscribe to a channel's real-time updates
  const subscribeToChannel = useCallback((channelId) => {
    subscribedChannelsRef.current.add(channelId);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe_channel',
        channel_id: channelId,
      }));
    }
  }, []);

  // Send typing indicator
  const sendTyping = useCallback((channelId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'typing',
        channel_id: channelId,
      }));
    }
  }, []);

  // Initialize on auth
  useEffect(() => {
    if (isAuthenticated) {
      fetchChannels();
      fetchDMConversations();
      fetchUsers();
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
    };
  }, [isAuthenticated, fetchChannels, fetchDMConversations, fetchUsers, connectWebSocket]);

  const value = {
    channels,
    dmConversations,
    currentChannel,
    setCurrentChannel,
    messages,
    setMessages,
    onlineUsers,
    typingUsers,
    allUsers,
    fetchChannels,
    fetchDMConversations,
    fetchMessages,
    sendMessage,
    createChannel,
    joinChannel,
    startDM,
    subscribeToChannel,
    sendTyping,
    fetchUsers,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}
