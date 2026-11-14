import { realApi } from './client';
import { mockApi } from './mock';

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
export const api = USE_MOCK ? mockApi : realApi;
export { ApiError } from './types';
