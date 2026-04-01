<script lang="ts">
  import { cva, type VariantProps } from 'class-variance-authority';
  import { cn } from '$utils/cn';

  const buttonVariants = cva(
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl border text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-0 disabled:pointer-events-none disabled:opacity-50',
    {
      variants: {
        variant: {
          default:
            'border-primary/70 bg-primary text-primary-foreground shadow-[0_10px_24px_rgba(249,115,22,0.24)] hover:-translate-y-0.5 hover:bg-primary/95',
          secondary:
            'border-white/10 bg-white/[0.04] text-foreground hover:border-white/20 hover:bg-white/[0.08]',
          ghost: 'border-transparent bg-transparent text-muted-foreground hover:bg-white/[0.06] hover:text-foreground',
          destructive: 'border-destructive/60 bg-destructive text-destructive-foreground hover:bg-destructive/90'
        },
        size: {
          sm: 'h-9 px-3.5',
          default: 'h-11 px-4.5',
          lg: 'h-12 px-5.5'
        }
      },
      defaultVariants: {
        variant: 'default',
        size: 'default'
      }
    }
  );

  export let variant: VariantProps<typeof buttonVariants>['variant'] = 'default';
  export let size: VariantProps<typeof buttonVariants>['size'] = 'default';
  export let className = '';
  export { className as class };
</script>

<button class={cn(buttonVariants({ variant, size }), className)} on:click on:keydown {...$$restProps}>
  <slot />
</button>
