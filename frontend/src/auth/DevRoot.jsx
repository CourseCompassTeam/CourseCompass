// App root for local development when no Clerk key is set. Uses a fake
// signed-in user, so the chat can be built and tested without Clerk.

import { useMemo } from 'react';

import AppShell from '../components/AppShell.jsx';
import ChatContainer from '../components/ChatContainer.jsx';
import { DevAuthService } from '../services/authService.js';
import { ChatService } from '../services/chatService.js';

export default function DevRoot({ apiClient }) {
  const chatService = useMemo(
    () => new ChatService(apiClient, new DevAuthService()),
    [apiClient],
  );

  return (
    <AppShell badge="Dev mode">
      <ChatContainer chatService={chatService} />
    </AppShell>
  );
}
