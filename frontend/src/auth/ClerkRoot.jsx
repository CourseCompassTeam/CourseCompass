// App root when a Clerk publishable key is configured.

import { useMemo } from 'react';
import { Show, SignInButton, UserButton, useAuth } from '@clerk/react';

import AppShell from '../components/AppShell.jsx';
import ChatContainer from '../components/ChatContainer.jsx';
import { ClerkAuthService } from '../services/authService.js';
import { ChatService } from '../services/chatService.js';

export default function ClerkRoot({ apiClient }) {
  return (
    <>
      <Show when="signed-out">
        <AppShell>
          <div className="sign-in">
            <h1>Plan your degree with confidence</h1>
            <p>
              Sign in to check your progress, explore courses, and get
              answers any time.
            </p>
            <SignInButton mode="modal">
              <button type="button" className="button">Sign in</button>
            </SignInButton>
          </div>
        </AppShell>
      </Show>
      <Show when="signed-in">
        <SignedInChat apiClient={apiClient} />
      </Show>
    </>
  );
}

function SignedInChat({ apiClient }) {
  const { getToken, userId } = useAuth();
  const chatService = useMemo(
    () => new ChatService(apiClient, new ClerkAuthService({ getToken, userId })),
    [apiClient, getToken, userId],
  );

  return (
    <AppShell userMenu={<UserButton />}>
      <ChatContainer chatService={chatService} />
    </AppShell>
  );
}
