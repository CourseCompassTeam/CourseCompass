// Top-level component: uses Clerk sign-in when a publishable key is set,
// otherwise a dev-mode fake user.

import { ClerkProvider } from '@clerk/react';

import ClerkRoot from './auth/ClerkRoot.jsx';
import DevRoot from './auth/DevRoot.jsx';
import { config } from './config.js';
import { createApiClient } from './services/createApiClient.js';

const apiClient = createApiClient();

export default function App() {
  if (!config.clerkPublishableKey) {
    return <DevRoot apiClient={apiClient} />;
  }
  return (
    <ClerkProvider publishableKey={config.clerkPublishableKey}>
      <ClerkRoot apiClient={apiClient} />
    </ClerkProvider>
  );
}
