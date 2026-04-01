<script lang="ts">
  export let value = 0;
</script>

<div class="h-2.5 w-full overflow-hidden rounded-full bg-white/[0.08]">
  <div
    class="h-full rounded-full bg-gradient-to-r from-primary via-amber-300 to-accent transition-all"
    style={`width: ${Math.min(Math.max(value, 0), 100)}%`}
  ></div>
</div>
