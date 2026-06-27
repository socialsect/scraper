import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-zinc-800 text-zinc-50 hover:bg-zinc-700',
        secondary:
          'border-transparent bg-zinc-900 text-zinc-300 hover:bg-zinc-800',
        destructive:
          'border-transparent bg-red-900/20 text-red-400 hover:bg-red-900/30',
        outline: 'text-zinc-300 border-zinc-700',
        success:
          'border-transparent bg-green-900/20 text-green-400 hover:bg-green-900/30',
        warning:
          'border-transparent bg-yellow-900/20 text-yellow-400 hover:bg-yellow-900/30',
        brand:
          'border-transparent bg-brand/20 text-brand-300 hover:bg-brand/30',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
