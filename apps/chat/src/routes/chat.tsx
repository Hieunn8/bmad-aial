import { createFileRoute, redirect } from '@tanstack/react-router';
import { ChatAssistantConsole } from '../components/epic6/ChatAssistantConsole';
import { pageShell } from '../styles/shared';

export const Route = createFileRoute('/chat')({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated && context.auth.isReady) {
      throw redirect({ to: '/login' });
    }
  },
  component: ChatPage,
});

function ChatPage() {
  return (
    <div style={pageShell}>
      <ChatAssistantConsole />
    </div>
  );
}
