<script lang="ts">
  import { cn } from '$utils/cn';

  export let value = '';
  export let className = '';
  export { className as class };
</script>

<input
  class={cn(
    'flex h-11 w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 py-2 text-sm text-foreground shadow-sm outline-none transition placeholder:text-muted-foreground focus-visible:border-primary/60 focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50',
    className
  )}
  bind:value
  on:input
  on:change
  on:keydown
  on:focus
  on:blur
  {...$$restProps}
/>
