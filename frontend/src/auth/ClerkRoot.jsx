// App root when a Clerk publishable key is configured.

import { useMemo } from 'react';
import {
  ClerkFailed,
  ClerkLoaded,
  ClerkLoading,
  Show,
  SignInButton,
  UserButton,
  useAuth,
} from '@clerk/react';

import AppShell from '../components/AppShell.jsx';
import ChatContainer from '../components/ChatContainer.jsx';
import { ClerkAuthService } from '../services/authService.js';
import { ChatService } from '../services/chatService.js';

export default function ClerkRoot({ apiClient }) {
  return (
    <>
      <ClerkLoading>
        <AppShell>
          <p className="status-page" role="status">Loading…</p>
        </AppShell>
      </ClerkLoading>
      <ClerkFailed>
        <AppShell>
          <div className="status-page" role="alert">
            <h1>Sign-in is unavailable</h1>
            <p>We couldn't reach the sign-in service. Please try again later.</p>
          </div>
        </AppShell>
      </ClerkFailed>
      <ClerkLoaded>
        <Show when="signed-out">
          <SignInScreen />
        </Show>
        <Show when="signed-in">
          <SignedInChat apiClient={apiClient} />
        </Show>
      </ClerkLoaded>
    </>
  );
}

function SignInScreen() {
  return (
    <AppShell>
      <div className="status-page">
        <h1>Plan your degree with confidence</h1>
        <p>
          Sign in to check your progress, explore courses, and get answers
          any time.
        </p>
        <SignInButton mode="modal">
          <button type="button" className="button">Sign in</button>
        </SignInButton>
      </div>
    </AppShell>
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
