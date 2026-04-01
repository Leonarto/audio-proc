<script lang="ts">
  import { cn } from '$utils/cn';

  export let className = '';
  export { className as class };
</script>

<section
  class={cn(
    'rounded-[1.4rem] border border-white/10 bg-white/[0.035] p-5 text-card-foreground shadow-[0_18px_40px_rgba(0,0,0,0.18)] backdrop-blur-xl',
    className
  )}
>
  <slot />
</section>
