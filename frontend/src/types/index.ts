export type UserRole = 'student' | 'teacher' | 'admin';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  profile_photo?: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface Subject {
  id: number;
  name: string;
  description: string;
  teacher_id: number;
  teacher?: User;
  teacher_name?: string;
  exam_count?: number;
  total_students?: number;
  created_at: string;
}

export interface Exam {
  id: number;
  title: string;
  description: string;
  subject_id: number;
  subject?: Subject;
  time_limit_minutes: number;
  total_marks: number;
  is_active: boolean;
  created_at: string;
  questions?: Question[];
}

export interface Question {
  id: number;
  exam_id: number;
  question_text: string;
  model_answer: string;
  marks: number;
  keywords: string[];
  created_at: string;
}

export interface Score {
  id: number;
  answer_id: number;
  keyword_score: number;
  similarity_score: number;
  grammar_score: number;
  completeness_score: number;
  total_score: number;
  feedback: string;
  is_overridden: boolean;
  overridden_by: number | null;
  overridden_at: string | null;
}

export interface Answer {
  id: number;
  question_id: number;
  student_id: number;
  answer_text: string;
  submitted_at: string;
  score?: Score;
  question?: Question;
  student?: User;
}

export interface ExamSubmission {
  answers: { question_id: number; answer_text: string }[];
}

export interface ScoreOverride {
  total_score: number;
  feedback: string;
}

export interface StudentDashboard {
  total_exams_taken: number;
  average_score: number;
  highest_score: number;
  lowest_score: number;
  recent_scores: { label: string; value: number }[];
  subject_scores: { label: string; value: number }[];
}

export interface RecentSubmissionResponse {
  student_id: number;
  student_name: string;
  question_id: number;
  total_score: number;
}

export interface TeacherDashboard {
  total_subjects: number;
  total_exams_created: number;
  total_students: number;
  total_submissions: number;
  average_class_score: number;
  subject_stats: { label: string; value: number }[];
  recent_submissions: RecentSubmissionResponse[];
}

export interface AdminDashboard {
  total_users: number;
  total_students: number;
  total_teachers: number;
  total_subjects: number;
  total_exams: number;
  total_questions: number;
  total_submissions: number;
  average_system_score: number;
  recent_registrations: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PlagiarismResult {
  answer_idx_1: number;
  answer_idx_2: number;
  similarity: number;
  flagged: boolean;
  question_id?: number;
  question_text?: string;
  student_1_id?: number;
  student_2_id?: number;
}

export interface AIDetectionResult {
  ai_probability: number;
  perplexity: number;
  burstiness: number;
  vocabulary_richness: number;
  ai_phrases_found: string[];
  flagged: boolean;
}
