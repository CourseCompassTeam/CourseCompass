// App root for local development when no Clerk key is set. Uses a fake
// signed-in user, so the chat can be built and tested without Clerk.

import { useMemo } from 'react';

import AppShell from '../components/AppShell.jsx';
import ChatContainer from '../components/ChatContainer.jsx';
import { ScheduleButton } from '../components/schedule/ScheduleDialog.jsx';
import TranscriptUploadProvider, {
  TranscriptUploadButton,
} from '../components/transcript/TranscriptUpload.jsx';
import { config } from '../config.js';
import { DevAuthService } from '../services/authService.js';
import { ChatService } from '../services/chatService.js';
import { ScheduleService } from '../services/scheduleService.js';
import { TranscriptService } from '../services/transcriptService.js';

export default function DevRoot({ apiClient }) {
  const { chatService, scheduleService, transcriptService } = useMemo(() => {
    const authService = new DevAuthService(config.devStudentId);
    return {
      chatService: new ChatService(apiClient, authService),
      scheduleService: new ScheduleService(apiClient, authService),
      transcriptService: new TranscriptService(apiClient, authService),
    };
  }, [apiClient]);

  return (
    <TranscriptUploadProvider transcriptService={transcriptService}>
      <AppShell
        badge="Dev mode"
        actions={(
          <>
            <ScheduleButton scheduleService={scheduleService} />
            <TranscriptUploadButton />
          </>
        )}
      >
        <ChatContainer chatService={chatService} />
      </AppShell>
    </TranscriptUploadProvider>
  );
}
