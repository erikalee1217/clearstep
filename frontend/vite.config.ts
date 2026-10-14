import { defineConfig } from 'vite';

export default defineConfig({ server: { proxy: { '/rank': 'http://127.0.0.1:8000', '/extract': 'http://127.0.0.1:8000' } } });
