import { type ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  color?: 'green' | 'yellow' | 'gray' | 'red' | 'blue' | 'gold' | 'purple';
  size?: 'sm' | 'md';
  icon?: ReactNode;
}

const colors = {
  green: 'bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300',
  yellow: 'bg-gold-100 text-gold-700 dark:bg-gold-900/40 dark:text-gold-300',
  gray: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  red: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  blue: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  gold: 'bg-gold-100 text-gold-700 dark:bg-gold-900/40 dark:text-gold-300',
  purple: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
};

export function Badge({ children, color = 'gray', size = 'sm', icon }: BadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-semibold ${size === 'sm' ? 'px-2.5 py-0.5 text-xs' : 'px-3 py-1 text-sm'} ${colors[color]}`}>
      {icon}
      {children}
    </span>
  );
}
