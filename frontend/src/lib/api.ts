import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
        window.location.href = '/';
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  getLoginUrl: () => `${API_BASE}/auth/github/login`,
  logout: () => {
    localStorage.removeItem('auth_token');
  },
};

export const reposApi = {
  list: async () => {
    const { data } = await api.get('/repos');
    return data;
  },
  search: async (q: string) => {
    const { data } = await api.get('/repos/search', { params: { q } });
    return data;
  },
};

export const prsApi = {
  list: async (repo: string, topic?: string) => {
    const params: Record<string, string> = { repo };
    if (topic) params.topic = topic;
    const { data } = await api.get('/prs', { params });
    return data;
  },

  getTopics: async (repo: string) => {
    const { data } = await api.get('/prs/topics', { params: { repo } });
    return data;
  },

  getOne: async (prNumber: number, repo: string) => {
    const { data } = await api.get(`/prs/${prNumber}`, { params: { repo } });
    return data;
  },

  getStats: async (repo: string) => {
    const { data } = await api.get('/prs/stats', { params: { repo } });
    return data;
  },
};

export const analyzeApi = {
  trigger: async (repo: string) => {
    const { data } = await api.post('/analyze', { repo });
    return data;
  },

  getStatus: async (jobId: string) => {
    const { data } = await api.get(`/analyze/status/${jobId}`);
    return data;
  },
};

export const chatApi = {
  sendMessage: async (prNumber: number, repo: string, message: string, history: Array<{ role: string; content: string }>) => {
    const { data } = await api.post('/chat', {
      pr_number: prNumber,
      repo,
      message,
      history,
    });
    return data;
  },
};

export const criteriaApi = {
  ingest: async (repo?: string) => {
    const { data } = await api.post('/criteria/ingest', {
      repo: repo || 'rocketride-io/rocketride-server',
    });
    return data;
  },
  getStatus: async (jobId: string) => {
    const { data } = await api.get(`/criteria/status/${jobId}`);
    return data;
  },
};

export const reviewApi = {
  generate: async (prNumber: number, repo: string) => {
    const { data } = await api.post('/review/generate', {
      pr_number: prNumber,
      repo,
    });
    return data;
  },
  submit: async (
    prNumber: number,
    repo: string,
    body: string,
    event: string
  ) => {
    const { data } = await api.post('/review/submit', {
      pr_number: prNumber,
      repo,
      body,
      event,
    });
    return data;
  },
  history: async (prNumber: number, repo: string) => {
    const { data } = await api.get(`/review/history/${prNumber}`, {
      params: { repo },
    });
    return data;
  },
  closeDuplicate: async (
    prNumber: number,
    repo: string,
    primaryPR: number
  ) => {
    const { data } = await api.post('/review/close-duplicate', null, {
      params: { pr_number: prNumber, repo, primary_pr: primaryPR },
    });
    return data;
  },
};

export default api;
