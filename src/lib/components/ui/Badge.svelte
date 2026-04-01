<script lang="ts">
  import { cva, type VariantProps } from 'class-variance-authority';
  import { cn } from '$utils/cn';

  const badgeVariants = cva(
    'inline-flex items-center rounded-full border px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.18em]',
    {
      variants: {
        variant: {
          neutral: 'border-white/10 bg-white/[0.05] text-muted-foreground',
          success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
          warning: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
          danger: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
          accent: 'border-teal-400/30 bg-teal-400/10 text-teal-200'
        }
      },
      defaultVariants: {
        variant: 'neutral'
      }
    }
  );

  export let variant: VariantProps<typeof badgeVariants>['variant'] = 'neutral';
  export let className = '';
  export { className as class };
</script>

<span class={cn(badgeVariants({ variant }), className)}>
  <slot />
</span>
