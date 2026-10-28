// App root for local development when no Clerk key is set. Uses a fake
// signed-in user, so the chat can be built and tested without Clerk.

import { useMemo } from 'react';

import AppShell from '../components/AppShell.jsx';
import ChatContainer from '../components/ChatContainer.jsx';
import TranscriptUpload from '../components/transcript/TranscriptUpload.jsx';
import { config } from '../config.js';
import { DevAuthService } from '../services/authService.js';
import { ChatService } from '../services/chatService.js';
import { TranscriptService } from '../services/transcriptService.js';

export default function DevRoot({ apiClient }) {
  const { chatService, transcriptService } = useMemo(() => {
    const authService = new DevAuthService(config.devStudentId);
    return {
      chatService: new ChatService(apiClient, authService),
      transcriptService: new TranscriptService(apiClient, authService),
    };
  }, [apiClient]);

  return (
    <AppShell
      badge="Dev mode"
      actions={<TranscriptUpload transcriptService={transcriptService} />}
    >
      <ChatContainer chatService={chatService} />
    </AppShell>
  );
}
