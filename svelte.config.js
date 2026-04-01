import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      fallback: 'index.html'
    }),
    alias: {
      $ui: 'src/lib/components/ui',
      $api: 'src/lib/api',
      $stores: 'src/lib/stores',
      $utils: 'src/lib/utils',
      $desktop: 'src/lib/desktop'
    }
  }
};

export default config;
