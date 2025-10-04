declare module 'framer-motion' {
  import * as React from 'react';

  export interface MotionProps {
    initial?: any;
    animate?: any;
    exit?: any;
    transition?: any;
    whileHover?: any;
    whileTap?: any;
    variants?: any;
    custom?: any;
    onAnimationComplete?: () => void;
    className?: string;
    style?: React.CSSProperties;
    children?: React.ReactNode;
  }

  export const motion: {
    div: React.FC<MotionProps & React.HTMLAttributes<HTMLDivElement>>;
    button: React.FC<MotionProps & React.ButtonHTMLAttributes<HTMLButtonElement>>;
    span: React.FC<MotionProps & React.HTMLAttributes<HTMLSpanElement>>;
    p: React.FC<MotionProps & React.HTMLAttributes<HTMLParagraphElement>>;
    a: React.FC<MotionProps & React.AnchorHTMLAttributes<HTMLAnchorElement>>;
    [key: string]: any;
  };

  export interface AnimatePresenceProps {
    children: React.ReactNode;
    initial?: boolean;
    mode?: 'wait' | 'sync' | 'popLayout';
  }

  export const AnimatePresence: React.FC<AnimatePresenceProps>;
}

declare module 'remark-gfm';
declare module 'react-katex';
