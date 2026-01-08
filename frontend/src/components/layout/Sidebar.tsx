'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  TrendingUp,
  Radio,
  Settings,
  Shield,
  FileText,
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Performance', href: '/performance', icon: TrendingUp },
  { name: 'Signals', href: '/signals', icon: Radio },
  { name: 'Configuration', href: '/configuration', icon: Settings },
  { name: 'Risk', href: '/risk', icon: Shield },
  { name: 'Audit', href: '/audit', icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-surface border-r border-border flex flex-col">
      <div className="p-6 border-b border-border">
        <h1 className="text-xl font-bold tracking-tight text-accent-cyan">
          QUANTUM
        </h1>
        <p className="text-xs text-text-tertiary mt-1 font-mono">
          TERMINAL v2.0
        </p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`
                group flex items-center px-4 py-3 text-sm font-medium rounded-md
                transition-all duration-200
                ${
                  isActive
                    ? 'bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                }
              `}
            >
              <item.icon className="mr-3 h-5 w-5" strokeWidth={1.5} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="p-4 bg-app-bg rounded-lg border border-border">
          <div className="flex items-center justify-between text-xs">
            <span className="text-text-secondary">Status</span>
            <span className="text-profit font-mono">ONLINE</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
