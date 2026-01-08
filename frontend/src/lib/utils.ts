import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, parseISO } from 'date-fns';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export function formatTime(timestamp: string): string {
  try {
    return format(parseISO(timestamp), 'HH:mm:ss');
  } catch {
    return '--:--:--';
  }
}

export function formatDateTime(timestamp: string): string {
  try {
    return format(parseISO(timestamp), 'MMM dd, HH:mm:ss');
  } catch {
    return 'Invalid Date';
  }
}
