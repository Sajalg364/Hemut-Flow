'use client';

export default function ChatDefaultPage() {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">💬</div>
      <h3 style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <img src="/logo.jpg" alt="Hemut Logo" style={{ width: '32px', height: '32px', borderRadius: '4px', marginRight: '12px' }} />
        Welcome to Hemut
      </h3>
      <p>Select a channel or start a direct message to begin collaborating with your logistics team.</p>
    </div>
  );
}
