import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import type {
  AuthTokens, LoginRequest, RegisterRequest, User,
  Subject, Exam, Question, Answer, ScoreOverride,
  StudentDashboard, TeacherDashboard, AdminDashboard,
} from '@/types';

/** Minimal shape of an API error (axios error with a FastAPI-style detail). */
export interface ApiErrorShape {
  response?: { status?: number; data?: { detail?: string } };
  message?: string;
}

export function asApiError(err: unknown): ApiErrorShape {
  return err as ApiErrorShape;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach token from Zustand persist storage
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem('auth-storage');
      if (stored) {
        const parsed = JSON.parse(stored);
        const token = parsed?.state?.token;
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
    } catch {}
  }
  return config;
});

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Skip redirect for login failures — the login page shows its own error.
      const url = error.config?.url || "";
      const isLoginRequest = url.includes("/auth/login");
      if (!isLoginRequest && typeof window !== "undefined") {
        localStorage.removeItem("auth-storage");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ---- Auth ----
export const authApi = {
  login: (data: LoginRequest) => api.post<AuthTokens>('/auth/login', data),
  register: (data: RegisterRequest) => api.post<User>('/auth/register', data),
  getMe: () => api.get<User>('/auth/me'),
  refreshToken: (refreshToken: string) => api.post<AuthTokens>('/auth/refresh', { refresh_token: refreshToken }),
};

// ---- Users (Admin) ----
export const usersApi = {
  getAll: (params?: { skip?: number; limit?: number; role?: string }) =>
    api.get<{ items: User[]; total: number; page: number; size: number; pages: number }>('/users', { params }),
  getById: (id: number) => api.get<User>(`/users/${id}`),
  create: (data: { name: string; email: string; password: string; role: string }) =>
    api.post<User>('/auth/register', data),
  update: (id: number, data: Partial<User>) => api.put<User>(`/users/${id}`, data),
  delete: (id: number) => api.delete(`/users/${id}`),
  activate: (id: number) => api.put<User>(`/users/${id}/activate`),
  bulkImport: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<{ created: number; skipped: number; errors: string[]; users: User[] }>('/users/bulk-import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ---- Subjects ----
export const subjectsApi = {
  getAll: (params?: { skip?: number; limit?: number }) =>
    api.get<{ items: Subject[]; total: number; page: number; size: number; pages: number }>('/subjects', { params }),
  getById: (id: number) => api.get<Subject>(`/subjects/${id}`),
  create: (data: { name: string; description: string; teacher_id?: number }) => api.post<Subject>('/subjects', data),
  update: (id: number, data: Partial<Subject>) => api.put<Subject>(`/subjects/${id}`, data),
  delete: (id: number) => api.delete(`/subjects/${id}`),
};

// ---- Teachers (for admin lookups) ----
export const teachersApi = {
  getAll: () => usersApi.getAll({ role: 'teacher', limit: 100 }),
};

// ---- Exams ----
export const examsApi = {
  getAll: (params?: { skip?: number; limit?: number; subject_id?: number }) =>
    api.get<{ items: Exam[]; total: number; page: number; size: number; pages: number }>('/exams', { params }),
  getById: (id: number) => api.get<Exam>(`/exams/${id}`),
  create: (data: { subject_id: number; title: string; description?: string; total_marks: number; time_limit_minutes: number; available_from?: string | null; available_until?: string | null }) =>
    api.post<Exam>('/exams', data),
  update: (id: number, data: Partial<Exam>) => api.put<Exam>(`/exams/${id}`, data),
  delete: (id: number) => api.delete(`/exams/${id}`),
};

// ---- Questions ----
export const questionsApi = {
  getAll: (params?: { exam_id?: number; skip?: number; limit?: number }) =>
    api.get<{ items: Question[]; total: number }>('/questions', { params }),
  getById: (id: number) => api.get<Question>(`/questions/${id}`),
  create: (data: { exam_id: number; question_text: string; model_answer: string; marks: number }) =>
    api.post<Question>('/questions', data),
  update: (id: number, data: Partial<Question>) => api.put<Question>(`/questions/${id}`, data),
  delete: (id: number) => api.delete(`/questions/${id}`),
};

// ---- Answers ----
export const answersApi = {
  submit: (data: { question_id: number; answer_text: string }) =>
    api.post<Answer>('/answers/submit', data),
  submitExam: (data: { answers: { question_id: number; answer_text: string }[] }) =>
    api.post<Answer[]>('/answers/submit-exam', data),
  getMyAnswers: (params?: { skip?: number; limit?: number }) =>
    api.get<{ items: Answer[]; total: number }>('/answers/my-answers', { params }),
  getQuestionAnswers: (questionId: number) =>
    api.get<{ items: Answer[] }>(`/answers/question/${questionId}`),
  getAllAnswers: (params?: { skip?: number; limit?: number; exam_id?: number }) =>
    api.get<{ items: Answer[]; total: number }>('/answers', { params }),
  overrideScore: (answerId: number, data: ScoreOverride) =>
    api.put<Answer>(`/answers/score/${answerId}/override`, data),
};

// ---- Dashboard ----
export const dashboardApi = {
  getStudent: () => api.get<StudentDashboard>('/dashboard/student'),
  getTeacher: () => api.get<TeacherDashboard>('/dashboard/teacher'),
  getAdmin: () => api.get<AdminDashboard>('/dashboard/admin'),
};

// ---- Export ----
export const exportApi = {
  exportResults: (examId: number) =>
    api.get(`/export/results/${examId}`, { responseType: 'blob' }),
  exportResultsXlsx: (examId: number) =>
    api.get(`/export/results/${examId}/xlsx`, { responseType: 'blob' }),
};

// ---- Settings ----
export const settingsApi = {
  getAll: () => api.get<Record<string, string>>('/settings'),
  get: (key: string) => api.get<{ key: string; value: string }>(`/settings/${key}`),
  update: (key: string, value: string) =>
    api.put<{ key: string; value: string }>(`/settings/${key}`, { value }),
  updateThresholds: (data: { plagiarism?: number; low_score?: number; pass_percentage?: number }) =>
    api.put<Record<string, string>>('/settings', data),
  updateWeights: (data: { keyword_weight?: number; similarity_weight?: number; grammar_weight?: number; completeness_weight?: number }) =>
    api.put<Record<string, string>>('/settings/weights', data),
  rescore: () =>
    api.post<{ rescored: number; errors: number; total: number; weights_used: Record<string, string> }>('/settings/rescore'),
};

export default api;
