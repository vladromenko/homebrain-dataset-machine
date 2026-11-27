import {defineConfig} from 'vite';
import wasm from 'vite-plugin-wasm';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import {fileURLToPath, URL} from 'node:url';
export default defineConfig({plugins:[react(),tailwindcss(),wasm()],base:'/lab-assets/',resolve:{alias:{'@':fileURLToPath(new URL('./src',import.meta.url))}},build:{target:'esnext',outDir:'../homebrain/static/lab',emptyOutDir:true},server:{proxy:{'/api':'http://127.0.0.1:8096'}}});
