import { loadEnv } from 'vite';
const env = loadEnv('development', '../../', '');
console.log(env.VITE_BASE_URL);
