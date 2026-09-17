import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/store/authStore';
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

/**
 * The single paginated envelope every list endpoint returns
 * (backend `app.utils.pagination.PaginatedResponse`).
 */
export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/** Query params accepted by the paginated list endpoints. `limit` is an alias of `size`. */
export interface PaginationParams {
  page?: number;
  size?: number;
  limit?: number;
  skip?: number;
}

/** The largest page the backend will serve, and the page size we page with. */
export const MAX_PAGE_SIZE = 100;

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

/**
 * Origin of the backend (`NEXT_PUBLIC_API_URL` without its trailing `/api`).
 * Used for routes that are not mounted under the `/api` client base, e.g. the
 * authenticated uploaded-file route.
 */
export const API_ORIGIN = (() => {
  const raw = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').trim();
  const origin = raw.replace(/\/+$/, '').replace(/\/api$/, '');
  return origin || 'http://localhost:8000';
})();

/**
 * Build a browser-usable URL for a stored upload (e.g. `User.profile_photo`).
 *
 * Uploads are no longer served from the public `/uploads/...` static path; the
 * backend now serves them from `${API_ORIGIN}/api/files/<filename>` and requires
 * the JWT. Plain `<img src>` requests cannot send headers, so the access token is
 * appended as `?token=`.
 *
 * Accepts legacy paths (`/uploads/x.png`), current paths (`/api/files/x.png`), a
 * bare filename, or an absolute URL (which is left untouched).
 */
export function fileUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  const value = path.trim();
  if (!value) return undefined;

  // Inline data / blob URLs need no rewriting.
  if (/^(data:|blob:)/i.test(value)) return value;

  const legacy = value.match(/\/uploads\/([^?#]+)/);
  const files = value.match(/\/api\/files\/([^?#]+)/);
  let filename: string | null = null;
  if (legacy) filename = legacy[1];
  else if (files) filename = files[1];
  else if (/^https?:\/\//i.test(value)) return value; // a remote URL we do not own
  else filename = value.replace(/^\/+/, '');
  filename = filename.replace(/^\/+/, '');

  if (!filename) return value;

  const url = `${API_ORIGIN}/api/files/${filename}`;
  const token = typeof window !== 'undefined' ? useAuthStore.getState().token : null;
  return token ? `${url}?token=${encodeURIComponent(token)}` : url;
}

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach the token held by the Zustand auth store
// (persisted under `auth-storage`, but read through the store so the in-memory
// value and the persisted value can never drift apart).
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().token;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
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

/**
 * Walk every page of a role-scoped list endpoint in chunks of `size`
 * (backend max 100) and collect the items, stopping as soon as a page comes
 * back short. Used only by views that genuinely aggregate over the whole set;
 * prefer a targeted `exam_id` / `question_id` / `student_id` filter.
 *
 * `maxPages` bounds the loop so a bug can never hammer the backend.
 */
export async function fetchAllPages<T>(
  fetchPage: (page: number, size: number) => Promise<{ data: Paginated<T> }>,
  size: number = MAX_PAGE_SIZE,
  maxPages = 50
): Promise<{ items: T[]; truncated: boolean }> {
  const items: T[] = [];
  for (let page = 1; page <= maxPages; page++) {
    const res = await fetchPage(page, size);
    const batch = res.data.items ?? [];
    items.push(...batch);
    if (batch.length < size) return { items, truncated: false };
    if (page === maxPages) return { items, truncated: true };
  }
  return { items, truncated: false };
}

// ---- Auth ----
export const authApi = {
  login: (data: LoginRequest) => api.post<AuthTokens>('/auth/login', data),
  register: (data: RegisterRequest) => api.post<User>('/auth/register', data),
  getMe: () => api.get<User>('/auth/me'),
  refreshToken: (refreshToken: string) => api.post<AuthTokens>('/auth/refresh', { refresh_token: refreshToken }),
};

// ---- Users (Admin) ----
export const usersApi = {
  getAll: (params?: PaginationParams & { role?: string }) =>
    api.get<Paginated<User>>('/users', { params }),
  getById: (id: number) => api.get<User>(`/users/${id}`),
  create: (data: { name: string; email: string; password: string; role: string }) =>
    api.post<User>('/auth/register', data),
  update: (id: number, data: Partial<User>) => api.put<User>(`/users/${id}`, data),
  delete: (id: number) => api.delete(`/users/${id}`),
  activate: (id: number) => api.put<User>(`/users/${id}/activate`),
  unlock: (id: number) => api.post<User>(`/users/${id}/unlock`),
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
  getAll: (params?: PaginationParams) =>
    api.get<Paginated<Subject>>('/subjects', { params }),
  getById: (id: number) => api.get<Subject>(`/subjects/${id}`),
  create: (data: { name: string; description: string; teacher_id?: number }) => api.post<Subject>('/subjects', data),
  update: (id: number, data: Partial<Subject>) => api.put<Subject>(`/subjects/${id}`, data),
  delete: (id: number) => api.delete(`/subjects/${id}`),
};

// ---- Teachers (for admin lookups) ----
export const teachersApi = {
  getAll: () => usersApi.getAll({ role: 'teacher', size: MAX_PAGE_SIZE }),
};

// ---- Exams ----
export const examsApi = {
  getAll: (params?: PaginationParams & { subject_id?: number }) =>
    api.get<Paginated<Exam>>('/exams', { params }),
  getById: (id: number) => api.get<Exam>(`/exams/${id}`),
  create: (data: { subject_id: number; title: string; description?: string; total_marks: number; time_limit_minutes: number; available_from?: string | null; available_until?: string | null }) =>
    api.post<Exam>('/exams', data),
  update: (id: number, data: Partial<Exam>) => api.put<Exam>(`/exams/${id}`, data),
  delete: (id: number) => api.delete(`/exams/${id}`),
};

// ---- Questions ----
export const questionsApi = {
  getAll: (params?: PaginationParams & { exam_id?: number }) =>
    api.get<Paginated<Question>>('/questions', { params }),
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
  getMyAnswers: (params?: PaginationParams & { exam_id?: number }) =>
    api.get<Paginated<Answer>>('/answers/my-answers', { params }),
  /** All student answers for one question (teacher only). */
  getByQuestion: (questionId: number, params?: PaginationParams) =>
    api.get<Paginated<Answer>>(`/answers/question/${questionId}`, { params }),
  getAllAnswers: (params?: PaginationParams & { exam_id?: number; question_id?: number; student_id?: number }) =>
    api.get<Paginated<Answer>>('/answers', { params }),
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
  exportResultsPdf: (examId: number) =>
    api.get(`/export/results/${examId}/pdf`, { responseType: 'blob' }),
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
