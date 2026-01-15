import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/layout/Sidebar';
import { WebSocketProvider } from '@/context/WebSocketContext';

export const metadata: Metadata = {
  title: 'Quantum Terminal | Algorithmic Trading Dashboard',
  description: 'Professional algorithmic trading dashboard with real-time analytics',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-terminal-bg text-terminal-text-primary antialiased">
        <WebSocketProvider>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-auto">
              {children}
            </main>
          </div>
        </WebSocketProvider>
      </body>
    </html>
  );
}
